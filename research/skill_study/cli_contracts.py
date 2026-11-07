"""Restricted static CLI contracts, with a trusted argparse reconstruction.

No source module is imported or executed. Unsupported/dynamic declarations are
unknown. A consistent command is not a runtime-success or security certificate.
"""

from __future__ import annotations

import argparse
import ast
import re
import shlex
from dataclasses import dataclass
from typing import Any, NoReturn


@dataclass(frozen=True)
class Option:
    names: tuple[str, ...]
    required: bool
    choices: tuple[Any, ...] | None
    value_type: str
    action: str
    line: int

    @property
    def takes_value(self) -> bool:
        return self.action == "store"


@dataclass(frozen=True)
class ParserContract:
    options: tuple[Option, ...]
    unknown_reasons: tuple[str, ...]

    @property
    def by_name(self) -> dict[str, Option]:
        return {name: option for option in self.options for name in option.names}


def parse_contract(text: str, path: str = "source.py") -> ParserContract:
    try:
        tree = ast.parse(text, filename=path)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return ParserContract((), ("syntax_not_supported:" + type(exc).__name__,))
    constructors: set[str] = set()
    unknown, options = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            function = node.value.func
            is_parser = (
                isinstance(function, ast.Attribute)
                and function.attr == "ArgumentParser"
                and isinstance(function.value, ast.Name)
                and function.value.id == "argparse"
            )
            # Imported aliases and parser factories are intentionally unsupported.
            if is_parser:
                constructors.update(t.id for t in node.targets if isinstance(t, ast.Name))
                if any(k.arg == "parents" for k in node.value.keywords):
                    unknown.append("inherited_parser")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"add_subparsers", "set_defaults"}:
                unknown.append("subparser_or_dynamic_defaults")
    if len(constructors) != 1:
        return ParserContract((), ("single_literal_argparse_parser_not_found",))
    parser_name = next(iter(constructors))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument":
            continue
        receiver = node.func.value
        if not isinstance(receiver, ast.Name) or receiver.id != parser_name:
            unknown.append("argument_group_or_foreign_receiver")
            continue
        try:
            names = tuple(ast.literal_eval(n) for n in node.args)
            if not names or any(not isinstance(n, str) or not n.startswith("-") for n in names):
                unknown.append("positional_or_dynamic_argument")
                continue
            keywords = {k.arg: k.value for k in node.keywords}
            action = ast.literal_eval(keywords["action"]) if "action" in keywords else "store"
            required = ast.literal_eval(keywords["required"]) if "required" in keywords else False
            choices = ast.literal_eval(keywords["choices"]) if "choices" in keywords else None
            if "nargs" in keywords or None in keywords:
                raise ValueError("nargs_or_keyword_expansion")
            if action not in {"store", "store_true", "store_false"} or type(required) is not bool:
                raise ValueError("unsupported_action_or_required")
            kind = "str"
            if "type" in keywords:
                type_node = keywords["type"]
                if not isinstance(type_node, ast.Name) or type_node.id not in {"str", "int", "float"}:
                    raise ValueError("untrusted_or_dynamic_type")
                kind = type_node.id
            if choices is not None and (
                not isinstance(choices, (list, tuple))
                or any(type(v) not in {str, int, float} for v in choices)
            ):
                raise ValueError("unsupported_choices")
            options.append(
                Option(
                    names,
                    required,
                    tuple(choices) if choices is not None else None,
                    kind,
                    action,
                    node.lineno,
                )
            )
        except (ValueError, TypeError, KeyError, SyntaxError) as exc:
            unknown.append("declaration_not_literal:" + str(exc)[:80])
    if not options:
        unknown.append("no_literal_options")
    all_names = [n for o in options for n in o.names]
    if len(all_names) != len(set(all_names)):
        unknown.append("duplicate_option_declarations")
    return ParserContract(tuple(options), tuple(sorted(set(unknown))))


def tokenize_arguments(command: str) -> tuple[list[str], str | None]:
    try:
        tokens = shlex.split(command, comments=True)
    except ValueError:
        return [], "shell_quoting_unknown"
    if len(tokens) < 2 or not re.fullmatch(r"python(?:3)?", tokens[0]) or not tokens[1].endswith(".py"):
        return [], "not_a_supported_python_script_command"
    if any(t in {"|", ";", "&&", "||", ">", ">>"} for t in tokens):
        return [], "compound_shell_command"
    if any("$" in t or "`" in t or "<" in t or ">" in t for t in tokens[2:]):
        return [], "shell_expansion_or_placeholder"
    return tokens[2:], None


def check_command(contract: ParserContract, command: str, *, values: bool = True) -> dict[str, Any]:
    tokens, unsupported = tokenize_arguments(command)
    if unsupported or contract.unknown_reasons:
        return {
            "status": "unknown",
            "reasons": [unsupported] if unsupported else list(contract.unknown_reasons),
            "findings": [],
            "runtime_verified": False,
        }
    if any(t in {"--help", "-h"} for t in tokens):
        return {"status": "help_not_task_execution", "findings": [], "runtime_verified": False}
    lookup, present, findings, i = contract.by_name, set(), [], 0
    while i < len(tokens):
        token = tokens[i]
        name, equal, attached = token.partition("=")
        option = lookup.get(name)
        if option is None:
            if token.startswith("-"):
                findings.append({"kind": "option_not_declared", "option": name})
            elif values:
                findings.append({"kind": "unexpected_positional", "value": token})
            i += 1
            continue
        present.add(option.names)
        if not option.takes_value:
            if equal and values:
                findings.append({"kind": "flag_does_not_take_value", "option": name})
            i += 1
            continue
        if equal:
            value = attached
            i += 1
        elif i + 1 < len(tokens) and (
            not tokens[i + 1].startswith("-") or re.fullmatch(r"-\d+|-\d*\.\d+", tokens[i + 1])
        ):
            value = tokens[i + 1]
            i += 2
        else:
            if values:
                findings.append({"kind": "option_value_missing", "option": name})
            i += 1
            continue
        if not values:
            continue
        try:
            converted = {"int": int, "float": float, "str": str}[option.value_type](value)
        except (ValueError, OverflowError):
            findings.append({"kind": "literal_type_mismatch", "option": name, "type": option.value_type})
            continue
        if option.choices is not None and converted not in option.choices:
            findings.append({"kind": "literal_choice_mismatch", "option": name, "value": value})
    if values:
        for option in contract.options:
            if option.required and option.names not in present:
                findings.append({"kind": "required_option_missing", "option": option.names[0]})
    return {
        "status": "inconsistent_static" if findings else "consistent_static",
        "findings": findings,
        "runtime_verified": False,
    }


class ReferenceParseError(ValueError):
    pass


class ReferenceParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ReferenceParseError(message)


def standard_library_reference(contract: ParserContract, command: str) -> str:
    """Run only our reconstructed whitelisted argparse declarations, not source."""
    tokens, unsupported = tokenize_arguments(command)
    if unsupported or contract.unknown_reasons:
        return "unknown"
    if any(t in {"--help", "-h"} for t in tokens):
        return "help_not_task_execution"
    parser = ReferenceParser(add_help=False, allow_abbrev=False)
    for option in contract.options:
        kwargs: dict[str, Any] = {"required": option.required, "action": option.action}
        if option.takes_value:
            kwargs["type"] = {"str": str, "int": int, "float": float}[option.value_type]
            if option.choices is not None:
                kwargs["choices"] = option.choices
        parser.add_argument(*option.names, **kwargs)
    try:
        parser.parse_args(tokens)
    except ReferenceParseError:
        return "inconsistent_static"
    return "consistent_static"

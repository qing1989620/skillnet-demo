from __future__ import annotations

from pathlib import Path

import pytest

from research.skill_study.cli_contracts import (
    check_command,
    parse_contract,
    standard_library_reference,
)
from research.skill_study.package_audit import commands
from research.skill_study.quality_pilot import variants

SOURCE = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--file', '-f', required=True)
parser.add_argument('--format', choices=['json', 'csv'])
parser.add_argument('--threshold', type=float)
parser.add_argument('--verbose', action='store_true')
"""


@pytest.mark.parametrize(
    "arguments,expected",
    [
        ("--file input.csv --format json", "consistent_static"),
        ("-f input.csv --format=csv --threshold -2.5", "consistent_static"),
        ("--file input.csv --verbose", "consistent_static"),
        ("--file input.csv --format impossible", "inconsistent_static"),
        ("--file input.csv --threshold nope", "inconsistent_static"),
        ("--format json", "inconsistent_static"),
        ("--file input.csv --invented", "inconsistent_static"),
        ("--file", "inconsistent_static"),
        ("--file --undeclared", "inconsistent_static"),
        ("--file input.csv --verbose=yes", "inconsistent_static"),
    ],
)
def test_literal_contract_matches_independent_argparse(arguments: str, expected: str) -> None:
    contract = parse_contract(SOURCE)
    command = "python3 scripts/a.py " + arguments
    assert check_command(contract, command)["status"] == expected
    assert standard_library_reference(contract, command) == expected
    assert not check_command(contract, command)["runtime_verified"]


def test_new_constraints_do_not_appear_in_option_presence_baseline() -> None:
    contract = parse_contract(SOURCE)
    for command in ["python3 a.py --file x --format impossible", "python3 a.py --format json"]:
        assert check_command(contract, command, values=False)["status"] == "consistent_static"
        assert check_command(contract, command)["status"] == "inconsistent_static"


@pytest.mark.parametrize(
    "extra",
    [
        "parser.add_argument(*runtime_options)\n",
        "parser.add_argument('--x', type=custom_function)\n",
        "parser.add_argument('--x', choices=compute_choices())\n",
        "parser.add_subparsers()\n",
        "parser.add_argument('positional')\n",
    ],
)
def test_unsupported_is_unknown(extra: str) -> None:
    contract = parse_contract(SOURCE + extra)
    assert check_command(contract, "python3 a.py --file x")["status"] == "unknown"


def test_source_never_executes(tmp_path: Path) -> None:
    marker = tmp_path / "must_not_be_created"
    contract = parse_contract(SOURCE + f"\nopen({str(marker)!r}, 'w').write('executed')\n")
    assert check_command(contract, "python3 a.py --file x")["status"] == "consistent_static"
    assert not marker.exists()


def test_variants_have_independent_known_outcomes_even_with_alias_repeats() -> None:
    contract = parse_contract(SOURCE)
    command = "python3 a.py --file x -f y --format json --threshold 1.0"
    for kind, changed, defect in variants(command, contract):
        result = standard_library_reference(contract, changed)
        assert (result == "inconsistent_static") == defect, kind


def test_multiline_examples_keep_original_coordinates() -> None:
    text = "example\npython3 scripts/a.py --file x \\\n+    --format json\nother\n"
    found = commands(text)
    assert len(found) == 1
    assert found[0]["start_line"] == 2 and found[0]["end_line"] == 3
    assert "--format json" in found[0]["command"]


def test_shell_operations_are_unknown_and_never_executed() -> None:
    contract = parse_contract(SOURCE)
    for command in ["python3 a.py --file x && remove-anything", "python3 a.py --file $SECRET"]:
        assert check_command(contract, command)["status"] == "unknown"


def test_shell_comment_is_not_a_positional_argument_and_hash_in_quotes_is_data() -> None:
    contract = parse_contract(SOURCE)
    for command in ["python3 a.py --file x # explanatory comment", 'python3 a.py --file "x#data.csv"']:
        assert check_command(contract, command)["status"] == "consistent_static"
        assert standard_library_reference(contract, command) == "consistent_static"
        assert all(
            standard_library_reference(contract, changed)
            == ("inconsistent_static" if bad else "consistent_static")
            for _, changed, bad in variants(command, contract)
        )

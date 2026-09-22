"""DeepSeek LLM 客户端：统一调用、JSON 输出、token 与成本记账。

整个 demo 的成本核算都走这里，方便做「优化成本」对比（对标 COBRA-Skills 表 2）。
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import config

log = logging.getLogger("skillnet.llm")


@dataclass
class UsageLedger:
    """全局 token / 成本账本，按角色（teacher / worker / judge）分账。"""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    by_role: dict[str, dict[str, float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, role: str, pt: int, ct: int) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += pt
            self.completion_tokens += ct
            slot = self.by_role.setdefault(
                role, {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}
            )
            slot["calls"] += 1
            slot["prompt"] += pt
            slot["completion"] += ct
            slot["cost"] += pt / 1e6 * config.PRICE_IN + ct / 1e6 * config.PRICE_OUT

    @property
    def cost_yuan(self) -> float:
        return (
            self.prompt_tokens / 1e6 * config.PRICE_IN
            + self.completion_tokens / 1e6 * config.PRICE_OUT
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "cost_yuan": round(self.cost_yuan, 4),
            "by_role": {
                k: {
                    "calls": v["calls"],
                    "prompt": v["prompt"],
                    "completion": v["completion"],
                    "cost_yuan": round(v["cost"], 4),
                }
                for k, v in self.by_role.items()
            },
        }

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.by_role.clear()


LEDGER = UsageLedger()
"""进程级默认账本。脚本 / 实验（bench、verify）直接用这一个即可。"""

_CTX: contextvars.ContextVar["UsageLedger | None"] = contextvars.ContextVar(
    "skillnet_ledger", default=None
)


def current_ledger() -> UsageLedger:
    """返回当前上下文的账本；不在任何 scope 内时回落到进程级默认账本。

    为什么需要这个：服务端是并发处理请求的。如果所有请求都往同一个全局账本里记账、
    又各自在开头 reset()，那么并发下每个请求返回的成本数字都是错的
    （A 请求会把 B 请求的 token 算进自己的账单，反之亦然）。
    用请求级账本后，每个请求只统计自己触发的调用。
    """
    return _CTX.get() or LEDGER


@contextlib.contextmanager
def ledger_scope(ledger: "UsageLedger | None" = None):
    """在一个作用域内隔离记账。FastAPI 的同步路由跑在线程池里，
    contextvars 会随请求复制，因此该作用域内的所有调用都记到同一个账本。"""
    led = ledger if ledger is not None else UsageLedger()
    token = _CTX.set(led)
    try:
        yield led
    finally:
        _CTX.reset(token)


class LLMError(RuntimeError):
    pass


_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=config.BASE_URL,
            headers={"Authorization": f"Bearer {config.API_KEY}"},
            timeout=httpx.Timeout(180.0, connect=20.0),
        )
    return _client


def chat(
    messages: list[dict[str, str]],
    *,
    role: str = "worker",
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str | None = None,
    retries: int = 3,
) -> str:
    """调用一次 chat completion，返回 assistant 文本。"""
    if not config.API_KEY:
        raise LLMError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置")

    payload = {
        "model": model or config.MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _get_client().post("/chat/completions", json=payload)
            if resp.status_code >= 400:
                raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            usage = data.get("usage") or {}
            current_ledger().record(
                role,
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
            )
            return data["choices"][0]["message"]["content"] or ""
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise LLMError(f"LLM 调用失败: {last_err}")


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def repair_truncated_json(text: str) -> str:
    """修复被 max_tokens 截断的 JSON：补全未闭合的字符串与括号。

    生成式模型在输出长 JSON 时很容易撞到 max_tokens 上限，
    此时尾部会停在半个字段上。直接丢弃整份输出代价太大，
    这里做一次「扫描 + 补括号」的尽力修复。
    """
    out: list[str] = []
    stack: list[str] = []
    in_str = False
    esc = False
    for ch in text:
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\" and in_str:
            out.append(ch)
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            out.append(ch)
            continue
        if in_str:
            out.append(ch)
            continue
        if ch in "{[":
            stack.append(ch)
            out.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            out.append(ch)
        else:
            out.append(ch)
    s = "".join(out).rstrip()
    if in_str:
        s += '"'
    while s and s[-1] in ",: \n\t":
        s = s[:-1].rstrip()
    for open_ch in reversed(stack):
        s += "}" if open_ch == "{" else "]"
    return s


def extract_json(text: str) -> Any:
    """从模型输出里稳健地抠出 JSON 对象/数组（含截断修复）。"""
    if not text:
        raise ValueError("空输出")
    m = _JSON_BLOCK.search(text)
    if m:
        text = m.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            chunk = text[start : end + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                # 容忍尾随逗号
                fixed = re.sub(r",\s*([}\]])", r"\1", chunk)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    continue
    # 最后一道：当作被截断处理。
    # 单次补括号常常不够——截断点可能正好落在一个无意义的位置（比如数字中间、
    # 或某个键名之后），补出来的串仍然非法。因此从尾部逐步回退，
    # 直到能解析出「前缀的完整部分」为止。实测这一步能把被截断的
    # 研究方案抢救回可用状态，而不是整份丢弃。
    start = text.find("{")
    if start != -1:
        body = text[start:]
        step = max(1, len(body) // 80)
        for cut in range(len(body), 0, -step):
            try:
                return json.loads(repair_truncated_json(body[:cut]))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"无法解析 JSON: {text[:200]}")


def chat_json(
    messages: list[dict[str, str]],
    *,
    role: str = "worker",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    model: str | None = None,
    default: Any = None,
) -> Any:
    """调用并解析 JSON；解析失败时返回 default（不中断整条流程）。

    失败时记录一行日志。只有当环境变量 `SKILLNET_DEBUG=1` 时才把模型原文落盘——
    默认不落盘，因为并发下多请求会互相覆盖同一个文件，
    而且原文里可能含有用户的研究内容，不该默认写进磁盘。
    """
    raw = ""
    try:
        raw = chat(
            messages,
            role=role,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        return extract_json(raw)
    except Exception as exc:  # noqa: BLE001
        if default is None:
            raise
        log.warning("LLM JSON 解析失败 role=%s err=%s raw_len=%d", role, exc, len(raw))
        if os.environ.get("SKILLNET_DEBUG") == "1":
            try:
                dump = config.OUT_DIR / f"_llm_raw_{os.getpid()}_{int(time.time())}.txt"
                dump.write_text(
                    f"[{type(exc).__name__}] {exc}\n\n---- RAW ({len(raw)} chars) ----\n{raw}",
                    encoding="utf-8",
                )
            except OSError:
                pass
        return default

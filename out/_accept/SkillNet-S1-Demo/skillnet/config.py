"""全局配置：读取 .env，暴露 LLM 与路径常量。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

SEED_DIR = ROOT / "seed" / "skills"
OUT_DIR = ROOT / "out"
DATA_DIR = ROOT / "data"
LIBRARY_FILE = DATA_DIR / "library.json"

# DeepSeek 官方定价（元 / 百万 token，缓存未命中输入 / 输出）
PRICE_IN = 2.0
PRICE_OUT = 8.0

for d in (OUT_DIR, DATA_DIR, SEED_DIR):
    d.mkdir(parents=True, exist_ok=True)

#!/usr/bin/env bash
# SkillNet-S1 · 面向科研 Agent 的技能运维层 —— 一键启动（macOS / Linux）
set -u
cd "$(dirname "$0")"

echo
echo "  =========================================================="
echo "    SkillNet-S1  ·  面向科研 Agent 的技能运维层  演示程序"
echo "  =========================================================="
echo

# ---------- 1. 选择 Python ----------
# 先挑已经装好依赖的解释器，避免在多 Python 环境下误选到干净的解释器重复安装依赖
PY=""
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 \
       && "$cand" -c 'import fastapi, uvicorn, httpx, pydantic, numpy' >/dev/null 2>&1; then
      PY="$cand"; break
    fi
  done
  if [ -z "$PY" ]; then
    for cand in python3 python; do
      if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
    done
  fi
fi

if [ -z "$PY" ]; then
  echo "  [错误] 未找到 Python。请安装 Python 3.10 或更高版本。"
  echo "         https://www.python.org/downloads/"
  exit 1
fi

# ---------- 2. 版本检查 ----------
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "  [错误] Python 版本过低，需要 3.10 或更高。当前：$("$PY" -V 2>&1)"
  exit 1
fi
echo "  [1/4] $("$PY" -V 2>&1)  已就绪"

# ---------- 3. 依赖 ----------
if ! "$PY" -c 'import fastapi, uvicorn, httpx, pydantic, numpy' >/dev/null 2>&1; then
  echo "  [2/4] 正在安装依赖，首次运行需联网，请稍候..."
  if ! "$PY" -m pip install -q -r requirements.txt; then
    echo
    echo "  [错误] 依赖安装失败。可尝试手动执行："
    echo "         $PY -m pip install -r requirements.txt"
    exit 1
  fi
  if ! "$PY" -c 'import fastapi, uvicorn, httpx, pydantic, numpy' >/dev/null 2>&1; then
    echo "  [错误] 依赖仍未就绪，请检查网络或 Python 环境。"
    exit 1
  fi
  echo "  [2/4] 依赖安装完成"
else
  echo "  [2/4] 依赖已就绪"
fi

# ---------- 4. 模型密钥（可选） ----------
KEYOK=0
if [ -f ".env" ]; then
  if "$PY" - <<'PYEOF' >/dev/null 2>&1
import pathlib, re
t = pathlib.Path(".env").read_text(encoding="utf-8")
m = re.search(r"DEEPSEEK_API_KEY=(\S+)", t)
raise SystemExit(0 if (m and "xxxx" not in m.group(1)) else 1)
PYEOF
  then KEYOK=1; fi
fi

if [ "$KEYOK" -eq 0 ]; then
  [ -f ".env" ] || cp .env.example .env 2>/dev/null
  echo "  [3/4] 未配置模型密钥 —— 技能库 / 检索 / 关系图 / 实验结果 可正常使用；"
  echo "        路由、执行、进化、一键演示 需在 .env 中填入 DEEPSEEK_API_KEY"
else
  echo "  [3/4] 模型密钥已配置"
fi

# ---------- 5. 启动 ----------
echo "  [4/4] 正在启动服务..."
echo
echo "  访问地址： http://127.0.0.1:8848"
echo "  浏览器会自动打开；按 Ctrl+C 停止服务。"
echo

exec "$PY" run.py

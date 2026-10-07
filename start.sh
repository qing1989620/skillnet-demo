#!/usr/bin/env bash
# SkillNet-S1 Demo 一键启动（macOS / Linux）
set -u
echo "============================================"
echo "  SkillNet-S1 Demo 一键启动"
echo "============================================"
PY_EXE=""
for C in python3 python; do
  if command -v "$C" >/dev/null 2>&1 && "$C" -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"; then
    PY_EXE="$C"; break
  fi
done
[ -z "$PY_EXE" ] && { echo "[错误] 未找到 Python 3.11+，请先安装。"; exit 1; }
echo "[1/3] 使用解释器: $PY_EXE"
echo "[2/3] 检查依赖..."
"$PY_EXE" -c "import fastapi, uvicorn, httpx, pydantic, numpy, pandas, matplotlib, openpyxl" 2>/dev/null || {
  "$PY_EXE" -m pip install -r requirements.txt || { echo "[错误] 依赖安装失败"; exit 1; }
}
echo "[3/3] 启动 http://127.0.0.1:8848 （Ctrl+C 退出）"
"$PY_EXE" run.py

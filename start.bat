@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0"

echo.
echo   ==========================================================
echo     SkillNet-S1  ·  面向科研 Agent 的技能运维层  演示程序
echo   ==========================================================
echo.

rem ---------- 1. 选择 Python 解释器 ----------
rem 策略：先挑「已经装好依赖」的解释器，避免在多 Python 环境下
rem 误选到一个干净的解释器、再去重复安装一遍依赖。
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY (
  py -3 -c "import fastapi,uvicorn,httpx,pydantic,numpy" >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  python -c "import fastapi,uvicorn,httpx,pydantic,numpy" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  python3 -c "import fastapi,uvicorn,httpx,pydantic,numpy" >nul 2>&1
  if not errorlevel 1 set "PY=python3"
)
rem 一个都没有依赖，就挑第一个可用的解释器，稍后统一安装
if not defined PY (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  python3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=python3"
)
if not defined PY (
  echo   [错误] 未找到 Python。
  echo.
  echo     请安装 Python 3.10 或更高版本，安装时务必勾选
  echo     "Add Python to PATH"。下载地址：
  echo     https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

rem ---------- 2. 版本检查 ----------
%PY% -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo   [错误] Python 版本过低，需要 3.10 或更高。当前：
  %PY% -V
  pause
  exit /b 1
)
for /f "delims=" %%v in ('%PY% -c "import sys;print(sys.version.split()[0])"') do set "PYVER=%%v"
echo   [1/4] Python %PYVER%  已就绪

rem ---------- 3. 依赖 ----------
%PY% -c "import fastapi,uvicorn,httpx,pydantic,numpy" >nul 2>&1
if errorlevel 1 (
  echo   [2/4] 正在安装依赖，首次运行需联网，请稍候...
  %PY% -m pip install -q -r requirements.txt
  %PY% -c "import fastapi,uvicorn,httpx,pydantic,numpy" >nul 2>&1
  if errorlevel 1 (
    echo.
    echo   [错误] 依赖安装失败。可尝试手动执行：
    echo          %PY% -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
  )
) else (
  echo   [2/4] 依赖已就绪
)

rem ---------- 4. 模型密钥（可选） ----------
set "KEYOK="
if exist "%~dp0.env" (
  %PY% -c "import re,pathlib;t=pathlib.Path('.env').read_text(encoding='utf-8');m=re.search(r'DEEPSEEK_API_KEY=(\S+)',t);raise SystemExit(0 if (m and 'xxxx' not in m.group(1)) else 1)" >nul 2>&1
  if not errorlevel 1 set "KEYOK=1"
)
if not defined KEYOK (
  if not exist "%~dp0.env" copy "%~dp0.env.example" "%~dp0.env" >nul 2>&1
  echo   [3/4] 未配置模型密钥 —— 技能库 / 检索 / 关系图 / 实验结果 可正常使用；
  echo         路由、执行、进化、一键演示 需在 .env 中填入 DEEPSEEK_API_KEY
) else (
  echo   [3/4] 模型密钥已配置
)

rem ---------- 5. 启动 ----------
echo   [4/4] 正在启动服务...
echo.
echo   访问地址： http://127.0.0.1:8848
echo   浏览器会自动打开；关闭本窗口即停止服务。
echo.

%PY% run.py
echo.
echo   服务已停止。
pause

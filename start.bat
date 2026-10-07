@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title SkillNet-S1 Demo

echo ============================================
echo   SkillNet-S1 Demo 一键启动
echo ============================================
echo [1/4] 挑选 Python 解释器...

set PY_EXE=
for %%P in (python py -3 python3) do (
    if not defined PY_EXE (
        %%P -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 set PY_EXE=%%P
    )
)
if not defined PY_EXE (
    echo [错误] 未找到 Python 3.11+，请先安装：https://www.python.org/downloads/
    echo        安装时勾选 "Add Python to PATH"。
    pause & exit /b 1
)
echo       使用解释器: !PY_EXE!

echo [2/4] 检查并安装依赖（首次运行约 1-2 分钟）...
!PY_EXE! -c "import fastapi, uvicorn, httpx, pydantic, numpy, pandas, matplotlib, openpyxl" >nul 2>&1
if not !errorlevel! equ 0 (
    !PY_EXE! -m pip install -r requirements.txt
    if not !errorlevel! equ 0 (
        echo [错误] 依赖安装失败，请检查网络后重试，或手动执行：
        echo        !PY_EXE! -m pip install -r requirements.txt
        pause & exit /b 1
    )
)
echo       依赖就绪。

echo [3/4] 检查配置...
if exist .env (
    findstr /C:"DEEPSEEK_API_KEY=sk" .env >nul 2>&1
    if !errorlevel! equ 0 (
        echo       已检测到 API 密钥：全部功能可用（含真实执行/进化）。
    ) else (
        echo       未填密钥：浏览/检索/星图/导出可用；真实执行需密钥（见 快速开始.txt）。
    )
) else (
    echo       未找到 .env：浏览/检索/星图/导出可用；真实执行需密钥（见 快速开始.txt）。
)

echo [4/4] 启动服务并打开浏览器（Ctrl+C 退出）...
start "" http://127.0.0.1:8848/
!PY_EXE! run.py --no-browser
pause

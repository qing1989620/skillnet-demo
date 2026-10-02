# -*- coding: utf-8 -*-
"""sandbox.py —— 受控代码执行沙箱。

为什么必须要有这一层
--------------------
Agent Skills 的官方定义把技能视为**可执行的程序性知识**：技能可以附带脚本，
由执行环境运行，只有输出进入上下文——「用 token 生成给列表排序，比直接跑排序算法
贵得多」。确定性操作交给代码，是技能区别于提示词的根本。

本项目此前的「执行」只是一次 LLM 调用产出方案文本，全程零代码运行，
因此产物必然停留在「作文」层面。本模块补上执行能力，使闭环真正闭合：
**生成代码 → 真实运行 → 捕获输出与产物 → 失败则带错误修复重试（Run→Validate→Fix）**。

安全边界（务实而非完备，必须显式声明）
--------------------------------------
- 子进程 + 独立临时工作目录，超时强制 kill；
- 环境变量白名单化（不继承 API Key 等敏感变量）；
- 不主动授予网络能力（但**无法在内核层面阻断**——本沙箱面向可信模型产出的
  分析代码，不是对抗性代码的隔离工具；生产环境应换容器/虚拟机级隔离，
  本模块 docstring 与 README 均已标注该边界）；
- 产物只收集工作目录内的新文件。
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

# 允许出现在沙箱环境里的变量（最小集：解释器自身需要，不含任何凭据）
_ENV_ALLOW = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT",
              "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "LANG", "LC_ALL")

# 产物收集：这些扩展名视为可交付文件
ARTIFACT_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".csv", ".txt",
                 ".json", ".md", ".html", ".xlsx", ".npy"}

MAX_OUTPUT_CHARS = 6000


def _clean_env(workdir: pathlib.Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _ENV_ALLOW}
    # 模型代码常需要临时目录可写；同时把 HOME 指向工作目录，避免污染用户目录
    env["TMPDIR"] = str(workdir)
    env["TEMP"] = str(workdir)
    env["TMP"] = str(workdir)
    env["HOME"] = str(workdir)
    env["MPLBACKEND"] = "Agg"                  # 无显示环境下绘图
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["MPLCONFIGDIR"] = str(workdir / ".mpl")   # 避免写入用户 matplotlib 缓存
    return env


def _safe_unlink(p: pathlib.Path) -> None:
    try:
        p.unlink()
    except OSError:
        pass


def run_python(code: str, timeout: int = 90, keep_dir: bool = False,
               workdir: pathlib.Path | None = None) -> dict[str, Any]:
    """执行一段 Python 代码，返回结构化结果。

    返回：
      ok        是否成功（退出码 0）
      stdout/stderr  截断后的输出文本
      returncode
      duration  秒
      artifacts [{name, bytes, path}]  运行期间在工作目录新生成的文件
      error_kind "timeout" | "exception" | "import" | ""（便于上层给修复提示）
      workdir   工作目录（keep_dir=True 时保留，便于人工复核）
    """
    tmp = pathlib.Path(workdir).resolve() if workdir else pathlib.Path(
        tempfile.mkdtemp(prefix="skillnet_sbx_"))
    tmp.mkdir(parents=True, exist_ok=True)
    script = tmp / "main.py"
    script.write_text(code, encoding="utf-8")
    before = {p.name for p in tmp.iterdir()}

    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(script)],     # -I: 隔离模式，忽略用户 site-packages 配置
            cwd=str(tmp), capture_output=True, text=True,
            timeout=timeout, env=_clean_env(tmp), encoding="utf-8", errors="replace",
        )
        rc, out, err = proc.returncode, proc.stdout or "", proc.stderr or ""
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc, timed_out = -1, True
        out = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = f"执行超时（超过 {timeout}s 被强制终止）"
    duration = round(time.time() - t0, 2)

    # 收集新产生的产物文件（排除脚本自身与缓存）
    artifacts: list[dict[str, Any]] = []
    for p in sorted(tmp.rglob("*")):
        if not p.is_file() or p.name in before or p.name == "main.py":
            continue
        if ".mpl" in p.parts or "__pycache__" in p.parts:
            continue
        if p.suffix.lower() not in ARTIFACT_EXTS:
            continue
        rel = p.relative_to(tmp).as_posix()
        artifacts.append({"name": rel, "bytes": p.stat().st_size, "path": str(p)})

    out_t = out[-MAX_OUTPUT_CHARS:] if len(out) > MAX_OUTPUT_CHARS else out
    err_t = err[-MAX_OUTPUT_CHARS:] if len(err) > MAX_OUTPUT_CHARS else err

    # 失败分类：给上层修复提示用（不同错误要用不同策略）
    kind = ""
    low = err_t.lower()
    if timed_out:
        kind = "timeout"
    elif rc != 0:
        if "modulenotfounderror" in low or "no module named" in low:
            kind = "import"
        elif "syntaxerror" in low or "indentationerror" in low:
            kind = "syntax"
        else:
            kind = "exception"

    result = {
        "ok": rc == 0 and not timed_out,
        "stdout": out_t, "stderr": err_t, "returncode": rc,
        "duration": duration, "artifacts": artifacts,
        "error_kind": kind, "workdir": str(tmp),
    }
    if not keep_dir and not artifacts:
        # 没有产物且不要求保留 -> 清理（有产物时保留，供 /api 预览）
        shutil.rmtree(tmp, ignore_errors=True)
        result["workdir"] = ""
    return result


def detect_missing_imports(stderr: str) -> list[str]:
    """从错误输出里提取缺失的第三方包名（用于给出可执行的修复建议）。"""
    names = set()
    for m in re.finditer(r"No module named ['\"]([A-Za-z0-9_.]+)['\"]", stderr or ""):
        names.add(m.group(1).split(".")[0])
    return sorted(names)


# 本机可用的科学计算栈（用于告诉模型：只能用这些，别 import 不存在的包）
def available_stack() -> dict[str, str]:
    """探测沙箱内可用的第三方库版本，供提示词约束生成代码。"""
    import importlib
    out: dict[str, str] = {}
    for name in ("numpy", "matplotlib", "scipy", "pandas", "sympy", "sklearn", "statsmodels"):
        try:
            mod = importlib.import_module(name)
            out[name] = getattr(mod, "__version__", "?")
        except ImportError:
            continue
    return out


MATPLOTLIB_CJK_HINT = (
    "# 中文字体（本机可用 Microsoft YaHei / SimHei）\n"
    "import matplotlib\n"
    "matplotlib.use('Agg')\n"
    "import matplotlib.pyplot as plt\n"
    "plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']\n"
    "plt.rcParams['axes.unicode_minus'] = False\n"
)

# -*- coding: utf-8 -*-
"""SkillNet-S1 交付打包：源码 + 文档 + 证据数据 → 单个 zip。

黑名单过滤（.env/密钥/中间产物），顶层套语义目录，只带证据不带调试垃圾。
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # skillnet-demo/
DEST = ROOT.parent / "SkillNet-S1-Demo.zip"
TOP = "SkillNet-S1-Demo"

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules",
                ".workbuddy", "out", ".e_b0", ".e_b1", ".idea", ".vscode"}
EXCLUDE_FILES = {".env", "desktop.ini", "Thumbs.db"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".log", ".tmp"}

# out/ 下只带证据：bench JSON + final_shots 截图 + 两个展示 run（json + artifacts）
OUT_INCLUDE = [
    ("out/bench", ["*.json"]),
    ("out/final_shots", ["*.png"]),
    ("out/runs/53e9d927-20261002-140122-0176", ["run.json", "artifacts/*"]),
    ("out/runs/b5bf6a46-20261002-130540-f1e3", ["run.json", "artifacts/*"]),
]


def excluded(p: Path, respect_dir_exclude: bool = True) -> bool:
    if p.name in EXCLUDE_FILES or p.suffix in EXCLUDE_SUFFIX:
        return True
    if not respect_dir_exclude:
        return False
    return any(part in EXCLUDE_DIRS for part in p.parts)


def main() -> None:
    assert (ROOT / "server.py").exists(), "请在 skillnet-demo 目录下运行"
    n = 0
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # 顶层直接放的关键文件
        for name in ("快速开始.txt", "README.md", "requirements.txt",
                     "start.bat", "start.sh", "run.py", "server.py", "verify.py",
                     ".env.example", ".gitignore"):
            src = ROOT / name
            if src.exists():
                z.write(src, f"{TOP}/{name}"); n += 1
        # 目录树
        for d in ("skillnet", "seed", "tasks", "tests", "tools", "web", "docs", "data"):
            base = ROOT / d
            for p in sorted(base.rglob("*")):
                if p.is_dir() or excluded(p):
                    continue
                z.write(p, f"{TOP}/{p.relative_to(ROOT).as_posix()}"); n += 1
        # out/ 证据（白名单式：绕过目录级排除，仅做文件级过滤）
        for rel, pats in OUT_INCLUDE:
            base = ROOT / rel
            if not base.exists():
                continue
            for p in sorted(base.rglob("*")):
                if not p.is_file() or excluded(p, respect_dir_exclude=False):
                    continue
                ok = any(p.match(pat) for pat in pats)
                if ok:
                    z.write(p, f"{TOP}/{p.relative_to(ROOT).as_posix()}"); n += 1
    mb = DEST.stat().st_size / 1024 / 1024
    print(f"打包完成：{DEST}")
    print(f"  文件数 {n} · 大小 {mb:.1f} MB")


if __name__ == "__main__":
    main()

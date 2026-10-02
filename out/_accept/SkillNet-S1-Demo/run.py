"""一键启动 SkillNet-S1 Demo。

    python run.py                # 默认 127.0.0.1:8848
    python run.py --port 9000
"""
from __future__ import annotations

import argparse
import webbrowser

import uvicorn

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"SkillNet-S1 Demo 启动中 → {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    uvicorn.run("server:app", host=args.host, port=args.port, log_level="warning")

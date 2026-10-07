"""一键启动 SkillNet-S1 Demo。

    python run.py                # 默认 127.0.0.1:8848
    python run.py --port 9000
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import webbrowser

import uvicorn
from skillnet import config  # Load .env before validating network exposure.

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    try:
        is_local = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        is_local = args.host.lower() == "localhost"
    if not is_local and not os.environ.get("SKILLNET_TOKEN", "").strip():
        ap.error("监听非本机地址需要设置 SKILLNET_TOKEN；本机演示可使用默认 127.0.0.1")

    url = f"http://{args.host}:{args.port}"
    print(f"SkillNet-S1 Demo 启动中 → {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    uvicorn.run("server:app", host=args.host, port=args.port, log_level="warning")

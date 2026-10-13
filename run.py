"""一键启动 SkillNet-S1 Demo。

    python run.py                # 默认 127.0.0.1:8848
    python run.py --port 9000
"""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import json
import socket
import threading
import time
from urllib.request import urlopen
import webbrowser

import uvicorn
from skillnet import config  # Load .env before validating network exposure.

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--version", action="store_true", help="Print release and Git identity")
    args = ap.parse_args()
    from skillnet.distribution import build_identity
    identity = build_identity()
    if args.version:
        print(json.dumps(identity, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    try:
        is_local = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        is_local = args.host.lower() == "localhost"
    if not is_local and not os.environ.get("SKILLNET_TOKEN", "").strip():
        ap.error("监听非本机地址需要设置 SKILLNET_TOKEN；本机演示可使用默认 127.0.0.1")

    url_host = f'[{args.host}]' if ':' in args.host else args.host
    url = f"http://{url_host}:{args.port}"
    # Bind before opening the browser so a stale service is never mistaken for
    # this process after an address-in-use error.
    listener = socket.socket(socket.AF_INET6 if ':' in args.host else socket.AF_INET, socket.SOCK_STREAM)
    if os.name == 'nt' and hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        listener.bind((args.host, args.port))
        listener.listen(128)
        listener.setblocking(False)
    except OSError as exc:
        listener.close()
        ap.error(f"端口 {args.port} 无法启动：{exc}。已有服务可能来自旧目录，请先关闭该服务，或使用 --port 9000。")
    print(f"项目目录：{Path(__file__).resolve().parent}")
    print(f"交付版本：{identity['release']} · Git：{identity['git_commit'] or 'source archive'}")
    print(f"SkillNet-S1 Demo 启动中 → {url}")
    if not args.no_browser:
        def open_when_ready():
            host = '127.0.0.1' if args.host == '0.0.0.0' else ('[::1]' if args.host == '::' else url_host)
            for _ in range(120):
                try:
                    with urlopen(f'http://{host}:{args.port}/api/health', timeout=1) as response:
                        ready = json.load(response)
                    if ready.get('distribution', {}).get('backend_sha256') == identity['backend_sha256']:
                        webbrowser.open(f'http://{host}:{args.port}')
                        return
                except Exception:
                    pass
                time.sleep(.5)
        threading.Thread(target=open_when_ready, daemon=True).start()
    try:
        uvicorn.Server(uvicorn.Config("server:app", host=args.host, port=args.port,
                                     log_level="warning")).run(sockets=[listener])
    finally:
        listener.close()

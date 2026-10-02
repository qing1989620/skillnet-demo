import json, threading, time, urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8848"
print("health:", urllib.request.urlopen(BASE + "/api/health", timeout=10).status)

body = json.dumps({"task": "对一批剂量-存活率实验数据做清洗与剂量-反应分析，并给出可复现的分析产物",
                   "max_steps": 2, "max_cost_yuan": 0.8, "max_seconds": 240}).encode()
req = urllib.request.Request(BASE + "/api/runs", data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
created = json.load(urllib.request.urlopen(req, timeout=30))
rid = created["run_id"]
print("创建 Run: %s | 返回耗时 %.0fms" % (rid, (time.time() - t0) * 1000))

events, ttfe = [], None
def consume():
    global ttfe
    try:
        with urllib.request.urlopen(BASE + "/api/runs/" + rid + "/stream", timeout=300) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if line == "event: end":
                    break
                if not line.startswith("data: "):
                    continue
                try:
                    ev = json.loads(line[6:])
                except ValueError:
                    continue
                if ev.get("type") == "end":
                    break
                if ttfe is None:
                    ttfe = (time.time() - t0) * 1000
                events.append(ev)
    except Exception as exc:
        print("  SSE 读取异常:", exc)

th = threading.Thread(target=consume, daemon=True); th.start(); th.join(timeout=280)

if ttfe is not None:
    print("\n★ TTFE（首个事件到达）: %.0fms" % ttfe)
else:
    print("\n★ 未收到事件")
print("  事件总数 %d" % len(events))
for k, v in Counter(e["type"] for e in events).most_common():
    print("    %-26s x%d" % (k, v))
print("\n  时间轴前 12 条：")
base_ts = events[0]["ts_ms"] if events else 0
for e in events[:12]:
    d = json.dumps(e.get("data") or {}, ensure_ascii=False)[:74]
    print("    +%6.1fs  %-24s step=%s %s" % ((e["ts_ms"] - base_ts) / 1000, e["type"], e.get("step"), d))

final = json.load(urllib.request.urlopen(BASE + "/api/runs/" + rid, timeout=30))
print("\n  Run 状态: %s | 时长 %.1fs | ¥%s" % (final["status"], final["duration_ms"] / 1000, final["cost_yuan"]))
print("  阶段耗时: %s" % json.dumps(final.get("staged"), ensure_ascii=False))
for s in final["steps"]:
    print("    step%d %s 尝试%d 产物%d 检查%s/%s 验收%s/%s" % (
        s["idx"], s["status"], s["n_attempts"], len(s["artifacts"]),
        s["checks_passed"], s["checks_total"], s["verification_passed"], s["verification_total"]))
print("  产物 %d 个: %s" % (len(final["artifacts"]), [a["name"] for a in final["artifacts"]][:6]))
lst = json.load(urllib.request.urlopen(BASE + "/api/runs?limit=5", timeout=20))
print("\n  Run 历史 %d 条: %s" % (len(lst["runs"]), [(r["run_id"][-13:], r["status"]) for r in lst["runs"][:4]]))

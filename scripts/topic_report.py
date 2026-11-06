#!/usr/bin/env python3
"""Collect topic material for a content creator (workplace / side-hustle).

Runs the installed `agent-reach` CLI and writes:
  /root/topics.md        readable report (title | author | stats | url)
  /root/topics_raw.json  raw items, for debugging

Edit KEYWORDS / HOT_WORDS below to change the field. Prints only ASCII.
"""
import json, subprocess, time, os, re, datetime

AR = os.path.expanduser("~/.local/bin/agent-reach")
OUT_MD = "/root/topics.md"
OUT_RAW = "/root/topics_raw.json"
KEYWORDS = ["副业", "职场", "裸辞", "下班后副业", "AI副业", "35岁职场", "自由职业", "搞钱", "打工人"]
HOT_WORDS = ["工作", "职场", "副业", "面试", "裁员", "加班", "创业", "接单", "收入", "AI", "大厂", "薪资", "程序员", "跳槽", "自由职业"]
STAT_KEYS = ("like", "collect", "comment", "share", "点赞", "收藏", "评论")


def run(args, timeout=120):
    try:
        p = subprocess.run([AR] + args, capture_output=True, text=True, timeout=timeout)
        out = p.stdout
        return json.loads(out[out.index("{"):])
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "items": [], "error": {"message": str(e)[:100]}}


def num(v):
    s = str(v).replace(",", "").strip()
    m = re.match(r"([\d.]+)\s*(万|w|k)?", s, re.I)
    if not m:
        return 0
    n = float(m.group(1))
    return n * (10000 if m.group(2) in ("万", "w", "W") else 1000 if m.group(2) in ("k", "K") else 1)


def stats(raw):
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if any(s in str(k).lower() for s in STAT_KEYS) and isinstance(v, (int, float, str)) and str(v).strip():
                out[k] = v
    return out


def line(it):
    st = stats(it.get("raw"))
    st_s = " ".join(f"{k}={v}" for k, v in list(st.items())[:3])
    t = (it.get("title") or (it.get("text") or "")[:40] or "").replace("\n", " ")[:60]
    return f"- {t} | {it.get('author') or ''} | {st_s} | {it.get('url') or ''}"


def main():
    report, raw_all, seen = [], {}, set()
    report.append("# Topic material " + datetime.date.today().isoformat())

    report.append("\n## V2EX hot")
    r = run(["v2ex", "hot", "--limit", "30"])
    items = r.get("items") or []
    raw_all["v2ex"] = items
    hit = [i for i in items if any(w.lower() in ((i.get("title") or "") + (i.get("text") or "")).lower() for w in HOT_WORDS)]
    report.append(f"(total {len(items)}, matched {len(hit)}; status ok={r.get('ok')})")
    report += [line(i) for i in (hit or items[:10])]

    report.append("\n## Bilibili hot")
    r = run(["bilibili", "hot", "--limit", "40"])
    items = r.get("items") or []
    raw_all["bilibili"] = items
    hit = [i for i in items if any(w.lower() in (i.get("title") or "").lower() for w in HOT_WORDS)]
    report.append(f"(total {len(items)}, matched {len(hit)}; status ok={r.get('ok')})")
    report += [line(i) for i in (hit or items[:10])]

    report.append("\n## Xiaohongshu search")
    for kw in KEYWORDS:
        r = run(["xiaohongshu", "search", kw, "--limit", "8"])
        items = r.get("items") or []
        raw_all["xhs:" + kw] = items
        err = (r.get("error") or {}).get("code", "")
        report.append(f"\n### {kw} (ok={r.get('ok')} {err})")
        if items and isinstance(items[0].get("raw"), dict):
            report.append("fields: " + ",".join(list(items[0]["raw"].keys())[:15]))
        items = sorted(items, key=lambda i: -max([num(v) for v in stats(i.get("raw")).values()] or [0]))
        for i in items:
            if i.get("url") in seen:
                continue
            seen.add(i.get("url"))
            report.append(line(i))
        time.sleep(12)  # same-platform searches must be >=10s apart

    report.append("\n## Web search")
    for q in ["副业 趋势 2026", "职场 热点 本周"]:
        r = run(["web", "search", q, "--limit", "5"])
        items = r.get("items") or []
        raw_all["web:" + q] = items
        report.append(f"\n### {q} (ok={r.get('ok')})")
        report += [line(i) for i in items]

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(raw_all, f, ensure_ascii=False)
    print("DONE lines:", len(report))


if __name__ == "__main__":
    main()

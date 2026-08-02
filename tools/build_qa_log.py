#!/usr/bin/env python3
"""
build_qa_log.py — 按公司归档对话问答编年史。

扫描 conversations/*.jsonl,把带公司标签(focus 或 companies)的问答
按时间归档到 data/<市场>/<TICKER>/qa_log.md。幂等:每次全量重建。

用法:python3 tools/build_qa_log.py
"""
from __future__ import annotations
import glob, json, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLY_EXCERPT = 500  # 回复摘录长度;完整原文可按 ts 回溯 conversations/


def ticker_dirs() -> dict:
    """ticker -> data/<market>/<safe_ticker> 目录映射(以 watchlist 为准)"""
    wl = json.load(open(os.path.join(ROOT, "watchlist.json"), encoding="utf-8"))
    out = {}
    for c in wl["companies"]:
        safe = c["ticker"].replace(".", "_").replace("-", "_")
        out[c["ticker"]] = os.path.join(ROOT, "data", c["market"], safe)
    return out


def main() -> None:
    dirs = ticker_dirs()
    per_company: dict[str, list] = defaultdict(list)

    for f in sorted(glob.glob(os.path.join(ROOT, "conversations", "*.jsonl"))):
        src = os.path.basename(f)
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except json.JSONDecodeError:
                continue
            tags = set(j.get("companies") or [])
            if j.get("focus"):
                tags.add(j["focus"])
            for t in tags & set(dirs):
                per_company[t].append((j.get("ts", ""), j, src))

    written = 0
    for ticker, items in per_company.items():
        items.sort(key=lambda x: x[0])
        d = dirs[ticker]
        os.makedirs(d, exist_ok=True)
        lines = [f"# {ticker} · 问答编年史",
                 "",
                 "> 自动生成(tools/build_qa_log.py),按时间归档所有涉及本公司的对话。",
                 "> 回复为摘录;完整原文按 ts 查 conversations/ 对应日期文件。",
                 ""]
        cur_date = None
        for ts, j, src in items:
            date = ts[:10] if ts else "未知日期"
            if date != cur_date:
                lines += [f"## {date}", ""]
                cur_date = date
            q = (j.get("question") or "").strip()
            r = (j.get("reply") or "").strip().replace("\n", " ")
            if len(r) > REPLY_EXCERPT:
                r = r[:REPLY_EXCERPT] + " …"
            lines += [f"**问**:{q}", "", f"**答(摘录)**:{r}", "",
                      f"<sub>ts: {ts} · 源: conversations/{src}</sub>", "", "---", ""]
        with open(os.path.join(d, "qa_log.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        written += 1
        print(f"  {ticker}: {len(items)} 条 -> {os.path.relpath(os.path.join(d,'qa_log.md'), ROOT)}")

    print(f"完成:{written} 家公司的问答编年史已生成。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
health_check.py — AI_INVEST_OS 每日自检(仅标准库,无依赖)。

用途:
  python3 tools/health_check.py            # 检查并打印健康报告(markdown)
  python3 tools/health_check.py --write    # 同时写入 health_report.md
  python3 tools/health_check.py --date 2026-08-02

检查项:
  1. 今日简报是否存在(briefings/YYYY-MM-DD.md)——缺失时退出码=1,供 Agent 触发补跑/告警
  2. 近30天简报出勤率
  3. 每家 watchlist 公司 updates.jsonl 的最后更新距今天数(>14 天标红)
  4. watchlist focus 字段完整性
  5. companies.json 中 reason 缺失(仅"标注"二字)的条目数——记忆协议执行度

接入方式(SEEKER 协议):invest-data-agent 每日抓取完成后运行本脚本;
若退出码非 0,当日任务视为未完成,重试一次并在简报"值得注意"区写入告警。
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALE_DAYS = 14
ATTENDANCE_WINDOW = 30


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def company_dir(market: str, ticker: str) -> str:
    # 与 data/ 目录命名保持一致:0700.HK -> 0700_HK, 7203.T -> 7203_T
    safe = ticker.replace(".", "_").replace("-", "_")
    return os.path.join(ROOT, "data", market, safe)


def last_update_date(market: str, ticker: str):
    path = os.path.join(company_dir(market, ticker), "updates.jsonl")
    if not os.path.exists(path):
        return None
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line).get("date")
                if d and (last is None or d > last):
                    last = d
            except json.JSONDecodeError:
                continue
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()), help="以哪一天为'今天'(YYYY-MM-DD)")
    ap.add_argument("--write", action="store_true", help="将报告写入 health_report.md")
    args = ap.parse_args()
    today = datetime.strptime(args.date, "%Y-%m-%d").date()

    problems: list[str] = []
    lines: list[str] = [f"# 系统健康报告 · {today}", ""]

    # 1) 今日简报
    todays_briefing = os.path.join(ROOT, "briefings", f"{today}.md")
    briefing_ok = os.path.exists(todays_briefing)
    lines.append(f"## 1. 今日简报:{'✅ 存在' if briefing_ok else '❌ 缺失'}")
    if not briefing_ok:
        problems.append(f"今日简报 briefings/{today}.md 缺失")

    # 2) 30 天出勤率
    missing = []
    for i in range(ATTENDANCE_WINDOW):
        d = today - timedelta(days=i)
        if not os.path.exists(os.path.join(ROOT, "briefings", f"{d}.md")):
            missing.append(str(d))
    rate = (ATTENDANCE_WINDOW - len(missing)) / ATTENDANCE_WINDOW * 100
    flag = "✅" if rate >= 95 else "⚠️"
    lines += ["", f"## 2. 近{ATTENDANCE_WINDOW}天简报出勤率:{flag} {rate:.0f}%(缺 {len(missing)} 天)"]
    if missing:
        lines.append("缺失日期:" + ", ".join(missing))
    if rate < 95:
        problems.append(f"出勤率 {rate:.0f}% 低于 95% 验收线")

    # 3) 公司覆盖时效
    wl = load_json(os.path.join(ROOT, "watchlist.json"))["companies"]
    lines += ["", f"## 3. 公司覆盖时效(>{STALE_DAYS} 天零更新标红)", "",
              "| 公司 | 最后更新 | 距今 | 状态 |", "|---|---|---|---|"]
    stale = []
    for c in wl:
        last = last_update_date(c["market"], c["ticker"])
        if last is None:
            lines.append(f"| {c['ticker']} | 无记录 | — | ❌ 无 updates.jsonl |")
            stale.append(c["ticker"])
            continue
        days = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
        mark = "🔴" if days > STALE_DAYS else "✅"
        lines.append(f"| {c['ticker']} | {last} | {days}d | {mark} |")
        if days > STALE_DAYS:
            stale.append(c["ticker"])
    if stale:
        problems.append(f"{len(stale)} 家公司超过 {STALE_DAYS} 天零更新:{', '.join(stale)}")

    # 4) focus 完整性
    no_focus = [c["ticker"] for c in wl if not c.get("focus")]
    lines += ["", f"## 4. focus 字段:{'✅ 全部非空' if not no_focus else '❌ 缺失 ' + ', '.join(no_focus)}"]
    if no_focus:
        problems.append(f"focus 缺失:{', '.join(no_focus)}")

    # 5) 标注理由完整性(记忆协议)
    comp = load_json(os.path.join(ROOT, "companies.json"))["companies"]
    bare = [c["ticker"] for c in comp
            if (c.get("reason") or "").strip() in ("", "标注") or (c.get("reason") or "").startswith("标注(依据") is False and (c.get("reason") or "").strip() == "标注"]
    bare = [c["ticker"] for c in comp if (c.get("reason") or "").strip() in ("", "标注")]
    lines += ["", f"## 5. 标注理由完整性:{'✅' if not bare else '⚠️'} {len(comp)-len(bare)}/{len(comp)} 条带理由"]
    if bare:
        lines.append("无理由条目:" + ", ".join(bare) + "(按协议应逐步补写理由并关联画像条目)")

    # 汇总
    lines += ["", "## 结论", ""]
    if problems:
        lines += [f"- ❗ {p}" for p in problems]
    else:
        lines.append("- ✅ 全部检查通过")

    report = "\n".join(lines)
    print(report)
    if args.write:
        with open(os.path.join(ROOT, "health_report.md"), "w", encoding="utf-8") as f:
            f.write(report + "\n")

    # 简报缺失是硬失败;其余为软告警
    return 1 if not briefing_ok else 0


if __name__ == "__main__":
    sys.exit(main())

# AI_INVEST_OS — 投资研究操作系统

**先读 SEEKER.md(主协议)。** 数据 Agent 维护公司数据库与每日简报,记忆层沉淀品味/原则/假设/问题,推荐闭环持续寻找伟大公司,Board 是驾驶舱。

## 目录结构

```
InvestOS/
├── SEEKER.md               # ★ SeekerMaster 主协议:角色分工/记忆架构/指令约定
├── watchlist.json          # 监控清单(数据 Agent 每日按此抓取)
├── companies.json          # 公司分类库:喜欢/观察/不喜欢 + 理由 + 变更历史
├── recommendations.jsonl   # AI 推荐记录(避免重复,可复盘命中率)
├── memory/
│   ├── taste_profile.md    # 用户投资品味画像(每次对话/标注后自动更新)
│   ├── principles.md       # 大师方法与好文章观点的结构化摘录
│   ├── hypotheses.md       # 投资假设追踪(证据关联条目id,状态演化)
│   ├── questions.md        # 开放问题清单
│   └── notes/              # 用户分享素材的原文存档
├── briefings/              # 每日简报(跨公司主线洞察)
├── tools/
│   └── sp500_crawler.py    # S&P500 基础数据爬虫(Mac 终端运行)
├── sp500_status.json       # 爬虫状态:ok/partial/failed(基础数据建立失败)
├── sp500_report.md         # 爬虫汇总报告
├── data/<市场>/<TICKER>/
│   ├── profile.md          # 公司画像(长期记忆,watchlist 公司才有)
│   ├── updates.jsonl       # 滚动更新记录,只追加不删除
│   ├── filings_index.json  # 申报文件全量索引(来源 SEC/交易所)
│   └── filings/<类型>/      # 近一年核心文件原文:10-K/10-Q/8-K/DEF-14A
└── board/
    ├── aggregate.py        # 聚合脚本:生成 board_data.json 并渲染 html
    ├── board_template.html # 驾驶舱模板(__DATA__ 占位符)
    └── board_data.json     # 聚合数据
```

## AI 协议(任何会话挂载本文件夹后按此执行)

### 对话指令约定

- **`深聊 <条目id>`**(如 `深聊 NVDA-20260611-01`):读取该条更新 + 公司 profile.md + taste_profile.md 作为上下文展开讨论。
- **`标注 <ticker或id> 喜欢|观察|不喜欢`**:写入 companies.json(含理由、日期、来源、history);喜欢/观察自动加入 watchlist.json;不喜欢的存档并停止推荐(满半年由每周任务提醒重审)。标注后更新 taste_profile.md 并告知更新了什么。
- **`推荐公司`**:读取 taste_profile + principles + companies.json → 排除不喜欢及已推荐 → 搜索匹配候选 → 每家给出"为什么你可能喜欢"(对应具体偏好条目)+ 风险点 → 追加写入 recommendations.jsonl。
- **用户分享文章/经验/想法**:原文存 memory/notes/,观点提炼进 principles.md,偏好信号写入 taste_profile.md,并简短告知更新内容。

### 更新记录 schema(updates.jsonl 每行)

```json
{"id":"NVDA-20260611-01","date":"2026-06-11","ticker":"NVDA","market":"US",
 "type":"财报|项目进展|媒体报道|自媒体分析|公告|监管/政策",
 "title":"...","summary":"事实摘要","analysis":"对投资逻辑的初步判断",
 "source":"...","url":"..."}
```

### companies.json 条目 schema

```json
{"ticker":"NVDA","market":"US","name_zh":"英伟达","status":"喜欢|观察|不喜欢",
 "reason":"归类理由","date":"YYYY-MM-DD","origin":"AI推荐|用户自选|Board条目",
 "history":[{"date":"...","status":"...","reason":"..."}]}
```

### board_data.json 结构

```json
{"generated":"YYYY-MM-DD","companies":{ticker:name_zh},
 "classifications":{ticker:{"status":"...","reason":"...","date":"..."}},
 "updates":[...按date降序...]}
```

## 定时任务

- **invest-data-agent**(每日 08:10):按 watchlist 搜索增量 → 追加 updates.jsonl → 聚合 board_data.json(含分类状态)→ 刷新 Board artifact。
- **invest-recommender**(每周一 08:30):基于品味画像推荐 2-3 家新公司;检查"不喜欢"满半年的公司提醒重审。

## Board 使用

- **桌面驾驶舱**:Cowork 侧边栏打开 "invest-update-board",七视图(今日/更新流/对话/推荐/公司库/记忆/复盘),内嵌对话与一键标注。
- **移动版(手机/iPad)**:每日 Agent 同步到 iCloud `InvestOS_Mobile/index.html`,在手机「文件」App → iCloud 云盘 → InvestOS_Mobile 打开。底部 Tab 导航;💬 按钮复制"深聊包"(粘贴到 Claude App 即可带上下文讨论);❤️👀✖️ 复制标注指令(回 Mac 主对话粘贴生效)。Mac 是大脑(数据/定时任务/记忆),移动端是终端。
- 模板:board_template.html(桌面)/ board_mobile_template.html(移动),aggregate.py 一次生成两版。

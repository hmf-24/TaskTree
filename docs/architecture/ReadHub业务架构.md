# ReadHub 业务逻辑与系统架构说明

ReadHub 是 Nexus 项目中的一个核心子模块，致力于提供一个高度私有化、全自动的 RSS 信息聚合与智能阅读中枢。

随着系统迭代，ReadHub 已经从传统的“后台定时器拉取数据”的旧模式，完全蜕变成了一个**“以 AI 为核心驱动的（Agent-Centric）按需计算架构”**。

---

## 1. 核心架构范式：AI 驱动 (Agent-Centric)

传统的 RSS 阅读器是由后台服务完全主导的。但在全新的 ReadHub 架构中，Python 后端和底层数据库已经退化为 AI 的“执行器”与“记忆库”。

* **传统模式**：定时任务死循环拉取 ➔ 后台强制调用 LLM 做信息提炼 ➔ 用户被动查看。
* **全新 AI 模式**：
  * **按需计算 (On-Demand)**：后台入库时只做极速的 HTML 脱水清洗，完全不再浪费任何 Token。只有在用户主动询问或 AI 智能体根据“生物钟（Schedule）”醒来需要推送早报时，AI 才会实时读取提取出的文本进行总结。
  * **主动外挂 (Agentic Crawling)**：赋予大模型挂载爬虫节点的权限，实现生态破壁（详见 WeWe-RSS 整合）。

---

## 2. 业务流转全景

### 2.1 订阅与节点挂载 (WeweRSS 深度整合)
为了打破微信公众号的封闭生态，ReadHub 深度集成了 WeWe-RSS 服务。最革命性的一点是，我们将 WeweRSS 包装成了一个 Agent Tool（`wewerss_agent_tool.py`）。
1. **用户意图**：用户在钉钉上对机器人说：“帮我订阅《晚点LatePost》公众号”。
2. **AI 工具调用**：钉钉大模型准确识别意图，携带用户的 `wewe_auth_code` 自动调用 `search_and_add` 接口。
3. **后台注册**：WeWe-RSS 在云端自动挂载该公众号爬虫节点。同时，Agent 将 `WeWe-RSS 聚合订阅 (all.json)` 的节点自动注入到本地 SQLite 的 `rss_feeds` 监控列表中。

### 2.2 数据入库 (轻量化与异步并发)
1. **防阻塞设计**：`RssService.fetch_feeds` 遍历监控列表时，采用了异步 Http 请求，对于同步的 `feedparser` 库则通过 `asyncio.run_in_executor` 放入线程池，防止阻塞 FastAPI 核心事件循环。
2. **轻量脱水清洗**：文章入库时，保留原始作者自带的 `summary`（不再进行破坏性覆盖），清洗并保留 `content_html`。
3. **实时推送降级 (Fallback Preview)**：如果发现有新文章，在向钉钉进行实时推送（`dingtalk_service.py`）时，如果原文缺少摘要，系统会自动抽取 HTML 标签过滤后的前 100 字作为预览推送，不消耗任何 LLM 资源。

### 2.3 交互查询与知识召回 (FTS5 全文检索)
当用户需要向系统询问特定资讯时，系统提供了两大维度的检索能力：
1. **时效维度的拉取**：大模型可以通过 `fetch_articles_tool.py` 获取最新未读的新闻集合。
2. **历史维度的召回 (SQLite FTS5)**：
   * 底层通过 Alembic / Migration 脚本建立并维护了 `rss_articles_fts` 倒排索引虚拟表。
   * 配置了基于 SQLite 内部引擎的 `AFTER INSERT/UPDATE/DELETE` 实时同步 Trigger。
   * 当用户需要深挖某一话题（如：“找一下上个月发的所有关于 AI 芯片的文章”），大模型将调用 `search_articles_tool.py`，以极低的延迟在 FTS5 引擎中匹配命中内容（`snippet` 高亮段落），并结合历史上下文生成完善的报告给用户。

---

## 3. 架构优势总结

1. **零闲置损耗**：杜绝了每天后台为几百篇“可能永远不会被看”的文章耗费大模型 API 额度的问题。
2. **跨平台与私有化**：脱离公域平台的审查与广告，借助 WeweRSS 和纯净的 SQLite FTS，打造了极其安全的本地化专属知识库。
3. **高扩展性**：AI 作为调度大脑，未来极易再扩展比如“图片反代（Image Proxy）”、“本地 Obsidian Markdown 双向同步”（`obsidian_service.py`）等新分支。

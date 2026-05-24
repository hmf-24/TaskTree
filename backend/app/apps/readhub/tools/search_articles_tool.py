from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class SearchArticlesSchema(BaseModel):
    query: str = Field(..., description="要搜索的关键词或句子（使用空格分隔多个关键词）")
    limit: int = Field(5, description="要返回的最大文章数量，默认 5 篇")

class SearchArticlesTool(BaseTool):
    name = "search_articles_tool"
    description = "全文检索历史文章。当用户需要查找关于特定主题、事件或关键词的往期新闻和文章时调用此工具。"
    parameters_schema = SearchArticlesSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        limit = kwargs.get("limit", 5)

        if not query:
            return ToolResult(success=False, output="必须提供搜索关键词 query")

        try:
            # 格式化 FTS5 查询字符串（将空格分隔的词转换为 AND 查询）
            # 例如 "AI 芯片" -> "AI AND 芯片"
            fts_query = " AND ".join([f'"{q}"' for q in query.split() if q.strip()])
            
            # 使用 FTS5 虚拟表进行检索，并联合查询获取原始数据
            # 注意: 使用 user_id 进行安全隔离，确保只能搜到自己订阅源的文章
            sql = text("""
                SELECT a.id, a.title, a.author, a.source_url, 
                       snippet(rss_articles_fts, -1, '<b>', '</b>', '...', 64) as match_snippet
                FROM rss_articles_fts fts
                JOIN rss_articles a ON fts.rowid = a.id
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE rss_articles_fts MATCH :query
                  AND f.user_id = :user_id
                ORDER BY rank
                LIMIT :limit
            """)
            
            result = await self.db.execute(sql, {"query": fts_query, "user_id": user_id, "limit": limit})
            rows = result.fetchall()
            
            if not rows:
                return ToolResult(success=True, output=f"未检索到与 '{query}' 相关的文章。")

            data = []
            for row in rows:
                data.append({
                    "id": row.id,
                    "title": row.title,
                    "author": row.author,
                    "url": row.source_url,
                    "snippet": row.match_snippet
                })

            import json
            return ToolResult(
                success=True,
                output=f"成功检索到 {len(data)} 篇相关文章，详细内容如下:\n{json.dumps(data, ensure_ascii=False, indent=2)}",
                data=data
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                output=f"检索文章失败: {str(e)}。可能是 FTS5 未启用或查询语法错误。"
            )

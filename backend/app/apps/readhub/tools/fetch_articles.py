from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from app.apps.readhub.service import RssService

class FetchArticlesSchema(BaseModel):
    limit: int = Field(5, description="要获取的未读文章数量，默认 5 篇")

class FetchArticlesTool(BaseTool):
    name = "fetch_articles_tool"
    description = "获取当前用户的最新未读订阅文章或新闻摘要"
    parameters_schema = FetchArticlesSchema

    def __init__(self, db: AsyncSession, llm_service):
        self.db = db
        self.llm_service = llm_service

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        limit = kwargs.get("limit", 5)
        
        try:
            result = await RssService.get_articles(db=self.db, user_id=user_id, unread_only=True, page_size=limit)
            items = result.get("items", [])
            data = []
            import re
            for item in items:
                # 提取纯文本内容作为补充，防止 summary 为空大模型无法理解
                raw = item.content_html or ""
                clean = re.sub(r'<[^>]+>', '', raw).strip()
                clean = re.sub(r'\s+', ' ', clean)
                content_preview = clean[:500] + "..." if len(clean) > 500 else clean

                final_summary = item.summary
                if not final_summary or final_summary.strip() == "" or "暂无内容" in final_summary:
                    final_summary = content_preview

                data.append({
                    "id": item.id,
                    "title": item.title,
                    "author": item.author,
                    "summary": final_summary,
                    "url": item.source_url
                })
            
            import json
            return ToolResult(
                success=True,
                output=f"成功获取了 {len(data)} 篇未读文章，包含标题、作者、原文链接(url)、内部系统ID(id)以及核心摘要(summary)。你可以直接基于 summary 回答用户的问题。详细数据:\n{json.dumps(data, ensure_ascii=False, indent=2)}",
                data=data
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"获取文章失败: {str(e)}"
            )

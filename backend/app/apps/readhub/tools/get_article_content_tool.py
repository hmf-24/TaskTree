from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import re

class GetArticleContentSchema(BaseModel):
    article_id: int = Field(..., description="要获取完整内容的文章的内部 ID")

class GetArticleContentTool(BaseTool):
    name = "get_article_content_tool"
    description = "根据文章 ID 获取文章的完整详细内容。当用户想深入了解某篇具体文章，或者对某篇文章的详细内容提问时调用此工具。"
    parameters_schema = GetArticleContentSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        article_id = kwargs.get("article_id")
        
        if not article_id:
            return ToolResult(success=False, output="必须提供 article_id")

        try:
            # 确保用户只能获取自己订阅的文章
            sql = text("""
                SELECT a.title, a.author, a.source_url, a.content_html, a.summary
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE a.id = :article_id AND f.user_id = :user_id
            """)
            
            result = await self.db.execute(sql, {"article_id": article_id, "user_id": user_id})
            row = result.fetchone()
            
            if not row:
                return ToolResult(success=False, output=f"未找到 ID 为 {article_id} 的文章，或您无权访问。")

            # 清理 HTML 标签，减少 token 消耗
            raw_content = row.content_html or ""
            clean_content = re.sub(r'<[^>]+>', ' ', raw_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # 如果清理后的内容还是太长，为了防止超出 Token 限制，做适度截断 (如保留 15000 字符)
            if len(clean_content) > 15000:
                clean_content = clean_content[:15000] + "...(后文省略)"
                
            if not clean_content and row.summary:
                clean_content = f"无法获取文章主体正文，这可能是由于源站限制。\n这是该文章的摘要信息:\n{row.summary}"

            output_text = f"成功获取文章完整内容:\n标题: {row.title}\n作者: {row.author}\n链接: {row.source_url}\n正文内容:\n{clean_content}"

            return ToolResult(
                success=True,
                output=output_text
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                output=f"获取文章完整内容失败: {str(e)}"
            )

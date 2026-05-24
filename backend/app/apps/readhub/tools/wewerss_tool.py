import httpx
from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rss import ReadHubSettings

class WeweRssSubscribeSchema(BaseModel):
    account_name: str = Field(..., description="要搜索和订阅的微信公众号名称或ID")
    action: str = Field("search_and_add", description="操作类型，可选：search_and_add")

class WeweRssAgentTool(BaseTool):
    name = "wewerss_subscribe_tool"
    description = "控制 WeweRSS 节点，自动搜索并订阅新的微信公众号。当用户要求关注或订阅某个微信公众号时调用此工具。"
    parameters_schema = WeweRssSubscribeSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        account_name = kwargs.get("account_name")
        action = kwargs.get("action", "search_and_add")

        if not account_name:
            return ToolResult(success=False, output="必须提供公众号名称 account_name")

        # 1. 获取用户的 WeweRSS 配置
        result = await self.db.execute(
            select(ReadHubSettings).where(ReadHubSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings or not settings.wewe_server_url:
            return ToolResult(
                success=False, 
                output="用户尚未配置 WeweRSS 服务器地址，请提示用户先在设置中配置 wewe_server_url 和 wewe_auth_code。"
            )

        base_url = settings.wewe_server_url.rstrip('/')
        auth_code = settings.wewe_auth_code

        headers = {}
        if auth_code:
            headers["Authorization"] = f"Bearer {auth_code}"
            
        params = {}
        if auth_code:
            params["auth_code"] = auth_code # 兼容旧版

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 2. 模拟搜索公众号
                # 注意：具体 API 路径可能因 WeweRSS 版本而异，这里假设为标准的 RESTful 结构
                search_url = f"{base_url}/api/v1/accounts/search"
                search_resp = await client.get(search_url, params={"q": account_name, **params}, headers=headers)
                
                if search_resp.status_code == 404:
                    return ToolResult(
                        success=False, 
                        output=f"WeweRSS 服务未提供 {search_url} 接口。请检查 WeweRSS 版本是否支持 API 订阅。"
                    )
                
                search_resp.raise_for_status()
                search_data = search_resp.json()
                accounts = search_data.get("data", [])
                
                if not accounts:
                    return ToolResult(success=False, output=f"未找到名为 '{account_name}' 的公众号，请检查名称是否准确。")

                # 选择最匹配的第一个
                target_account = accounts[0]
                biz_id = target_account.get("biz")
                
                # 3. 模拟添加订阅
                add_url = f"{base_url}/api/v1/accounts/add"
                add_resp = await client.post(add_url, json={"biz": biz_id}, params=params, headers=headers)
                add_resp.raise_for_status()
                
                # 4. 自动挂载 all.json 聚合源到 ReadHub
                from app.models.rss import RssFeed
                feed_url = f"{base_url}/feeds/all.json"
                if auth_code:
                    feed_url += f"?auth_code={auth_code}"
                
                existing = await self.db.execute(
                    select(RssFeed).where(RssFeed.user_id == user_id, RssFeed.url == feed_url)
                )
                existing_feed = existing.scalar_one_or_none()
                if not existing_feed:
                    new_feed = RssFeed(
                        user_id=user_id,
                        url=feed_url,
                        name="WeWe-RSS 聚合订阅",
                        is_active=True,
                    )
                    self.db.add(new_feed)
                    await self.db.commit()

                return ToolResult(
                    success=True, 
                    output=f"成功在 WeweRSS 中订阅了公众号：{target_account.get('name', account_name)}。爬虫节点已挂载，后续有新文章会自动推送到数据库。"
                )

        except httpx.HTTPError as e:
            return ToolResult(
                success=False, 
                output=f"调用 WeweRSS API 失败: {str(e)}。可能是接口不兼容或网络不通。"
            )
        except Exception as e:
            return ToolResult(
                success=False, 
                output=f"发生未知错误: {str(e)}"
            )

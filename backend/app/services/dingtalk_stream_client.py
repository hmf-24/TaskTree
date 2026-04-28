"""
钉钉Stream模式客户端
==================
通过WebSocket主动连接钉钉服务器，监听并处理消息推送。
适用于本地开发环境（无需公网IP）。
"""
import asyncio
from typing import Optional, Callable, Awaitable
from dingtalk_stream import AckMessage
import dingtalk_stream


class DingtalkMessageHandler:
    """钉钉消息处理器"""
    
    def __init__(self, db_session_factory):
        """初始化处理器
        
        Args:
            db_session_factory: 数据库会话工厂
        """
        self.db_session_factory = db_session_factory
    
    async def handle_message(self, message: dict) -> AckMessage:
        """处理钉钉推送的消息
        
        Args:
            message: 钉钉消息对象
            
        Returns:
            AckMessage: 响应消息
        """
        from app.api.v1.dingtalk import process_dingtalk_message
        from app.services.dingtalk_service import DingtalkService
        from app.services.rate_limiter import dingtalk_rate_limiter
        from app.models import UserNotificationSettings
        from sqlalchemy import select
        
        try:
            # 提取消息信息
            sender_id = message.get("senderId")
            content = message.get("text", {}).get("content", "")
            
            print(f"📨 收到钉钉消息: sender={sender_id}, content={content[:50]}...")
            
            if not sender_id or not content:
                return AckMessage.STATUS_OK
            
            # 查询用户映射
            async with self.db_session_factory() as db:
                result = await db.execute(
                    select(UserNotificationSettings).where(
                        UserNotificationSettings.dingtalk_user_id == sender_id
                    )
                )
                settings = result.scalar_one_or_none()
                
                if not settings:
                    # 用户未绑定
                    dingtalk_service = DingtalkService()
                    await dingtalk_service.send_message(
                        sender_id,
                        "请先绑定钉钉账号，访问系统设置进行绑定"
                    )
                    return AckMessage.STATUS_OK
                
                user_id = settings.user_id
                
                # 检查频率限制
                is_allowed, rate_limit_info = dingtalk_rate_limiter.is_allowed(user_id)
                if not is_allowed:
                    dingtalk_service = DingtalkService()
                    await dingtalk_service.send_message(
                        sender_id,
                        f"请求过于频繁，请在 {rate_limit_info['retry_after']} 秒后重试"
                    )
                    return AckMessage.STATUS_OK
                
                # 异步处理消息（不阻塞响应）
                asyncio.create_task(
                    process_dingtalk_message(
                        user_id=user_id,
                        dingtalk_user_id=sender_id,
                        message_content=content,
                        db=db
                    )
                )
            
            return AckMessage.STATUS_OK
        
        except Exception as e:
            print(f"❌ 处理钉钉消息失败: {e}")
            import traceback
            traceback.print_exc()
            return AckMessage.STATUS_OK  # 仍返回成功，避免钉钉重试


class DingtalkStreamClient:
    """钉钉Stream模式客户端"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        message_handler: Callable[[dict], Awaitable[AckMessage]]
    ):
        """初始化Stream客户端
        
        Args:
            client_id: 钉钉AppKey
            client_secret: 钉钉AppSecret
            message_handler: 消息处理回调函数
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.message_handler = message_handler
        self.client: Optional[dingtalk_stream.DingTalkStreamClient] = None
        self._running = False
    
    async def start(self) -> None:
        """启动客户端，建立WebSocket连接"""
        try:
            print(f"🚀 正在启动钉钉Stream客户端...")
            print(f"   ClientID: {self.client_id[:10]}...")
            
            # 创建Stream客户端
            credential = dingtalk_stream.Credential(
                self.client_id,
                self.client_secret
            )
            self.client = dingtalk_stream.DingTalkStreamClient(credential)
            
            # 注册消息回调
            self.client.register_callback_handler(
                dingtalk_stream.ChatbotMessage.TOPIC,
                self._handle_message_wrapper
            )
            
            # 启动客户端（非阻塞）
            asyncio.create_task(self.client.start_forever())
            self._running = True
            
            print(f"✅ 钉钉Stream客户端已启动")
        
        except Exception as e:
            print(f"❌ 启动钉钉Stream客户端失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _handle_message_wrapper(self, message: dingtalk_stream.ChatbotMessage):
        """消息处理包装器（同步转异步）"""
        try:
            # 提取消息数据
            message_dict = {
                "senderId": message.sender_id,
                "text": {
                    "content": message.text
                }
            }
            
            # 创建异步任务处理消息
            asyncio.create_task(self._async_handle_message(message_dict, message))
            
            # 立即返回成功响应
            return AckMessage.STATUS_OK
        
        except Exception as e:
            print(f"❌ 消息包装器错误: {e}")
            return AckMessage.STATUS_OK
    
    async def _async_handle_message(
        self,
        message_dict: dict,
        original_message: dingtalk_stream.ChatbotMessage
    ):
        """异步处理消息"""
        try:
            await self.message_handler(message_dict)
        except Exception as e:
            print(f"❌ 异步消息处理失败: {e}")
    
    async def stop(self) -> None:
        """停止客户端，断开连接"""
        try:
            if self.client:
                print(f"🛑 正在停止钉钉Stream客户端...")
                # dingtalk-stream SDK 会自动清理资源
                self._running = False
                print(f"✅ 钉钉Stream客户端已停止")
        except Exception as e:
            print(f"❌ 停止钉钉Stream客户端失败: {e}")
    
    def is_running(self) -> bool:
        """检查客户端是否运行中"""
        return self._running


async def start_dingtalk_stream_mode(app):
    """启动钉钉Stream模式
    
    Args:
        app: FastAPI应用实例
    """
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    
    # 检查配置
    if not settings.DINGTALK_STREAM_ENABLED:
        print("ℹ️  钉钉Stream模式未启用")
        return
    
    if not settings.DINGTALK_CLIENT_ID or not settings.DINGTALK_CLIENT_SECRET:
        print("⚠️  钉钉Stream模式配置不完整，跳过启动")
        print(f"   DINGTALK_CLIENT_ID: {'已配置' if settings.DINGTALK_CLIENT_ID else '未配置'}")
        print(f"   DINGTALK_CLIENT_SECRET: {'已配置' if settings.DINGTALK_CLIENT_SECRET else '未配置'}")
        return
    
    try:
        # 创建消息处理器
        handler = DingtalkMessageHandler(AsyncSessionLocal)
        
        # 创建并启动Stream客户端
        client = DingtalkStreamClient(
            client_id=settings.DINGTALK_CLIENT_ID,
            client_secret=settings.DINGTALK_CLIENT_SECRET,
            message_handler=handler.handle_message
        )
        
        await client.start()
        
        # 保存客户端引用
        app.state.dingtalk_stream_client = client
        
        print(f"🎉 钉钉Stream模式已启动")
    
    except Exception as e:
        print(f"❌ 启动钉钉Stream模式失败: {e}")
        import traceback
        traceback.print_exc()

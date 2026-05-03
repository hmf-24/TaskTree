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
            print(f"🔄 开始处理消息...")
            
            # 提取消息信息
            sender_id = message.get("senderId")
            content = message.get("text", {}).get("content", "")
            
            print(f"📨 处理消息: sender={sender_id}, content={content[:50]}...")
            
            if not sender_id or not content:
                print(f"⚠️  消息信息不完整，跳过处理")
                return AckMessage.STATUS_OK
            
            print(f"🔍 查询用户映射: sender_id={sender_id}")
            
            # 查询用户映射
            async with self.db_session_factory() as db:
                result = await db.execute(
                    select(UserNotificationSettings).where(
                        UserNotificationSettings.dingtalk_user_id == sender_id
                    )
                )
                settings = result.scalar_one_or_none()
                
                print(f"🔍 查询结果: settings={settings}")
                
                if not settings:
                    # 用户未绑定
                    print(f"⚠️  用户未绑定，发送绑定提示")
                    dingtalk_service = DingtalkService()
                    await dingtalk_service.send_message(
                        sender_id,
                        "请先绑定钉钉账号，访问系统设置进行绑定"
                    )
                    return AckMessage.STATUS_OK
                
                user_id = settings.user_id
                print(f"✅ 找到用户: user_id={user_id}")
                
                # 检查频率限制
                is_allowed, rate_limit_info = dingtalk_rate_limiter.is_allowed(user_id)
                if not is_allowed:
                    print(f"⚠️  频率限制超出")
                    dingtalk_service = DingtalkService()
                    await dingtalk_service.send_message(
                        sender_id,
                        f"请求过于频繁，请在 {rate_limit_info['retry_after']} 秒后重试"
                    )
                    return AckMessage.STATUS_OK
                
                print(f"🚀 开始处理钉钉消息...")
                # 同步处理消息（等待AI回复完成）
                await process_dingtalk_message(
                    user_id=user_id,
                    dingtalk_user_id=sender_id,
                    message_content=content,
                    db=db
                )
                print(f"✅ 消息处理完成")
            
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
        # 消息去重缓存: {message_key: timestamp}
        self._processed_messages: dict = {}
        self._dedup_ttl = 60  # 60秒内相同消息视为重复
    
    def _is_duplicate(self, sender_id: str, content: str, msg_id: str = None) -> bool:
        """检查消息是否重复（基于 msg_id 或 sender + content 的 TTL 缓存）"""
        import time
        now = time.time()
        
        # 清理过期条目
        expired = [k for k, t in self._processed_messages.items() if now - t > self._dedup_ttl]
        for k in expired:
            del self._processed_messages[k]
        
        # 生成去重键
        if msg_id:
            dedup_key = f"msg:{msg_id}"
        else:
            dedup_key = f"content:{sender_id}:{content.strip()}"
        
        if dedup_key in self._processed_messages:
            print(f"🔁 检测到重复消息，跳过处理: {content[:30]}...")
            return True
        
        self._processed_messages[dedup_key] = now
        return False
    
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
            
            # 注册消息回调（使用实例方法）
            self.client.register_callback_handler(
                dingtalk_stream.ChatbotMessage.TOPIC,
                self
            )
            
            # 启动客户端（在后台运行）
            import threading
            def run_client():
                import asyncio
                asyncio.run(self.client.start_forever())
            
            thread = threading.Thread(target=run_client, daemon=True)
            thread.start()
            
            self._running = True
            
            print(f"✅ 钉钉Stream客户端已启动")
        
        except Exception as e:
            print(f"❌ 启动钉钉Stream客户端失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def __call__(self, message: dingtalk_stream.ChatbotMessage):
        """使类实例可调用 — 委托给 raw_process，不再单独处理"""
        # 不做任何处理，所有逻辑统一由 raw_process 处理
        # 返回 AckMessage 避免 SDK 报错
        return AckMessage()
    
    def pre_start(self):
        """SDK要求的预启动方法"""
        print(f"🔧 pre_start 被调用")
        pass
    
    async def raw_process(self, message):
        """SDK 唯一的消息处理入口（异步）"""
        import threading
        import time as _time
        
        # 从message.data中提取消息信息
        data = message.data if hasattr(message, 'data') else {}
        sender_id = data.get('senderStaffId') or data.get('senderId')
        msg_id = data.get('msgId')
        create_at = data.get('createAt')  # 毫秒时间戳
        text_data = data.get('text', {})
        content = text_data.get('content', '') if isinstance(text_data, dict) else ''
        
        if not sender_id or not content:
            print(f"⚠️  消息信息不完整: sender_id={sender_id}, content={content}")
            return AckMessage()
        
        # ── 防重放：拒绝超过 30 秒的旧消息 ──
        if create_at:
            try:
                msg_age_sec = (_time.time() * 1000 - int(create_at)) / 1000
                if msg_age_sec > 30:
                    print(f"⏰ 丢弃过期消息 (距今 {msg_age_sec:.1f}s): {content[:30]}...")
                    return AckMessage()
            except (ValueError, TypeError):
                pass  # createAt 格式异常时跳过时间检查
        
        # ── 去重检查（第二道防线） ──
        if self._is_duplicate(sender_id, content, msg_id):
            return AckMessage()
        
        print(f"📨 收到钉钉消息: sender={sender_id}, content={content[:50]}...")
        
        # 提取消息数据
        message_dict = {
            "senderId": sender_id,
            "text": {
                "content": content.strip()
            }
        }
        
        # 在后台线程中处理消息
        def process_in_thread():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.message_handler(message_dict))
            finally:
                loop.close()
        
        thread = threading.Thread(target=process_in_thread, daemon=True)
        thread.start()
        
        # 立即返回AckMessage对象
        return AckMessage()
    
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
    """启动钉钉Stream模式 - 为所有启用Stream的用户启动客户端
    
    Args:
        app: FastAPI应用实例
    """
    from app.core.database import get_session_maker
    from app.models import UserNotificationSettings
    from app.core.crypto import decrypt_api_key
    from sqlalchemy import select
    
    print("🔍 正在检查启用Stream模式的用户...")
    
    # 初始化客户端管理器
    if not hasattr(app.state, 'dingtalk_stream_clients'):
        app.state.dingtalk_stream_clients = {}
    
    session_maker = get_session_maker()
    async with session_maker() as db:
        # 查询所有启用Stream模式的用户
        result = await db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.dingtalk_stream_enabled == True
            )
        )
        settings_list = result.scalars().all()
        
        if not settings_list:
            print("ℹ️  没有用户启用钉钉Stream模式")
            return
        
        print(f"📋 找到 {len(settings_list)} 个启用Stream模式的用户")
        
        # 为每个用户启动Stream客户端
        for settings in settings_list:
            if not settings.dingtalk_client_id or not settings.dingtalk_client_secret_encrypted:
                print(f"⚠️  用户 {settings.user_id} 的Stream配置不完整，跳过")
                continue
            
            try:
                # 解密Client Secret
                client_secret = decrypt_api_key(settings.dingtalk_client_secret_encrypted)
                
                # 创建消息处理器
                handler = DingtalkMessageHandler(get_session_maker())
                
                # 创建并启动Stream客户端
                client = DingtalkStreamClient(
                    client_id=settings.dingtalk_client_id,
                    client_secret=client_secret,
                    message_handler=handler.handle_message
                )
                
                await client.start()
                
                # 保存客户端引用
                app.state.dingtalk_stream_clients[settings.user_id] = client
                
                print(f"✅ 用户 {settings.user_id} 的钉钉Stream客户端已启动")
            
            except Exception as e:
                print(f"❌ 启动用户 {settings.user_id} 的Stream客户端失败: {e}")
                import traceback
                traceback.print_exc()
        
        if app.state.dingtalk_stream_clients:
            print(f"🎉 钉钉Stream模式已启动，共 {len(app.state.dingtalk_stream_clients)} 个客户端")
        else:
            print("⚠️  没有成功启动任何Stream客户端")


async def restart_user_stream_client(app, user_id: int, settings):
    """重启指定用户的Stream客户端
    
    Args:
        app: FastAPI应用实例
        user_id: 用户ID
        settings: 用户的通知设置
    """
    from app.core.crypto import decrypt_api_key
    from app.core.database import get_session_maker
    
    # 初始化客户端管理器
    if not hasattr(app.state, 'dingtalk_stream_clients'):
        app.state.dingtalk_stream_clients = {}
    
    # 停止旧客户端
    if user_id in app.state.dingtalk_stream_clients:
        try:
            await app.state.dingtalk_stream_clients[user_id].stop()
            del app.state.dingtalk_stream_clients[user_id]
            print(f"🛑 已停止用户 {user_id} 的旧Stream客户端")
        except Exception as e:
            print(f"⚠️  停止用户 {user_id} 的旧Stream客户端失败: {e}")
    
    # 如果未启用Stream模式，直接返回
    if not settings.dingtalk_stream_enabled:
        print(f"ℹ️  用户 {user_id} 未启用Stream模式")
        return
    
    # 检查配置
    if not settings.dingtalk_client_id or not settings.dingtalk_client_secret_encrypted:
        print(f"⚠️  用户 {user_id} 的Stream配置不完整")
        return
    
    try:
        # 解密Client Secret
        client_secret = decrypt_api_key(settings.dingtalk_client_secret_encrypted)
        
        # 创建消息处理器
        handler = DingtalkMessageHandler(get_session_maker())
        
        # 创建并启动Stream客户端
        client = DingtalkStreamClient(
            client_id=settings.dingtalk_client_id,
            client_secret=client_secret,
            message_handler=handler.handle_message
        )
        
        await client.start()
        
        # 保存客户端引用
        app.state.dingtalk_stream_clients[user_id] = client
        
        print(f"✅ 用户 {user_id} 的钉钉Stream客户端已重启")
    
    except Exception as e:
        print(f"❌ 重启用户 {user_id} 的Stream客户端失败: {e}")
        import traceback
        traceback.print_exc()

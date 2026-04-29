"""
TaskTree 钉钉通知服务
====================
封装钉钉机器人Webhook推送功能和Stream模式消息发送。
"""
import hmac
import hashlib
import base64
import json
import time
from urllib.parse import quote
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class DingtalkService:
    """钉钉通知服务"""

    def __init__(self, webhook_url: str = None, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret
        # 钉钉API基础URL
        self.api_base_url = "https://api.dingtalk.com"
        # Access Token缓存
        self._access_token_cache = {}

    async def send_message(
        self,
        dingtalk_user_id: str = None,
        content: str = None,
        msg_type: str = "markdown",
        title: str = "TaskTree 任务提醒",
        webhook_url: str = None,
        secret: str = None,
        # Stream模式参数
        use_stream_mode: bool = False,
        client_id: str = None,
        client_secret: str = None,
        robot_code: str = None
    ) -> dict:
        """发送钉钉消息（支持Webhook和Stream两种模式）

        Args:
            dingtalk_user_id: 钉钉用户ID（用于私聊）
            content: 消息内容（Markdown格式）
            msg_type: 消息类型 text/markdown
            title: 标题（仅markdown用）
            webhook_url: Webhook URL（可覆盖默认值）
            secret: 签名密钥（可覆盖默认值）
            use_stream_mode: 是否使用Stream模式
            client_id: Stream模式的Client ID
            client_secret: Stream模式的Client Secret
            robot_code: Stream模式的机器人Code

        Returns:
            {"success": bool, "message_id": str, "error": str}
        """
        # 如果启用Stream模式且提供了必要参数，使用Stream API
        if use_stream_mode and client_id and client_secret:
            print(f"🔄 使用Stream模式发送消息")
            return await self._send_message_stream(
                dingtalk_user_id=dingtalk_user_id,
                content=content,
                msg_type=msg_type,
                title=title,
                client_id=client_id,
                client_secret=client_secret,
                robot_code=robot_code or client_id  # 如果没有robot_code，使用client_id
            )
        
        # 否则使用Webhook模式
        print(f"🔄 使用Webhook模式发送消息")
        return await self._send_message_webhook(
            dingtalk_user_id=dingtalk_user_id,
            content=content,
            msg_type=msg_type,
            title=title,
            webhook_url=webhook_url,
            secret=secret
        )

    async def _send_message_webhook(
        self,
        dingtalk_user_id: str = None,
        content: str = None,
        msg_type: str = "markdown",
        title: str = "TaskTree 任务提醒",
        webhook_url: str = None,
        secret: str = None
    ) -> dict:
        """使用Webhook模式发送消息"""
        url = webhook_url or self.webhook_url
        sig_secret = secret or self.secret
        
        if not url:
            return {"success": False, "error": "未配置Webhook URL"}

        # 构建消息体
        if msg_type == "markdown":
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
        else:
            message = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
        
        # 如果指定了用户ID，添加@提及
        if dingtalk_user_id:
            message["at"] = {
                "atUserIds": [dingtalk_user_id]
            }

        try:
            # 如果配置了签名，使用签名验证
            final_url = url
            if sig_secret:
                timestamp, sign = self._generate_sign(sig_secret)
                final_url = f"{url}&timestamp={timestamp}&sign={sign}"

            async with httpx.AsyncClient() as client:
                print(f"📡 发送钉钉消息到: {final_url[:50]}...")
                print(f"📝 消息内容: {message}")
                
                response = await client.post(
                    final_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )

                result = response.json()
                print(f"📬 钉钉响应: {result}")

                if result.get("errcode") == 0:
                    return {
                        "success": True,
                        "message_id": result.get("msgid", "")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("errmsg", "发送失败")
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_message_stream(
        self,
        dingtalk_user_id: str,
        content: str,
        msg_type: str,
        title: str,
        client_id: str,
        client_secret: str,
        robot_code: str
    ) -> dict:
        """使用Stream模式发送消息（单聊）"""
        try:
            # 1. 获取Access Token
            access_token = await self._get_access_token(client_id, client_secret)
            if not access_token:
                return {"success": False, "error": "获取Access Token失败"}
            
            # 2. 构建消息内容
            if msg_type == "markdown":
                msg_param = json.dumps({
                    "title": title,
                    "text": content
                }, ensure_ascii=False)
                msg_key = "sampleMarkdown"
            else:
                msg_param = json.dumps({
                    "content": content
                }, ensure_ascii=False)
                msg_key = "sampleText"
            
            # 3. 调用钉钉消息发送API
            api_url = f"{self.api_base_url}/v1.0/robot/oToMessages/batchSend"
            headers = {
                "Content-Type": "application/json",
                "x-acs-dingtalk-access-token": access_token
            }
            payload = {
                "robotCode": robot_code,
                "userIds": [dingtalk_user_id],
                "msgKey": msg_key,
                "msgParam": msg_param
            }
            
            print(f"📡 Stream模式发送消息:")
            print(f"   API: {api_url}")
            print(f"   Robot Code: {robot_code}")
            print(f"   User ID: {dingtalk_user_id}")
            print(f"   Msg Key: {msg_key}")
            print(f"   Msg Param: {msg_param}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                result = response.json()
                print(f"📬 钉钉Stream API响应: {result}")
                
                # 检查响应
                if response.status_code == 200:
                    # 钉钉新版API成功时返回processQueryKey
                    if "processQueryKey" in result:
                        return {
                            "success": True,
                            "message_id": result.get("processQueryKey", "")
                        }
                    # 或者检查是否有错误码
                    elif result.get("code") == "0" or not result.get("code"):
                        return {
                            "success": True,
                            "message_id": result.get("processQueryKey", "")
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("message", "发送失败")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {result.get('message', '发送失败')}"
                    }
        
        except Exception as e:
            print(f"❌ Stream模式发送消息失败: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def _get_access_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """获取钉钉Access Token（带缓存）"""
        # 检查缓存
        cache_key = f"{client_id}:{client_secret}"
        if cache_key in self._access_token_cache:
            cached = self._access_token_cache[cache_key]
            # 检查是否过期（提前5分钟刷新）
            if time.time() < cached["expires_at"] - 300:
                print(f"✅ 使用缓存的Access Token")
                return cached["token"]
        
        # 获取新的Access Token
        try:
            api_url = f"{self.api_base_url}/v1.0/oauth2/accessToken"
            payload = {
                "appKey": client_id,
                "appSecret": client_secret
            }
            
            print(f"🔑 获取Access Token: {api_url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                
                result = response.json()
                print(f"🔑 Access Token响应: {result}")
                
                if response.status_code == 200 and "accessToken" in result:
                    token = result["accessToken"]
                    expires_in = result.get("expireIn", 7200)  # 默认2小时
                    
                    # 缓存Token
                    self._access_token_cache[cache_key] = {
                        "token": token,
                        "expires_at": time.time() + expires_in
                    }
                    
                    print(f"✅ 获取Access Token成功，有效期: {expires_in}秒")
                    return token
                else:
                    print(f"❌ 获取Access Token失败: {result}")
                    return None
        
        except Exception as e:
            print(f"❌ 获取Access Token异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_sign(self, secret: str) -> tuple:
        """生成签名

        Args:
            secret: 钉钉机器人密钥

        Returns:
            (timestamp, sign)
        """
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = quote(base64.b64encode(hmac_code))
        return timestamp, sign

    async def send_task_reminder(
        self,
        task_name: str,
        project_name: str,
        due_date: str,
        status: str,
        priority: str,
        task_url: str,
        message_id: int = None
    ) -> dict:
        """发送任务提醒

        Args:
            task_name: 任务名称
            project_name: 项目名称
            due_date: 截止时间
            status: 任务状态
            priority: 优先级
            task_url: 任务详情链接
            message_id: 通知记录ID（用于回调）

        Returns:
            发送结果
        """
        # 状态映射
        status_map = {
            "pending": "待处理",
            "in_progress": "进行中",
            "completed": "已完成",
            "cancelled": "已取消"
        }

        # 优先级emoji
        priority_emoji = {
            "high": "🔴 紧急",
            "medium": "🟡 普通",
            "low": "🟢 低优"
        }

        status_text = status_map.get(status, status)
        priority_text = priority_emoji.get(priority, priority)

        # 构建回调链接
        callback_url = f"{task_url}?notify_id={message_id}" if message_id else task_url

        content = f"""## 🔔 任务提醒

**任务名称**: {task_name}
**所属项目**: {project_name}
**任务状态**: {status_text}
**优先级**: {priority_text}
**截止时间**: {due_date or "未设置"}

> [{task_name}]({callback_url})

---
*来自 TaskTree 智能提醒*"""

        return await self.send_message(content, title=f"任务提醒：{task_name}")

    async def send_batch_reminder(
        self,
        tasks: list,
        project_name: str,
        reason: str,
        task_base_url: str
    ) -> dict:
        """发送批量任务提醒

        Args:
            tasks: 任务列表
            project_name: 项目名称
            reason: 提醒原因
            task_base_url: 任务基础链接

        Returns:
            发送结果
        """
        if not tasks:
            return {"success": False, "error": "没有需要提醒的任务"}

        # 构建任务列表
        task_lines = []
        for task in tasks:
            task_url = f"{task_base_url}/project/{task.get('project_id')}?task={task.get('id')}"
            task_lines.append(
                f"- [{task.get('name')}]({task_url}) - {task.get('status_text', '待处理')}"
            )

        content = f"""## 🔔 {reason}

**项目**: {project_name}

{chr(10).join(task_lines)}

---
*来自 TaskTree 智能提醒*"""

        return await self.send_message(
            content,
            title=f"任务提醒 - {project_name}"
        )


# 全局服务实例
dingtalk_service = DingtalkService()
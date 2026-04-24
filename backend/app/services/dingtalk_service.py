"""
TaskTree 钉钉通知服务
====================
封装钉钉机器人Webhook推送功能。
"""
import hmac
import hashlib
import base64
import json
import time
from urllib.parse import quote
import httpx
from typing import Optional


class DingtalkService:
    """钉钉通知服务"""

    def __init__(self, webhook_url: str = None, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret

    async def send_message(
        self,
        dingtalk_user_id: str = None,
        content: str = None,
        msg_type: str = "markdown",
        title: str = "TaskTree 任务提醒",
        webhook_url: str = None,
        secret: str = None
    ) -> dict:
        """发送钉钉消息

        Args:
            dingtalk_user_id: 钉钉用户ID（用于私聊）
            content: 消息内容（Markdown格式）
            msg_type: 消息类型 text/markdown
            title: 标题（仅markdown用）
            webhook_url: Webhook URL（可覆盖默认值）
            secret: 签名密钥（可覆盖默认值）

        Returns:
            {"success": bool, "message_id": str, "error": str}
        """
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
                response = await client.post(
                    final_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )

                result = response.json()

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
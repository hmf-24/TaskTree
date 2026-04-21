"""
TaskTree 智能分析服务 - Minmax 大模型
=====================================
使用 Minmax API 分析任务数据，判断是否需要提醒用户。
"""
import json
import os
import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone


class MinmaxService:
    """Minimax 大模型服务"""

    def __init__(self, api_key: str = None, group_id: str = None):
        self.api_key = api_key or os.getenv("MINMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINMAX_GROUP_ID", "")
        self.base_url = "https://api.minimax.chat/v1"

    async def analyze_tasks(self, user_tasks: list, project_name: str) -> dict:
        """分析任务数据，判断是否需要提醒

        Args:
            user_tasks: 用户任务列表
            project_name: 项目名称

        Returns:
            {
                "need_remind": bool,
                "remind_reason": str,
                "priority": "high/medium/low",
                "message": str,
                "tasks_to_remind": [task_ids]
            }
        """
        if not user_tasks:
            return {
                "need_remind": False,
                "remind_reason": "没有任务",
                "priority": "low",
                "message": "",
                "tasks_to_remind": []
            }

        # 构建任务摘要
        task_summary = self._build_task_summary(user_tasks)

        prompt = f"""你是一个任务管理助手。请分析以下任务数据，判断是否需要提醒用户处理。

项目名称：{project_name}

任务列表：
{task_summary}

请根据以下维度分析：

1. 截止时间：是否有任务即将截止（24小时内）或已逾期？
2. 进度落后：是否有任务长时间（3天以上）没有更新进度？
3. 依赖阻塞：是否有前置任务已完成，可以开始的任务？

请返回JSON格式的分析结果（必须是有效的JSON）：
{{
    "need_remind": true/false,
    "remind_reason": "简短原因（不超过50字）",
    "priority": "high/medium/low",
    "message": "给用户的提醒消息（Markdown格式，不超过200字）",
    "tasks_to_remind": [需要提醒的任务ID列表]
}}

注意：
- 如果没有需要提醒的任务，need_remind 返回 false
- 只返回JSON，不要其他内容"""

        try:
            response = await self._call_api(prompt)
            result = self._parse_response(response)
            return result
        except Exception as e:
            print(f"Minimax API error: {e}")
            # 降级处理：使用规则判断
            return self._fallback_analysis(user_tasks)

    def _build_task_summary(self, tasks: list) -> str:
        """构建任务摘要"""
        lines = []
        now = datetime.now(timezone.utc)

        for task in tasks:
            due = task.get("due_date")
            status = task.get("status", "pending")
            progress = task.get("progress", 0)
            updated = task.get("updated_at", "")

            # 计算剩余时间
            remaining = ""
            if due:
                try:
                    due_date = datetime.fromisoformat(due.replace("Z", "+00:00"))
                    if due_date > now:
                        delta = due_date - now
                        remaining = f"剩余{delta.days}天"
                    else:
                        remaining = "已逾期"
                except:
                    pass

            # 更新时间
            days_ago = ""
            if updated:
                try:
                    updated_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    delta = now - updated_date
                    days_ago = f"距今{delta.days}天"
                except:
                    pass

            line = f"- 任务{task['id']}: {task['name']} | 状态:{status} | 进度:{progress}% | 截止:{remaining or '无'} | 更新:{days_ago or '无'}"
            lines.append(line)

        return "\n".join(lines) if lines else "暂无任务"

    async def _call_api(self, prompt: str) -> str:
        """调用 Minmax API"""
        import httpx

        url = f"{self.base_url}/text/chatcompletion_v2"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "abab6.5s-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业的任务管理助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")

            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _parse_response(self, response: str) -> dict:
        """解析 API 响应"""
        try:
            # 提取 JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "need_remind": data.get("need_remind", False),
                    "remind_reason": data.get("remind_reason", ""),
                    "priority": data.get("priority", "low"),
                    "message": data.get("message", ""),
                    "tasks_to_remind": data.get("tasks_to_remind", [])
                }
        except:
            pass

        return self._fallback_analysis([])

    def _fallback_analysis(self, tasks: list) -> dict:
        """降级分析：使用简单规则判断"""
        now = datetime.now(timezone.utc)
        need_remind = False
        reason = ""
        priority = "low"
        task_ids = []

        for task in tasks:
            # 检查逾期
            if task.get("due_date"):
                try:
                    due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
                    if due < now and task.get("status") != "completed":
                        need_remind = True
                        reason = "有逾期任务"
                        priority = "high"
                        task_ids.append(task["id"])
                except:
                    pass

            # 检查即将截止（24小时内）
            if not need_remind and task.get("due_date"):
                try:
                    due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
                    delta = due - now
                    if 0 < delta.total_seconds() < 86400:
                        need_remind = True
                        reason = "有任务即将截止"
                        priority = "high"
                        task_ids.append(task["id"])
                except:
                    pass

        return {
            "need_remind": need_remind,
            "remind_reason": reason,
            "priority": priority,
            "message": f"您有{len(task_ids)}个任务需要关注" if need_remind else "",
            "tasks_to_remind": task_ids
        }


# 全局服务实例
minimax_service = MinmaxService()
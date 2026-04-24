"""
TaskTree 大模型服务
================
统一支持多种大模型提供商：Minimax、OpenAI、Anthropic。
用于智能分析任务并生成提醒内容和任务分类。
"""
import json
import os
import re
import httpx
from typing import Optional, Any
from datetime import datetime, timedelta, timezone


class LLMService:
    """统一大模型服务"""

    PROVIDERS = {
        "minimax": {
            "name": "Minimax",
            "models": ["abab6.5s-chat", "abab6.5g-chat"],
            "default_model": "abab6.5s-chat"
        },
        "openai": {
            "name": "OpenAI",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "default_model": "gpt-4o-mini"
        },
        "anthropic": {
            "name": "Anthropic",
            "models": ["claude-sonnet-4-20250514", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "default_model": "claude-sonnet-4-20250514"
        }
    }

    def __init__(
        self,
        provider: str = "minimax",
        api_key: str = None,
        model: str = None,
        group_id: str = None
    ):
        self.provider = provider
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or "MiniMax-M2.7"
        self.group_id = group_id

    async def analyze_tasks(
        self,
        user_tasks: list,
        project_name: str,
        analysis_config: dict = None
    ) -> dict:
        """分析任务数据，判断是否需要提醒（多维度智能分析）"""
        if not user_tasks:
            return self._empty_result()

        # 默认配置：启用所有分析维度
        config = analysis_config or {
            "overdue": True,
            "progress_stalled": True,
            "dependency_unblocked": True,
            "team_load": True,
            "complexity": True,
            "risk_prediction": True
        }

        if not self.api_key:
            return self._fallback_analysis(user_tasks, config)

        task_summary = self._build_task_summary(user_tasks)
        analysis_dims = self._build_analysis_dims(config)

        prompt = f"""你是一个专业的任务管理顾问。请分析以下任务数据：

项目名称：{project_name}
任务列表：
{task_summary}

请根据以下维度分析：
{analysis_dims}

返回JSON格式：
{{
    "need_remind": true/false,
    "remind_reason": "简短原因",
    "priority": "high/medium/low",
    "message": "提醒消息(Markdown)",
    "tasks_to_remind": [task_ids],
    "plan": "规划建议",
    "analysis": {{
        "overdue": [{{"task_id": 1, "task_name": "name", "days_overdue": 2}}],
        "progress_stalled": [{{"task_id": 2, "task_name": "name", "days_no_update": 5}}],
        "dependency_unblocked": [{{"task_id": 3, "task_name": "name", "blocked_by": "name"}}],
        "team_load": {{"concurrent_tasks": 5, "avg_progress": 45, "load_status": "normal/heavy/overloaded"}},
        "complexity": [{{"task_id": 4, "task_name": "name", "complexity_score": 8}}],
        "risk_prediction": [{{"task_id": 5, "task_name": "name", "risk_level": "high/medium/low"}}]
    }}
}}"""

        try:
            response = await self._call_api(prompt)
            return self._parse_response(response)
        except Exception as e:
            print(f"LLM API error: {e}")
            return self._fallback_analysis(user_tasks, config)

    async def analyze_task_complexity(
        self,
        task_info: dict,
        user_context: dict = None
    ) -> dict:
        """分析单个任务的复杂度"""
        if not self.api_key:
            return self._simple_complexity_analysis(task_info)

        prompt = f"""分析任务复杂度：

任务：{task_info.get('name', '')}
描述：{task_info.get('description', '')}
预估：{task_info.get('estimated_time', 0)}h
子任务：{task_info.get('subtasks_count', 0)}
依赖：{task_info.get('dependencies_count', 0)}

JSON：{{"complexity_score": 1-10, "complexity_level": "low/medium/high", "factors": [], "suggestions": []}}"""

        try:
            response = await self._call_api(prompt)
            return self._parse_response(response)
        except:
            return self._simple_complexity_analysis(task_info)

    async def generate_task_suggestions(
        self,
        tasks: list,
        user_intent: str = None
    ) -> dict:
        """根据用户意图生成任务建议"""
        if not self.api_key:
            return {"schedule": [], "reason": "未配置API Key"}

        task_summary = self._build_task_summary(tasks)
        prompt = f"""根据用户意图安排任务：

意图：{user_intent or "帮我安排工作"}
任务：
{task_summary}

JSON：{{"schedule": [{{"task_id": 1, "suggested_time": "上午"}}], "priority_order": []}}"""

        try:
            response = await self._call_api(prompt)
            return self._parse_response(response)
        except:
            return {"schedule": [], "reason": str(Exception)}

    async def auto_classify_tasks(
        self,
        tasks: list,
        project_context: dict = None
    ) -> dict:
        """自动分类任务"""
        if not self.api_key:
            return {"classifications": [], "tags": []}

        task_summary = self._build_task_summary(tasks)
        prompt = f"""分析并分类任务：

项目：{project_context.get('name', '') if project_context else ''}
任务：
{task_summary}

JSON：{{
    "classifications": [{{"task_id": 1, "suggested_tags": ["重要"], "suggested_priority": "high", "category": "开发"}}],
    "tags": [{{"name": "重要", "color": "#ff4d4f"}}]
}}"""

        try:
            response = await self._call_api(prompt)
            return self._parse_response(response)
        except:
            return {"classifications": [], "tags": []}

    async def test_connection(self) -> dict:
        """测试大模型连通性，返回响应内容和耗时"""
        import time
        start = time.time()
        try:
            prompt = "请回复：ok，如果收到这条消息请在回复前加上当前时间。"
            response = await self._call_api(prompt)
            elapsed = int((time.time() - start) * 1000)
            return {
                "success": True,
                "model": self.model,
                "response_time_ms": elapsed,
                "sample_output": response[:200] if response else "",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        通用对话接口，支持多轮对话
        
        Args:
            messages: 对话历史，格式为 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数，控制随机性 (0-1)
            max_tokens: 最大生成 token 数
            
        Returns:
            str: AI 的回复内容
        """
        p = self.provider.lower()
        
        if p in ("minimax", "minmax"):
            return await self._chat_minimax(messages, temperature, max_tokens)
        elif p == "openai":
            return await self._chat_openai(messages, temperature, max_tokens)
        elif p == "anthropic":
            return await self._chat_anthropic(messages, temperature, max_tokens)
        else:
            raise Exception(f"Unknown provider: {self.provider}")

    async def _chat_minimax(self, messages: list, temperature: float, max_tokens: int) -> str:
        """Minimax 对话接口"""
        url = "https://api.minimaxi.com/anthropic/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        # 提取 system 消息
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})
        
        payload = {
            "model": self.model or "MiniMax-M2.7",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages
        }
        
        if system_content:
            payload["system"] = system_content
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            data = response.json()
            # Minimax 返回的 content 数组中可能包含 thinking 和 text 类型
            # 需要找到 type="text" 的内容
            content_list = data.get("content", [])
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
            return ""

    async def _chat_openai(self, messages: list, temperature: float, max_tokens: int) -> str:
        """OpenAI 对话接口"""
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    async def _chat_anthropic(self, messages: list, temperature: float, max_tokens: int) -> str:
        """Anthropic 对话接口"""
        url = "https://api.anthropic.com/v1/messages"
        
        # 提取 system 消息
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})
        
        payload = {
            "model": self.model or "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages
        }
        
        if system_content:
            payload["system"] = system_content
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json=payload,
                timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            return response.json().get("content", [{}])[0].get("text", "")

    async def parse_progress(self, message: str, user_id: int = None) -> dict:
        """
        解析用户通过钉钉发送的进度反馈消息
        
        Args:
            message: 用户发送的消息内容
            user_id: 用户 ID（用于日志记录）
            
        Returns:
            dict: 解析结果，包含进度类型、关键词、数值等
        """
        if not self.api_key:
            return self._simple_progress_parse(message)

        prompt = f"""你是一个任务进度解析助手。请分析用户的钉钉消息，提取进度信息。

用户消息：{message}

请返回 JSON 格式的解析结果：
{{
    "progress_type": "completed|in_progress|problem|extend|query",
    "confidence": 0.0-1.0,
    "keywords": ["关键词1", "关键词2"],
    "progress_value": 0-100,
    "problem_description": "问题描述（如果有）",
    "extend_days": 0,
    "raw_message": "{message}"
}}

进度类型说明：
- completed: 任务已完成
- in_progress: 任务进行中，可能包含进度百分比
- problem: 遇到问题或障碍
- extend: 请求延期
- query: 查询任务状态

关键词应该是任务名称或相关描述词。
如果消息中有百分比数字，提取到 progress_value。
如果消息中有"延期"、"推迟"等词，提取天数到 extend_days。"""

        try:
            response = await self._call_api(prompt)
            result = self._parse_response(response)
            
            # 确保返回的是有效的进度解析结果
            if result and "progress_type" in result:
                return result
            else:
                return self._simple_progress_parse(message)
        except Exception as e:
            print(f"LLM 进度解析失败: {e}")
            return self._simple_progress_parse(message)

    async def parse_user_intent(self, text: str) -> dict:
        """解析用户自然语言输入的意图"""
        if not self.api_key:
            return self._simple_intent_parse(text)

        prompt = f"""解析用户输入的提醒意图：

输入：{text}

JSON：{{
    "intent": "schedule_remind/once_remind/auto_plan/custom_rule",
    "params": {{"time": "15:00", "repeat": "daily/once", "conditions": []}},
    "confidence": 0.9
}}"""

        try:
            response = await self._call_api(prompt)
            return self._parse_response(response)
        except:
            return self._simple_intent_parse(text)

    def _build_task_summary(self, tasks: list) -> str:
        """构建任务摘要"""
        lines = []
        now = datetime.now(timezone.utc)
        for task in tasks:
            due = task.get("due_date", "")
            status = task.get("status", "pending")
            progress = task.get("progress", 0)
            remaining = ""
            if due:
                try:
                    due_date = datetime.fromisoformat(due.replace("Z", "+00:00"))
                    remaining = f"剩余{(due_date - now).days}天" if due_date > now else "已逾期"
                except:
                    pass
            lines.append(f"- 任务{task['id']}: {task['name']} | {status} | {progress}% | {remaining}")
        return "\n".join(lines) if lines else "暂无任务"

    def _build_analysis_dims(self, config: dict) -> str:
        """构建分析维度"""
        dims = []
        if config.get("overdue"):
            dims.append("1. 截止时间：是否逾期或即将截止？")
        if config.get("progress_stalled"):
            dims.append("2. 进度落后：3天以上无更新？")
        if config.get("dependency_unblocked"):
            dims.append("3. 依赖解除：前置任务完成可开始？")
        if config.get("team_load"):
            dims.append("4. 团队负荷：并发任务数量？")
        if config.get("complexity"):
            dims.append("5. 任务复杂度：哪些最复杂？")
        if config.get("risk_prediction"):
            dims.append("6. 风险预测：哪些可能延期？")
        return "\n".join(dims)

    async def _call_api(self, prompt: str) -> str:
        """调用大模型API"""
        p = self.provider.lower()
        # 兼容 minimax / minmax 两种写法
        if p in ("minimax", "minmax"):
            return await self._call_minimax(prompt)
        elif p == "openai":
            return await self._call_openai(prompt)
        elif p == "anthropic":
            return await self._call_anthropic(prompt)
        raise Exception(f"Unknown provider: {self.provider}")

    async def _call_minimax(self, prompt: str) -> str:
        url = "https://api.minimaxi.com/anthropic/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or "MiniMax-M2.7",
            "max_tokens": 1500,
            "system": "你是一个专业的任务管理助手。",
            "messages": [{"role": "user", "content": prompt}]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            data = response.json()
            # Minimax 返回的 content 数组中可能包含 thinking 和 text 类型
            content_list = data.get("content", [])
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
            return ""

    async def _call_openai(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "你是一个专业的任务管理助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    async def _call_anthropic(self, prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model or "claude-sonnet-4-20250514",
            "max_tokens": 1500,
            "system": "你是一个专业的任务管理助手。",
            "messages": [{"role": "user", "content": prompt}]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json=payload,
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")
            return response.json().get("content", [{}])[0].get("text", "")

    def _parse_response(self, response: str) -> dict:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "need_remind": data.get("need_remind", False),
                    "remind_reason": data.get("remind_reason", ""),
                    "priority": data.get("priority", "low"),
                    "message": data.get("message", ""),
                    "tasks_to_remind": data.get("tasks_to_remind", []),
                    "plan": data.get("plan", ""),
                    "analysis": data.get("analysis", {})
                }
        except:
            pass
        return self._empty_result()

    def _empty_result(self) -> dict:
        return {
            "need_remind": False,
            "remind_reason": "",
            "priority": "low",
            "message": "",
            "tasks_to_remind": [],
            "plan": "",
            "analysis": {}
        }

    def _fallback_analysis(self, tasks: list, config: dict) -> dict:
        now = datetime.now(timezone.utc)
        need_remind = False
        reason = ""
        priority = "low"
        task_ids = []
        analysis = {
            "overdue": [],
            "progress_stalled": [],
            "dependency_unblocked": [],
            "team_load": {"concurrent_tasks": 0, "avg_progress": 0, "load_status": "normal"},
            "complexity": [],
            "risk_prediction": []
        }

        for task in tasks:
            if task.get("due_date"):
                try:
                    due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
                    if due < now and task.get("status") != "completed":
                        need_remind = True
                        reason = "有逾期任务"
                        priority = "high"
                        task_ids.append(task["id"])
                        analysis["overdue"].append({"task_id": task["id"], "task_name": task["name"]})
                except:
                    pass

        return {
            "need_remind": need_remind,
            "remind_reason": reason,
            "priority": priority,
            "message": f"您有{len(task_ids)}个任务需要关注",
            "tasks_to_remind": task_ids,
            "plan": "请优先处理逾期任务",
            "analysis": analysis
        }

    def _simple_complexity_analysis(self, task_info: dict) -> dict:
        score = min(3 + (task_info.get("estimated_time", 0) // 4) + (task_info.get("subtasks_count", 0) // 2), 10)
        level = "low" if score <= 3 else "medium" if score <= 6 else "high"
        return {"complexity_score": score, "complexity_level": level, "factors": [], "suggestions": []}

    def _simple_intent_parse(self, text: str) -> dict:
        intent = "custom_rule"
        params = {"repeat": "once", "conditions": []}
        confidence = 0.5
        if "每天" in text:
            params["repeat"] = "daily"
            confidence = 0.8
        elif "每周" in text:
            params["repeat"] = "weekly"
            confidence = 0.8
        match = re.search(r"(\d+)[点时]", text)
        if match:
            params["time"] = f"{match.group(1)}:00"
        return {"intent": intent, "params": params, "raw": text, "confidence": confidence}

    def _simple_progress_parse(self, message: str) -> dict:
        """简单的进度解析降级方案（规则引擎）"""
        progress_type = "query"
        confidence = 0.5
        keywords = []
        progress_value = 0
        problem_description = ""
        extend_days = 0
        
        # 检测进度类型
        if any(word in message for word in ["完成", "已完成", "done", "finished"]):
            progress_type = "completed"
            confidence = 0.9
        elif any(word in message for word in ["进行中", "进行", "doing", "in progress", "进度"]):
            progress_type = "in_progress"
            confidence = 0.8
        elif any(word in message for word in ["问题", "遇到", "卡住", "困难", "issue", "problem", "stuck"]):
            progress_type = "problem"
            confidence = 0.8
        elif any(word in message for word in ["延期", "推迟", "延后", "extend", "delay"]):
            progress_type = "extend"
            confidence = 0.8
        
        # 提取百分比
        percent_match = re.search(r"(\d+)%", message)
        if percent_match:
            progress_value = int(percent_match.group(1))
            confidence = min(confidence + 0.1, 1.0)
        
        # 提取延期天数
        if progress_type == "extend":
            days_match = re.search(r"(\d+)\s*天", message)
            if days_match:
                extend_days = int(days_match.group(1))
        
        # 提取问题描述
        if progress_type == "problem":
            # 尝试提取冒号后的内容
            colon_match = re.search(r"[:：](.*?)(?:[。，、]|$)", message)
            if colon_match:
                problem_description = colon_match.group(1).strip()
            else:
                problem_description = message
        
        # 提取关键词（简单的词语分割）
        # 移除常见的虚词
        stop_words = {"的", "了", "和", "是", "在", "我", "你", "他", "已", "正在", "已经"}
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", message)
        keywords = [w for w in words if w not in stop_words and len(w) > 1][:5]
        
        return {
            "progress_type": progress_type,
            "confidence": confidence,
            "keywords": keywords,
            "progress_value": progress_value,
            "problem_description": problem_description,
            "extend_days": extend_days,
            "raw_message": message
        }


llm_service = LLMService()

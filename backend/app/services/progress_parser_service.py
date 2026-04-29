"""
进度解析服务
============
使用 LLM 解析用户的进度反馈消息，提取进度类型、关键信息等。
支持规则引擎降级方案。

功能：
- LLM 进度解析（支持自然语言理解）
- 规则引擎降级（关键词识别）
- 提取进度类型、百分比、问题描述、延期天数等
"""
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.services.llm_service import LLMService


class ProgressParserService:
    """进度解析服务"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化进度解析服务
        
        Args:
            llm_service: LLM 服务实例（可选，如果不提供则只使用规则引擎）
        """
        self.llm_service = llm_service
        
        # 进度类型关键词映射
        self.type_keywords = {
            "completed": ["完成", "完成了", "做完", "做完了", "搞定", "搞定了", "结束", "结束了", "finished", "done", "complete"],
            "in_progress": ["进行中", "正在做", "正在进行", "开始", "开始了", "进度", "进展", "in progress", "working on", "started"],
            "problem": ["问题", "困难", "阻塞", "卡住", "遇到", "bug", "错误", "异常", "issue", "problem", "blocked", "stuck"],
            "extend": ["延期", "推迟", "延后", "需要更多时间", "来不及", "delay", "postpone", "extend"],
            "query": ["查询", "状态", "怎么样", "如何", "进展", "情况", "query", "status", "how"]
        }

    def parse(self, message: str, task_name: Optional[str] = None) -> Dict[str, Any]:
        """
        解析进度反馈消息（优先使用 LLM）
        
        Args:
            message: 用户消息内容
            task_name: 任务名称（可选，用于上下文）
            
        Returns:
            Dict: 解析结果，包含：
                - type: 进度类型（completed/in_progress/problem/extend/query）
                - progress: 进度百分比（0-100）
                - description: 问题描述或备注
                - extend_days: 延期天数
                - confidence: 置信度（0-1）
                - keywords: 提取的关键词列表
        """
        # 注意：这个方法是同步的，不能调用异步的LLM服务
        # 直接使用规则引擎
        return self._parse_with_rules(message)

    def parse_with_fallback(self, message: str, task_name: Optional[str] = None) -> Dict[str, Any]:
        """
        解析进度反馈消息（带降级处理）
        
        这是 parse() 的别名，提供更明确的语义
        """
        return self.parse(message, task_name)

    def _parse_with_llm(self, message: str, task_name: Optional[str] = None) -> Dict[str, Any]:
        """
        使用 LLM 解析进度反馈
        
        Args:
            message: 用户消息内容
            task_name: 任务名称（可选）
            
        Returns:
            Dict: 解析结果
        """
        # 构建提示词
        prompt = self._build_prompt(message, task_name)
        
        # 调用 LLM
        response = self.llm_service.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度，更确定性的输出
            max_tokens=500
        )
        
        # 解析 LLM 响应
        try:
            result = json.loads(response)
            
            # 验证必需字段
            if "type" not in result:
                raise ValueError("LLM 响应缺少 type 字段")
            
            # 设置默认值
            result.setdefault("progress", 0)
            result.setdefault("description", "")
            result.setdefault("extend_days", 0)
            result.setdefault("confidence", 0.8)
            result.setdefault("keywords", [])
            
            return result
            
        except json.JSONDecodeError:
            # JSON 解析失败，尝试从文本中提取
            return self._extract_from_text(response)

    def _parse_with_rules(self, message: str) -> Dict[str, Any]:
        """
        使用规则引擎解析进度反馈（降级方案）
        
        Args:
            message: 用户消息内容
            
        Returns:
            Dict: 解析结果
        """
        message_lower = message.lower()
        
        # 识别进度类型
        progress_type = "query"  # 默认为查询
        confidence = 0.5
        keywords = []
        
        for ptype, kwords in self.type_keywords.items():
            for keyword in kwords:
                if keyword in message_lower:
                    progress_type = ptype
                    confidence = 0.7
                    keywords.append(keyword)
                    break
            if keywords:
                break
        
        # 提取进度百分比
        progress = self._extract_progress(message)
        
        # 提取延期天数
        extend_days = self._extract_extend_days(message)
        
        # 提取问题描述
        description = self._extract_description(message, progress_type)
        
        return {
            "type": progress_type,
            "progress": progress,
            "description": description,
            "extend_days": extend_days,
            "confidence": confidence,
            "keywords": keywords
        }

    def _build_prompt(self, message: str, task_name: Optional[str] = None) -> str:
        """
        构建 LLM 提示词
        
        Args:
            message: 用户消息内容
            task_name: 任务名称（可选）
            
        Returns:
            str: 提示词
        """
        task_context = f"任务名称：{task_name}\n" if task_name else ""
        
        prompt = f"""你是一个任务进度解析助手。请分析用户的进度反馈消息，提取关键信息。

{task_context}用户消息：{message}

请以 JSON 格式返回解析结果，包含以下字段：
- type: 进度类型，必须是以下之一：
  * "completed": 任务已完成
  * "in_progress": 任务进行中
  * "problem": 遇到问题
  * "extend": 需要延期
  * "query": 查询状态
- progress: 进度百分比（0-100 的整数），如果消息中没有明确提到，根据 type 推断：
  * completed → 100
  * in_progress → 根据描述推断（默认 50）
  * problem → 保持当前进度（返回 0 表示不更新）
  * extend → 保持当前进度（返回 0 表示不更新）
  * query → 不更新（返回 0）
- description: 问题描述或备注（如果有）
- extend_days: 延期天数（如果是延期类型）
- confidence: 置信度（0-1 之间的小数）
- keywords: 提取的关键词列表

示例输出：
{{"type": "completed", "progress": 100, "description": "", "extend_days": 0, "confidence": 0.95, "keywords": ["完成"]}}
{{"type": "in_progress", "progress": 60, "description": "已完成前端部分", "extend_days": 0, "confidence": 0.9, "keywords": ["进度", "60%"]}}
{{"type": "problem", "progress": 0, "description": "API 接口返回 500 错误", "extend_days": 0, "confidence": 0.85, "keywords": ["问题", "错误"]}}

请只返回 JSON，不要包含其他文字。"""
        
        return prompt

    def _extract_progress(self, message: str) -> int:
        """
        从消息中提取进度百分比
        
        Args:
            message: 用户消息内容
            
        Returns:
            int: 进度百分比（0-100）
        """
        # 匹配百分比模式：50%、50、百分之50
        patterns = [
            r'(\d+)\s*%',  # 50%
            r'(\d+)\s*percent',  # 50 percent
            r'百分之\s*(\d+)',  # 百分之50
            r'进度\s*[:：]?\s*(\d+)',  # 进度：50
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                progress = int(match.group(1))
                return min(100, max(0, progress))  # 限制在 0-100 范围
        
        return 0

    def _extract_extend_days(self, message: str) -> int:
        """
        从消息中提取延期天数
        
        Args:
            message: 用户消息内容
            
        Returns:
            int: 延期天数
        """
        # 匹配延期天数模式：延期3天、推迟2天、需要5天
        patterns = [
            r'延期\s*(\d+)\s*天',
            r'推迟\s*(\d+)\s*天',
            r'延后\s*(\d+)\s*天',
            r'需要\s*(\d+)\s*天',
            r'delay\s+(\d+)\s+days?',
            r'extend\s+(\d+)\s+days?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 0

    def _extract_description(self, message: str, progress_type: str) -> str:
        """
        提取问题描述或备注
        
        Args:
            message: 用户消息内容
            progress_type: 进度类型
            
        Returns:
            str: 描述文本
        """
        # 如果是问题类型，尝试提取问题描述
        if progress_type == "problem":
            # 移除常见的前缀词
            desc = message
            for prefix in ["遇到问题", "遇到", "问题", "bug", "错误", "异常", "："]:
                desc = desc.replace(prefix, "").strip()
            return desc
        
        # 其他类型，返回原消息（去除进度类型关键词）
        desc = message
        for keywords in self.type_keywords.values():
            for keyword in keywords:
                desc = desc.replace(keyword, "").strip()
        
        return desc if desc != message else ""

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        从 LLM 文本响应中提取结构化信息（当 JSON 解析失败时）
        
        Args:
            text: LLM 响应文本
            
        Returns:
            Dict: 解析结果
        """
        # 尝试找到 JSON 部分
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # 完全失败，返回默认结果
        return {
            "type": "query",
            "progress": 0,
            "description": text[:200],  # 截取前 200 字符
            "extend_days": 0,
            "confidence": 0.3,
            "keywords": []
        }

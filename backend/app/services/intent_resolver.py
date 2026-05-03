"""
意图解析器
==========
TaskTree 意图理解的核心模块，参考 Claude Code 的三层处理架构:

Level 1: 斜杠命令 → 确定性路由 (零延迟)
Level 2: 规则引擎 → 快速匹配 (毫秒级)
Level 3: LLM 深度理解 → 上下文增强 (秒级)

设计原则 (来自 Claude Code):
- handlePromptSubmit → 统一入口
- 斜杠命令优先解析
- processUserInput → 输入预处理
- queryLoop → LLM 查询循环
- System Prompt 引导意图理解
- AskUserQuestion → 主动澄清
"""
import json
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.slash_commands import (
    SlashCommandRouter,
    IntentType,
    IntentResult,
    slash_command_router,
)
from app.services.intent_prompts import (
    build_intent_system_prompt,
    build_intent_user_prompt,
    get_clarification_message,
)
from app.services.context_builder import ContextBuilder
from app.services.llm_service import LLMService


class IntentResolver:
    """
    意图解析器 — 三级处理架构
    
    对应 Claude Code 的处理流程:
    handlePromptSubmit → processUserInput → queryLoop
    
    我们的流程:
    resolve() → _try_slash_command() → _try_rule_engine() → _resolve_with_llm()
    """
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
        self.slash_router = slash_command_router
        self.context_builder = ContextBuilder(db)
    
    async def resolve(
        self,
        message: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """
        统一意图解析入口
        
        三级处理:
        1. 斜杠命令 (确定性, 零延迟)
        2. 规则引擎 (快速匹配, 高置信度时直接返回)
        3. LLM 深度理解 (带上下文, 秒级)
        
        Args:
            message: 用户原始消息
            user_id: 用户 ID
            context: 预构建的上下文 (如果已有)
            
        Returns:
            IntentResult: 意图解析结果
        """
        # 预处理: 清理消息
        cleaned = self._preprocess(message)
        
        if not cleaned:
            return IntentResult(
                intent=IntentType.GENERAL_CHAT,
                confidence=1.0,
                raw_message=message,
                source="preprocess",
                clarification="消息内容为空",
            )
        
        # ── Level 1: 斜杠命令 ────────────────────────────────
        if self.slash_router.is_slash_command(cleaned):
            result = self.slash_router.parse(cleaned)
            if result:
                print(f"🎯 [L1/SlashCommand] /{cleaned.split()[0][1:]} → {result.intent.value} (conf={result.confidence})")
                return result
        
        # ── Level 2: 规则引擎快速匹配 ────────────────────────
        rule_result = self._try_rule_engine(cleaned)
        if rule_result and rule_result.confidence >= 0.85:
            print(f"🎯 [L2/RuleEngine] → {rule_result.intent.value} (conf={rule_result.confidence})")
            return rule_result
        
        # ── Level 3: LLM 深度理解 ────────────────────────────
        # 构建上下文 (如果未提供)
        if context is None:
            context = await self.context_builder.build(user_id)
        
        llm_result = await self._resolve_with_llm(
            cleaned, user_id, context, hint=rule_result
        )
        print(f"🎯 [L3/LLM] → {llm_result.intent.value} (conf={llm_result.confidence})")
        return llm_result
    
    # ── 预处理 ──────────────────────────────────────────────────

    def _preprocess(self, message: str) -> str:
        """
        输入预处理
        
        参考 Claude Code 的 expandPastedTextRefs + exit 命令检测
        """
        # 去除前后空白
        cleaned = message.strip()
        
        # 去除钉钉消息中可能的 @机器人 前缀
        # 钉钉消息中 @机器人 已被 SDK 去除，但以防万一
        cleaned = re.sub(r'^@\S+\s*', '', cleaned).strip()
        
        return cleaned
    
    # ── Level 2: 规则引擎 ──────────────────────────────────────

    def _try_rule_engine(self, message: str) -> Optional[IntentResult]:
        """
        规则引擎快速匹配
        
        对于高频、模式明确的意图，使用关键词+正则快速判断。
        仅在高置信度 (>=0.85) 时被 resolve() 采纳。
        """
        msg_lower = message.lower().replace(" ", "")
        
        # ── 查询任务列表 ──
        list_keywords = [
            "我的任务", "任务列表", "所有任务", "我有哪些任务",
            "查任务", "任务有哪些", "看看任务", "查看任务",
        ]
        if any(kw in msg_lower for kw in list_keywords):
            return IntentResult(
                intent=IntentType.QUERY_TASK_LIST,
                confidence=0.95,
                raw_message=message,
                source="rule_engine",
            )
        
        if msg_lower in ("list", "ls", "任务"):
            return IntentResult(
                intent=IntentType.QUERY_TASK_LIST,
                confidence=0.90,
                raw_message=message,
                source="rule_engine",
            )
        
        # ── 查询任务详情 ──
        detail_patterns = [
            # "详细说下XX" / "说下XX" / "看下XX" / "描述一下XX" — 明确要求卡片
            (r'^(?:详细)?(?:说下|说说|看下|看看|描述一下|介绍一下)\s*(.+?)(?:这个)?(?:任务|的情况|的详情)?$', 0.90),
            # "XX的详情" / "XX的情况" — 偏向卡片
            (r'^(.+?)(?:的|这个)\s*(?:详情|情况|详细信息)$', 0.88),
            # "XX的进度" / "XX的状态" / "XX怎么样了" — 可能是追问，交给 LLM
            (r'^(.+?)(?:的|这个)\s*(?:进度|状态)$', 0.75),
            (r'^(.+?)\s*(?:怎么样了?|什么情况|什么状态|如何了?|咋样了?)$', 0.75),
            # "XX目前进度如何" — 明确是追问进度，交给 LLM
            (r'^(.+?)(?:目前|现在)?(?:进度|状态)(?:如何|怎样|怎么样).*$', 0.70),
            # "查看XX" / "查下XX"（非列表意图）
            (r'^(?:查看|查下|查询)\s*(.+?)(?:这个)?(?:任务)?(?:的详情)?$', 0.85),
        ]
        for pattern, conf in detail_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                task_name = match.group(1).strip()
                if task_name and len(task_name) > 1:
                    return IntentResult(
                        intent=IntentType.QUERY_TASK_DETAIL,
                        confidence=conf,
                        task_reference={"name": task_name, "id": None},
                        raw_message=message,
                        source="rule_engine",
                    )
        
        # ── 完成任务 ──
        completed_patterns = [
            (r'^(.+?)\s*(完成了|做完了|搞定了|结束了|finished|done)$', 0.90),
            (r'^(完成|搞定|做完)\s+(.+)$', 0.88),
        ]
        for pattern, conf in completed_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # 提取任务名称
                task_name = match.group(1).strip()
                if match.lastindex and match.lastindex >= 2:
                    # 第二个模式: "完成 任务名"
                    task_name = match.group(2).strip()
                
                return IntentResult(
                    intent=IntentType.UPDATE_PROGRESS,
                    confidence=conf,
                    task_reference={"name": task_name, "id": None},
                    params={"status": "completed", "progress": 100},
                    raw_message=message,
                    source="rule_engine",
                )
        
        # ── 进度更新 ──
        progress_match = re.search(
            r'(.+?)\s*(?:进度|progress)\s*[:：]?\s*(\d+)\s*%',
            message, re.IGNORECASE
        )
        if progress_match:
            task_name = progress_match.group(1).strip()
            progress = int(progress_match.group(2))
            return IntentResult(
                intent=IntentType.UPDATE_PROGRESS,
                confidence=0.90,
                task_reference={"name": task_name, "id": None},
                params={
                    "progress": min(100, max(0, progress)),
                    "status": "completed" if progress >= 100 else "in_progress",
                },
                raw_message=message,
                source="rule_engine",
            )
        
        # ── 创建任务 ──
        create_patterns = [
            r'^(?:创建|新建|添加|新增)\s*(?:一个|个)?\s*(?:任务|task)\s*[:：]?\s*(.+)$',
            r'^(?:帮我|请)\s*(?:创建|新建|添加)\s*(?:一个|个)?\s*(.+?)(?:的任务|任务)?$',
        ]
        for pattern in create_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                task_name = match.group(1).strip()
                if task_name:
                    return IntentResult(
                        intent=IntentType.CREATE_TASK,
                        confidence=0.88,
                        params={"new_task_name": task_name},
                        raw_message=message,
                        source="rule_engine",
                    )
        
        # ── 分析项目 ──
        analyze_keywords = ["分析", "分析一下", "项目分析", "项目进展"]
        if any(kw in msg_lower for kw in analyze_keywords):
            return IntentResult(
                intent=IntentType.ANALYZE_PROJECT,
                confidence=0.85,
                raw_message=message,
                source="rule_engine",
            )
        
        # ── 帮助 ──
        help_keywords = ["帮助", "help", "使用说明", "怎么用"]
        if any(kw in msg_lower for kw in help_keywords):
            help_text = self.slash_router._format_help_text()
            return IntentResult(
                intent=IntentType.GENERAL_CHAT,
                confidence=0.90,
                params={"help_text": help_text},
                raw_message=message,
                source="rule_engine",
            )
        
        # ── 规则引擎无法高置信度判断 ──
        # 返回低置信度的猜测，作为 LLM 的 hint
        return self._guess_intent(message)
    
    def _guess_intent(self, message: str) -> Optional[IntentResult]:
        """
        低置信度猜测 — 为 LLM 提供 hint
        
        不会被 resolve() 直接采纳 (置信度 < 0.85)，
        但会传递给 LLM 作为参考。
        """
        msg = message.lower()
        
        # 包含进度相关词汇
        if any(kw in msg for kw in ["完成", "进度", "开始", "做完"]):
            return IntentResult(
                intent=IntentType.UPDATE_PROGRESS,
                confidence=0.50,
                raw_message=message,
                source="rule_engine",
            )
        
        # 包含查询相关词汇
        if any(kw in msg for kw in ["怎么样", "状态", "情况", "查看", "看看", "详细", "说下", "描述", "介绍"]):
            return IntentResult(
                intent=IntentType.QUERY_TASK_DETAIL,
                confidence=0.45,
                raw_message=message,
                source="rule_engine",
            )
        
        # 包含修改相关词汇
        if any(kw in msg for kw in ["改", "修改", "延期", "推迟", "截止"]):
            return IntentResult(
                intent=IntentType.MODIFY_TASK,
                confidence=0.50,
                raw_message=message,
                source="rule_engine",
            )
        
        # 包含创建相关词汇
        if any(kw in msg for kw in ["创建", "新建", "添加", "新增"]):
            return IntentResult(
                intent=IntentType.CREATE_TASK,
                confidence=0.50,
                raw_message=message,
                source="rule_engine",
            )
        
        return None
    
    # ── Level 3: LLM 深度理解 ─────────────────────────────────

    async def _resolve_with_llm(
        self,
        message: str,
        user_id: int,
        context: Dict[str, Any],
        hint: Optional[IntentResult] = None
    ) -> IntentResult:
        """
        LLM 深度意图理解
        
        参考 Claude Code 的 queryLoop:
        1. 构建 System Prompt (带上下文)
        2. 调用 LLM
        3. 解析 JSON 响应
        4. 置信度评估 → 可能生成澄清消息
        """
        # 构建 System Prompt
        system_prompt = build_intent_system_prompt(
            user_context=context,
            include_examples=True,
        )
        
        # 构建用户 Prompt
        user_prompt = build_intent_user_prompt(message)
        
        # 如果有规则引擎的 hint，附加到用户 prompt
        if hint:
            user_prompt += (
                f"\n\n提示: 规则引擎初步判断意图为 {hint.intent.value} "
                f"(置信度: {hint.confidence:.2f})，请在此基础上进行更准确的判断。"
            )
        
        try:
            # 调用 LLM
            response = await self.llm_service.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # 低温度，更确定性
                max_tokens=500,
            )
            
            # 解析 LLM 响应
            result = self._parse_llm_response(response, message)
            
            # 置信度策略: 低置信度生成澄清消息
            if result.confidence < 0.4:
                result.clarification = get_clarification_message(
                    "ambiguous_intent"
                )
            elif result.confidence < 0.7 and not result.task_reference:
                # 中置信度但没有任务引用
                if result.intent in (
                    IntentType.UPDATE_PROGRESS,
                    IntentType.QUERY_TASK_DETAIL,
                    IntentType.MODIFY_TASK,
                ):
                    result.clarification = get_clarification_message(
                        "missing_task_name"
                    )
            
            return result
            
        except Exception as e:
            print(f"❌ LLM 意图解析失败: {e}")
            
            # LLM 失败时降级到规则引擎结果或默认
            if hint:
                hint.source = "rule_engine_fallback"
                return hint
            
            return IntentResult(
                intent=IntentType.GENERAL_CHAT,
                confidence=0.3,
                raw_message=message,
                source="fallback",
                clarification=get_clarification_message("ambiguous_intent"),
            )
    
    def _parse_llm_response(
        self, response: str, original_message: str
    ) -> IntentResult:
        """
        解析 LLM 返回的 JSON 意图结果
        
        鲁棒解析: 多层回退
        1. 直接 json.loads (最干净的输出)
        2. 提取 {} 内容后 json.loads
        3. 清洗常见格式问题后重试
        """
        # 预处理: 去除 markdown 代码块标记
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()
        
        # 尝试解析的候选字符串
        candidates = [cleaned]
        
        # 尝试提取 {} 内的 JSON
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
        if json_match:
            candidates.append(json_match.group())
        
        # 更宽松的提取
        json_match2 = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match2 and json_match2.group() not in candidates:
            candidates.append(json_match2.group())
        
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                return self._build_intent_from_dict(data, original_message)
            except json.JSONDecodeError:
                pass
            
            # 尝试修复常见问题
            try:
                fixed = candidate
                # 去除 trailing commas
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r',\s*]', ']', fixed)
                # 移除 reasoning 等可能包含特殊字符的字段
                fixed = re.sub(r',?\s*"reasoning"\s*:\s*"[^"]*"', '', fixed)
                data = json.loads(fixed)
                return self._build_intent_from_dict(data, original_message)
            except json.JSONDecodeError:
                continue
        
        # 所有解析都失败
        print(f"⚠️ LLM 响应解析失败，所有候选均无效")
        print(f"   原始响应: {response[:200]}...")
        
        return IntentResult(
            intent=IntentType.GENERAL_CHAT,
            confidence=0.3,
            raw_message=original_message,
            source="llm_parse_error",
            clarification=get_clarification_message("ambiguous_intent"),
        )
    
    def _build_intent_from_dict(
        self, data: dict, original_message: str
    ) -> IntentResult:
        """从解析好的 dict 构建 IntentResult"""
        # 解析意图类型
        intent_str = data.get("intent", "general_chat")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.GENERAL_CHAT
        
        # 解析置信度
        confidence = float(data.get("confidence", 0.5))
        confidence = min(1.0, max(0.0, confidence))
        
        # 解析任务引用
        task_ref = data.get("task_reference")
        if task_ref and isinstance(task_ref, dict):
            task_ref = {
                "name": task_ref.get("name"),
                "id": task_ref.get("id"),
            }
            if not task_ref["name"] and not task_ref["id"]:
                task_ref = None
        else:
            task_ref = None
        
        # 解析参数
        params = data.get("params", {})
        if not isinstance(params, dict):
            params = {}
        
        # 清理 params 中的 None 值
        params = {k: v for k, v in params.items() if v is not None}
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            params=params,
            task_reference=task_ref,
            raw_message=original_message,
            source="llm",
        )

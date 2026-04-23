"""
AI 对话服务
==========
负责对话历史的 CRUD、上下文构建、LLM 调用封装
"""
import asyncio
import json
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime, timezone

from app.models import AIConversation, User, Project, Task
from app.services.llm_service import LLMService


class LLMError(Exception):
    """LLM 调用错误基类"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 超时错误"""
    pass


class LLMAuthError(LLMError):
    """LLM 认证错误"""
    pass


class LLMRateLimitError(LLMError):
    """LLM 速率限制错误"""
    pass


class AIConversationService:
    """AI 对话服务"""
    
    MAX_MESSAGES = 30  # 最多保留30条消息 (15轮对话)
    MAX_CONTEXT_TOKENS = 4000  # 上下文 token 限制
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def create_conversation(
        self,
        user_id: int,
        project_id: int,
        conversation_type: str,
        initial_message: Optional[str] = None
    ) -> AIConversation:
        """创建新对话"""
        # 生成对话标题
        title = self._generate_title(conversation_type, initial_message)
        
        # 创建对话记录
        conversation = AIConversation(
            user_id=user_id,
            project_id=project_id,
            conversation_type=conversation_type,
            title=title,
            messages=json.dumps([], ensure_ascii=False),
            context_data=json.dumps({}, ensure_ascii=False)
        )
        
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        # 如果有初始消息,添加到对话历史
        if initial_message:
            await self.add_message(conversation.id, "user", initial_message)
        
        return conversation
    
    async def get_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[AIConversation]:
        """获取对话详情 (验证权限)"""
        result = await self.db.execute(
            select(AIConversation).where(
                and_(
                    AIConversation.id == conversation_id,
                    AIConversation.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def list_conversations(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        conversation_type: Optional[str] = None,
        limit: int = 20
    ) -> List[AIConversation]:
        """获取对话列表"""
        query = select(AIConversation).where(AIConversation.user_id == user_id)
        
        if project_id:
            query = query.where(AIConversation.project_id == project_id)
        
        if conversation_type:
            query = query.where(AIConversation.conversation_type == conversation_type)
        
        query = query.order_by(desc(AIConversation.updated_at)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_message(
        self,
        conversation_id: int,
        role: str,  # "user" | "assistant"
        content: str,
        actions: Optional[List[Dict]] = None
    ) -> AIConversation:
        """添加消息到对话历史"""
        result = await self.db.execute(
            select(AIConversation).where(AIConversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # 加载现有消息
        messages = conversation.messages_list
        
        # 添加新消息
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if actions:
            message["actions"] = actions
        
        messages.append(message)
        
        # 压缩消息历史
        if len(messages) > self.MAX_MESSAGES:
            messages = messages[-self.MAX_MESSAGES:]
        
        # 保存
        conversation.messages_list = messages
        conversation.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(conversation)
        
        return conversation
    
    async def send_message(
        self,
        conversation_id: int,
        user_id: int,
        user_message: str,
        context_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送消息并获取 AI 回复"""
        
        # 1. 加载对话
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        # 2. 添加用户消息
        await self.add_message(conversation_id, "user", user_message)
        
        # 3. 构建上下文
        context = await self.build_context(conversation)
        
        # 4. 构建 LLM 消息
        messages = self._build_llm_messages(
            conversation.conversation_type,
            conversation.messages_list,
            context
        )
        
        # 5. 调用 LLM
        try:
            response = await self._call_llm_with_retry(messages)
        except Exception as e:
            # 错误处理
            raise
        
        # 6. 保存 AI 回复
        await self.add_message(conversation_id, "assistant", response)
        
        # 7. 重新加载对话
        await self.db.refresh(conversation)
        
        return {
            "reply": response,
            "conversation_id": conversation_id,
            "message_count": len(conversation.messages_list)
        }
    
    async def build_context(
        self,
        conversation: AIConversation
    ) -> Dict[str, Any]:
        """构建对话上下文 (项目信息 + 任务数据)"""
        
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == conversation.project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {}
        
        # 获取项目任务
        result = await self.db.execute(
            select(Task).where(Task.project_id == conversation.project_id)
        )
        tasks = list(result.scalars().all())
        
        # 统计任务状态
        completed_count = sum(1 for t in tasks if t.status == 'completed')
        in_progress_count = sum(1 for t in tasks if t.status == 'in_progress')
        pending_count = sum(1 for t in tasks if t.status == 'pending')
        
        context = {
            "project_name": project.name,
            "project_description": project.description,
            "task_count": len(tasks),
            "completed_count": completed_count,
            "in_progress_count": in_progress_count,
            "pending_count": pending_count,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "progress": t.progress,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "start_date": t.start_date.isoformat() if t.start_date else None,
                    "estimated_time": t.estimated_time,
                    "actual_time": t.actual_time
                }
                for t in tasks
            ]
        }
        
        return context
    
    async def compress_messages(
        self,
        messages: List[Dict]
    ) -> List[Dict]:
        """压缩消息历史 (保留最近30条)"""
        if len(messages) <= self.MAX_MESSAGES:
            return messages
        
        return messages[-self.MAX_MESSAGES:]
    
    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """删除对话"""
        result = await self.db.execute(
            select(AIConversation).where(
                and_(
                    AIConversation.id == conversation_id,
                    AIConversation.user_id == user_id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return False
        
        await self.db.delete(conversation)
        await self.db.commit()
        
        return True
    
    def _generate_title(self, conversation_type: str, initial_message: Optional[str] = None) -> str:
        """生成对话标题"""
        type_labels = {
            'create': '任务创建',
            'analyze': '任务分析',
            'modify': '任务修改',
            'plan': '项目规划'
        }
        
        base_title = type_labels.get(conversation_type, '对话')
        
        if initial_message and len(initial_message) > 0:
            # 使用初始消息的前20个字符作为标题
            title = f"{base_title} - {initial_message[:20]}"
            if len(initial_message) > 20:
                title += "..."
            return title
        
        # 使用时间戳
        timestamp = datetime.now(timezone.utc).strftime("%m-%d %H:%M")
        return f"{base_title} - {timestamp}"
    
    def _build_llm_messages(
        self,
        conversation_type: str,
        messages: List[Dict],
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """构建 LLM 消息列表"""
        
        # 系统提示词
        system_prompts = {
            'create': self._get_create_system_prompt(context),
            'analyze': self._get_analyze_system_prompt(context),
            'modify': self._get_modify_system_prompt(context),
            'plan': self._get_plan_system_prompt(context)
        }
        
        system_prompt = system_prompts.get(conversation_type, "你是一个专业的任务管理助手。")
        
        # 构建消息列表
        llm_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加对话历史
        for msg in messages:
            llm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return llm_messages
    
    def _get_create_system_prompt(self, context: Dict[str, Any]) -> str:
        """任务创建模式的系统提示词"""
        return f"""你是一个专业的任务管理助手,帮助用户创建和分解任务。

项目信息:
- 项目名称: {context.get('project_name', '')}
- 项目描述: {context.get('project_description', '')}
- 现有任务数: {context.get('task_count', 0)}

请根据用户的需求,帮助他们:
1. 明确任务目标和范围
2. 分解复杂任务为子任务
3. 建议合理的优先级和时间安排
4. 识别任务依赖关系

回复时请使用 Markdown 格式,保持简洁专业。"""
    
    def _get_analyze_system_prompt(self, context: Dict[str, Any]) -> str:
        """任务分析模式的系统提示词"""
        task_summary = self._build_task_summary(context.get('tasks', []))
        
        return f"""你是一个资深项目管理专家,负责分析项目任务情况。

项目信息:
- 项目名称: {context.get('project_name', '')}
- 任务总数: {context.get('task_count', 0)}
- 已完成: {context.get('completed_count', 0)}
- 进行中: {context.get('in_progress_count', 0)}
- 待开始: {context.get('pending_count', 0)}

任务详情:
{task_summary}

请从以下维度分析:
1. 任务瓶颈: 识别阻塞项目进度的关键任务
2. 时间冲突: 发现截止日期冲突或不合理的任务
3. 优先级问题: 指出优先级设置不合理的任务
4. 延期风险: 预测可能延期的任务
5. 资源分配: 分析任务负载是否均衡

回复时请使用 Markdown 格式,提供具体的任务 ID 和建议。"""
    
    def _get_modify_system_prompt(self, context: Dict[str, Any]) -> str:
        """任务修改模式的系统提示词"""
        task_summary = self._build_task_summary(context.get('tasks', []))
        
        return f"""你是一个任务管理助手,帮助用户修改任务。

项目信息:
- 项目名称: {context.get('project_name', '')}

任务列表:
{task_summary}

请理解用户的自然语言指令,并:
1. 识别需要修改的任务
2. 确定修改类型 (截止日期、优先级、状态等)
3. 生成具体的修改建议
4. 请求用户确认

回复时请明确说明将要执行的操作,并等待用户确认。"""
    
    def _get_plan_system_prompt(self, context: Dict[str, Any]) -> str:
        """项目规划模式的系统提示词"""
        task_summary = self._build_task_summary(context.get('tasks', []))
        
        return f"""你是一个项目规划专家,帮助用户完善项目计划。

项目信息:
- 项目名称: {context.get('project_name', '')}
- 项目描述: {context.get('project_description', '')}
- 现有任务数: {context.get('task_count', 0)}

现有任务:
{task_summary}

请分析项目结构并:
1. 识别缺失的任务类型 (如测试、文档、部署等)
2. 建议新任务的优先级和时间安排
3. 指出任务结构的改进空间
4. 提供项目里程碑建议

回复时请使用 Markdown 格式,提供具体可行的建议。"""
    
    def _build_task_summary(self, tasks: List[Dict]) -> str:
        """构建任务摘要"""
        if not tasks:
            return "暂无任务"
        
        lines = []
        now = datetime.now(timezone.utc)
        
        for task in tasks[:50]:  # 最多显示50个任务
            due_info = ""
            if task.get('due_date'):
                try:
                    due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                    days_remaining = (due_date - now).days
                    if days_remaining < 0:
                        due_info = f"已逾期{abs(days_remaining)}天"
                    else:
                        due_info = f"剩余{days_remaining}天"
                except:
                    due_info = task['due_date']
            
            lines.append(
                f"- 任务#{task['id']}: {task['name']} | "
                f"状态:{task['status']} | "
                f"优先级:{task['priority']} | "
                f"进度:{task['progress']}% | "
                f"{due_info}"
            )
        
        if len(tasks) > 50:
            lines.append(f"... 还有 {len(tasks) - 50} 个任务")
        
        return "\n".join(lines)
    
    async def _call_llm_with_retry(
        self,
        messages: List[Dict],
        max_retries: int = 3
    ) -> str:
        """带重试的 LLM 调用"""
        
        for attempt in range(max_retries):
            try:
                response = await self.llm_service.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                return response
                
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise LLMTimeoutError("LLM 服务响应超时,请稍后重试")
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
            except Exception as e:
                error_msg = str(e)
                
                if "401" in error_msg or "403" in error_msg:
                    raise LLMAuthError("API Key 无效或已过期,请检查配置")
                
                elif "429" in error_msg:
                    if attempt == max_retries - 1:
                        raise LLMRateLimitError("API 调用频率超限,请稍后重试")
                    await asyncio.sleep(5 * (attempt + 1))
                
                elif "500" in error_msg or "503" in error_msg:
                    if attempt == max_retries - 1:
                        raise LLMError(f"LLM 服务暂时不可用: {error_msg}")
                    await asyncio.sleep(3 ** attempt)
                
                else:
                    raise LLMError(f"LLM 调用失败: {error_msg}")

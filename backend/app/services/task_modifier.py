"""
任务修改器
=========
解析自然语言并执行任务修改操作
"""
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone, date

from app.models import Task
from app.services.llm_service import LLMService


class TaskModifier:
    """任务修改器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def parse_modification_intent(
        self,
        user_input: str,
        context_tasks: List[Task]
    ) -> Dict[str, Any]:
        """解析修改意图"""
        
        # 构建任务上下文
        task_context = self._build_task_context(context_tasks)
        
        # 构建 prompt
        prompt = self._build_modification_prompt(user_input, task_context)
        
        # 调用 LLM
        try:
            response = await self.llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是一个任务管理助手,负责解析用户的任务修改意图。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # 解析响应
            result = self._parse_intent_response(response)
            return result
            
        except Exception as e:
            # 如果 LLM 调用失败,尝试简单的规则匹配
            return self._fallback_intent_parse(user_input, context_tasks)
    
    async def execute_modification(
        self,
        modification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行修改操作"""
        
        action = modification.get('action')
        task_ids = modification.get('task_ids', [])
        params = modification.get('params', {})
        
        results = {
            'success': [],
            'failed': [],
            'errors': []
        }
        
        for task_id in task_ids:
            try:
                # 验证任务存在
                result = await self.db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if not task:
                    results['failed'].append(task_id)
                    results['errors'].append(f"任务 #{task_id} 不存在")
                    continue
                
                # 执行修改
                if action == 'update_due_date':
                    await self._update_due_date(task, params)
                    results['success'].append(task_id)
                
                elif action == 'update_priority':
                    await self._update_priority(task, params)
                    results['success'].append(task_id)
                
                elif action == 'update_status':
                    await self._update_status(task, params)
                    results['success'].append(task_id)
                
                elif action == 'update_description':
                    await self._update_description(task, params)
                    results['success'].append(task_id)
                
                elif action == 'batch_update':
                    await self._batch_update(task, params)
                    results['success'].append(task_id)
                
                else:
                    results['failed'].append(task_id)
                    results['errors'].append(f"任务 #{task_id} 不支持的操作: {action}")
                
            except Exception as e:
                results['failed'].append(task_id)
                results['errors'].append(f"任务 #{task_id} 修改失败: {str(e)}")
        
        await self.db.commit()
        
        return {
            'total': len(task_ids),
            'success_count': len(results['success']),
            'failed_count': len(results['failed']),
            'results': results
        }
    
    def _build_task_context(self, tasks: List[Task]) -> str:
        """构建任务上下文"""
        lines = []
        for task in tasks[:20]:  # 最多显示20个任务
            lines.append(
                f"- 任务#{task.id}: {task.name} | "
                f"状态:{task.status} | "
                f"优先级:{task.priority} | "
                f"截止日期:{task.due_date or '无'}"
            )
        
        if len(tasks) > 20:
            lines.append(f"... 还有 {len(tasks) - 20} 个任务")
        
        return "\n".join(lines)
    
    def _build_modification_prompt(self, user_input: str, task_context: str) -> str:
        """构建修改意图解析 prompt"""
        
        prompt = f"""你是一个任务管理助手。用户想要修改任务,请解析用户意图。

用户输入: {user_input}

当前任务上下文:
{task_context}

请识别以下修改类型:
1. update_due_date: 修改截止日期
2. update_priority: 修改优先级
3. update_status: 修改状态
4. update_description: 修改描述
5. batch_update: 批量修改

返回 JSON 格式:
{{
  "action": "update_due_date|update_priority|...",
  "task_ids": [123, 456],
  "params": {{
    "due_date": "2024-12-31",
    "offset_days": 3,
    "priority": "high",
    "status": "in_progress",
    "description": "新描述"
  }},
  "confirmation_message": "将任务 #123 的截止日期延后3天至 2024-12-31,是否确认?",
  "confidence": 0.9
}}

请确保返回有效的 JSON 格式。"""
        
        return prompt
    
    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """解析意图响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # 验证必需字段
                result = {
                    "action": data.get("action", ""),
                    "task_ids": data.get("task_ids", []),
                    "params": data.get("params", {}),
                    "confirmation_message": data.get("confirmation_message", ""),
                    "confidence": data.get("confidence", 0.5)
                }
                
                return result
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse intent response: {e}")
    
    def _fallback_intent_parse(self, user_input: str, tasks: List[Task]) -> Dict[str, Any]:
        """简单的规则匹配 (LLM 不可用时的后备方案)"""
        
        # 尝试识别任务 ID
        task_id_match = re.search(r'#?(\d+)', user_input)
        task_ids = [int(task_id_match.group(1))] if task_id_match else []
        
        # 如果没有指定任务 ID,使用第一个任务
        if not task_ids and tasks:
            task_ids = [tasks[0].id]
        
        # 识别修改类型
        if any(keyword in user_input for keyword in ['延后', '推迟', '延期', '截止']):
            # 尝试提取天数
            days_match = re.search(r'(\d+)\s*天', user_input)
            offset_days = int(days_match.group(1)) if days_match else 3
            
            return {
                "action": "update_due_date",
                "task_ids": task_ids,
                "params": {"offset_days": offset_days},
                "confirmation_message": f"将任务延后 {offset_days} 天,是否确认?",
                "confidence": 0.7
            }
        
        elif any(keyword in user_input for keyword in ['优先级', '重要', '紧急']):
            priority = 'high' if any(k in user_input for k in ['高', '重要', '紧急']) else 'medium'
            
            return {
                "action": "update_priority",
                "task_ids": task_ids,
                "params": {"priority": priority},
                "confirmation_message": f"将任务优先级设置为 {priority},是否确认?",
                "confidence": 0.7
            }
        
        elif any(keyword in user_input for keyword in ['完成', '开始', '状态']):
            if '完成' in user_input:
                status = 'completed'
            elif '开始' in user_input:
                status = 'in_progress'
            else:
                status = 'pending'
            
            return {
                "action": "update_status",
                "task_ids": task_ids,
                "params": {"status": status},
                "confirmation_message": f"将任务状态设置为 {status},是否确认?",
                "confidence": 0.7
            }
        
        else:
            return {
                "action": "unknown",
                "task_ids": [],
                "params": {},
                "confirmation_message": "无法理解您的意图,请更明确地描述要执行的操作",
                "confidence": 0.3
            }
    
    async def _update_due_date(self, task: Task, params: Dict[str, Any]):
        """更新截止日期"""
        if 'due_date' in params:
            # 直接设置日期
            due_date_str = params['due_date']
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        elif 'offset_days' in params:
            # 相对偏移
            offset_days = params['offset_days']
            if task.due_date:
                task.due_date = task.due_date + timedelta(days=offset_days)
            else:
                # 如果没有截止日期,从今天开始计算
                task.due_date = date.today() + timedelta(days=offset_days)
        
        task.updated_at = datetime.now(timezone.utc)
    
    async def _update_priority(self, task: Task, params: Dict[str, Any]):
        """更新优先级"""
        priority = params.get('priority', 'medium')
        if priority in ['high', 'medium', 'low']:
            task.priority = priority
            task.updated_at = datetime.now(timezone.utc)
    
    async def _update_status(self, task: Task, params: Dict[str, Any]):
        """更新状态"""
        status = params.get('status', 'pending')
        if status in ['pending', 'in_progress', 'completed', 'cancelled']:
            task.status = status
            
            # 如果标记为完成,设置进度为100%
            if status == 'completed':
                task.progress = 100
            
            task.updated_at = datetime.now(timezone.utc)
    
    async def _update_description(self, task: Task, params: Dict[str, Any]):
        """更新描述"""
        description = params.get('description', '')
        task.description = description
        task.updated_at = datetime.now(timezone.utc)
    
    async def _batch_update(self, task: Task, params: Dict[str, Any]):
        """批量更新多个字段"""
        if 'priority' in params:
            task.priority = params['priority']
        
        if 'status' in params:
            task.status = params['status']
        
        if 'due_date' in params:
            task.due_date = datetime.strptime(params['due_date'], '%Y-%m-%d').date()
        
        if 'description' in params:
            task.description = params['description']
        
        task.updated_at = datetime.now(timezone.utc)
    
    def _parse_relative_date(
        self,
        base_date: datetime,
        offset_str: str
    ) -> datetime:
        """解析相对日期 (如"延后3天")"""
        # 提取数字
        match = re.search(r'(\d+)', offset_str)
        if not match:
            return base_date
        
        days = int(match.group(1))
        
        # 判断是延后还是提前
        if any(keyword in offset_str for keyword in ['延后', '推迟', '延期']):
            return base_date + timedelta(days=days)
        elif any(keyword in offset_str for keyword in ['提前', '提早']):
            return base_date - timedelta(days=days)
        else:
            return base_date + timedelta(days=days)
    
    def _identify_tasks_by_description(
        self,
        description: str,
        tasks: List[Task]
    ) -> List[int]:
        """根据描述识别任务"""
        # 简单的关键词匹配
        matched_task_ids = []
        
        for task in tasks:
            if description.lower() in task.name.lower():
                matched_task_ids.append(task.id)
        
        return matched_task_ids

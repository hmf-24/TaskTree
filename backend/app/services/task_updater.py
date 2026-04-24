"""
任务更新服务
============
根据进度反馈自动更新任务状态、进度、截止日期等

更新规则:
- completed: 状态 → "已完成", 进度 → 100%
- in_progress: 状态 → "进行中"
- progress_value: 进度字段 → 百分比
- problem_description: 追加到任务描述
- extend_days: 截止日期 → 延期 N 天
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta, date
from app.models import Task, Project, ProjectMember, ProgressFeedback
from app.schemas import ParseResultSchema


class TaskUpdaterService:
    """任务更新服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_from_feedback(
        self,
        task_id: int,
        parse_result: ParseResultSchema,
        user_id: int,
        message_content: str
    ) -> Task:
        """
        根据反馈更新任务
        
        Args:
            task_id: 任务 ID
            parse_result: 解析结果
            user_id: 用户 ID
            message_content: 原始消息内容
            
        Returns:
            更新后的任务
            
        Raises:
            PermissionError: 无权限修改此任务
            ValueError: 任务不存在
        """
        # 获取任务
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 验证权限
        if not await self._check_permission(task, user_id):
            raise PermissionError("无权限修改此任务")
        
        # 记录原始状态（用于日志）
        old_status = task.status
        old_progress = task.progress
        old_due_date = task.due_date
        
        # 根据进度类型更新任务
        if parse_result.progress_type == "completed":
            # 任务已完成
            task.status = "completed"
            task.progress = 100
        
        elif parse_result.progress_type == "in_progress":
            # 任务进行中
            task.status = "in_progress"
            # 如果有进度值，更新进度
            if parse_result.progress_value and parse_result.progress_value > 0:
                task.progress = min(parse_result.progress_value, 100)
        
        elif parse_result.progress_type == "problem":
            # 遇到问题
            # 追加问题描述到任务描述
            if parse_result.problem_description:
                problem_text = f"\n\n**问题反馈 ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')})**:\n{parse_result.problem_description}"
                task.description = (task.description or "") + problem_text
        
        elif parse_result.progress_type == "extend":
            # 请求延期
            if parse_result.extend_days and parse_result.extend_days > 0:
                if task.due_date:
                    # 如果有截止日期，延期
                    task.due_date = task.due_date + timedelta(days=parse_result.extend_days)
                else:
                    # 如果没有截止日期，设置为今天 + 延期天数
                    task.due_date = date.today() + timedelta(days=parse_result.extend_days)
        
        elif parse_result.progress_type == "query":
            # 查询状态（不修改任务）
            pass
        
        # 更新时间戳
        task.updated_at = datetime.now(timezone.utc)
        
        # 保存到数据库
        await self.db.commit()
        await self.db.refresh(task)
        
        # 记录进度反馈
        await self._save_feedback(
            user_id=user_id,
            task_id=task_id,
            message_content=message_content,
            parse_result=parse_result
        )
        
        # 记录操作日志
        await self._log_operation(
            task_id=task_id,
            user_id=user_id,
            old_status=old_status,
            new_status=task.status,
            old_progress=old_progress,
            new_progress=task.progress,
            old_due_date=old_due_date,
            new_due_date=task.due_date,
            parse_result=parse_result
        )
        
        return task
    
    async def _get_task(self, task_id: int) -> Optional[Task]:
        """获取任务"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def _check_permission(self, task: Task, user_id: int) -> bool:
        """
        检查用户权限
        
        用户可以修改任务的条件:
        1. 用户是任务的负责人
        2. 用户是项目的成员
        
        Args:
            task: 任务对象
            user_id: 用户 ID
            
        Returns:
            是否有权限
        """
        # 1. 检查是否是任务负责人
        if task.assignee_id == user_id:
            return True
        
        # 2. 检查是否是项目成员
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        
        return member is not None
    
    async def _save_feedback(
        self,
        user_id: int,
        task_id: int,
        message_content: str,
        parse_result: ParseResultSchema
    ):
        """保存进度反馈记录"""
        import json
        
        feedback = ProgressFeedback(
            user_id=user_id,
            task_id=task_id,
            message_content=message_content,
            parsed_result=json.dumps(parse_result.model_dump(), ensure_ascii=False),
            feedback_type=parse_result.progress_type,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(feedback)
        await self.db.flush()
    
    async def _log_operation(
        self,
        task_id: int,
        user_id: int,
        old_status: str,
        new_status: str,
        old_progress: int,
        new_progress: int,
        old_due_date: Optional[date],
        new_due_date: Optional[date],
        parse_result: ParseResultSchema
    ):
        """
        记录操作日志
        
        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            old_status: 旧状态
            new_status: 新状态
            old_progress: 旧进度
            new_progress: 新进度
            old_due_date: 旧截止日期
            new_due_date: 新截止日期
            parse_result: 解析结果
        """
        import json
        from app.models import OperationLog
        
        # 构建变更记录
        changes = {}
        
        if old_status != new_status:
            changes['status'] = {'old': old_status, 'new': new_status}
        
        if old_progress != new_progress:
            changes['progress'] = {'old': old_progress, 'new': new_progress}
        
        if old_due_date != new_due_date:
            changes['due_date'] = {
                'old': old_due_date.isoformat() if old_due_date else None,
                'new': new_due_date.isoformat() if new_due_date else None
            }
        
        # 如果有变更，记录日志
        if changes:
            # 获取任务的项目 ID
            task = await self._get_task(task_id)
            
            log = OperationLog(
                user_id=user_id,
                project_id=task.project_id if task else None,
                task_id=task_id,
                action="update_from_dingtalk",
                old_value=json.dumps(changes, ensure_ascii=False),
                new_value=json.dumps({
                    'source': 'dingtalk_feedback',
                    'feedback_type': parse_result.progress_type,
                    'message': parse_result.raw_message
                }, ensure_ascii=False),
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(log)
            await self.db.flush()
    
    def _validate_status_transition(
        self,
        old_status: str,
        new_status: str
    ) -> bool:
        """
        验证状态转换是否有效
        
        有效的状态转换:
        - pending → in_progress
        - pending → completed
        - in_progress → completed
        - in_progress → pending (回退)
        
        Args:
            old_status: 旧状态
            new_status: 新状态
            
        Returns:
            是否有效
        """
        valid_transitions = {
            'pending': ['in_progress', 'completed', 'cancelled'],
            'in_progress': ['completed', 'pending', 'cancelled'],
            'completed': ['in_progress'],  # 允许重新打开
            'cancelled': ['pending']  # 允许恢复
        }
        
        if old_status == new_status:
            return True
        
        return new_status in valid_transitions.get(old_status, [])

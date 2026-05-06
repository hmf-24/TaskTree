"""
任务匹配服务
============
根据关键词在用户任务列表中智能匹配任务

匹配策略:
1. 完全匹配任务名称 (权重: 100)
2. 任务名称包含关键词 (权重: 80)
3. 任务描述包含关键词 (权重: 60)
4. 优先匹配"进行中"或"待处理"状态 (权重: +20)
5. 优先匹配最近更新的任务 (权重: +10)
"""
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from datetime import datetime, timezone, timedelta
from app.models import Task


class TaskMatcherService:
    """任务匹配服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def match(
        self,
        keywords: List[str],
        user_id: int,
        project_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Task]:
        """
        根据关键词匹配任务
        
        Args:
            keywords: 关键词列表
            user_id: 用户 ID
            project_id: 项目 ID (可选，限制在特定项目内搜索)
            limit: 返回最多任务数
            
        Returns:
            匹配的任务列表（按匹配分数排序）
        """
        # 获取用户的所有任务
        tasks = await self._get_user_tasks(user_id, project_id)
        
        if not tasks:
            return []
        
        # 计算每个任务的匹配分数
        scored_tasks: List[Tuple[Task, float]] = []
        for task in tasks:
            score = self._calculate_match_score(task, keywords)
            if score > 0:
                scored_tasks.append((task, score))
        
        # 按分数排序
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 limit 个任务
        return [task for task, score in scored_tasks[:limit]]
    
    async def _get_user_tasks(
        self,
        user_id: int,
        project_id: Optional[int] = None
    ) -> List[Task]:
        """
        获取用户的所有任务
        
        Args:
            user_id: 用户 ID
            project_id: 项目 ID (可选)
            
        Returns:
            任务列表
        """
        # 构建查询（单用户模式下，不对 assignee_id 进行过滤）
        query = select(Task)
        
        # 如果指定了项目，限制在该项目内
        if project_id:
            query = query.where(Task.project_id == project_id)
        
        # 只查询未完成和未取消的任务
        query = query.where(
            Task.status.in_(['pending', 'in_progress'])
        )
        
        # 执行查询
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        return list(tasks)
    
    def _calculate_match_score(self, task: Task, keywords: List[str]) -> float:
        """
        计算任务的匹配分数
        
        Args:
            task: 任务对象
            keywords: 关键词列表
            
        Returns:
            匹配分数（越高越匹配）
        """
        score = 0.0
        
        task_name = (task.name or "").lower()
        task_description = (task.description or "").lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # 1. 完全匹配任务名称 (权重: 100)
            if task_name == keyword_lower:
                score += 100
            # 2. 任务名称包含关键词 (权重: 80)
            elif keyword_lower in task_name:
                score += 80
            # 3. 任务描述包含关键词 (权重: 60)
            elif keyword_lower in task_description:
                score += 60
            # 4. 反向匹配：关键词（整个句子）中包含任务名称 (权重: 70)
            elif task_name and task_name in keyword_lower:
                score += 70
        
        # 如果基础得分为 0，说明完全不匹配，不应计算加分项
        if score == 0:
            return 0.0
        
        # 4. 优先匹配"进行中"或"待处理"状态 (权重: +20)
        if task.status in ['in_progress', 'pending']:
            score += 20
        
        # 5. 优先匹配最近更新的任务 (权重: +10)
        if task.updated_at:
            try:
                # 确保两个datetime都有时区信息
                now_utc = datetime.now(timezone.utc)
                task_updated = task.updated_at
                
                # 如果task.updated_at没有时区信息，添加UTC时区
                if task_updated.tzinfo is None:
                    task_updated = task_updated.replace(tzinfo=timezone.utc)
                
                days_since_update = (now_utc - task_updated).days
                if days_since_update == 0:
                    score += 10
                elif days_since_update <= 7:
                    score += 5
            except Exception as e:
                # 如果时间计算失败，跳过这个加分项
                print(f"⚠️  计算任务更新时间失败: {e}")
                pass
        
        return score
    
    async def match_single(
        self,
        keywords: List[str],
        user_id: int,
        project_id: Optional[int] = None
    ) -> Optional[Task]:
        """
        匹配单个最佳任务
        
        Args:
            keywords: 关键词列表
            user_id: 用户 ID
            project_id: 项目 ID (可选)
            
        Returns:
            最佳匹配的任务，如果没有匹配则返回 None
        """
        tasks = await self.match(keywords, user_id, project_id, limit=1)
        return tasks[0] if tasks else None
    
    async def match_with_scores(
        self,
        keywords: List[str],
        user_id: int,
        project_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Tuple[Task, float]]:
        """
        匹配任务并返回分数
        
        Args:
            keywords: 关键词列表
            user_id: 用户 ID
            project_id: 项目 ID (可选)
            limit: 返回最多任务数
            
        Returns:
            (任务, 分数) 元组列表
        """
        # 获取用户的所有任务
        tasks = await self._get_user_tasks(user_id, project_id)
        
        if not tasks:
            return []
        
        # 计算每个任务的匹配分数
        scored_tasks: List[Tuple[Task, float]] = []
        for task in tasks:
            score = self._calculate_match_score(task, keywords)
            if score > 0:
                scored_tasks.append((task, score))
        
        # 按分数排序
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 limit 个任务
        return scored_tasks[:limit]

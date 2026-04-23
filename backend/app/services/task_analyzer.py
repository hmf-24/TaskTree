"""
任务分析器
=========
分析项目任务并生成优化建议
"""
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models import Project, Task
from app.services.llm_service import LLMService


class TaskAnalyzer:
    """任务分析器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def analyze_project_tasks(
        self,
        project_id: int,
        user_id: int,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析项目任务"""
        
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 获取项目任务
        tasks = await self._get_project_tasks(project_id)
        
        if not tasks:
            return {
                "summary": "项目暂无任务",
                "issues": [],
                "recommendations": [],
                "risk_score": 0
            }
        
        # 构建分析 prompt
        prompt = await self._build_analysis_prompt(project, tasks, focus_areas)
        
        # 调用 LLM
        try:
            response = await self.llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是一个资深项目管理专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # 解析响应
            result = await self._parse_analysis_response(response)
            return result
            
        except Exception as e:
            # 如果 LLM 调用失败,返回基础分析
            return await self._fallback_analysis(tasks)
    
    async def _get_project_tasks(
        self,
        project_id: int
    ) -> List[Task]:
        """获取项目所有任务"""
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        return list(result.scalars().all())
    
    async def _build_analysis_prompt(
        self,
        project: Project,
        tasks: List[Task],
        focus_areas: Optional[List[str]]
    ) -> str:
        """构建分析 prompt"""
        
        # 统计任务状态
        completed_count = sum(1 for t in tasks if t.status == 'completed')
        in_progress_count = sum(1 for t in tasks if t.status == 'in_progress')
        pending_count = sum(1 for t in tasks if t.status == 'pending')
        
        # 构建任务详情
        task_details = self._build_task_details(tasks)
        
        # 构建分析维度
        analysis_dims = self._build_analysis_dimensions(focus_areas)
        
        prompt = f"""你是一个资深项目管理专家。请分析以下项目的任务情况:

项目名称: {project.name}
项目描述: {project.description or '无'}
任务总数: {len(tasks)}
已完成: {completed_count}
进行中: {in_progress_count}
待开始: {pending_count}

任务详情:
{task_details}

请从以下维度分析:
{analysis_dims}

返回 JSON 格式:
{{
  "summary": "整体评估摘要 (2-3句话)",
  "issues": [
    {{
      "type": "bottleneck|conflict|priority|risk|resource",
      "severity": "high|medium|low",
      "task_ids": [1, 2, 3],
      "description": "问题描述",
      "suggestion": "优化建议"
    }}
  ],
  "recommendations": [
    {{
      "action": "adjust_deadline|change_priority|add_resource|split_task",
      "task_id": 123,
      "details": "具体建议"
    }}
  ],
  "risk_score": 0-100
}}

请确保返回有效的 JSON 格式。"""
        
        return prompt
    
    def _build_task_details(self, tasks: List[Task]) -> str:
        """构建任务详情字符串"""
        lines = []
        now = datetime.now(timezone.utc)
        
        for task in tasks[:50]:  # 最多分析50个任务
            due_info = ""
            if task.due_date:
                try:
                    due_date = datetime.combine(task.due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    days_remaining = (due_date - now).days
                    if days_remaining < 0:
                        due_info = f"已逾期{abs(days_remaining)}天"
                    else:
                        due_info = f"剩余{days_remaining}天"
                except:
                    due_info = str(task.due_date)
            
            lines.append(
                f"- 任务#{task.id}: {task.name} | "
                f"状态:{task.status} | "
                f"优先级:{task.priority} | "
                f"进度:{task.progress}% | "
                f"{due_info}"
            )
        
        if len(tasks) > 50:
            lines.append(f"... 还有 {len(tasks) - 50} 个任务")
        
        return "\n".join(lines)
    
    def _build_analysis_dimensions(self, focus_areas: Optional[List[str]]) -> str:
        """构建分析维度"""
        all_dimensions = {
            "bottleneck": "1. 任务瓶颈: 识别阻塞项目进度的关键任务",
            "conflict": "2. 时间冲突: 发现截止日期冲突或不合理的任务",
            "priority": "3. 优先级问题: 指出优先级设置不合理的任务",
            "risk": "4. 延期风险: 预测可能延期的任务",
            "resource": "5. 资源分配: 分析任务负载是否均衡"
        }
        
        if focus_areas:
            # 只分析指定的维度
            dims = [all_dimensions[area] for area in focus_areas if area in all_dimensions]
        else:
            # 分析所有维度
            dims = list(all_dimensions.values())
        
        return "\n".join(dims)
    
    async def _parse_analysis_response(
        self,
        response: str
    ) -> Dict[str, Any]:
        """解析 LLM 分析响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # 验证必需字段
                result = {
                    "summary": data.get("summary", ""),
                    "issues": data.get("issues", []),
                    "recommendations": data.get("recommendations", []),
                    "risk_score": data.get("risk_score", 0)
                }
                
                return result
            else:
                # 如果没有找到 JSON,返回文本响应
                return {
                    "summary": response[:200],
                    "issues": [],
                    "recommendations": [],
                    "risk_score": 0
                }
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    
    async def _fallback_analysis(self, tasks: List[Task]) -> Dict[str, Any]:
        """基础分析 (LLM 不可用时的后备方案)"""
        now = datetime.now(timezone.utc)
        issues = []
        recommendations = []
        risk_score = 0
        
        # 检查逾期任务
        overdue_tasks = []
        for task in tasks:
            if task.due_date and task.status != 'completed':
                due_date = datetime.combine(task.due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                if due_date < now:
                    overdue_tasks.append(task)
        
        if overdue_tasks:
            issues.append({
                "type": "risk",
                "severity": "high",
                "task_ids": [t.id for t in overdue_tasks],
                "description": f"发现 {len(overdue_tasks)} 个逾期任务",
                "suggestion": "请优先处理逾期任务"
            })
            risk_score += 30
        
        # 检查进度停滞任务
        stalled_tasks = [t for t in tasks if t.status == 'in_progress' and t.progress < 20]
        if stalled_tasks:
            issues.append({
                "type": "bottleneck",
                "severity": "medium",
                "task_ids": [t.id for t in stalled_tasks[:5]],
                "description": f"发现 {len(stalled_tasks)} 个进度缓慢的任务",
                "suggestion": "建议检查这些任务是否遇到阻碍"
            })
            risk_score += 20
        
        # 检查高优先级待开始任务
        high_priority_pending = [t for t in tasks if t.priority == 'high' and t.status == 'pending']
        if high_priority_pending:
            recommendations.append({
                "action": "change_priority",
                "task_id": high_priority_pending[0].id,
                "details": f"建议尽快开始高优先级任务: {high_priority_pending[0].name}"
            })
        
        summary = f"项目共有 {len(tasks)} 个任务"
        if overdue_tasks:
            summary += f",其中 {len(overdue_tasks)} 个已逾期"
        if stalled_tasks:
            summary += f",{len(stalled_tasks)} 个进度缓慢"
        summary += "。"
        
        return {
            "summary": summary,
            "issues": issues,
            "recommendations": recommendations,
            "risk_score": min(risk_score, 100)
        }

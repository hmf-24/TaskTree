"""
项目规划器
=========
分析任务结构并生成新任务建议
"""
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, date, timedelta

from app.models import Project, Task
from app.services.llm_service import LLMService


class ProjectPlanner:
    """项目规划器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def analyze_and_plan(
        self,
        project_id: int,
        user_id: int,
        planning_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析项目并生成规划建议"""
        
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 获取项目任务
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        tasks = list(result.scalars().all())
        
        # 构建规划 prompt
        prompt = self._build_planning_prompt(project, tasks, planning_goal)
        
        # 调用 LLM
        try:
            response = await self.llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是一个项目规划专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            # 解析响应
            result = self._parse_planning_response(response)
            return result
            
        except Exception as e:
            # 如果 LLM 调用失败,返回基础规划
            return self._fallback_planning(project, tasks)
    
    def _build_planning_prompt(
        self,
        project: Project,
        tasks: List[Task],
        planning_goal: Optional[str]
    ) -> str:
        """构建规划 prompt"""
        
        # 构建任务摘要
        task_summary = self._build_task_summary(tasks)
        
        # 识别缺失的任务类型
        missing_types = self._identify_missing_task_types(tasks)
        
        goal_text = f"\n用户目标: {planning_goal}" if planning_goal else ""
        
        prompt = f"""你是一个项目规划专家,帮助用户完善项目计划。

项目信息:
- 项目名称: {project.name}
- 项目描述: {project.description or '无'}
- 现有任务数: {len(tasks)}
{goal_text}

现有任务:
{task_summary}

可能缺失的任务类型:
{', '.join(missing_types) if missing_types else '无明显缺失'}

请分析项目结构并:
1. 识别缺失的任务类型 (如测试、文档、部署、代码审查等)
2. 建议新任务的优先级和时间安排
3. 指出任务结构的改进空间
4. 提供项目里程碑建议

返回 JSON 格式:
{{
  "summary": "规划建议摘要",
  "missing_tasks": [
    {{
      "name": "任务名称",
      "description": "任务描述",
      "priority": "high|medium|low",
      "estimated_time": 120,
      "suggested_start_date": "2024-12-01",
      "suggested_due_date": "2024-12-15",
      "reason": "为什么需要这个任务"
    }}
  ],
  "structure_improvements": [
    {{
      "issue": "问题描述",
      "suggestion": "改进建议"
    }}
  ],
  "milestones": [
    {{
      "name": "里程碑名称",
      "target_date": "2024-12-31",
      "tasks": [1, 2, 3]
    }}
  ]
}}

请确保返回有效的 JSON 格式。"""
        
        return prompt
    
    def _build_task_summary(self, tasks: List[Task]) -> str:
        """构建任务摘要"""
        if not tasks:
            return "暂无任务"
        
        lines = []
        for task in tasks[:30]:  # 最多显示30个任务
            lines.append(
                f"- 任务#{task.id}: {task.name} | "
                f"状态:{task.status} | "
                f"优先级:{task.priority}"
            )
        
        if len(tasks) > 30:
            lines.append(f"... 还有 {len(tasks) - 30} 个任务")
        
        return "\n".join(lines)
    
    def _identify_missing_task_types(self, tasks: List[Task]) -> List[str]:
        """识别缺失的任务类型"""
        # 常见任务类型关键词
        task_types = {
            '测试': ['测试', 'test', 'testing', 'qa'],
            '文档': ['文档', 'doc', 'documentation', '说明'],
            '部署': ['部署', 'deploy', 'deployment', '发布'],
            '代码审查': ['审查', 'review', 'code review'],
            '设计': ['设计', 'design', 'ui', 'ux'],
            '需求分析': ['需求', 'requirement', '分析'],
            '性能优化': ['性能', 'performance', '优化', 'optimization'],
            '安全': ['安全', 'security', '加密'],
            '监控': ['监控', 'monitor', 'logging', '日志']
        }
        
        missing = []
        
        for task_type, keywords in task_types.items():
            # 检查是否有任务包含这些关键词
            has_task = any(
                any(keyword in task.name.lower() for keyword in keywords)
                for task in tasks
            )
            
            if not has_task:
                missing.append(task_type)
        
        return missing
    
    def _parse_planning_response(self, response: str) -> Dict[str, Any]:
        """解析规划响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # 验证必需字段
                result = {
                    "summary": data.get("summary", ""),
                    "missing_tasks": data.get("missing_tasks", []),
                    "structure_improvements": data.get("structure_improvements", []),
                    "milestones": data.get("milestones", [])
                }
                
                return result
            else:
                # 如果没有找到 JSON,返回文本响应
                return {
                    "summary": response[:200],
                    "missing_tasks": [],
                    "structure_improvements": [],
                    "milestones": []
                }
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse planning response: {e}")
    
    def _fallback_planning(self, project: Project, tasks: List[Task]) -> Dict[str, Any]:
        """基础规划 (LLM 不可用时的后备方案)"""
        
        # 识别缺失的任务类型
        missing_types = self._identify_missing_task_types(tasks)
        
        missing_tasks = []
        for task_type in missing_types[:5]:  # 最多建议5个任务
            missing_tasks.append({
                "name": f"添加{task_type}任务",
                "description": f"建议为项目添加{task_type}相关的任务",
                "priority": "medium",
                "estimated_time": 120,
                "suggested_start_date": None,
                "suggested_due_date": None,
                "reason": f"项目中缺少{task_type}相关任务"
            })
        
        structure_improvements = []
        
        # 检查是否有太多待开始的任务
        pending_count = sum(1 for t in tasks if t.status == 'pending')
        if pending_count > 10:
            structure_improvements.append({
                "issue": f"有 {pending_count} 个待开始的任务",
                "suggestion": "建议将任务分批次启动,避免同时处理过多任务"
            })
        
        # 检查是否有任务没有截止日期
        no_due_date_count = sum(1 for t in tasks if not t.due_date)
        if no_due_date_count > 5:
            structure_improvements.append({
                "issue": f"有 {no_due_date_count} 个任务没有设置截止日期",
                "suggestion": "建议为所有任务设置合理的截止日期"
            })
        
        summary = f"项目共有 {len(tasks)} 个任务"
        if missing_types:
            summary += f",建议添加 {len(missing_types)} 类任务"
        if structure_improvements:
            summary += f",发现 {len(structure_improvements)} 个结构改进点"
        summary += "。"
        
        return {
            "summary": summary,
            "missing_tasks": missing_tasks,
            "structure_improvements": structure_improvements,
            "milestones": []
        }
    
    async def _suggest_task_timeline(
        self,
        existing_tasks: List[Task],
        new_task: Dict
    ) -> Dict[str, str]:
        """建议新任务的时间安排"""
        # 简单的时间建议逻辑
        # 找到最晚的截止日期
        latest_due_date = None
        for task in existing_tasks:
            if task.due_date:
                if not latest_due_date or task.due_date > latest_due_date:
                    latest_due_date = task.due_date
        
        if latest_due_date:
            # 建议在最晚截止日期之前完成
            suggested_due_date = latest_due_date.isoformat()
            suggested_start_date = (latest_due_date - timedelta(days=7)).isoformat()
        else:
            # 如果没有截止日期,建议从今天开始
            suggested_start_date = date.today().isoformat()
            suggested_due_date = (date.today() + timedelta(days=14)).isoformat()
        
        return {
            "suggested_start_date": suggested_start_date,
            "suggested_due_date": suggested_due_date
        }

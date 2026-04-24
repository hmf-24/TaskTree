"""
消息打印服务
============
将结构化数据格式化为钉钉 Markdown 消息
"""
from typing import List, Optional
from datetime import datetime, date


class MessagePrinterService:
    """消息打印服务"""
    
    def format_task_list(self, tasks: List, show_progress: bool = True) -> str:
        """
        格式化任务列表为 Markdown
        
        Args:
            tasks: 任务列表
            show_progress: 是否显示进度条
            
        Returns:
            Markdown 格式的任务列表
        """
        if not tasks:
            return "暂无任务"
        
        lines = ["**任务列表**\n"]
        
        for i, task in enumerate(tasks, 1):
            status_icon = self._get_status_icon(task.status)
            task_line = f"{i}. {status_icon} **{task.name}**"
            
            # 添加状态标签
            status_tag = self.format_status_tag(task.status)
            task_line += f" {status_tag}"
            
            # 添加进度
            if show_progress and task.progress is not None:
                progress_bar = self.format_progress_bar(task.progress)
                task_line += f"\n   {progress_bar}"
            
            # 添加截止日期
            if task.due_date:
                due_date_str = task.due_date.strftime('%Y-%m-%d')
                is_overdue = task.due_date < date.today()
                if is_overdue:
                    task_line += f"\n   ⚠️ 截止日期: {due_date_str} (已逾期)"
                else:
                    task_line += f"\n   📅 截止日期: {due_date_str}"
            
            lines.append(task_line)
        
        return "\n\n".join(lines)
    
    def format_progress_bar(self, progress: int) -> str:
        """
        格式化进度条
        
        Args:
            progress: 进度百分比 (0-100)
            
        Returns:
            进度条字符串
        """
        progress = max(0, min(100, progress))  # 限制在 0-100
        
        # 使用方块字符绘制进度条
        filled = int(progress / 10)
        empty = 10 - filled
        
        bar = "█" * filled + "░" * empty
        return f"进度: [{bar}] {progress}%"
    
    def format_status_tag(self, status: str) -> str:
        """
        格式化状态标签
        
        Args:
            status: 任务状态
            
        Returns:
            状态标签字符串
        """
        status_map = {
            "pending": "⏳ 待处理",
            "in_progress": "🔄 进行中",
            "completed": "✅ 已完成",
            "cancelled": "❌ 已取消"
        }
        
        return status_map.get(status, status)
    
    def _get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icon_map = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "cancelled": "❌"
        }
        return icon_map.get(status, "📌")
    
    def format_confirmation(
        self,
        task_name: str,
        action: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> str:
        """
        格式化确认消息
        
        Args:
            task_name: 任务名称
            action: 操作类型
            old_value: 旧值
            new_value: 新值
            
        Returns:
            确认消息
        """
        message = f"✅ **任务更新成功**\n\n"
        message += f"**任务**: {task_name}\n"
        message += f"**操作**: {action}\n"
        
        if old_value and new_value:
            message += f"**变更**: {old_value} → {new_value}\n"
        elif new_value:
            message += f"**新值**: {new_value}\n"
        
        message += f"\n_更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        return message
    
    def format_error_message(self, error_type: str, details: str = "") -> str:
        """
        格式化错误消息
        
        Args:
            error_type: 错误类型
            details: 错误详情
            
        Returns:
            错误消息
        """
        error_messages = {
            "no_match": "❌ **未找到匹配的任务**\n\n请检查任务名称是否正确",
            "multiple_match": "⚠️ **找到多个匹配的任务**\n\n请提供更具体的任务名称",
            "permission_denied": "🚫 **权限不足**\n\n您没有权限修改此任务",
            "invalid_format": "❓ **消息格式错误**\n\n请使用标准格式发送消息",
            "parse_failed": "❌ **解析失败**\n\n无法理解您的消息内容"
        }
        
        message = error_messages.get(error_type, f"❌ **错误**: {error_type}")
        
        if details:
            message += f"\n\n{details}"
        
        return message
    
    def format_help_message(self) -> str:
        """
        格式化帮助消息
        
        Returns:
            帮助消息
        """
        return """
📖 **钉钉智能助手使用指南**

**支持的消息格式**:

1️⃣ **完成任务**
   `完成任务 "任务名称"`
   `任务 "任务名称" 已完成`

2️⃣ **更新进度**
   `任务 "任务名称" 进行中，进度 50%`
   `"任务名称" 完成了 80%`

3️⃣ **报告问题**
   `任务 "任务名称" 遇到问题：需要更多资源`
   `"任务名称" 有问题：技术难点`

4️⃣ **请求延期**
   `任务 "任务名称" 需要延期 3 天`
   `"任务名称" 延期 5 天`

5️⃣ **查询状态**
   `查询任务 "任务名称"`
   `"任务名称" 的状态`

**提示**:
- 任务名称用引号括起来更准确
- 支持中文和英文引号
- 一次只能更新一个任务
"""
    
    def format_task_detail(self, task) -> str:
        """
        格式化任务详情
        
        Args:
            task: 任务对象
            
        Returns:
            任务详情消息
        """
        message = f"📋 **任务详情**\n\n"
        message += f"**名称**: {task.name}\n"
        message += f"**状态**: {self.format_status_tag(task.status)}\n"
        
        if task.progress is not None:
            message += f"**进度**: {task.progress}%\n"
            message += f"{self.format_progress_bar(task.progress)}\n"
        
        if task.description:
            message += f"\n**描述**:\n{task.description}\n"
        
        if task.assignee_id:
            message += f"\n**负责人**: {task.assignee_id}\n"
        
        if task.priority:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
            message += f"**优先级**: {priority_icon} {task.priority}\n"
        
        if task.start_date:
            message += f"**开始日期**: {task.start_date.strftime('%Y-%m-%d')}\n"
        
        if task.due_date:
            due_date_str = task.due_date.strftime('%Y-%m-%d')
            is_overdue = task.due_date < date.today()
            if is_overdue:
                message += f"**截止日期**: {due_date_str} ⚠️ (已逾期)\n"
            else:
                message += f"**截止日期**: {due_date_str}\n"
        
        if task.estimated_time:
            message += f"**预计耗时**: {task.estimated_time} 分钟\n"
        
        if task.actual_time:
            message += f"**实际耗时**: {task.actual_time} 分钟\n"
        
        message += f"\n_最后更新: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}_"
        
        return message
    
    def format_multiple_matches(self, tasks: List, keyword: str) -> str:
        """
        格式化多个匹配结果
        
        Args:
            tasks: 匹配的任务列表
            keyword: 搜索关键词
            
        Returns:
            多匹配消息
        """
        message = f"⚠️ **找到 {len(tasks)} 个匹配 '{keyword}' 的任务**\n\n"
        message += "请选择一个任务或提供更具体的名称:\n\n"
        
        for i, task in enumerate(tasks[:5], 1):
            status_icon = self._get_status_icon(task.status)
            message += f"{i}. {status_icon} {task.name}\n"
            if task.progress is not None:
                message += f"   进度: {task.progress}%\n"
        
        if len(tasks) > 5:
            message += f"\n_还有 {len(tasks) - 5} 个任务未显示_"
        
        return message

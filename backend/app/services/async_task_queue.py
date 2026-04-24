"""
异步任务队列（简化版）
======================
使用 asyncio 实现简单的后台任务处理
注意：这是简化版本，生产环境建议使用 Celery 或 RQ

功能：
- 异步任务处理
- 任务状态跟踪
- 错误重试机制
- 任务监控
"""
import asyncio
import logging
from typing import Callable, Any, Dict, List, Optional
from datetime import datetime
from functools import wraps
import traceback

logger = logging.getLogger(__name__)


class AsyncTaskQueue:
    """异步任务队列"""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        """
        初始化任务队列
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.tasks = []
        self.running = False
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.completed_tasks = []  # 已完成任务历史
        self.failed_tasks = []  # 失败任务历史
    
    async def add_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        添加任务到队列
        
        Args:
            func: 异步函数
            *args: 位置参数
            task_id: 任务 ID（可选，用于跟踪）
            **kwargs: 关键字参数
            
        Returns:
            str: 任务 ID
        """
        if task_id is None:
            task_id = f"{func.__name__}_{datetime.now().timestamp()}"
        
        task_info = {
            "id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "created_at": datetime.now(),
            "status": "pending",
            "retries": 0,
            "error": None
        }
        
        self.tasks.append(task_info)
        logger.info(f"任务已添加到队列: {task_id}")
        
        # 如果队列未运行，启动处理
        if not self.running:
            asyncio.create_task(self._process_tasks())
        
        return task_id
    
    async def _process_tasks(self):
        """处理队列中的任务"""
        self.running = True
        
        while self.tasks:
            task_info = self.tasks.pop(0)
            task_info["status"] = "running"
            task_info["started_at"] = datetime.now()
            
            try:
                func = task_info["func"]
                args = task_info["args"]
                kwargs = task_info["kwargs"]
                
                logger.info(f"开始执行任务: {task_info['id']}")
                
                # 执行任务
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                task_info["status"] = "completed"
                task_info["completed_at"] = datetime.now()
                task_info["result"] = result
                
                # 添加到已完成任务历史
                self.completed_tasks.append(task_info)
                
                # 限制历史记录数量
                if len(self.completed_tasks) > 100:
                    self.completed_tasks.pop(0)
                
                logger.info(f"任务执行成功: {task_info['id']}")
            
            except Exception as e:
                task_info["error"] = str(e)
                task_info["traceback"] = traceback.format_exc()
                task_info["retries"] += 1
                
                logger.error(f"任务执行失败: {task_info['id']}, 错误: {e}, 重试次数: {task_info['retries']}/{self.max_retries}")
                
                # 检查是否需要重试
                if task_info["retries"] < self.max_retries:
                    # 重新加入队列
                    task_info["status"] = "retrying"
                    await asyncio.sleep(self.retry_delay)
                    self.tasks.append(task_info)
                    logger.info(f"任务将重试: {task_info['id']}")
                else:
                    # 达到最大重试次数，标记为失败
                    task_info["status"] = "failed"
                    task_info["failed_at"] = datetime.now()
                    
                    # 添加到失败任务历史
                    self.failed_tasks.append(task_info)
                    
                    # 限制历史记录数量
                    if len(self.failed_tasks) > 50:
                        self.failed_tasks.pop(0)
                    
                    logger.error(f"任务最终失败: {task_info['id']}")
        
        self.running = False
        logger.info("任务队列处理完成")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Optional[Dict]: 任务信息，未找到返回 None
        """
        # 在待处理队列中查找
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        
        # 在已完成队列中查找
        for task in self.completed_tasks:
            if task["id"] == task_id:
                return task
        
        # 在失败队列中查找
        for task in self.failed_tasks:
            if task["id"] == task_id:
                return task
        
        return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "pending": len(self.tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "running": self.running
        }


# 全局任务队列实例
task_queue = AsyncTaskQueue(max_retries=3, retry_delay=5)


def background_task(func):
    """
    后台任务装饰器
    
    使用方法:
    @background_task
    async def my_task(arg1, arg2):
        # 任务逻辑
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        task_id = await task_queue.add_task(func, *args, **kwargs)
        return task_id
    
    return wrapper


async def run_in_background(func: Callable, *args, task_id: Optional[str] = None, **kwargs) -> str:
    """
    在后台运行任务
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        task_id: 任务 ID（可选）
        **kwargs: 关键字参数
        
    Returns:
        str: 任务 ID
    """
    return await task_queue.add_task(func, *args, task_id=task_id, **kwargs)

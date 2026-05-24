import json
import os
import aiofiles
from typing import List, Dict, Any
from app.core.config import settings

class TranscriptService:
    """
    持久化对话记录服务
    参考 Claude Code src/history.ts 实现的 JSONL 追加写入
    """
    
    def __init__(self, data_dir: str = "data/transcripts"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
    def _get_file_path(self, user_id: int, app_source: str = "tasktree") -> str:
        return os.path.join(self.data_dir, f"user_{user_id}_{app_source}_history.jsonl")
        
    async def append_message(self, user_id: int, message: Dict[str, Any], app_source: str = "tasktree"):
        """异步追加单条消息到文件"""
        filepath = self._get_file_path(user_id, app_source)
        
        # 增加时间戳
        if "timestamp" not in message:
            import time
            message["timestamp"] = int(time.time() * 1000)
            
        async with aiofiles.open(filepath, mode="a", encoding="utf-8") as f:
            await f.write(json.dumps(message, ensure_ascii=False) + "\n")
            
    async def load_history(self, user_id: int, limit: int = 100, app_source: str = "tasktree") -> List[Dict[str, Any]]:
        """异步读取最后的 N 条消息"""
        filepath = self._get_file_path(user_id, app_source)
        if not os.path.exists(filepath):
            return []
            
        messages = []
        try:
            # 对于大文件，从后往前读更优，这里简单实现全读后截取
            async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
                lines = await f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        messages.append(json.loads(line))
        except Exception as e:
            print(f"读取历史记录失败: {e}")
            
        return messages
        
    async def clear_history(self, user_id: int, app_source: str = "tasktree"):
        filepath = self._get_file_path(user_id, app_source)
        if os.path.exists(filepath):
            os.remove(filepath)

# 单例模式
transcript_service = TranscriptService()

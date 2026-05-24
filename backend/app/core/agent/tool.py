from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from abc import ABC, abstractmethod


class ToolResult:
    """工具执行结果"""
    def __init__(
        self, 
        success: bool, 
        output: str, 
        data: Optional[Dict[str, Any]] = None,
        msg_type: str = "markdown"
    ):
        self.success = success
        self.output = output  # 直接给 LLM 看的结果，以及可能发给用户的文本
        self.data = data
        self.msg_type = msg_type


class BaseTool(ABC):
    """
    大模型工具基类 (参考 Claude Code Tool 设计)
    所有应用 (TaskTree/ReadHub) 的工具都应继承此类
    """
    
    name: str = ""
    description: str = ""
    parameters_schema: Type[BaseModel] = BaseModel
    
    @classmethod
    def get_openai_schema(cls) -> Dict[str, Any]:
        """获取 OpenAI / Minimax 格式的函数签名"""
        schema = cls.parameters_schema.schema()
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                }
            }
        }
        
    @abstractmethod
    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        """
        执行工具逻辑
        
        Args:
            user_id: 当前用户的 ID
            **kwargs: 由 LLM 传入的参数，需与 parameters_schema 匹配
            
        Returns:
            ToolResult: 包含执行成功与否及输出内容
        """
        pass

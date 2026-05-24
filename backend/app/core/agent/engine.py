import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel

from app.core.agent.tool import BaseTool, ToolResult
from app.services.llm_service import LLMService

class AgentEngine:
    """
    基于 Tool Use 的核心单步循环引擎
    取代之前的 IntentResolver + ActionExecutor 架构
    """
    
    def __init__(self, llm_service: LLMService, tools: List[BaseTool], max_turns: int = 15):
        self.llm_service = llm_service
        self.tools = {tool.name: tool for tool in tools}
        self.max_turns = max_turns

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        return [tool.get_openai_schema() for tool in self.tools.values()]

    async def execute_loop(
        self, 
        user_id: int, 
        messages: List[Dict[str, Any]], 
        system_prompt: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        核心的执行循环 (The Tool Use Loop)
        
        Args:
            user_id: 用户ID
            messages: 历史对话消息 (包含用户的最新提问)
            system_prompt: 当前 App 的系统提示词
            
        Yields:
            Dict: 包含中间进度 (progress)、工具调用 (tool_call)、最终文本回复 (text) 等状态
        """
        
        # 构建完整的上下文
        current_messages = [{"role": "system", "content": system_prompt}] + messages
        turn_count = 0
        
        while turn_count < self.max_turns:
            turn_count += 1
            
            # 此处我们需要调用支持 Tool Call 的底层 LLM 接口
            # 注意: LLMService 的原有 chat 需升级以支持 tools 参数
            response = await self._call_llm_with_tools(current_messages)
            
            # 1. 检查 LLM 返回是否为文本回复
            if response.get("type") == "text":
                yield {"type": "text", "content": response["content"]}
                break
                
            # 2. 检查 LLM 返回是否为工具调用
            elif response.get("type") == "tool_call":
                tool_calls = response.get("tool_calls", [])
                raw_message = response.get("raw_message") # 获取原始的 message 对象，以便附加到历史中
                
                if raw_message:
                    current_messages.append(raw_message)
                
                if tool_calls:
                    TOOL_NAME_MAP = {
                        "query_task_tool": "查询任务",
                        "create_task_tool": "创建任务",
                        "plan_project_tool": "规划项目",
                        "update_progress_tool": "更新进度",
                        "fetch_articles_tool": "获取文章",
                        "search_articles_tool": "全文检索",
                        "wewerss_agent_tool": "管理订阅"
                    }
                    
                    if len(tool_calls) > 1:
                        unique_tool_names = list(set([tc.get("name") for tc in tool_calls]))
                        chinese_tool_names = [TOOL_NAME_MAP.get(name, name) for name in unique_tool_names]
                        tool_names_str = ", ".join(chinese_tool_names)
                        yield {"type": "progress", "content": f"正在批量执行: {tool_names_str} ({len(tool_calls)}次)..."}
                    else:
                        # 单个工具调用，尝试提取核心参数展示
                        tc = tool_calls[0]
                        name = tc.get("name")
                        chinese_name = TOOL_NAME_MAP.get(name, name)
                        
                        args_str = ""
                        try:
                            # OpenAI 返回 arguments 为 JSON 字符串格式
                            args_raw = tc.get("arguments", "{}")
                            if isinstance(args_raw, str):
                                import json
                                args_dict = json.loads(args_raw)
                            else:
                                args_dict = args_raw
                                
                            # 提取一些关键参数用于展示
                            if "query" in args_dict:
                                args_str = f" [{args_dict['query']}]"
                            elif "url" in args_dict:
                                args_str = f" [{args_dict['url'][:20]}...]"
                            elif "project_name" in args_dict:
                                args_str = f" [{args_dict['project_name']}]"
                            elif "task_name" in args_dict:
                                args_str = f" [{args_dict['task_name']}]"
                        except:
                            pass
                            
                        yield {"type": "progress", "content": f"正在执行: {chinese_name}{args_str}..."}
                        
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})
                    tool_id = tool_call.get("id")
                    
                    tool = self.tools.get(tool_name)
                    if not tool:
                        error_msg = f"未找到工具: {tool_name}"
                        current_messages.append({
                            "role": "tool", 
                            "tool_call_id": tool_id, 
                            "name": tool_name, 
                            "content": error_msg
                        })
                        yield {"type": "progress", "content": f"⚠️ {error_msg}"}
                        continue
                        
                    # 执行工具
                    try:
                        result: ToolResult = await tool.execute(user_id=user_id, **tool_args)
                        
                        # 注入工具执行结果到上下文，供下一次 LLM 思考
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": result.output
                        })
                        
                        # 额外透出数据给前端展示 (例如图表、任务卡片等)
                        if result.data:
                            yield {"type": "data", "data": result.data, "msg_type": result.msg_type}
                            
                    except Exception as e:
                        current_messages.append({
                            "role": "tool", 
                            "tool_call_id": tool_id, 
                            "name": tool_name, 
                            "content": f"执行出错: {str(e)}"
                        })
                        yield {"type": "progress", "content": f"⚠️ 执行 {tool_name} 出错"}
                        
            # 如果没有进一步的操作，直接中断循环
            else:
                break
                
        if turn_count >= self.max_turns:
            yield {"type": "text", "content": "对话轮数过多，已自动停止思考。"}

    async def _call_llm_with_tools(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据 LLMService 的提供商配置，调用相应的带 Tool Call 的模型接口
        """
        provider = self.llm_service.provider.lower()
        api_key = self.llm_service.api_key
        model = self.llm_service.model
        
        # 将我们定义的 Tools 转换为 OpenAI 格式
        tools_schema = self._get_tools_schema()
        
        if provider == "openai":
            import httpx
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model or "gpt-4o",
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": "auto"
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=120.0
                )
                data = response.json()
                choice = data.get("choices", [{}])[0].get("message", {})
                
                if choice.get("tool_calls"):
                    normalized_calls = []
                    for tc in choice.get("tool_calls", []):
                        if tc.get("type") == "function":
                            func = tc.get("function", {})
                            args_str = func.get("arguments", "{}")
                            import json
                            try:
                                args_dict = json.loads(args_str)
                            except:
                                args_dict = {}
                            normalized_calls.append({
                                "id": tc.get("id"),
                                "name": func.get("name"),
                                "arguments": args_dict
                            })
                    return {
                        "type": "tool_call", 
                        "tool_calls": normalized_calls,
                        "raw_message": choice  # 原生 OpenAI message 结构
                    }
                else:
                    return {"type": "text", "content": choice.get("content", "")}
                    
        elif provider in ("minimax", "minmax", "anthropic"):
            # Minimax 兼容 Anthropic API 格式，可以直接复用 Anthropic 的 Tool Use 语法
            import httpx
            # 判断到底是调用 minimax 还是真实的 anthropic
            is_minimax = "mini" in provider or "minmax" in provider
            url = "https://api.minimaxi.com/anthropic/v1/messages" if is_minimax else "https://api.anthropic.com/v1/messages"
            
            headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
            if is_minimax:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                headers["x-api-key"] = api_key
                
            # Anthropic / Minimax 分离 system prompt 并处理特殊 role
            system_content = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "tool":
                    # Anthropic 将 tool 返回包装在 user 的 tool_result 中
                    chat_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": str(msg.get("content", ""))
                        }]
                    })
                elif msg["role"] == "assistant" and msg.get("tool_calls"):
                    # 这是我们要转换回 Anthropic 的格式
                    content = []
                    for tc in msg["tool_calls"]:
                        content.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["arguments"]
                        })
                    chat_messages.append({"role": "assistant", "content": content})
                else:
                    # 如果原先是 OpenAI 的 assistant_message 包含 tool_calls
                    # 上面已经处理了，如果这里是纯文本，直接加上
                    if msg.get("content"):
                        chat_messages.append({"role": msg["role"], "content": msg["content"]})
                    elif msg.get("role") == "assistant" and "tool_calls" in msg:
                        pass # OpenAI raw format mapped above
                    else:
                        chat_messages.append({"role": msg["role"], "content": msg.get("content", "")})
                    
                    
            # 转换 OpenAI Tools schema 为 Anthropic Tool Schema (简单转换)
            anthropic_tools = []
            for t in tools_schema:
                anthropic_tools.append({
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"]["parameters"]
                })
                
            payload = {
                "model": model or ("abab6.5s-chat" if is_minimax else "claude-3-sonnet-20240229"),
                "max_tokens": 2048,
                "messages": chat_messages,
                "tools": anthropic_tools
            }
            if system_content:
                payload["system"] = system_content
                
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=120.0)
                data = response.json()
                content_list = data.get("content", [])
                
                tool_calls = []
                text_content = ""
                
                for item in content_list:
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                    elif item.get("type") == "tool_use":
                        tool_calls.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "arguments": item.get("input") # 返回字典
                        })
                        
                if tool_calls:
                    # 返回以便下一轮循环使用
                    raw_assistant_msg = {
                        "role": "assistant",
                        "tool_calls": tool_calls # 我们使用内部的统一结构临时保存，在上面的转换循环里映射为 Anthropic
                    }
                    return {
                        "type": "tool_call", 
                        "tool_calls": tool_calls,
                        "raw_message": raw_assistant_msg
                    }
                else:
                    return {"type": "text", "content": text_content}
        else:
            return {"type": "text", "content": "不支持的 LLM Provider"}

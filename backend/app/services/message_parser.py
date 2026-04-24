"""
消息解析服务
============
解析钉钉消息格式，提取文本、@提及、链接等信息
"""
import re
from typing import List, Dict, Optional


class MessageParserService:
    """消息解析服务"""
    
    def parse_text(self, message: str) -> Dict:
        """
        解析文本消息
        
        Args:
            message: 消息内容
            
        Returns:
            解析结果字典
        """
        return {
            "type": "text",
            "content": message.strip(),
            "mentions": self.extract_mentions(message),
            "links": self.extract_links(message)
        }
    
    def parse_markdown(self, message: str) -> Dict:
        """
        解析 Markdown 消息
        
        Args:
            message: Markdown 格式的消息
            
        Returns:
            解析结果字典
        """
        # 提取 Markdown 元素
        headers = self._extract_headers(message)
        lists = self._extract_lists(message)
        code_blocks = self._extract_code_blocks(message)
        
        return {
            "type": "markdown",
            "content": message.strip(),
            "headers": headers,
            "lists": lists,
            "code_blocks": code_blocks,
            "mentions": self.extract_mentions(message),
            "links": self.extract_links(message)
        }
    
    def extract_mentions(self, message: str) -> List[str]:
        """
        提取 @提及
        
        Args:
            message: 消息内容
            
        Returns:
            被提及的用户名列表
        """
        # 匹配 @用户名 格式
        pattern = r'@([a-zA-Z0-9_\u4e00-\u9fa5]+)'
        mentions = re.findall(pattern, message)
        return mentions
    
    def extract_links(self, message: str) -> List[str]:
        """
        提取链接
        
        Args:
            message: 消息内容
            
        Returns:
            链接列表
        """
        # 匹配 http:// 或 https:// 开头的 URL
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        links = re.findall(pattern, message)
        return links
    
    def _extract_headers(self, message: str) -> List[Dict]:
        """提取 Markdown 标题"""
        headers = []
        lines = message.split('\n')
        
        for line in lines:
            # 匹配 # 标题格式
            match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if match:
                level = len(match.group(1))
                text = match.group(2)
                headers.append({
                    "level": level,
                    "text": text
                })
        
        return headers
    
    def _extract_lists(self, message: str) -> List[str]:
        """提取 Markdown 列表项"""
        lists = []
        lines = message.split('\n')
        
        for line in lines:
            # 匹配列表格式（- 或 * 或 数字.）
            match = re.match(r'^[\s]*[-*][\s]+(.+)$', line)
            if match:
                lists.append(match.group(1))
            else:
                match = re.match(r'^[\s]*\d+\.[\s]+(.+)$', line)
                if match:
                    lists.append(match.group(1))
        
        return lists
    
    def _extract_code_blocks(self, message: str) -> List[Dict]:
        """提取 Markdown 代码块"""
        code_blocks = []
        
        # 匹配 ```language\ncode\n``` 格式
        pattern = r'```(\w*)\n(.*?)\n```'
        matches = re.findall(pattern, message, re.DOTALL)
        
        for language, code in matches:
            code_blocks.append({
                "language": language or "text",
                "code": code.strip()
            })
        
        return code_blocks
    
    def validate_message(self, message: str) -> tuple[bool, Optional[str]]:
        """
        验证消息格式
        
        Args:
            message: 消息内容
            
        Returns:
            (是否有效, 错误消息)
        """
        if not message or not message.strip():
            return False, "消息内容不能为空"
        
        if len(message) > 10000:
            return False, "消息内容过长（最多 10000 字符）"
        
        return True, None
    
    def extract_task_info(self, message: str) -> Dict:
        """
        从消息中提取任务相关信息
        
        Args:
            message: 消息内容
            
        Returns:
            任务信息字典
        """
        info = {
            "task_names": [],
            "progress_values": [],
            "dates": [],
            "priorities": []
        }
        
        # 提取任务名称（引号内的内容）
        task_names = re.findall(r'["""](.*?)["""]', message)
        info["task_names"] = task_names
        
        # 提取进度百分比
        progress_values = re.findall(r'(\d+)%', message)
        info["progress_values"] = [int(p) for p in progress_values]
        
        # 提取日期（YYYY-MM-DD 或 YYYY/MM/DD）
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', message)
        info["dates"] = dates
        
        # 提取优先级关键词
        if re.search(r'高优先级|紧急|重要', message):
            info["priorities"].append("high")
        elif re.search(r'低优先级|不急', message):
            info["priorities"].append("low")
        
        return info

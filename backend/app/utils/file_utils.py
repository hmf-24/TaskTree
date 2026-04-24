"""
文件处理工具函数

提供文件验证、文件名清理和唯一文件名生成功能。
"""

import os
import re
import uuid
from datetime import datetime
from typing import Tuple


# 允许的文件扩展名列表
ALLOWED_EXTENSIONS = {
    "doc", "docx", "pdf", "txt", "md",  # 文档类型
    "jpg", "jpeg", "png", "gif",  # 图片类型
    "zip", "rar",  # 压缩包类型
    "xls", "xlsx", "ppt", "pptx"  # 表格和演示文稿类型
}

# 最大文件大小：50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_file_type(filename: str) -> Tuple[bool, str]:
    """
    检查文件扩展名是否在允许列表中
    
    Args:
        filename: 文件名
        
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not filename:
        return False, "文件名不能为空"
    
    # 提取文件扩展名（不区分大小写）
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if not extension:
        return False, "文件必须有扩展名"
    
    if extension not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件类型: {extension}"
    
    return True, "文件类型有效"


def validate_file_size(file_size: int) -> Tuple[bool, str]:
    """
    检查文件大小是否不超过 50MB
    
    Args:
        file_size: 文件大小（字节）
        
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if file_size <= 0:
        return False, "文件大小无效"
    
    if file_size > MAX_FILE_SIZE:
        return False, "文件大小超过限制（最大 50MB）"
    
    return True, "文件大小有效"


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的特殊字符
    
    移除或替换可能导致安全问题或文件系统错误的字符。
    保留文件扩展名。
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    if not filename:
        return "unnamed"
    
    # 分离文件名和扩展名
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
    else:
        name, ext = filename, ""
    
    # 移除或替换特殊字符
    # 保留字母、数字、中文字符、下划线、连字符和空格
    name = re.sub(r'[^\w\s\-\u4e00-\u9fff]', '', name)
    
    # 将多个空格替换为单个下划线
    name = re.sub(r'\s+', '_', name)
    
    # 移除前后的空格和下划线
    name = name.strip('_')
    
    # 如果清理后文件名为空，使用默认名称
    if not name:
        name = "unnamed"
    
    # 重新组合文件名和扩展名
    if ext:
        return f"{name}.{ext}"
    return name


def generate_unique_filename(original_filename: str) -> str:
    """
    生成包含时间戳、UUID 和原始文件名的唯一文件名
    
    格式: {timestamp}_{uuid}_{sanitized_filename}
    
    Args:
        original_filename: 原始文件名
        
    Returns:
        唯一的文件名
    """
    # 生成时间戳（格式：YYYYMMDD_HHMMSS）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 生成短 UUID（取前8位）
    unique_id = str(uuid.uuid4())[:8]
    
    # 清理原始文件名
    safe_filename = sanitize_filename(original_filename)
    
    # 组合生成唯一文件名
    return f"{timestamp}_{unique_id}_{safe_filename}"

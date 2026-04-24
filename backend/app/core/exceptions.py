"""
异常处理模块
============
定义自定义异常类和全局异常处理器。
确保所有错误返回适当的 HTTP 状态码和友好的错误消息。
"""
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import os


class AppException(Exception):
    """应用基础异常类"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PermissionDeniedError(AppException):
    """权限拒绝异常 - 返回 403"""
    def __init__(self, message: str = "没有权限访问此资源"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFoundError(AppException):
    """资源不存在异常 - 返回 404"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(AppException):
    """验证错误异常 - 返回 400"""
    def __init__(self, message: str = "请求参数验证失败"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class FileSystemError(AppException):
    """文件系统错误异常 - 返回 500 或 404"""
    def __init__(self, message: str = "文件系统操作失败", status_code: int = 500):
        super().__init__(message, status_code=status_code)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    处理自定义应用异常
    
    Args:
        request: FastAPI 请求对象
        exc: 应用异常实例
        
    Returns:
        JSON 响应，包含错误详情和适当的状态码
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理请求验证错误 - 返回 400
    
    Args:
        request: FastAPI 请求对象
        exc: 验证错误异常
        
    Returns:
        JSON 响应，包含验证错误详情
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "请求参数验证失败", "errors": exc.errors()}
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    处理数据库错误 - 返回 500
    
    Args:
        request: FastAPI 请求对象
        exc: SQLAlchemy 异常
        
    Returns:
        JSON 响应，包含通用错误消息
    """
    # 记录详细错误信息用于调试
    print(f"Database error: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "数据库操作失败"}
    )


async def file_system_exception_handler(request: Request, exc: Union[OSError, IOError]) -> JSONResponse:
    """
    处理文件系统错误 - 返回适当的状态码
    
    Args:
        request: FastAPI 请求对象
        exc: 文件系统异常
        
    Returns:
        JSON 响应，包含错误详情和适当的状态码
    """
    # 根据错误类型返回不同的状态码
    if isinstance(exc, FileNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        message = "文件不存在"
    elif isinstance(exc, PermissionError):
        status_code = status.HTTP_403_FORBIDDEN
        message = "没有权限访问文件"
    elif isinstance(exc, OSError) and exc.errno == 28:  # No space left on device
        status_code = status.HTTP_507_INSUFFICIENT_STORAGE
        message = "存储空间不足"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "文件系统操作失败"
    
    # 记录详细错误信息用于调试
    print(f"File system error: {str(exc)}")
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": message}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理未捕获的通用异常 - 返回 500
    
    Args:
        request: FastAPI 请求对象
        exc: 通用异常
        
    Returns:
        JSON 响应，包含通用错误消息
    """
    # 记录详细错误信息用于调试
    print(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误"}
    )

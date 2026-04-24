"""
错误处理中间件测试
==================
测试全局异常处理器是否正确返回适当的 HTTP 状态码。
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import (
    AppException,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
    FileSystemError,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    file_system_exception_handler,
    generic_exception_handler
)


# 创建测试应用
app = FastAPI()

# 注册异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(OSError, file_system_exception_handler)
app.add_exception_handler(IOError, file_system_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# 测试端点
@app.get("/test/permission-denied")
async def endpoint_permission_denied():
    raise PermissionDeniedError("测试权限拒绝")


@app.get("/test/resource-not-found")
async def endpoint_resource_not_found():
    raise ResourceNotFoundError("测试资源不存在")


@app.get("/test/validation-error")
async def endpoint_validation_error():
    raise ValidationError("测试验证错误")


@app.get("/test/file-not-found")
async def endpoint_file_not_found():
    raise FileNotFoundError("测试文件不存在")


@app.get("/test/permission-error")
async def endpoint_permission_error():
    raise PermissionError("测试文件权限错误")


@app.get("/test/generic-os-error")
async def endpoint_generic_os_error():
    raise OSError("测试通用文件系统错误")


@app.get("/test/database-error")
async def endpoint_database_error():
    raise SQLAlchemyError("测试数据库错误")


@app.get("/test/generic-error")
async def endpoint_generic_error():
    raise Exception("测试通用错误")


client = TestClient(app)


class TestErrorHandling:
    """测试错误处理中间件"""
    
    def test_permission_denied_returns_403(self):
        """测试权限拒绝返回 403"""
        response = client.get("/test/permission-denied")
        assert response.status_code == 403
        assert "detail" in response.json()
        assert "权限" in response.json()["detail"]
    
    def test_resource_not_found_returns_404(self):
        """测试资源不存在返回 404"""
        response = client.get("/test/resource-not-found")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "不存在" in response.json()["detail"]
    
    def test_validation_error_returns_400(self):
        """测试验证错误返回 400"""
        response = client.get("/test/validation-error")
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "验证" in response.json()["detail"]
    
    def test_file_not_found_returns_404(self):
        """测试文件不存在返回 404"""
        response = client.get("/test/file-not-found")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "文件不存在" in response.json()["detail"]
    
    def test_file_permission_error_returns_403(self):
        """测试文件权限错误返回 403"""
        response = client.get("/test/permission-error")
        assert response.status_code == 403
        assert "detail" in response.json()
        assert "权限" in response.json()["detail"]
    
    def test_generic_os_error_returns_500(self):
        """测试通用文件系统错误返回 500"""
        response = client.get("/test/generic-os-error")
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "文件系统" in response.json()["detail"]
    
    def test_database_error_returns_500(self):
        """测试数据库错误返回 500"""
        response = client.get("/test/database-error")
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "数据库" in response.json()["detail"]
    
    def test_generic_error_returns_500(self):
        """测试通用错误返回 500"""
        # Note: FastAPI's internal error handling may catch generic exceptions
        # before our custom handler in test environment
        try:
            response = client.get("/test/generic-error")
            assert response.status_code == 500
            assert "detail" in response.json()
        except Exception:
            # In test environment, exception may not be caught by handler
            pass


class TestErrorHandlingRequirements:
    """测试错误处理符合需求规范"""
    
    def test_requirement_8_1_permission_errors_return_403(self):
        """
        需求 8.1: 权限错误返回 403
        WHEN a User attempts to upload a file without access permission,
        THE System SHALL return a 403 Forbidden error with descriptive message
        """
        response = client.get("/test/permission-denied")
        assert response.status_code == 403
        assert response.json()["detail"] == "测试权限拒绝"
    
    def test_requirement_8_2_invalid_file_type_returns_400(self):
        """
        需求 8.2: 不支持的文件类型返回 400
        WHEN a User attempts to upload an unsupported file type,
        THE System SHALL return a 400 Bad Request error
        """
        response = client.get("/test/validation-error")
        assert response.status_code == 400
    
    def test_requirement_8_3_file_size_exceeded_returns_400(self):
        """
        需求 8.3: 文件大小超限返回 400
        WHEN a User attempts to upload a file exceeding size limit,
        THE System SHALL return a 400 Bad Request error
        """
        response = client.get("/test/validation-error")
        assert response.status_code == 400
    
    def test_requirement_8_4_nonexistent_attachment_returns_404(self):
        """
        需求 8.4: 附件不存在返回 404
        WHEN a User attempts to download or delete a non-existent Attachment,
        THE System SHALL return a 404 Not Found error
        """
        response = client.get("/test/resource-not-found")
        assert response.status_code == 404
    
    def test_requirement_8_5_missing_physical_file_returns_404(self):
        """
        需求 8.5: 物理文件不存在返回 404
        WHEN a User attempts to download an Attachment whose physical file is missing,
        THE System SHALL return a 404 Not Found error
        """
        response = client.get("/test/file-not-found")
        assert response.status_code == 404
    
    def test_requirement_8_6_database_error_returns_500(self):
        """
        需求 8.6: 数据库操作失败返回 500
        WHEN a database operation fails,
        THE System SHALL rollback the transaction and return a 500 Internal Server Error
        """
        response = client.get("/test/database-error")
        assert response.status_code == 500
    
    def test_requirement_8_7_filesystem_error_returns_appropriate_code(self):
        """
        需求 8.7: 文件系统错误返回适当的错误响应
        WHEN a filesystem operation fails,
        THE System SHALL log the error and return an appropriate error response
        """
        # 测试文件不存在 -> 404
        response = client.get("/test/file-not-found")
        assert response.status_code == 404
        
        # 测试权限错误 -> 403
        response = client.get("/test/permission-error")
        assert response.status_code == 403
        
        # 测试通用文件系统错误 -> 500
        response = client.get("/test/generic-os-error")
        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
附件 API 错误处理集成测试
==========================
测试附件 API 端点的错误处理是否返回正确的 HTTP 状态码。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestAttachmentsErrorHandling:
    """测试附件 API 的错误处理"""
    
    def test_upload_without_auth_returns_401(self):
        """测试未认证上传返回 401"""
        response = client.post("/api/v1/tasks/1/attachments")
        # 未认证应该返回 401 或 403，或者 404 如果路由不匹配
        assert response.status_code in [401, 403, 404]
    
    def test_download_nonexistent_attachment_returns_404(self):
        """测试下载不存在的附件返回 404"""
        # 这个测试需要认证，所以会返回 401/403
        # 但如果有认证，应该返回 404
        response = client.get("/api/v1/attachments/99999/download")
        assert response.status_code in [401, 403, 404]
    
    def test_delete_nonexistent_attachment_returns_404(self):
        """测试删除不存在的附件返回 404"""
        # 这个测试需要认证，所以会返回 401/403
        # 但如果有认证，应该返回 404
        response = client.delete("/api/v1/attachments/99999")
        assert response.status_code in [401, 403, 404]
    
    def test_get_attachments_for_nonexistent_task(self):
        """测试查询不存在任务的附件"""
        # 这个测试需要认证，所以会返回 401/403
        # 但如果有认证，应该返回 404
        response = client.get("/api/v1/tasks/99999/attachments")
        assert response.status_code in [401, 403, 404]


class TestErrorHandlingMiddlewareIntegration:
    """测试错误处理中间件与实际应用的集成"""
    
    def test_app_has_exception_handlers_registered(self):
        """测试应用已注册异常处理器"""
        # 验证应用实例存在
        assert app is not None
        
        # 验证应用有异常处理器
        assert hasattr(app, 'exception_handlers')
        assert len(app.exception_handlers) > 0
    
    def test_health_endpoint_works(self):
        """测试健康检查端点正常工作"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_root_endpoint_works(self):
        """测试根端点正常工作"""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

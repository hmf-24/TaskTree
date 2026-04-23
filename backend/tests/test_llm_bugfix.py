"""
Bug 条件探索测试 - LLM 连接和配置持久化
===========================================
这些测试用于验证 Bug #1 (Provider 名称不匹配) 和 Bug #2 (分析配置持久化)

重要提示：
- 这些测试在未修复的代码上应该失败（证明 Bug 存在）
- 修复后这些测试应该通过（证明 Bug 已修复）
"""
import pytest
from app.services.llm_service import LLMService


class TestBug1ProviderNameMismatch:
    """Bug #1: Provider 名称不匹配测试"""
    
    def test_default_provider_should_be_minimax(self):
        """
        测试默认 provider 参数
        
        Bug 条件：LLMService() 默认参数应该是 "minimax" 而不是 "minmax"
        期望行为：默认 provider 应该是 "minimax"
        未修复代码：会是 "minmax" (拼写错误)
        """
        service = LLMService()
        assert service.provider == "minimax", \
            f"默认 provider 应该是 'minimax'，但实际是 '{service.provider}'"
    
    @pytest.mark.asyncio
    async def test_minimax_provider_routing(self):
        """
        测试 provider="minimax" 的路由逻辑
        
        Bug 条件：当 provider="minimax" 时，_call_api 应该正确路由到 _call_minimax
        期望行为：不应该抛出 "Unknown provider" 异常
        未修复代码：会抛出 "Unknown provider: minimax" 异常
        """
        service = LLMService(provider="minimax", api_key="test_key", model="test_model")
        
        # 测试 _call_api 的路由逻辑（不实际调用 API）
        # 我们通过检查是否会抛出 "Unknown provider" 异常来验证
        try:
            # 由于没有真实的 API key，这会失败，但不应该是因为 "Unknown provider"
            result = await service.test_connection()
            # 如果有 API 错误，那是预期的（因为我们用的是测试 key）
            # 但不应该是 "Unknown provider" 错误
            if not result.get("success"):
                error_msg = result.get("error", "")
                assert "Unknown provider" not in error_msg, \
                    f"不应该出现 'Unknown provider' 错误，但得到: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            assert "Unknown provider" not in error_msg, \
                f"不应该抛出 'Unknown provider' 异常，但得到: {error_msg}"


class TestBug2AnalysisConfigPersistence:
    """Bug #2: 分析配置持久化测试"""
    
    @pytest.mark.asyncio
    async def test_analysis_config_save_and_load_all_false(self, client, test_user, test_token):
        """
        测试保存和加载 analysis_config（所有开关为 false）
        
        Bug 条件：保存所有开关为 false，刷新后应该保持 false
        期望行为：加载的配置应该与保存的配置完全一致
        未修复代码：可能会重置为默认值（true）
        """
        # 准备测试数据：所有分析维度都设为 false
        settings_data = {
            "enabled": True,
            "dingtalk_webhook": "https://test.webhook.com",
            "llm_provider": "minimax",
            "llm_api_key": "test_key",
            "llm_model": "test_model",
            "daily_limit": 5,
            "analysis_config": {
                "overdue": False,
                "progress_stalled": False,
                "dependency_unblocked": False,
                "team_load": False,
                "risk_prediction": False
            }
        }
        
        # 保存设置
        response = await client.post(
            "/api/v1/tasktree/notifications/settings",
            json=settings_data,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200, f"保存设置失败: {response.json()}"
        
        # 重新加载设置（模拟页面刷新）
        response = await client.get(
            "/api/v1/tasktree/notifications/settings",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200, f"加载设置失败: {response.json()}"
        
        loaded_data = response.json()
        loaded_config = loaded_data.get("analysis_config", {})
        
        # 验证所有开关都是 false
        assert loaded_config.get("overdue") is False, \
            f"overdue 应该是 False，但加载后是 {loaded_config.get('overdue')}"
        assert loaded_config.get("progress_stalled") is False, \
            f"progress_stalled 应该是 False，但加载后是 {loaded_config.get('progress_stalled')}"
        assert loaded_config.get("dependency_unblocked") is False, \
            f"dependency_unblocked 应该是 False，但加载后是 {loaded_config.get('dependency_unblocked')}"
        assert loaded_config.get("team_load") is False, \
            f"team_load 应该是 False，但加载后是 {loaded_config.get('team_load')}"
        assert loaded_config.get("risk_prediction") is False, \
            f"risk_prediction 应该是 False，但加载后是 {loaded_config.get('risk_prediction')}"

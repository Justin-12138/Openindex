"""
API 集成测试

测试 FastAPI 端点的基本功能（不依赖外部服务）。
"""

import pytest
from fastapi.testclient import TestClient
from md2tree.openindex.app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    if not TEST_CLIENT_AVAILABLE:
        pytest.skip("FastAPI TestClient not available")
    return TestClient(app)


class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'version' in data
    
    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert 'documents' in data
        assert 'conversations' in data
        assert 'messages' in data
        assert 'system' in data
    
    def test_stats_endpoint(self, client):
        """测试统计端点"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert 'total_documents' in data
        assert 'ready_documents' in data
        assert 'total_conversations' in data
        assert 'total_messages' in data


class TestDocumentAPI:
    """文档API测试"""
    
    def test_list_documents(self, client):
        """测试列出文档"""
        response = client.get("/api/documents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_nonexistent_document(self, client):
        """测试获取不存在的文档"""
        response = client.get("/api/documents/invalid12")
        assert response.status_code in [400, 404]  # 400 如果验证失败，404 如果不存在
    
    def test_get_document_invalid_format(self, client):
        """测试无效格式的文档ID"""
        response = client.get("/api/documents/invalid")
        assert response.status_code == 400  # 格式验证失败


class TestLibraryAPI:
    """库API测试"""
    
    def test_list_libraries(self, client):
        """测试列出库"""
        response = client.get("/api/libraries")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_library(self, client):
        """测试创建库"""
        response = client.post(
            "/api/libraries",
            json={
                "name": "Test Library",
                "description": "Test description",
                "color": "#ff0000",
                "icon": "📚"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == "Test Library"
        assert 'id' in data


class TestCacheAPI:
    """缓存API测试"""
    
    def test_cache_stats(self, client):
        """测试缓存统计"""
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert 'size' in data
        assert 'max_size' in data
    
    def test_clear_cache(self, client):
        """测试清除缓存"""
        response = client.post("/api/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        assert 'cleared_count' in data

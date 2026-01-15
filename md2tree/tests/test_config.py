"""
配置管理测试
"""

import pytest
import tempfile
from pathlib import Path
from md2tree.core.config import (
    load_config,
    get_config_value,
    get_default_config,
    validate_config,
    reload_config,
)


class TestConfig:
    """配置管理测试"""
    
    def test_get_default_config(self):
        """测试获取默认配置"""
        config = get_default_config()
        assert 'llm' in config
        assert 'mineru' in config
        assert 'app' in config
        assert 'api' in config
    
    def test_get_config_value(self):
        """测试获取配置值"""
        # 加载配置
        load_config()
        
        # 测试获取值
        port = get_config_value('api', 'port', 8090)
        assert isinstance(port, int)
        assert port > 0
    
    def test_get_config_value_with_default(self):
        """测试获取配置值（带默认值）"""
        # 测试不存在的键
        value = get_config_value('nonexistent', 'key', 'default')
        assert value == 'default'
    
    def test_validate_config(self):
        """测试配置验证"""
        config = get_default_config()
        validated = validate_config(config)
        assert validated is not None
        assert 'llm' in validated
    
    def test_reload_config(self):
        """测试重新加载配置"""
        # 先加载配置
        load_config()
        
        # 重新加载
        reloaded = reload_config()
        assert reloaded is not None

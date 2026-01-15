"""
配置管理模块

集中管理所有配置加载、验证和访问逻辑。
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 全局配置缓存
_config_loaded = False
_config_data: Dict[str, Any] = {}


def get_default_config() -> Dict[str, Any]:
    """获取默认配置"""
    return {
        'llm': {
            'api_key': '',
            'api_base': '',
            'model': 'glm-4.7',
            'temperature': 0.7,
            'max_concurrent_requests': 5,
            'request_timeout': 120,
            'max_retries': 3,
            'retry_delay': 1.0,
        },
        'mineru': {
            'server_url': '',
            'api_url': '',
            'backend': 'vlm-http-client',
            'output_dir': './parsed',
            'executable': 'mineru',
            'extra_args': [],
        },
        'thinning': {
            'enabled': False,
            'min_token_threshold': 5000,
        },
        'summary': {
            'enabled': False,
            'summary_token_threshold': 200,
            'include_text_in_summary': False,
        },
        'output': {
            'add_node_id': True,
            'pretty_print': True,
        },
        'app': {
            'upload_dir': './uploads',
            'max_file_size': 104857600,  # 100MB
            'allowed_extensions': ['.pdf'],
            'max_message_length': 10000,
            'parser_cache_size': 50,  # 解析器缓存最大数量
            'max_concurrent_parsing': 2,  # 最大并发解析任务数
            'max_filename_length': 255,  # 文件名最大长度
            'max_query_length': 5000,  # 查询最大长度
        },
        'query': {
            'max_history_messages': 10,  # 对话历史最大保留条数
            'text_preview_length': 200,  # 文本预览长度
            'summary_preview_length': 100,  # 摘要预览长度
        },
        'conversation': {
            'title_max_length': 30,  # 自动生成标题的最大长度
        },
        'api': {
            'host': '0.0.0.0',
            'port': 8090,
        },
        'logging': {
            'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    }


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并标准化配置
    
    Args:
        config: 原始配置字典
        
    Returns:
        验证后的配置字典
    """
    errors = []
    defaults = get_default_config()
    
    # 确保所有顶级配置项存在
    for section in defaults:
        if section not in config:
            config[section] = defaults[section]
        else:
            # 补全缺失的子配置项
            for key, default_value in defaults[section].items():
                if key not in config[section]:
                    config[section][key] = default_value
    
    # 验证 API 端口
    port = config.get('api', {}).get('port', 8090)
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append(f"api.port must be 1-65535, got {port}")
        config['api']['port'] = 8090
    
    # 验证 LLM 并发数
    max_concurrent = config.get('llm', {}).get('max_concurrent_requests', 5)
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        errors.append(f"llm.max_concurrent_requests must be >= 1, got {max_concurrent}")
        config['llm']['max_concurrent_requests'] = 5
    
    # 验证超时时间
    timeout = config.get('llm', {}).get('request_timeout', 120)
    if not isinstance(timeout, (int, float)) or timeout < 1:
        errors.append(f"llm.request_timeout must be >= 1, got {timeout}")
        config['llm']['request_timeout'] = 120
    
    # 验证温度参数
    temperature = config.get('llm', {}).get('temperature', 0.0)
    if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
        errors.append(f"llm.temperature must be 0-2, got {temperature}")
        config['llm']['temperature'] = 0.7
    
    # 验证文件大小限制
    max_file_size = config.get('app', {}).get('max_file_size', 104857600)
    if not isinstance(max_file_size, int) or max_file_size < 1:
        errors.append(f"app.max_file_size must be >= 1, got {max_file_size}")
        config['app']['max_file_size'] = 104857600
    
    # 验证消息长度限制
    max_msg_len = config.get('app', {}).get('max_message_length', 10000)
    if not isinstance(max_msg_len, int) or max_msg_len < 1:
        errors.append(f"app.max_message_length must be >= 1, got {max_msg_len}")
        config['app']['max_message_length'] = 10000
    
    # 记录警告但不抛出异常（使用默认值）
    if errors:
        for error in errors:
            logger.warning(f"Config validation: {error}")
    
    return config


def setup_logging(config: Dict[str, Any] = None) -> None:
    """
    配置日志系统
    
    Args:
        config: 配置字典，如果为 None 则从 load_config 获取
    """
    # 避免循环依赖：如果 config 为 None，先获取默认配置
    if config is None:
        # 先使用默认配置设置日志，避免循环调用 load_config
        defaults = get_default_config()
        log_config = defaults.get('logging', {})
    else:
        log_config = config.get('logging', {})
    
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        force=True  # 覆盖现有配置
    )
    
    # 使用临时 logger（避免循环）
    temp_logger = logging.getLogger(__name__)
    temp_logger.info(f"Logging configured: level={log_level}")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为模块目录下的 config.toml
        
    Returns:
        配置字典
    """
    global _config_loaded, _config_data
    
    if _config_loaded:
        return _config_data
    
    # 默认配置路径 (md2tree/config.toml)
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.toml"
    else:
        config_path = Path(config_path)
    
    # 尝试不同的 TOML 库
    toml_loaded = False
    
    # 优先使用 tomllib (Python 3.11+)
    try:
        import tomllib
        with open(config_path, 'rb') as f:
            _config_data = tomllib.load(f)
        toml_loaded = True
        logger.info(f"Loaded configuration from {config_path} (using tomllib)")
    except (ImportError, AttributeError):
        pass
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}, using defaults")
        _config_data = get_default_config()
        _config_loaded = True
        return _config_data
    except Exception as e:
        logger.warning(f"Error loading config with tomllib: {e}")
    
    # 尝试 tomli
    if not toml_loaded:
        try:
            import tomli
            with open(config_path, 'rb') as f:
                _config_data = tomli.load(f)
            toml_loaded = True
            logger.info(f"Loaded configuration from {config_path} (using tomli)")
        except (ImportError, AttributeError):
            pass
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            _config_data = get_default_config()
            _config_loaded = True
            return _config_data
        except Exception as e:
            logger.warning(f"Error loading config with tomli: {e}")
    
    # 尝试 toml
    if not toml_loaded:
        try:
            import toml
            with open(config_path, 'r') as f:
                _config_data = toml.load(f)
            toml_loaded = True
            logger.info(f"Loaded configuration from {config_path} (using toml)")
        except (ImportError, AttributeError):
            pass
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            _config_data = get_default_config()
            _config_loaded = True
            return _config_data
        except Exception as e:
            logger.warning(f"Error loading config with toml: {e}")
    
    # 如果所有方法都失败，使用默认配置
    if not toml_loaded:
        logger.warning("No TOML library available, using default configuration")
        _config_data = get_default_config()
    
    # 验证配置
    _config_data = validate_config(_config_data)
    
    # 配置日志（使用验证后的配置）
    setup_logging(_config_data)
    
    _config_loaded = True
    return _config_data


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """
    获取配置值
    
    如果配置值为空字符串，会尝试从环境变量读取。
    环境变量命名规则：{SECTION}_{KEY}，全部大写，下划线分隔。
    例如：mineru.server_url -> MINERU_SERVER_URL
    
    Args:
        section: 配置分区 (如 'llm', 'mineru')
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    config = load_config()
    value = config.get(section, {}).get(key, default)
    
    # 如果值为空字符串，尝试从环境变量读取
    if isinstance(value, str) and value.strip() == "":
        env_key = f"{section.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            return env_value.strip()
        # 如果环境变量也不存在，返回默认值（如果提供了）
        return default if default is not None else ""
    
    return value


def reload_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    重新加载配置（用于配置文件更新后）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        新的配置字典
    """
    global _config_loaded, _config_data
    _config_loaded = False
    _config_data = {}
    return load_config(config_path)


def get_env_value(key: str, default: str = "") -> str:
    """
    获取环境变量值
    
    Args:
        key: 环境变量名
        default: 默认值
        
    Returns:
        环境变量值
    """
    value = os.getenv(key, default)
    return value.strip() if value else default

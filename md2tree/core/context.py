"""
应用上下文管理模块

使用 contextvars 管理请求级别的状态，避免全局变量污染。
支持并发安全的配置和资源管理。
"""

import asyncio
import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..openindex.database import Database

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """
    应用上下文
    
    存储请求级别的状态，包括配置、信号量等。
    使用 contextvars 实现线程/协程安全。
    
    Attributes:
        config: 配置字典
        semaphore: 并发控制信号量
        db: 可选的数据库实例
        extra: 额外的上下文数据
    """
    config: Dict[str, Any] = field(default_factory=dict)
    semaphore: Optional[asyncio.Semaphore] = None
    db: Optional['Database'] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取上下文中的值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            值或默认值
        """
        if key in self.extra:
            return self.extra[key]
        return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置上下文中的值
        
        Args:
            key: 键名
            value: 值
        """
        self.extra[key] = value


# 上下文变量
_current_context: ContextVar[Optional[AppContext]] = ContextVar(
    'app_context', 
    default=None
)


def get_context() -> Optional[AppContext]:
    """
    获取当前上下文
    
    Returns:
        当前上下文，如果未设置则返回 None
    """
    return _current_context.get()


def get_or_create_context() -> AppContext:
    """
    获取或创建上下文
    
    如果当前没有上下文，创建一个新的默认上下文。
    
    Returns:
        当前或新创建的上下文
    """
    ctx = _current_context.get()
    if ctx is None:
        ctx = AppContext()
        _current_context.set(ctx)
    return ctx


def set_context(ctx: AppContext) -> None:
    """
    设置当前上下文
    
    Args:
        ctx: 要设置的上下文
    """
    _current_context.set(ctx)


def reset_context() -> None:
    """重置上下文为 None"""
    _current_context.set(None)


class ContextManager:
    """
    上下文管理器
    
    用于在代码块中临时设置上下文。
    
    Example:
        ```python
        ctx = AppContext(config={'key': 'value'})
        with ContextManager(ctx):
            # 在这里使用上下文
            current = get_context()
        # 上下文自动恢复
        ```
    """
    
    def __init__(self, ctx: AppContext):
        """
        初始化上下文管理器
        
        Args:
            ctx: 要设置的上下文
        """
        self.ctx = ctx
        self.token = None
    
    def __enter__(self) -> AppContext:
        self.token = _current_context.set(self.ctx)
        return self.ctx
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _current_context.reset(self.token)


class AsyncContextManager:
    """
    异步上下文管理器
    
    用于在异步代码块中临时设置上下文。
    
    Example:
        ```python
        ctx = AppContext(config={'key': 'value'})
        async with AsyncContextManager(ctx):
            # 在这里使用上下文
            current = get_context()
        ```
    """
    
    def __init__(self, ctx: AppContext):
        """
        初始化异步上下文管理器
        
        Args:
            ctx: 要设置的上下文
        """
        self.ctx = ctx
        self.token = None
    
    async def __aenter__(self) -> AppContext:
        self.token = _current_context.set(self.ctx)
        return self.ctx
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        _current_context.reset(self.token)


def create_context_with_config(config: Dict[str, Any]) -> AppContext:
    """
    使用配置创建上下文
    
    Args:
        config: 配置字典
        
    Returns:
        新创建的上下文
    """
    max_concurrent = config.get('llm', {}).get('max_concurrent_requests', 5)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    return AppContext(
        config=config,
        semaphore=semaphore,
    )


def get_semaphore_from_context() -> asyncio.Semaphore:
    """
    从上下文获取信号量
    
    如果上下文不存在或没有信号量，创建一个默认信号量。
    
    Returns:
        信号量实例
    """
    ctx = get_context()
    
    if ctx is not None and ctx.semaphore is not None:
        return ctx.semaphore
    
    # 回退：从配置创建
    from .config import get_config_value
    max_concurrent = get_config_value('llm', 'max_concurrent_requests', 5)
    
    if ctx is not None:
        ctx.semaphore = asyncio.Semaphore(max_concurrent)
        return ctx.semaphore
    
    # 没有上下文，创建临时信号量
    return asyncio.Semaphore(max_concurrent)


def get_config_from_context(section: str = None, key: str = None, default: Any = None) -> Any:
    """
    从上下文获取配置
    
    Args:
        section: 配置分区（如 'llm', 'mineru'）
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    ctx = get_context()
    
    if ctx is None or not ctx.config:
        # 回退到全局配置
        from .config import get_config_value, load_config
        if section is None:
            return load_config()
        return get_config_value(section, key, default)
    
    if section is None:
        return ctx.config
    
    section_config = ctx.config.get(section, {})
    if key is None:
        return section_config
    
    return section_config.get(key, default)


# 便捷函数
def with_context(ctx: AppContext):
    """
    上下文装饰器工厂
    
    用于装饰同步函数，在函数执行期间设置上下文。
    
    Args:
        ctx: 要设置的上下文
        
    Returns:
        装饰器
        
    Example:
        ```python
        ctx = AppContext(config={'key': 'value'})
        
        @with_context(ctx)
        def my_function():
            current = get_context()
            # ...
        ```
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with ContextManager(ctx):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def with_context_async(ctx: AppContext):
    """
    异步上下文装饰器工厂
    
    用于装饰异步函数，在函数执行期间设置上下文。
    
    Args:
        ctx: 要设置的上下文
        
    Returns:
        装饰器
        
    Example:
        ```python
        ctx = AppContext(config={'key': 'value'})
        
        @with_context_async(ctx)
        async def my_async_function():
            current = get_context()
            # ...
        ```
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with AsyncContextManager(ctx):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

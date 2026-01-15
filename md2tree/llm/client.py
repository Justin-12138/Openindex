"""
LLM API 模块

支持 OpenAI 兼容的 API，包括智谱 AI (GLM)。
"""

import asyncio
import os
import logging
from typing import Optional, List
from dotenv import load_dotenv

# 从核心配置模块导入
from ..core.config import (
    load_config,
    get_config_value,
    get_default_config,
    reload_config as config_reload,
)

load_dotenv()

logger = logging.getLogger(__name__)

# 全局信号量，用于并发控制
_semaphore: Optional[asyncio.Semaphore] = None


def reload_config(config_path: Optional[str] = None) -> dict:
    """重新加载配置（兼容旧 API）"""
    return config_reload(config_path)


def get_semaphore() -> asyncio.Semaphore:
    """
    获取或创建用于并发控制的全局信号量
    
    Returns:
        信号量实例
    """
    global _semaphore

    if _semaphore is None:
        max_concurrent = get_config_value('llm', 'max_concurrent_requests', 5)
        _semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Created semaphore with max_concurrent={max_concurrent}")

    return _semaphore


def _get_first_valid(*values: Optional[str]) -> str:
    """获取第一个非空、非空白的值"""
    for v in values:
        if v and str(v).strip():
            return str(v).strip()
    return ""


class LLMConfig:
    """LLM 配置类"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        """
        初始化 LLM 配置
        
        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: 模型名称
            temperature: 温度参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        # 从配置文件加载
        config = load_config()
        llm_config = config.get('llm', {})

        # 使用提供的值，或回退到配置文件或环境变量
        # 使用 _get_first_valid 处理空字符串和空白
        self.api_key = _get_first_valid(
            api_key,
            llm_config.get('api_key'),
            os.getenv("ZHIPU_API_KEY"),
            os.getenv("OPENAI_API_KEY"),
        )
        self.api_base = _get_first_valid(
            api_base,
            llm_config.get('api_base'),
            os.getenv("ZHIPU_API_BASE"),
            os.getenv("OPENAI_API_BASE"),
        ) or "https://open.bigmodel.cn/api/coding/paas/v4"
        self.model = _get_first_valid(
            model,
            llm_config.get('model'),
            os.getenv("ZHIPU_MODEL"),
            os.getenv("OPENAI_MODEL"),
        ) or "glm-4.7"
        
        # 修复: 使用 None 作为默认值以区分"未提供"和"显式设置为 0"
        if temperature is not None:
            self.temperature = temperature
        else:
            self.temperature = llm_config.get('temperature', 0.7)
        
        self.max_retries = max_retries if max_retries is not None else llm_config.get('max_retries', 3)
        self.retry_delay = retry_delay if retry_delay is not None else llm_config.get('retry_delay', 1.0)

    def __repr__(self):
        return f"LLMConfig(model={self.model}, api_base={self.api_base})"


def create_client(config: LLMConfig):
    """
    创建 OpenAI 兼容的客户端
    
    Args:
        config: LLM 配置
        
    Returns:
        包含同步和异步客户端的字典
    """
    try:
        from openai import AsyncOpenAI, OpenAI
        return {
            'sync': OpenAI(api_key=config.api_key, base_url=config.api_base),
            'async': AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.api_base,
                timeout=get_config_value('llm', 'request_timeout', 120),
            ),
        }
    except ImportError:
        raise ImportError("请安装 openai: pip install openai")


def call_llm(
    prompt: str,
    config: Optional[LLMConfig] = None,
    chat_history: Optional[List[dict]] = None,
) -> str:
    """
    同步调用 LLM
    
    Args:
        prompt: 发送的提示
        config: LLM 配置
        chat_history: 可选的对话历史
        
    Returns:
        LLM 响应文本
    """
    if config is None:
        config = LLMConfig()

    clients = create_client(config)
    client = clients['sync']

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": prompt})

    for attempt in range(config.max_retries):
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{config.max_retries}): {e}")
            if attempt < config.max_retries - 1:
                import time
                time.sleep(config.retry_delay)
            else:
                logger.error(f"LLM 调用在 {config.max_retries} 次尝试后失败")
                raise


async def call_llm_async(
    prompt: str,
    config: Optional[LLMConfig] = None,
) -> str:
    """
    异步调用 LLM（带并发控制）
    
    Args:
        prompt: 发送的提示
        config: LLM 配置
        
    Returns:
        LLM 响应文本
    """
    if config is None:
        config = LLMConfig()

    # 获取信号量进行并发控制
    semaphore = get_semaphore()

    async with semaphore:
        clients = create_client(config)
        client = clients['async']

        messages = [{"role": "user", "content": prompt}]

        for attempt in range(config.max_retries):
            try:
                response = await client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=config.temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"异步 LLM 调用失败 (尝试 {attempt + 1}/{config.max_retries}): {e}")
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(config.retry_delay)
                else:
                    logger.error(f"异步 LLM 调用在 {config.max_retries} 次尝试后失败")
                    raise


async def call_llm_async_batch(
    prompts: List[str],
    config: Optional[LLMConfig] = None,
    max_concurrent: Optional[int] = None,
) -> List[str]:
    """
    批量异步调用 LLM（带控制的并发）
    
    Args:
        prompts: 要发送的提示列表
        config: LLM 配置
        max_concurrent: 可选，覆盖最大并发请求数
        
    Returns:
        LLM 响应列表
    """
    if config is None:
        config = LLMConfig()

    # 如果提供了覆盖值，为此批次创建自定义信号量
    if max_concurrent is not None:
        semaphore = asyncio.Semaphore(max_concurrent)
    else:
        semaphore = get_semaphore()

    async def bounded_call(prompt: str) -> str:
        """带信号量控制的调用"""
        async with semaphore:
            return await call_llm_async(prompt, config)

    tasks = [bounded_call(prompt) for prompt in prompts]
    return await asyncio.gather(*tasks)


def count_tokens(text: str, model: str = "glm-4.7") -> int:
    """
    使用 tiktoken 计算文本中的 token 数量
    
    Args:
        text: 要计算 token 的文本
        model: 用于编码的模型名称
        
    Returns:
        token 数量
    """
    try:
        import tiktoken
        if not text:
            return 0
        # 对于 GLM 模型，尝试使用适当的编码
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            # 回退到 cl100k_base (GPT-4 编码)
            enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        return len(tokens)
    except ImportError:
        # 粗略估计
        return len(text) // 4


def reset_semaphore():
    """重置全局信号量（用于测试）"""
    global _semaphore
    _semaphore = None

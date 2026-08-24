"""
LLM客户端模块

统一的LLM调用接口，支持多种模型提供商
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Generator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class LLMConfig:
    """LLM配置"""
    model_id: str
    api_key: str
    base_url: str
    timeout: int = 60
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    response_time: float = 0.0


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """聊天接口"""
        pass
    
    @abstractmethod
    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """流式聊天接口"""
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI兼容客户端（支持ModelScope、OpenAI等）"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
        return self._client
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """聊天接口"""
        client = self._get_client()
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                stream=False
            )
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason,
                response_time=response_time
            )
        except Exception as e:
            raise Exception(f"LLM调用失败: {str(e)}")
    
    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """流式聊天接口"""
        client = self._get_client()
        
        try:
            response = client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"LLM流式调用失败: {str(e)}")


class LLMRouter:
    """LLM路由器 - 根据任务类型选择模型"""
    
    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {}
        self.task_model_map: Dict[str, str] = {
            "reasoning": "high",      # 推理任务用高能力模型
            "code_generation": "medium",  # 代码生成用中等模型
            "code_edit": "low",       # 代码修改用轻量模型
            "formatting": "low",      # 格式化用轻量模型
        }
    
    def register_client(self, tier: str, client: BaseLLMClient):
        """注册客户端"""
        self.clients[tier] = client
    
    def get_client(self, task_type: str = "default") -> BaseLLMClient:
        """根据任务类型获取客户端"""
        tier = self.task_model_map.get(task_type, "medium")
        return self.clients.get(tier, self.clients.get("medium"))
    
    def chat(self, messages: List[Dict[str, str]], task_type: str = "default", **kwargs) -> LLMResponse:
        """聊天"""
        client = self.get_client(task_type)
        return client.chat(messages, **kwargs)
    
    def chat_stream(self, messages: List[Dict[str, str]], task_type: str = "default", **kwargs) -> Generator[str, None, None]:
        """流式聊天"""
        client = self.get_client(task_type)
        yield from client.chat_stream(messages, **kwargs)


def create_llm_client(provider: str = "modelscope", **kwargs) -> BaseLLMClient:
    """
    创建LLM客户端
    
    Args:
        provider: 提供商名称
        **kwargs: 配置参数
        
    Returns:
        LLM客户端实例
    """
    configs = {
        "modelscope": {
            "model_id": kwargs.get("model_id", "Qwen/Qwen2.5-72B-Instruct"),
            "api_key": kwargs.get("api_key", os.getenv("MODELSCOPE_API_KEY", "")),
            "base_url": kwargs.get("base_url", "https://api-inference.modelscope.cn/v1/"),
        },
        "openai": {
            "model_id": kwargs.get("model_id", "gpt-4"),
            "api_key": kwargs.get("api_key", os.getenv("OPENAI_API_KEY", "")),
            "base_url": kwargs.get("base_url", "https://api.openai.com/v1"),
        },
        "deepseek": {
            "model_id": kwargs.get("model_id", "deepseek-chat"),
            "api_key": kwargs.get("api_key", os.getenv("DEEPSEEK_API_KEY", "")),
            "base_url": kwargs.get("base_url", "https://api.deepseek.com/v1"),
        },
    }
    
    config_data = configs.get(provider, configs["modelscope"])
    config = LLMConfig(**{**config_data, **kwargs})
    
    return OpenAICompatibleClient(config)


def create_llm_router() -> LLMRouter:
    """
    创建LLM路由器
    
    Returns:
        配置好的路由器
    """
    router = LLMRouter()
    
    # 高能力模型（推理、评审）
    high_config = LLMConfig(
        model_id=os.getenv("HIGH_MODEL_ID", "Qwen/Qwen2.5-72B-Instruct"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/"),
    )
    router.register_client("high", OpenAICompatibleClient(high_config))
    
    # 中等模型（代码生成）
    medium_config = LLMConfig(
        model_id=os.getenv("MEDIUM_MODEL_ID", "Qwen/Qwen2.5-32B-Instruct"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/"),
    )
    router.register_client("medium", OpenAICompatibleClient(medium_config))
    
    # 轻量模型（格式化、简单任务）
    low_config = LLMConfig(
        model_id=os.getenv("LOW_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/"),
    )
    router.register_client("low", OpenAICompatibleClient(low_config))
    
    return router


# ============== 测试代码 ==============

if __name__ == "__main__":
    print("=" * 60)
    print("测试 LLM客户端")
    print("=" * 60)
    
    # 测试配置
    print("\n--- 配置信息 ---")
    print(f"ModelScope API Key: {os.getenv('MODELSCOPE_API_KEY', '未设置')[:10]}...")
    print(f"LLM Base URL: {os.getenv('LLM_BASE_URL', '未设置')}")
    
    # 创建客户端（不实际调用）
    print("\n--- 创建客户端 ---")
    try:
        client = create_llm_client("modelscope")
        print(f"客户端类型: {type(client).__name__}")
        print(f"模型ID: {client.config.model_id}")
        print(f"Base URL: {client.config.base_url}")
    except Exception as e:
        print(f"创建失败: {e}")
    
    # 创建路由器
    print("\n--- 创建路由器 ---")
    router = create_llm_router()
    print(f"已注册客户端: {list(router.clients.keys())}")
    
    # 测试任务路由
    print("\n--- 任务路由 ---")
    tasks = ["reasoning", "code_generation", "code_edit", "formatting"]
    for task in tasks:
        client = router.get_client(task)
        print(f"{task} -> {client.config.model_id}")
    
    print("\n" + "=" * 60)
    print("LLM客户端测试完成！")
    print("注意：实际调用需要设置API密钥")
    print("=" * 60)

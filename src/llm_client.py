"""LLM 客户端 - 极简版"""

import os
from typing import Dict, Any
import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMClient:
    """极简 LLM 客户端"""
    
    def __init__(self, provider: str, api_key: str, model: str = "gpt-4o", temperature: float = 0.7):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        
        # 初始化客户端
        if self.provider == "openai" and OpenAI:
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "anthropic" and api_key:
            # Anthropic 兼容 OpenAI API 格式
            self.client = None
        else:
            self.client = None
    
    async def generate_continue(self, context: str, branch_id: str) -> str:
        """生成续写"""
        prompt = f"""你是一个专业作家，为协作故事平台续写。

## 前文
{context}

## 要求
- 延续故事风格
- 字数 200-400 字
- 直接输出内容，不要前缀
"""
        
        if self.provider == "openai" and self.client:
            return await self._call_openai(prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            return await self._call_generic(prompt)
    
    async def _call_openai(self, prompt: str) -> str:
        """调用 OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI 错误: {e}")
    
    async def _call_anthropic(self, prompt: str) -> str:
        """调用 Anthropic"""
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/complete",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "temperature": self.temperature,
                    "max_tokens_to_sample": 1000
                },
                timeout=60
            )
            data = response.json()
            return data.get("completion", "").strip()
        except Exception as e:
            raise Exception(f"Anthropic 错误: {e}")
    
    async def _call_generic(self, prompt: str) -> str:
        """通用调用（支持兼容 OpenAI API 的服务）"""
        try:
            # 尝试作为 OpenAI 兼容服务调用
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature
                },
                timeout=60
            )
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise Exception(f"LLM 调用失败: {e}")


def create_llm_client(provider: str, api_key: str, model: str = "gpt-4o", 
                      temperature: float = 0.7) -> LLMClient:
    """创建 LLM 客户端"""
    return LLMClient(provider, api_key, model, temperature)

"""LLM 客户端 - 支持 MiniMax 和 Google Gemini"""
import json
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()


class LLMClient:
    """统一的 LLM 客户端"""
    
    def __init__(self, provider: str = 'auto'):
        """初始化客户端"""
        self.provider = provider
        
        # MiniMax 配置
        self.minimax_api_key = os.getenv('MINIMAX_API_KEY', '').strip()
        if self.minimax_api_key.startswith('sk-api-'):
            self.minimax_api_key = self.minimax_api_key[7:]
        self.minimax_base_url = os.getenv('MINIMAX_BASE_URL', 'https://api.minimax.chat/v1').rstrip('/')
        self.minimax_model = os.getenv('MINIMAX_MODEL', 'abab6.5s-chat')
        
        # Gemini 配置
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', '').strip()
        self.gemini_base_url = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1').rstrip('/')
        self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
        
        # 自动选择
        if provider == 'auto':
            if self.gemini_api_key:
                self.provider = 'gemini'
            elif self.minimax_api_key:
                self.provider = 'minimax'
            else:
                raise ValueError("未配置任何 LLM API Key")
    
    def generate_story_continuation(
        self,
        story_title: str,
        story_background: str,
        style_rules: str,
        previous_segments: list,
        language: str = 'zh'
    ) -> str:
        """生成故事续写（300-500字）"""
        context = {
            'title': story_title,
            'background': story_background,
            'style': style_rules,
            'previous_segments': '\n'.join([
                seg.get('content', '') for seg in previous_segments[-3:]
            ]),
            'segment_count': len(previous_segments)
        }
        
        prompt = self._build_prompt(context)
        
        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        else:
            return self._call_minimax(prompt)
    
    def _build_prompt(self, context: dict) -> str:
        """构建续写 prompt"""
        return f"""你是一个专业的故事作家，为协作故事平台续写内容。

## 故事信息
标题：{context['title']}
背景：{context['background']}
风格：{context['style']}
已有 {context['segment_count']} 个片段。

## 前文内容
{context['previous_segments']}

## 要求
1. 字数：**必须写 300-500 字**
2. 自然衔接前文，推动剧情发展
3. 保持人物性格和世界观一致性
4. 注重心理描写和感官细节

请直接输出续写内容（300-500字），不要有任何前缀说明。"""
    
    def _call_gemini(self, prompt: str) -> str:
        """调用 Google Gemini API"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未配置")
        
        url = f"{self.gemini_base_url}/models/{self.gemini_model}:generateContent"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 2000,
                "temperature": 0.7
            }
        }
        
        response = requests.post(
            f"{url}?key={self.gemini_api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        if response.status_code != 200:
            raise Exception(f"Gemini API 错误: {response.status_code}")
        
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    
    def _call_minimax(self, prompt: str) -> str:
        """调用 MiniMax API"""
        if not self.minimax_api_key:
            raise ValueError("MINIMAX_API_KEY 未配置")
        
        url = f"{self.minimax_base_url}/chat/completions"
        
        payload = {
            "model": self.minimax_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_output_tokens": 1000
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.minimax_api_key}"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        if response.status_code != 200:
            raise Exception(f"MiniMax API 错误: {response.status_code}")
        
        data = response.json()
        return data['choices'][0]['message']['content'].strip()


def create_llm_client(provider: str = 'auto') -> LLMClient:
    """创建 LLM 客户端"""
    return LLMClient(provider)

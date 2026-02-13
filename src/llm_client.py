"""LLM 客户端 - 支持 Ollama、MiniMax 和 Google Gemini"""
import json
import requests
import subprocess
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()


class LLMClient:
    """统一的 LLM 客户端"""
    
    def __init__(self, provider: str = 'auto'):
        """初始化客户端"""
        self.provider = provider
        
        # Ollama 本地配置（优先）
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'qwen3:32b')
        self.ollama_keep_alive = os.getenv('OLLAMA_KEEP_ALIVE', '-1')
        self.ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '300'))
        self.ollama_models = [m.strip() for m in os.getenv('OLLAMA_MODELS', 'qwen3:32b').split(',')]
        
        # MiniMax 配置
        self.minimax_api_key = os.getenv('MINIMAX_API_KEY', '').strip()
        self.minimax_api_secret = os.getenv('MINIMAX_API_SECRET', '').strip()
        self.minimax_base_url = os.getenv('MINIMAX_BASE_URL', 'https://api.minimax.chat/v1').rstrip('/')
        self.minimax_model = os.getenv('MINIMAX_MODEL', 'abab6.5s-chat')
        
        # Gemini 配置
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', '').strip()
        self.gemini_base_url = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1').rstrip('/')
        self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
        
        # 选择 provider
        if provider == 'auto':
            if self._check_ollama():
                self.provider = 'ollama'
            elif self.minimax_api_key:
                self.provider = 'minimax'
            elif self.gemini_api_key:
                self.provider = 'gemini'
            else:
                raise ValueError("未配置任何 LLM")
        elif provider == 'ollama':
            if not self._check_ollama():
                raise ValueError("Ollama 不可用，请先安装并运行 Ollama")
        elif provider == 'minimax':
            if not self.minimax_api_key:
                raise ValueError("MINIMAX_API_KEY 未配置")
        elif provider == 'gemini':
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY 未配置")
    
    def _check_ollama(self) -> bool:
        """检查 Ollama 是否可用"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _switch_model(self, model_name: str) -> bool:
        """切换到指定模型"""
        try:
            # 检查模型是否存在
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if model_name not in models:
                    print(f"⚠️ 模型 {model_name} 不存在，正在下载...")
                    subprocess.run(['ollama', 'pull', model_name], check=True)
            
            # 加载模型
            load_url = f"{self.ollama_base_url}/api/load"
            payload = {"model": model_name, "keep_alive": self.ollama_keep_alive}
            response = requests.post(load_url, json=payload, timeout=60)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 切换模型失败: {e}")
            return False
    
    def generate_story_continuation(
        self,
        story_title: str,
        story_background: str,
        style_rules: str,
        previous_segments: list,
        language: str = 'zh',
        # 新增参数
        story_summary: str = "",
        story_metadata: Dict = None,
        story_characters: list = None,
        story_outline: list = None,
    ) -> str:
        """
        生成故事续写
        """
        context = {
            'title': story_title,
            'background': story_background,
            'style': style_rules,
            'previous_segments': '\n'.join([
                seg.get('content', '') for seg in previous_segments[-5:]
            ]),
            'segment_count': len(previous_segments),
            'summary': story_summary,
            'metadata': story_metadata or {},
            'characters': story_characters or [],
            'outline': story_outline or [],
        }
        
        prompt = self._build_prompt(context)
        
        # 按 provider 调用
        if self.provider == 'ollama':
            return self._call_ollama(prompt)
        elif self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'minimax':
            return self._call_minimax(prompt)
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")
    
    def _build_prompt(self, context: dict) -> str:
        """构建续写 prompt - 包含完整故事信息"""
        
        # 构建角色信息
        characters_info = ""
        if context.get('characters'):
            chars = context['characters']
            if isinstance(chars, list):
                for char in chars[:5]:  # 最多5个角色
                    if isinstance(char, dict):
                        characters_info += f"- {char.get('name', '')}: {char.get('description', '')}\n"
                    else:
                        characters_info += f"- {char}\n"
        
        # 构建大纲信息
        outline_info = ""
        if context.get('outline'):
            outline = context['outline']
            if isinstance(outline, list):
                for item in outline[:5]:  # 最多5个大纲节点
                    if isinstance(item, dict):
                        outline_info += f"- 第{item.get('chapter', '?')}章: {item.get('title', '')} - {item.get('summary', '')}\n"
                    else:
                        outline_info += f"- {item}\n"
        
        # 构建元数据信息
        metadata_info = ""
        if context.get('metadata'):
            meta = context['metadata']
            if isinstance(meta, dict):
                genre = meta.get('genre', '')
                if genre:
                    metadata_info += f"类型: {genre}\n"
        
        prompt = f"""你是一个专业的故事作家，为协作故事平台续写内容。请严格遵循以下故事设定。

## 故事基本信息
标题：{context['title']}
背景：{context['background']}
类型：{metadata_info}
写作风格：{context['style']}
已有 {context['segment_count']} 个片段。

## 角色设定
{characters_info if characters_info else '（无角色设定）'}

## 故事大纲
{outline_info if outline_info else '（无大纲）'}

## 当前故事进展摘要
{context['summary'] if context['summary'] else '（暂无摘要）'}

## 前文内容（最近5个片段）
{context['previous_segments'] if context['previous_segments'] else '（暂无前文）'}

## 续写要求
1. **字数：300-500字**
2. **必须衔接前文**，延续故事主线
3. **必须推进剧情**，不能原地踏步
4. **保持一致性**：世界观、角色性格、叙事风格必须与前文一致
5. **注重细节**：心理描写、感官描写、环境描写并重
6. **禁止**：与前文矛盾、脱离主线、无意义的流水账

## 续写格式
请直接输出续写内容，不要有任何前缀说明。确保内容有实质性推进。

"""
        
        return prompt
    
    def _call_gemini(self, prompt: str) -> str:
        """调用 Google Gemini API"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未配置")
        
        print(f"\n{'='*60}")
        print(f"📝 Gemini Prompt (发送给 LLM)")
        print(f"{'='*60}")
        print(prompt[:3000])
        print(f"{'='*60}\n")
        
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
    
    def _call_ollama(self, prompt: str) -> str:
        """调用 Ollama 本地模型"""
        if not self._check_ollama():
            raise ValueError("Ollama 不可用")
        
        print(f"\n{'='*60}")
        print(f"📝 Ollama Prompt (模型: {self.ollama_model})")
        print(f"{'='*60}")
        print(prompt[:2000])
        print(f"{'='*60}\n")
        
        url = f"{self.ollama_base_url}/api/generate"
        
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 1000,
                "top_k": 40,
                "top_p": 0.9
            }
        }
        
        response = requests.post(url, json=payload, timeout=self.ollama_timeout)
        
        if response.status_code != 200:
            raise Exception(f"Ollama API 错误: {response.status_code}")
        
        data = response.json()
        content = data.get('response', '').strip()
        
        # 清理可能的 thinking 内容
        if '</think>' in content:
            content = content.split('</think>')[-1].strip()
        
        return content
    
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
        
        # 添加 Group ID（如果配置了）
        group_id = getattr(self, 'minimax_group_id', None)
        if group_id and group_id != 'your_minimax_group_id_here':
            headers["X-GroupId"] = group_id
        
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        if response.status_code != 200:
            raise Exception(f"MiniMax API 错误: {response.status_code}")
        
        data = response.json()
        return data['choices'][0]['message']['content'].strip()


def create_llm_client(provider: str = 'auto') -> LLMClient:
    """创建 LLM 客户端"""
    return LLMClient(provider)

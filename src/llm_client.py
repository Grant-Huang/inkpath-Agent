"""LLM 客户端 - MiniMax API 集成"""
import os
import requests
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class MiniMaxClient:
    """MiniMax API 客户端（中国国内版本）"""
    
    def __init__(self):
        """初始化 MiniMax 客户端"""
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.group_id = os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        self.model = os.getenv("MINIMAX_MODEL", "abab6.5s-chat")
        self.temperature = float(os.getenv("MINIMAX_TEMPERATURE", "0.7"))
        self.top_p = float(os.getenv("MINIMAX_TOP_P", "0.9"))
        self.max_tokens = int(os.getenv("MINIMAX_MAX_TOKENS", "2000"))
        
        if not self.api_key or self.api_key == "your_minimax_api_key_here":
            logger.warning("MiniMax API Key 未配置，将使用占位内容")
        if not self.group_id or self.group_id == "your_minimax_group_id_here":
            logger.warning("MiniMax Group ID 未配置，将使用占位内容")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用 MiniMax API 生成内容
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
        
        Returns:
            生成的内容
        """
        # 检查配置
        if not self.api_key or self.api_key == "your_minimax_api_key_here":
            logger.error("MiniMax API Key 未配置")
            return "错误：MiniMax API Key 未配置，请在 .env 文件中设置 MINIMAX_API_KEY"
        
        # Group ID 可能是可选的，取决于 API 版本
        use_group_id = self.group_id and self.group_id != "your_minimax_group_id_here"
        if not use_group_id:
            logger.warning("MiniMax Group ID 未配置，某些 API 可能需要此参数")
        
        try:
            # 构建消息列表
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 构建请求体（根据 MiniMax API 格式调整）
            # MiniMax 可能使用不同的消息格式
            if "/anthropic" in self.base_url or "anthropic" in self.model.lower():
                # Anthropic 兼容格式
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "max_tokens": self.max_tokens,
                    "stream": False
                }
            else:
                # MiniMax 原生格式
                # 转换消息格式为 MiniMax 格式
                minimax_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        minimax_messages.append({
                            "sender_type": "SYSTEM",
                            "text": msg["content"]
                        })
                    elif msg["role"] == "user":
                        minimax_messages.append({
                            "sender_type": "USER",
                            "text": msg["content"]
                        })
                    else:
                        minimax_messages.append({
                            "sender_type": "BOT",
                            "text": msg["content"]
                        })
                
                payload = {
                    "model": self.model,
                    "messages": minimax_messages,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "max_tokens": self.max_tokens,
                    "stream": False
                }
            
            # 添加 group_id（某些 MiniMax API 版本需要）
            if use_group_id:
                payload["group_id"] = self.group_id
            
            # 构建请求头（MiniMax API 格式）
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送请求（MiniMax API 端点）
            # 根据不同的 API 格式选择正确的端点
            base_url_clean = self.base_url.rstrip('/')
            
            # 判断 API 类型并构建正确的 URL
            if "/anthropic" in base_url_clean:
                # Anthropic 兼容格式，尝试不同的端点路径
                # 可能需要的路径: /v1/messages 或 /messages
                if "/v1" in base_url_clean:
                    url = base_url_clean.replace("/anthropic", "/v1/messages")
                else:
                    # 尝试添加 /v1/messages
                    url = f"{base_url_clean}/v1/messages"
                logger.info(f"尝试 Anthropic 兼容格式端点: {url}")
            elif "minimaxi.com" in base_url_clean or "minimax.chat" in base_url_clean:
                # MiniMax 标准 API
                if "/v1" in base_url_clean:
                    # 如果已有 /v1，添加 /text/chatcompletion
                    url = f"{base_url_clean}/text/chatcompletion"
                else:
                    # 否则添加 /v1/text/chatcompletion
                    url = f"{base_url_clean}/v1/text/chatcompletion"
            else:
                # 默认 OpenAI 兼容格式
                url = f"{base_url_clean}/chat/completions"
            
            logger.info(f"调用 MiniMax API: {url} (model: {self.model})")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            # 详细的错误信息
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_body = response.json()
                    error_detail += f": {error_body}"
                except:
                    error_detail += f": {response.text[:200]}"
                logger.error(f"MiniMax API 请求失败: {error_detail}")
                raise requests.exceptions.HTTPError(f"{error_detail} for url: {url}")
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应（支持多种可能的响应格式）
            # 格式1: Anthropic 兼容格式（MiniMax 2.1）
            if "content" in result and isinstance(result["content"], list):
                # 从 content 数组中提取 type 为 'text' 的内容
                text_contents = []
                for item in result["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            text_contents.append(text)
                
                if text_contents:
                    content = "\n".join(text_contents)
                    logger.info(f"MiniMax 生成成功，长度: {len(content)} 字符")
                    return content.strip()
            
            # 格式2: OpenAI 兼容格式
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                if content:
                    logger.info(f"MiniMax 生成成功，长度: {len(content)} 字符")
                    return content.strip()
            
            # 格式3: MiniMax 原生格式
            if "reply" in result:
                reply = result["reply"]
                if isinstance(reply, str):
                    logger.info(f"MiniMax 生成成功，长度: {len(reply)} 字符")
                    return reply.strip()
                elif isinstance(reply, list) and len(reply) > 0:
                    # 如果 reply 是列表，取第一个元素
                    content = reply[0].get("text", "") if isinstance(reply[0], dict) else str(reply[0])
                    if content:
                        logger.info(f"MiniMax 生成成功，长度: {len(content)} 字符")
                        return content.strip()
            
            # 格式4: 直接返回文本字段
            if "text" in result:
                content = result["text"]
                if content:
                    logger.info(f"MiniMax 生成成功，长度: {len(content)} 字符")
                    return content.strip()
            
            logger.error(f"MiniMax API 响应格式异常: {result}")
            return f"错误：MiniMax API 响应格式异常 - {result}"
        
        except requests.exceptions.RequestException as e:
            logger.error(f"MiniMax API 请求失败: {e}")
            return f"错误：MiniMax API 请求失败 - {str(e)}"
        except Exception as e:
            logger.error(f"MiniMax API 调用异常: {e}", exc_info=True)
            return f"错误：MiniMax API 调用异常 - {str(e)}"


# 全局 LLM 客户端实例
_llm_client: Optional[MiniMaxClient] = None


def get_llm_client() -> MiniMaxClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = MiniMaxClient()
    return _llm_client

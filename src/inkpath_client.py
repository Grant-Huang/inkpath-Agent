"""InkPath API 客户端 - 极简版"""

import requests
import time
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class InkPathClient:
    """InkPath API 客户端"""
    
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip('/')
        self._api_key = api_key  # 保存 API Key
        self._access_token: Optional[str] = None
        
        # 先尝试用 API Key 登录获取 JWT
        if api_key:
            self._login_with_api_key(api_key)
    
    def _login_with_api_key(self, api_key: str) -> bool:
        """使用 API Key 登录获取 JWT"""
        try:
            response = requests.post(
                f"{self.base_url}/bot/login",  # 后端 auth_bp 的 url_prefix 是 /api_v1，route 是 /bot/login
                json={"api_key": api_key},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                if self._access_token:
                    logger.info("Bot 登录成功，获取 JWT Token")
                    return True
            else:
                logger.warning(f"Bot 登录失败: {response.text}")
        except Exception as e:
            logger.warning(f"Bot 登录异常: {e}")
        return False
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 设置认证 Header
        headers = kwargs.get('headers', {})
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        kwargs['headers'] = headers
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    # 尝试重新登录
                    if self._access_token and self._api_key:
                        logger.warning("JWT 失效，尝试重新登录...")
                        if self._login_with_api_key(self._api_key):
                            # 重新设置 Header
                            kwargs['headers']['Authorization'] = f'Bearer {self._access_token}'
                            continue
                    raise Exception("未授权，请检查 API Key")
                elif response.status_code == 429:
                    wait = 2 ** attempt * 10
                    logger.warning(f"速率限制，等待 {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    error_data = response.json().get('error', {})
                    if isinstance(error_data, dict):
                        error = error_data.get('message', response.text)
                    else:
                        error = str(error_data)
                    raise Exception(f"{response.status_code}: {error}")
                    
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception("请求失败")
    
    @property
    def session(self):
        if not hasattr(self, '_session'):
            self._session = requests.Session()
            self._session.headers.update({'Content-Type': 'application/json'})
        return self._session
    
    def get(self, endpoint: str) -> Dict:
        return self._request('GET', endpoint)
    
    def post(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request('PUT', endpoint, json=data)
    
    def patch(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request('PATCH', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Dict:
        return self._request('DELETE', endpoint)

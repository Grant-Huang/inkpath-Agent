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
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': api_key  # 使用新认证方式
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise Exception("未授权，请检查 API Key")
                elif response.status_code == 429:
                    wait = 2 ** attempt * 10
                    logger.warning(f"速率限制，等待 {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    error = response.json().get('error', {}).get('message', response.text)
                    raise Exception(f"{response.status_code}: {error}")
                    
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception("请求失败")
    
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

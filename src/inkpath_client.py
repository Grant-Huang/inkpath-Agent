"""InkPath API 客户端"""
import requests
import time
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class InkPathClient:
    """InkPath API 客户端"""
    
    def __init__(self, api_base: str, api_key: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_base: API 基础 URL
            api_key: API Key（可选，可在后续设置）
        """
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def set_api_key(self, api_key: str):
        """设置 API Key"""
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"
    
    def _request(self, method: str, endpoint: str, timeout: int = 60, **kwargs) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            timeout: 超时时间（秒）
            **kwargs: 其他请求参数
        
        Returns:
            API 响应数据
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=timeout,
                    **kwargs
                )
                
                # 处理速率限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"速率限制，等待 {retry_after} 秒后重试...")
                    time.sleep(retry_after)
                    continue
                
                # 处理错误响应
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_code = error_data.get('error', {}).get('code', 'UNKNOWN')
                    error_msg = error_data.get('error', {}).get('message', response.text)
                    
                    if error_code == "NOT_YOUR_TURN":
                        raise NotYourTurnError("不是你的轮次")
                    elif error_code == "COHERENCE_CHECK_FAILED":
                        raise CoherenceCheckFailedError("连续性校验失败")
                    else:
                        response.raise_for_status()
                
                return response.json()
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"请求失败，{wait_time} 秒后重试 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(wait_time)
                    continue
                raise
        
        raise Exception("请求失败，已达到最大重试次数")
    
    def register_bot(self, name: str, model: str, language: str = "zh", 
                     role: str = "narrator", webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        注册 Bot
        
        Args:
            name: Bot 名称
            model: 使用的模型
            language: 语言
            role: 角色
            webhook_url: Webhook URL（可选）
        
        Returns:
            注册结果，包含 bot_id 和 api_key
        """
        payload = {
            "name": name,
            "model": model,
            "language": language,
            "role": role
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        result = self._request("POST", "/auth/register", json=payload)
        data = result["data"]
        
        # 自动设置 API Key
        if "api_key" in data:
            self.set_api_key(data["api_key"])
        
        return data
    
    def get_stories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取故事列表"""
        result = self._request("GET", "/stories", params={"limit": limit})
        return result["data"]["stories"]
    
    def get_story(self, story_id: str) -> Dict[str, Any]:
        """获取故事详情"""
        result = self._request("GET", f"/stories/{story_id}")
        return result["data"]
    
    def create_story(self, title: str, background: str, style_rules: Optional[str] = None,
                     language: str = "zh", min_length: int = 150, max_length: int = 500,
                     story_pack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建故事
        
        Args:
            title: 故事标题
            background: 故事背景
            style_rules: 写作风格规范
            language: 语言
            min_length: 最小续写长度
            max_length: 最大续写长度
            story_pack: 故事包（可选）
        
        Returns:
            创建的故事数据
        """
        payload = {
            "title": title,
            "background": background,
            "language": language,
            "min_length": min_length,
            "max_length": max_length
        }
        if style_rules:
            payload["style_rules"] = style_rules
        if story_pack:
            payload["story_pack"] = story_pack
        
        result = self._request("POST", "/stories", json=payload)
        return result["data"]
    
    def get_branches(self, story_id: str, limit: int = 6, sort: str = "activity") -> List[Dict[str, Any]]:
        """获取分支列表"""
        result = self._request("GET", f"/stories/{story_id}/branches", 
                              params={"limit": limit, "sort": sort})
        return result["data"]["branches"]
    
    def get_branch(self, branch_id: str) -> Dict[str, Any]:
        """获取分支详情（包含所有续写段）"""
        result = self._request("GET", f"/branches/{branch_id}")
        return result["data"]
    
    def get_branch_summary(self, branch_id: str) -> Dict[str, Any]:
        """获取分支摘要"""
        result = self._request("GET", f"/branches/{branch_id}/summary")
        return result["data"]
    
    def create_branch(self, story_id: str, title: str, initial_segment: str,
                     description: Optional[str] = None, 
                     fork_at_segment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        创建分支
        
        Args:
            story_id: 故事 ID
            title: 分支标题
            initial_segment: 第一段续写
            description: 分支描述
            fork_at_segment_id: 从哪一段分叉
        
        Returns:
            创建的分支数据
        """
        payload = {
            "title": title,
            "initial_segment": initial_segment
        }
        if description:
            payload["description"] = description
        if fork_at_segment_id:
            payload["fork_at_segment_id"] = fork_at_segment_id
        
        result = self._request("POST", f"/stories/{story_id}/branches", json=payload)
        return result["data"]
    
    def join_branch(self, branch_id: str, role: str = "narrator") -> Dict[str, Any]:
        """
        加入分支
        
        Args:
            branch_id: 分支 ID
            role: 参与身份
        
        Returns:
            加入结果，包含轮次位置
        """
        result = self._request("POST", f"/branches/{branch_id}/join", json={"role": role})
        return result["data"]
    
    def submit_segment(self, branch_id: str, content: str) -> Dict[str, Any]:
        """
        提交续写
        
        Args:
            branch_id: 分支 ID
            content: 续写内容（150-500 字/单词）
        
        Returns:
            提交结果
        """
        result = self._request("POST", f"/branches/{branch_id}/segments", json={"content": content}, timeout=180)
        return result["data"]
    
    def get_segments(self, branch_id: str) -> Dict[str, Any]:
        """
        获取分支的续写片段
        
        Args:
            branch_id: 分支 ID
        
        Returns:
            片段列表
        """
        result = self._request("GET", f"/branches/{branch_id}/segments")
        return result["data"]
    
    def vote(self, target_type: str, target_id: str, vote_value: int) -> Dict[str, Any]:
        """
        投票
        
        Args:
            target_type: 'branch' 或 'segment'
            target_id: 分支或续写段的 UUID
            vote_value: 1（赞成）或 -1（反对）
        
        Returns:
            投票结果
        """
        result = self._request("POST", "/votes", json={
            "target_type": target_type,
            "target_id": target_id,
            "vote": vote_value
        })
        return result["data"]
    
    def get_vote_summary(self, target_type: str, target_id: str) -> Dict[str, Any]:
        """获取投票统计"""
        if target_type == "branch":
            endpoint = f"/branches/{target_id}/votes/summary"
        elif target_type == "segment":
            endpoint = f"/segments/{target_id}/votes/summary"
        else:
            raise ValueError("target_type 必须是 'branch' 或 'segment'")
        
        result = self._request("GET", endpoint)
        return result["data"]
    
    def create_comment(self, branch_id: str, content: str, 
                      parent_comment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        发表评论
        
        Args:
            branch_id: 分支 ID
            content: 评论内容
            parent_comment_id: 父评论 ID（回复评论时使用）
        
        Returns:
            评论数据
        """
        payload = {"content": content}
        if parent_comment_id:
            payload["parent_comment_id"] = parent_comment_id
        
        result = self._request("POST", f"/branches/{branch_id}/comments", json=payload)
        return result["data"]


class NotYourTurnError(Exception):
    """不是你的轮次异常"""
    pass


class CoherenceCheckFailedError(Exception):
    """连续性校验失败异常"""
    pass

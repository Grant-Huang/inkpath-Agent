"""InkPath API 客户端 - 增强版"""
import requests
import time
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class InkPathClient:
    """InkPath API 客户端"""
    
    def __init__(self, api_base: str, api_key: Optional[str] = None):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time_ms": 0,
        }
    
    def _request(self, method: str, endpoint: str, timeout: int = 60, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        logger.info(f"📤 [{method}] {url}")
        
        start_time = time.time()
        try:
            response = requests.request(
                method=method, url=url, headers=self.headers, timeout=timeout, **kwargs
            )
            duration_ms = (time.time() - start_time) * 1000
            
            self.stats["total_requests"] += 1
            self.stats["total_time_ms"] += duration_ms
            
            if response.status_code < 400:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
                logger.error(f"   ❌ {response.status_code}: {response.text[:200]}")
            
            logger.info(f"   ✅ {response.status_code} ({duration_ms:.0f}ms)")
            
            # 处理速率限制
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"   ⚠️ 速率限制，等待 {retry_after}s...")
                time.sleep(retry_after)
                return self._request(method, endpoint, timeout, **kwargs)
            
            # 错误处理
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    code = error_data.get('error', {}).get('code', 'UNKNOWN')
                    msg = error_data.get('error', {}).get('message', response.text)
                    raise Exception(f"{code}: {msg}")
                except:
                    raise Exception(f"API错误 {response.status_code}")
            
            return response.json()
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1
            self.stats["total_time_ms"] += duration_ms
            
            logger.error(f"   ❌ {type(e).__name__}: {str(e)[:100]}")
            
            # 重试逻辑
            for attempt in range(2):
                wait_time = 2 ** attempt
                logger.warning(f"   🔄 重试 ({attempt+2}/3) 等待 {wait_time}s...")
                time.sleep(wait_time)
                try:
                    return self._request(method, endpoint, timeout, **kwargs)
                except:
                    continue
            
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        avg = self.stats["total_time_ms"] / max(self.stats["total_requests"], 1)
        rate = self.stats["successful_requests"] / max(self.stats["total_requests"], 1) * 100
        return {**self.stats, "avg_ms": avg, "success_rate": f"{rate:.1f}%"}
    
    def get_me(self) -> Dict[str, Any]:
        """获取当前 Bot 信息"""
        return self._request("GET", "/auth/bot/me")
    
    def get_stories(self, limit: int = 20) -> list:
        """获取故事列表"""
        result = self._request("GET", "/stories", params={"limit": limit})
        stories = result["data"]["stories"]
        logger.info(f"   📚 找到 {len(stories)} 个故事")
        return stories
    
    def get_story(self, story_id: str) -> Dict[str, Any]:
        """获取故事详情"""
        result = self._request("GET", f"/stories/{story_id}")
        return result["data"]
    
    def get_branches(self, story_id: str, limit: int = 6, sort: str = "activity") -> list:
        """获取分支列表"""
        result = self._request("GET", f"/stories/{story_id}/branches", 
                            params={"limit": limit, "sort": sort})
        branches = result["data"]["branches"]
        logger.info(f"   🌿 找到 {len(branches)} 个分支")
        return branches
    
    def get_branch(self, branch_id: str) -> Dict[str, Any]:
        """获取分支详情（关键函数！显示所有字段）"""
        result = self._request("GET", f"/branches/{branch_id}")
        data = result["data"]
        
        # 修复：后端返回 segments_count 和 active_bots_count，不是 segments 和 active_bots
        segments_count = data.get("segments_count", 0)
        active_bots_count = data.get("active_bots_count", 0)
        creator_bot = data.get("creator_bot_id", "N/A")
        status = data.get("status", "unknown")
        
        logger.info(f"   📄 分支详情:")
        logger.info(f"      - 续写段数: {segments_count}")
        logger.info(f"      - 活跃Bot数: {active_bots_count}")
        logger.info(f"      - 创建者: {str(creator_bot)[:8]}...")
        logger.info(f"      - 状态: {status}")
        logger.info(f"      - segments_count类型: {type(segments_count)}")
        logger.info(f"      - active_bots_count类型: {type(active_bots_count)}")
        
        # 返回修改后的数据，供 Agent 使用
        return {
            **data,
            "segments_count": segments_count,
            "active_bots_count": active_bots_count
        }
    
    def join_branch(self, branch_id: str, role: str = "narrator") -> Dict[str, Any]:
        """加入分支（关键函数！显示所有字段）"""
        logger.info(f"   🚀 尝试加入分支...")
        
        result = self._request("POST", f"/branches/{branch_id}/join", json={"role": role})
        
        # 详细日志 - API 返回的是 join_order，不是 your_turn_order!
        your_turn = result["data"].get("join_order")  # ✅ 修复字段名
        message = result["data"].get("message", "")
        branch_id_result = result["data"].get("branch_id", "N/A")
        joined_at = result.get("joined_at", "")
        
        logger.info(f"   ✅ 加入响应:")
        logger.info(f"      - join_order: {your_turn} (类型: {type(your_turn)})")
        logger.info(f"      - message: {message}")
        logger.info(f"      - branch_id: {str(branch_id_result)[:8]}...")
        logger.info(f"      - joined_at: {joined_at}")
        logger.info(f"      - 完整响应: {json.dumps(result, ensure_ascii=False, indent=6)[:500]}")
        
        return result
    
    def submit_segment(self, branch_id: str, content: str) -> Dict[str, Any]:
        """提交续写"""
        logger.info(f"   📝 提交续写 ({len(content)} 字)")
        
        start_time = time.time()
        result = self._request("POST", f"/branches/{branch_id}/segments", 
                            json={"content": content}, timeout=300)
        
        duration_ms = (time.time() - start_time) * 1000
        segment = result.get("segment", {})
        next_bot = result.get("next_bot", {})
        
        logger.info(f"   ✅ 续写成功! ({duration_ms:.0f}ms)")
        logger.info(f"      - segment_id: {segment.get('id', 'N/A')}")
        logger.info(f"      - 下一位: {next_bot.get('name', 'N/A')}")
        
        return result
    
    def get_branch_summary(self, branch_id: str) -> Dict[str, Any]:
        """获取分支摘要"""
        return self._request("GET", f"/branches/{branch_id}/summary")
    
    def create_branch(self, story_id: str, title: str, description: str = "", 
                      initial_segment: str = None) -> Dict[str, Any]:
        """创建新分支"""
        logger.info(f"   🆕 创建新分支: {title}")
        
        data = {"title": title, "description": description}
        if initial_segment:
            data["initial_segment"] = initial_segment
        
        result = self._request("POST", f"/stories/{story_id}/branches", json=data)
        
        branch = result.get("data", {})
        logger.info(f"   ✅ 分支创建成功: {branch.get('id', 'N/A')}")
        
        return result
    
    def cleanup_stuck_memberships(self, hours: int = 1) -> Dict[str, Any]:
        """清理卡住的 Bot 分支成员关系"""
        logger.info(f"   🧹 清理不活跃的 Bot (超时: {hours}小时)")
        
        result = self._request("POST", f"/cron/cleanup-stuck-memberships?hours={hours}")
        
        cleaned = result.get("data", {}).get("cleaned", [])
        logger.info(f"   ✅ 清理完成: {len(cleaned)} 个 membership")
        
        for item in cleaned[:5]:  # 只显示前5个
            logger.info(f"      - {item.get('bot_name', 'Unknown')}")
        
        return result
    
    def get_segments(self, branch_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """获取分支的续写片段"""
        logger.info(f"   📖 获取片段 (limit={limit}, offset={offset})")
        
        result = self._request("GET", f"/branches/{branch_id}/segments", 
                             params={"limit": limit, "offset": offset})
        
        segments = result.get("data", {}).get("segments", [])
        logger.info(f"   ✅ 获取到 {len(segments)} 个片段")
        
        return result

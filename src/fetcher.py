"""
InkPath Agent - 信息抓取模块

职责：
1. 从 InkPath API 抓取必要信息
2. 实现动态加载和预加载策略
3. 缓存管理
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentHomeData:
    """首页数据结构"""
    agent: Dict[str, Any] = field(default_factory=dict)
    stories_summary: Dict[str, int] = field(default_factory=dict)
    recent_activity: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    server_time: str = ""


@dataclass
class StorySummary:
    """故事摘要数据结构"""
    id: str
    title: str
    summary: str = ""
    next_action: str = ""
    auto_continue: bool = True
    segments_count: int = 0
    last_updated: str = ""


class InkPathFetcher:
    """InkPath API 信息抓取器"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # 缓存
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 60  # 缓存 60 秒
        
        # 预加载队列
        self._preload_queue: asyncio.Queue = asyncio.Queue()
        
    async def _request(self, endpoint: str, method: str = 'GET', 
                       data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 HTTP 请求"""
        import aiohttp
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    async with session.get(url, headers=self.headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        else:
                            logger.error(f"请求失败: {endpoint} - {resp.status}")
                            return None
                elif method == 'POST':
                    async with session.post(url, json=data, headers=self.headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        else:
                            logger.error(f"请求失败: {endpoint} - {resp.status}")
                            return None
        except Exception as e:
            logger.error(f"请求异常: {endpoint} - {e}")
            return None
    
    # =====================================================
    # 首页信息抓取
    # =====================================================
    
    async def fetch_home(self, use_cache: bool = True) -> Optional[AgentHomeData]:
        """
        获取首页信息
        
        策略：
        - 登录后立即调用
        - 之后每 5 分钟轮询
        - 页面切换时刷新
        """
        cache_key = 'home'
        
        # 检查缓存
        if use_cache and self._is_fresh(cache_key):
            logger.debug("使用缓存的首页数据")
            return self._cache.get(cache_key)
        
        result = await self._request('/api/v1/agent/home')
        
        if result and result.get('data'):
            data = AgentHomeData(
                agent=result['data'].get('agent', {}),
                stories_summary=result['data'].get('stories_summary', {}),
                recent_activity=result['data'].get('recent_activity', []),
                alerts=result['data'].get('alerts', []),
                server_time=result['data'].get('server_time', '')
            )
            self._cache[cache_key] = data
            self._cache_time[cache_key] = time.time()
            return data
        
        return None
    
    # =====================================================
    # 故事列表抓取
    # =====================================================
    
    async def fetch_stories(self, page: int = 1, limit: int = 20,
                            status: str = 'all',
                            use_cache: bool = True) -> List[StorySummary]:
        """
        获取故事列表
        
        策略：
        - 首页加载时抓取第一页
        - 滚动到底部时加载更多
        - 下拉刷新时重新抓取
        """
        cache_key = f'stories_{page}_{limit}_{status}'
        
        if use_cache and self._is_fresh(cache_key):
            return self._cache.get(cache_key, [])
        
        params = f'?page={page}&limit={limit}&status={status}'
        result = await self._request(f'/api/v1/agent/stories{params}')
        
        if result and result.get('data'):
            stories = []
            for item in result['data'].get('stories', []):
                stories.append(StorySummary(
                    id=item.get('id'),
                    title=item.get('title', '未知'),
                    summary=item.get('summary', ''),
                    next_action=item.get('next_action', ''),
                    auto_continue=item.get('auto_continue', True),
                    segments_count=item.get('segments_count', 0),
                    last_updated=item.get('last_updated', '')
                ))
            
            self._cache[cache_key] = stories
            self._cache_time[cache_key] = time.time()
            return stories
        
        return []
    
    # =====================================================
    # 故事详情抓取
    # =====================================================
    
    async def fetch_story_detail(self, story_id: str,
                                 use_cache: bool = True) -> Optional[Dict]:
        """
        获取故事详情
        
        策略：
        - 点击故事时立即加载
        - 进入详情页时预加载
        """
        cache_key = f'story_detail_{story_id}'
        
        if use_cache and self._is_fresh(cache_key):
            return self._cache.get(cache_key)
        
        result = await self._request(f'/api/v1/agent/stories/{story_id}')
        
        if result and result.get('data'):
            self._cache[cache_key] = result['data']
            self._cache_time[cache_key] = time.time()
            return result['data']
        
        return None
    
    # =====================================================
    # 故事进度抓取（轻量级）
    # =====================================================
    
    async def fetch_story_progress(self, story_id: str) -> Optional[Dict]:
        """
        获取故事进度（轻量级接口）
        
        策略：
        - 轮询监控时使用
        - 频繁调用，快速响应
        """
        result = await self._request(f'/api/v1/agent/stories/{story_id}/progress')
        
        if result and result.get('data'):
            return result['data']
        
        return None
    
    # =====================================================
    # 统计数据抓取
    # =====================================================
    
    async def fetch_stats(self, use_cache: bool = True) -> Optional[Dict]:
        """
        获取 Agent 统计数据
        """
        cache_key = 'stats'
        
        if use_cache and self._is_fresh(cache_key):
            return self._cache.get(cache_key)
        
        result = await self._request('/api/v1/agent/stats')
        
        if result and result.get('data'):
            self._cache[cache_key] = result['data']
            self._cache_time[cache_key] = time.time()
            return result['data']
        
        return None
    
    # =====================================================
    # 预加载
    # =====================================================
    
    async def preload_story(self, story_id: str) -> Optional[Dict]:
        """
        预加载故事完整数据
        
        策略：
        - 用户悬停在故事上时触发
        - 进入详情页前在后台预加载
        """
        result = await self._request(f'/api/v1/agent/preload/{story_id}')
        
        if result and result.get('data'):
            logger.info(f"预加载完成: {story_id}")
            return result['data']
        
        return None
    
    async def preload_stories(self, story_ids: List[str]):
        """
        批量预加载多个故事
        
        策略：
        - 首页加载后预加载前 3 个故事
        - 列表滚动时预加载可视区域附近的 3 个故事
        """
        tasks = [self.preload_story(sid) for sid in story_ids[:5]]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # =====================================================
    # 缓存管理
    # =====================================================
    
    def _is_fresh(self, key: str) -> bool:
        """检查缓存是否新鲜"""
        if key not in self._cache:
            return False
        if key not in self._cache_time:
            return False
        return (time.time() - self._cache_time[key]) < self._cache_ttl
    
    def invalidate(self, key: str = None):
        """使缓存失效"""
        if key:
            self._cache.pop(key, None)
            self._cache_time.pop(key, None)
        else:
            self._cache.clear()
            self._cache_time.clear()
        logger.debug(f"缓存已失效: {key or '全部'}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'keys': list(self._cache.keys()),
            'ttl': self._cache_ttl,
            'age': {
                k: time.time() - self._cache_time.get(k, 0)
                for k in self._cache.keys()
            }
        }


# =====================================================
# 使用示例
# =====================================================
"""
# 初始化抓取器
fetcher = InkPathFetcher(
    base_url='https://inkpath-api.onrender.com',
    token='your-jwt-token'
)

# 1. 登录后立即获取首页
home_data = await fetcher.fetch_home(use_cache=False)

# 2. 获取故事列表（第一页）
stories = await fetcher.fetch_stories(page=1, limit=20)

# 3. 批量预加载前 5 个故事
await fetcher.preload_stories([s.id for s in stories[:5]])

# 4. 点击故事时获取详情
detail = await fetcher.fetch_story_detail(story_id)

# 5. 监控时轮询进度
progress = await fetcher.fetch_story_progress(story_id)

# 6. 下拉刷新时重新获取
stories = await fetcher.fetch_stories(page=1, use_cache=False)
"""

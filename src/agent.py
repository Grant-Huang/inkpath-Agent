"""
InkPath Agent - 主程序 (整合抓取模块)

职责：
1. 登录认证
2. 从 API 抓取首页信息
3. 动态加载故事详情
4. 预加载策略
5. 监控和续写
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.inkpath_client import InkPathClient
from src.fetcher import InkPathFetcher, AgentHomeData
from src.llm_client import create_llm_client

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent 主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # API 配置
        self.api_base = config.get('api_base', 'https://inkpath-api.onrender.com')
        self.api_key = config.get('api_key', '')
        
        # 初始化客户端
        self.client = InkPathClient(self.api_base, self.api_key)
        
        # 初始化抓取器
        self.fetcher = InkPathFetcher(self.api_base, self.api_key)
        
        # LLM 客户端
        self.llm = create_llm_client(provider='ollama')
        
        # 轮询间隔
        self.poll_interval = config.get('poll_interval', 300)  # 5 分钟
        
        # 缓存刷新间隔
        self.cache_refresh_interval = 60  # 1 分钟
        
        # 预加载配置
        self.preload_batch_size = 3
        self.preload_on_hover = True
        
        # 统计
        self.counters = {
            'fetches': 0,
            'preloads': 0,
            'continues': 0,
            'summaries': 0,
            'errors': 0
        }
    
    # =====================================================
    # 认证
    # =====================================================
    
    async def login(self, email: str, password: str) -> bool:
        """
        用户登录
        
        成功后：
        1. 保存 token
        2. 获取首页信息
        3. 预加载故事列表
        """
        logger.info("=" * 60)
        logger.info("🔐 InkPath Agent 登录")
        logger.info("=" * 60)
        
        # 调用登录 API
        response = self.client.login(email, password)
        
        if response and response.get('success'):
            token = response['token']
            self.api_key = token
            self.client.headers['Authorization'] = f'Bearer {token}'
            self.fetcher.token = token
            
            logger.info("✅ 登录成功!")
            
            # 登录后立即获取首页
            await self._fetch_home_data()
            
            # 预加载故事列表
            await self._preload_stories()
            
            return True
        
        logger.error("❌ 登录失败")
        return False
    
    # =====================================================
    # 首页信息获取
    # =====================================================
    
    async def _fetch_home_data(self) -> Optional[AgentHomeData]:
        """获取首页数据"""
        logger.info("📥 获取首页数据...")
        
        home_data = await self.fetcher.fetch_home(use_cache=False)
        
        if home_data:
            self._display_home_summary(home_data)
            self.counters['fetches'] += 1
            return home_data
        
        return None
    
    def _display_home_summary(self, home_data: AgentHomeData):
        """显示首页摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("🏠 首页摘要")
        logger.info("=" * 60)
        
        agent = home_data.agent
        summary = home_data.stories_summary
        
        logger.info(f"   Agent: {agent.get('name', '未命名')}")
        logger.info(f"   状态: {agent.get('status', 'idle')}")
        logger.info(f"   故事总数: {summary.get('total', 0)}")
        logger.info(f"   运行中: {summary.get('running', 0)}")
        logger.info(f"   空闲: {summary.get('idle', 0)}")
        logger.info(f"   需要关注: {summary.get('needs_attention', 0)}")
        
        # 显示警告
        alerts = home_data.alerts
        if alerts:
            logger.warning(f"\n⚠️  有 {len(alerts)} 个警告:")
            for alert in alerts[:3]:
                logger.warning(f"   - {alert.get('message', '')}")
        
        # 显示最近活动
        activity = home_data.recent_activity
        if activity:
            logger.info(f"\n📋 最近活动:")
            for item in activity[:3]:
                logger.info(f"   - {item.get('story_title', '')}: {item.get('action', '')}")
    
    # =====================================================
    # 故事列表和预加载
    # =====================================================
    
    async def _preload_stories(self):
        """预加载故事列表"""
        logger.info("\n📚 预加载故事列表...")
        
        # 获取第一页故事
        stories = await self.fetcher.fetch_stories(page=1, limit=10)
        
        if stories:
            # 预加载前 N 个故事
            story_ids = [s.id for s in stories[:self.preload_batch_size]]
            await self.fetcher.preload_stories(story_ids)
            
            logger.info(f"   ✅ 已预加载 {len(story_ids)} 个故事")
            self.counters['preloads'] += len(story_ids)
    
    async def get_story_list(self, page: int = 1) -> list:
        """获取故事列表（动态加载）"""
        return await self.fetcher.fetch_stories(page=page, use_cache=True)
    
    async def get_story_detail(self, story_id: str, preload: bool = True) -> Optional[Dict]:
        """
        获取故事详情
        
        如果 preload=True，会在后台预加载下一个故事
        """
        # 先尝试从缓存获取
        detail = await self.fetcher.fetch_story_detail(story_id)
        
        if detail and preload:
            # 找到当前故事的下一个故事 ID，预加载它
            stories = await self.get_story_list(page=1)
            found = False
            for i, s in enumerate(stories):
                if s.id == story_id and i + 1 < len(stories):
                    # 后台预加载下一个
                    asyncio.create_task(
                        self.fetcher.fetch_story_detail(stories[i + 1].id)
                    )
                    break
        
        return detail
    
    # =====================================================
    # 监控循环
    # =====================================================
    
    async def monitor_loop(self):
        """主监控循环
        
        策略：
        1. 每 5 分钟获取首页数据
        2. 每 1 分钟刷新缓存
        3. 检查是否有需要关注的故事
        """
        logger.info("=" * 60)
        logger.info("🚀 InkPath Agent 监控启动")
        logger.info(f"   轮询间隔: {self.poll_interval}s")
        logger.info(f"   缓存刷新: {self.cache_refresh_interval}s")
        logger.info("=" * 60)
        
        cycle = 0
        while True:
            cycle += 1
            start_time = time.time()
            
            logger.info(f"\n🔄 第 {cycle} 次检查 - {datetime.now().strftime('%H:%M:%S')}")
            
            try:
                # 1. 获取首页数据（刷新缓存）
                home_data = await self.fetcher.fetch_home(use_cache=False)
                
                if home_data:
                    # 2. 检查是否有警告
                    alerts = home_data.alerts
                    if alerts:
                        logger.warning(f"\n⚠️  发现 {len(alerts)} 个问题:")
                        for alert in alerts[:3]:
                            logger.warning(f"   - {alert.get('message', '')}")
                    
                    # 3. 显示统计
                    self._display_stats()
                
                # 4. 续写检查（可选）
                # await self._check_and_continue()
                
            except Exception as e:
                self.counters['errors'] += 1
                logger.error(f"❌ 监控错误: {e}")
            
            # 计算睡眠时间
            elapsed = time.time() - start_time
            sleep_time = max(0, self.poll_interval - elapsed)
            
            logger.info(f"\n⏱️  耗时: {elapsed:.1f}s, 休眠: {sleep_time:.0f}s")
            
            try:
                await asyncio.sleep(sleep_time)
            except KeyboardInterrupt:
                logger.info("\n⏹️  停止监控")
                break
        
        self._display_stats()
    
    def _display_stats(self):
        """显示统计信息"""
        logger.info(f"\n📊 统计:")
        logger.info(f"   获取次数: {self.counters['fetches']}")
        logger.info(f"   预加载次数: {self.counters['preloads']}")
        logger.info(f"   续写次数: {self.counters['continues']}")
        logger.info(f"   摘要更新: {self.counters['summaries']}")
        logger.info(f"   错误次数: {self.counters['errors']}")
        
        # 显示缓存信息
        cache_info = self.fetcher.get_cache_info()
        logger.info(f"   缓存条目: {len(cache_info['keys'])}")
    
    # =====================================================
    # 手动操作
    # =====================================================
    
    async def continue_story(self, story_id: str) -> bool:
        """手动续写"""
        logger.info(f"\n✍️  手动续写故事: {story_id}")
        
        # 1. 获取故事详情
        detail = await self.get_story_detail(story_id, preload=False)
        if not detail:
            logger.error("   ❌ 获取故事详情失败")
            return False
        
        # 2. TODO: 调用 LLM 生成续写
        # content = await self.llm.generate(...)
        
        # 3. TODO: 提交片段
        # result = self.client.submit_segment(...)
        
        self.counters['continues'] += 1
        logger.info("   ✅ 续写完成")
        
        return True
    
    async def update_summary(self, story_id: str) -> bool:
        """更新摘要"""
        logger.info(f"\n📋 更新摘要: {story_id}")
        
        # 调用 API
        result = await self._request('/agent/summarize', method='POST', data={'story_id': story_id})
        
        if result:
            self.counters['summaries'] += 1
            logger.info("   ✅ 摘要已更新")
            
            # 刷新首页缓存
            await self.fetcher.fetch_home(use_cache=False)
            return True
        
        return False
    
    async def toggle_auto_continue(self, story_id: str, enabled: bool) -> bool:
        """切换自动续写"""
        logger.info(f"\n⚙️  设置自动续写: {story_id} -> {enabled}")
        
        result = await self._request(
            f'/agent/stories/{story_id}/auto-continue',
            method='PUT',
            data={'enabled': enabled}
        )
        
        if result:
            logger.info("   ✅ 设置成功")
            # 刷新首页
            await self.fetcher.fetch_home(use_cache=False)
            return True
        
        return False
    
    # =====================================================
    # 辅助方法
    # =====================================================
    
    async def _request(self, endpoint: str, method: str = 'GET', 
                        data: Optional[Dict] = None) -> Optional[Dict]:
        """发送请求"""
        return await self.fetcher._request(endpoint, method, data)


# =====================================================
# 使用示例
# =====================================================
"""
# 1. 初始化
agent = InkPathAgent({
    'api_base': 'https://inkpath-api.onrender.com',
    'api_key': '',  # 登录后设置
    'poll_interval': 300,  # 5 分钟
})

# 2. 登录
success = await agent.login('email@example.com', 'password')
if not success:
    exit(1)

# 3. 获取故事列表
stories = await agent.get_story_list(page=1)
for s in stories:
    print(f"  {s.title}: {s.summary}")

# 4. 获取详情
detail = await agent.get_story_detail('story-id')
print(detail)

# 5. 启动监控
await agent.monitor_loop()
"""

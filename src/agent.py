"""InkPath Agent - 极简主程序"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Optional

from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent 主类"""
    
    def __init__(self, client: InkPathClient, settings):
        self.client = client
        self.settings = settings
        
        # LLM 客户端
        self.llm = create_llm_client(
            provider=settings.llm.provider,
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            temperature=settings.llm.temperature
        )
        
        # 统计
        self.stats = {
            'continues': 0,
            'votes': 0,
            'errors': 0
        }
    
    def run(self):
        """运行 Agent（监控循环）"""
        logger.info("=" * 50)
        logger.info("🚀 InkPath Agent 启动")
        logger.info(f"   轮询间隔: {self.settings.agent.poll_interval}s")
        logger.info(f"   自动投票: {self.settings.agent.auto_vote}")
        logger.info(f"   自动加入分支: {self.settings.agent.auto_join_branches}")
        logger.info("=" * 50)
        
        asyncio.run(self._run_loop())
    
    async def _run_loop(self):
        """主循环"""
        cycle = 0
        while True:
            cycle += 1
            logger.info(f"\n🔄 第 {cycle} 次检查 - {datetime.now().strftime('%H:%M:%S')}")
            
            try:
                # 获取分配的故事
                stories = await self._fetch_stories()
                
                if stories:
                    logger.info(f"   📚 发现 {len(stories)} 个故事")
                    
                    # 检查每个故事
                    for story in stories[:3]:  # 只处理前3个
                        await self._process_story(story)
                else:
                    logger.info("   📭 没有分配的故事")
                
                # 显示统计
                logger.info(f"\n📊 统计 - 续写:{self.stats['continues']} 投票:{self.stats['votes']} 错误:{self.stats['errors']}")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"   ❌ 错误: {e}")
            
            # 等待
            await asyncio.sleep(self.settings.agent.poll_interval)
    
    async def _fetch_stories(self) -> list:
        """获取故事列表"""
        try:
            # 调用 API 获取分配的故事
            result = self.client.get(f"/users/me/stories")
            if result and result.get('success'):
                return result.get('data', {}).get('stories', [])
        except Exception as e:
            logger.warning(f"   获取故事列表失败: {e}")
        return []
    
    async def _process_story(self, story: dict):
        """处理单个故事"""
        story_id = story.get('id')
        story_title = story.get('title', '')[:20]
        
        # 获取故事分支
        branches = await self._fetch_branches(story_id)
        
        if not branches:
            logger.info(f"   📝 {story_title}: 无分支，创建开篇")
            # TODO: 创建分支
            return
        
        # 检查是否可以续写
        for branch in branches[:2]:
            await self._try_continue(branch)
    
    async def _fetch_branches(self, story_id: str) -> list:
        """获取分支列表"""
        try:
            result = self.client.get(f"/stories/{story_id}/branches")
            if result and result.get('success'):
                return result.get('data', {}).get('branches', [])
        except Exception as e:
            logger.warning(f"   获取分支失败: {e}")
        return []
    
    async def _try_continue(self, branch: dict) -> bool:
        """尝试续写"""
        branch_id = branch.get('id')
        last_segment = await self._get_last_segment(branch_id)
        
        if not last_segment:
            return False
        
        # 调用 LLM 生成续写
        content = await self._generate_continue(last_segment, branch_id)
        
        if not content:
            return False
        
        # 提交续写
        result = self.client.post(f"/branches/{branch_id}/segments", {
            'content': content
        })
        
        if result and result.get('success'):
            self.stats['continues'] += 1
            logger.info(f"   ✍️  续写成功")
            
            # 自动投票
            if self.settings.agent.auto_vote:
                await self._vote(result.get('data', {}).get('segment', {}).get('id'))
            
            return True
        
        return False
    
    async def _get_last_segment(self, branch_id: str) -> Optional[dict]:
        """获取最后一片段"""
        try:
            result = self.client.get(f"/branches/{branch_id}/segments?limit=1")
            if result and result.get('success'):
                segments = result.get('data', {}).get('segments', [])
                return segments[0] if segments else None
        except Exception as e:
            logger.warning(f"   获取片段失败: {e}")
        return None
    
    async def _generate_continue(self, last_segment: dict, branch_id: str) -> Optional[str]:
        """调用 LLM 生成续写"""
        try:
            content = await self.llm.generate_continue(
                context=last_segment.get('content', ''),
                branch_id=branch_id
            )
            return content
        except Exception as e:
            logger.warning(f"   LLM 生成失败: {e}")
        return None
    
    async def _vote(self, segment_id: str):
        """投票"""
        try:
            result = self.client.post("/votes", {
                'target_type': 'segment',
                'target_id': segment_id,
                'vote': 1
            })
            if result and result.get('success'):
                self.stats['votes'] += 1
                logger.info(f"   👍 投票成功")
        except Exception as e:
            logger.warning(f"   投票失败: {e}")

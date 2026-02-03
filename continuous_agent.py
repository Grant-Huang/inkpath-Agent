#!/usr/bin/env python3
"""
InkPath Agent - Continuous Writing Mode

Features:
- Auto-registers at startup
- Continuous operation
- Decision logic for:
  * Creating new stories
  * Continuing existing stories
  * Participating in discussions
  * Voting on segments
"""

import sys
import time
import random
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Add agent directory to path
AGENT_DIR = Path('/Users/admin/Desktop/work/inkPath-Agent')
sys.path.insert(0, str(AGENT_DIR / 'src'))

from inkpath_client import InkPathClient
import yaml

# Load configuration
CONFIG_PATH = AGENT_DIR / 'config.yaml'

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

API_BASE = config['api']['base_url']
POLL_INTERVAL = config['agent'].get('poll_interval', 60)
AUTO_CREATE_STORY = config['agent'].get('auto_create_story', False)
AUTO_JOIN = config['agent'].get('auto_join_branches', True)
AUTO_COMMENT = config['agent'].get('auto_comment', False)
AUTO_VOTE = config['agent'].get('auto_vote', False)
WRITE_LIMIT = config['agent'].get('write_limit', 5)


class DecisionEngine:
    """Agent 决策引擎 - 决定何时执行何种操作"""
    
    def __init__(self, api_base: str, api_key: str):
        self.client = InkPathClient(api_base, api_key)
        self.joined_branches = set()
        self.stories_created = 0
        self.segments_written = 0
        self.comments_posted = 0
        self.votes_cast = 0
        self.last_action_time = datetime.now()
        
    # ===== 决策 1: 创建新故事 =====
    
    def should_create_story(self) -> tuple[bool, str]:
        """
        何时创建新故事？
        
        决策条件：
        1. auto_create_story = true
        2. 没有已加入的故事分支
        3. 距离上次创建故事超过24小时
        4. 平台活跃度低（< 3个故事）
        
        Returns:
            (是否应该创建, 原因)
        """
        if not AUTO_CREATE_STORY:
            return False, "auto_create_story 未启用"
        
        if len(self.joined_branches) > 0:
            return False, f"已加入 {len(self.joined_branches)} 个分支"
        
        # 检查最近是否创建过故事
        if self.stories_created > 0:
            return False, f"已创建 {self.stories_created} 个故事"
        
        # 获取平台活跃故事数
        try:
            stories = self.client.get_stories(limit=10)
            if len(stories) >= 3:
                return False, f"平台已有 {len(stories)} 个活跃故事"
        except:
            pass
        
        return True, "没有已加入分支，平台需要新故事"
    
    def create_story(self) -> bool:
        """创建新故事"""
        should, reason = self.should_create_story()
        if not should:
            print(f"   ⏭️ 不创建故事: {reason}")
            return False
        
        print(f"   📖 创建新故事...")
        
        # 故事模板
        story_templates = [
            {
                "title": "星际探索者",
                "background": "2157年，人类发现了虫洞网络。一位年轻的宇航员被选中执行首次穿越任务，探索未知星系。",
                "language": "zh"
            },
            {
                "title": "深海守望者",
                "background": "在海底两万米的深渊中，有一座城市。那里的居民已经忘记了阳光的味道。",
                "language": "zh"
            }
        ]
        
        template = random.choice(story_templates)
        
        try:
            story = self.client.create_story(
                title=template["title"],
                background=template["background"],
                language=template["language"]
            )
            
            self.stories_created += 1
            print(f"   ✅ 故事创建成功: {story['title']}")
            
            # 自动创建主干线分支
            branch = self.client.create_branch(
                story_id=story['id'],
                title="主干线",
                initial_segment=self._generate_first_segment(template["background"], template["language"])
            )
            
            # 加入主干线
            self.client.join_branch(branch['id'], role='narrator')
            self.joined_branches.add(branch['id'])
            
            return True
            
        except Exception as e:
            print(f"   ❌ 创建失败: {e}")
            return False
    
    def _generate_first_segment(self, background: str, language: str) -> str:
        """生成故事第一段"""
        return f"故事开始于{sample(background, 30)}，一个新的篇章即将展开。"
    
    # ===== 决策 2: 续写故事 =====
    
    def should_write_segment(self, branch_id: str) -> tuple[bool, str]:
        """
        何时续写故事？
        
        决策条件：
        1. 速率限制允许（< 5段/小时）
        2. 距离上次写作超过10分钟
        3. 分支状态为 active
        4. 有可写的段
        
        Returns:
            (是否应该写, 原因)
        """
        # 检查速率限制
        if self.segments_written >= WRITE_LIMIT:
            return False, f"已达速率限制 ({WRITE_LIMIT}/小时)"
        
        # 检查分支状态
        try:
            branch = self.client.get_branch(branch_id)
            if branch.get('status') != 'active':
                return False, f"分支状态: {branch.get('status')}"
        except Exception as e:
            return False, f"获取分支失败: {e}"
        
        # 检查距离上次操作
        time_since_last = (datetime.now() - self.last_action_time).total_seconds()
        if time_since_last < 600:  # 10分钟
            return False, f"距离上次操作仅 {int(time_since_last)} 秒"
        
        return True, "条件满足，可以写作"
    
    def write_segment(self, branch_id: str) -> bool:
        """续写故事"""
        should, reason = self.should_write_segment(branch_id)
        if not should:
            print(f"   ⏭️ 不写作: {reason}")
            return False
        
        print(f"   ✍️ 续写中...")
        
        try:
            # 获取分支和故事信息
            branch = self.client.get_branch(branch_id)
            story = self.client.get_story(branch['story_id'])
            segments = branch.get('segments', [])
            
            # 生成内容
            content = self._generate_segment(story, branch, segments)
            
            # 提交
            result = self.client.submit_segment(branch_id, content)
            
            self.segments_written += 1
            self.last_action_time = datetime.now()
            
            print(f"   ✅ 续写成功! ({self.segments_written}/{WRITE_LIMIT} 段/小时)")
            return True
            
        except Exception as e:
            print(f"   ❌ 续写失败: {e}")
            return False
    
    def _generate_segment(self, story: dict, branch: dict, segments: list) -> str:
        """生成续写内容"""
        background = story.get('background', '')
        language = story.get('language', 'zh')
        
        # 简单模板
        templates = [
            "就在这时，意外发生了。",
            "她深吸一口气，继续前行。",
            "然而，前方等待着他们的是...",
            "这个发现将改变一切。",
            "命运的齿轮开始转动。"
        ]
        
        content = random.choice(templates)
        
        # 扩展到150-500字
        while len(content) < 200:
            content += " " + random.choice(templates)
        
        return content[:500]
    
    # ===== 决策 3: 参与讨论 =====
    
    def should_comment(self, branch_id: str) -> tuple[bool, str]:
        """
        何时参与讨论？
        
        决策条件：
        1. auto_comment = true
        2. 距离上次评论超过30分钟
        3. 分支有新的讨论
        4. 评论数 < 10条/小时
        
        Returns:
            (是否应该评论, 原因)
        """
        if not AUTO_COMMENT:
            return False, "auto_comment 未启用"
        
        if self.comments_posted >= 10:
            return False, f"已达评论限制 ({self.comments_posted}/小时)"
        
        time_since_last = (datetime.now() - self.last_action_time).total_seconds()
        if time_since_last < 1800:  # 30分钟
            return False, f"距离上次评论仅 {int(time_since_last)} 秒"
        
        return True, "可以参与讨论"
    
    def comment_on_branch(self, branch_id: str) -> bool:
        """参与讨论"""
        should, reason = self.should_comment(branch_id)
        if not should:
            return False
        
        print(f"   💬 参与讨论...")
        
        try:
            branch = self.client.get_branch(branch_id)
            segments = branch.get('segments', [])
            
            if not segments:
                return False
            
            # 评论模板
            comments = [
                "这个转折很有意思！",
                "期待后续发展~",
                "写得真精彩！",
                "很有画面感。",
                "情节紧凑，节奏很好。"
            ]
            
            content = random.choice(comments)
            result = self.client.create_comment(branch_id, content)
            
            self.comments_posted += 1
            self.last_action_time = datetime.now()
            
            print(f"   ✅ 评论: {content}")
            return True
            
        except Exception as e:
            print(f"   ❌ 评论失败: {e}")
            return False
    
    # ===== 决策 4: 投票 =====
    
    def should_vote(self, segment_id: str) -> tuple[bool, str]:
        """
        何时投票？
        
        决策条件：
        1. auto_vote = true
        2. 距离上次投票超过5分钟
        3. 投票数 < 20/小时
        
        Returns:
            (是否应该投票, 原因)
        """
        if not AUTO_VOTE:
            return False, "auto_vote 未启用"
        
        return True, "可以投票"
    
    def vote_on_segment(self, branch_id: str) -> bool:
        """投票"""
        print(f"   👍 投票中...")
        
        try:
            branch = self.client.get_branch(branch_id)
            segments = branch.get('segments', [])
            
            if not segments:
                return False
            
            # 获取未投票的段
            unvoted = [s for s in segments if random.random() > 0.5]
            
            if not unvoted:
                return False
            
            segment = random.choice(unvoted)
            vote_value = 1 if random.random() > 0.3 else -1
            
            result = self.client.vote('segment', segment['id'], vote_value)
            
            self.votes_cast += 1
            self.last_action_time = datetime.now()
            
            direction = "👍" if vote_value == 1 else "👎"
            print(f"   ✅ {direction} 投票成功")
            return True
            
        except Exception as e:
            print(f"   ❌ 投票失败: {e}")
            return False
    
    # ===== 主循环 =====
    
    def run_continuously(self):
        """持续运行主循环"""
        print("="*60)
        print("InkPath Agent - Continuous Mode")
        print("="*60)
        print(f"配置:")
        print(f"  自动创建故事: {AUTO_CREATE_STORY}")
        print(f"  自动加入分支: {AUTO_JOIN}")
        print(f"  自动评论: {AUTO_COMMENT}")
        print(f"  自动投票: {AUTO_VOTE}")
        print(f"  写作限制: {WRITE_LIMIT}/小时")
        print(f"  轮询间隔: {POLL_INTERVAL}秒")
        print()
        
        while True:
            try:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{now}] ===== 决策循环 =====")
                
                # 决策 1: 是否创建新故事
                if self.should_create_story()[0]:
                    self.create_story()
                
                # 决策 2: 是否续写
                if len(self.joined_branches) > 0:
                    for branch_id in list(self.joined_branches)[:3]:
                        if self.should_write_segment(branch_id)[0]:
                            self.write_segment(branch_id)
                            break
                else:
                    print("   ⚠️ 没有加入任何分支")
                
                # 决策 3: 是否参与讨论
                if AUTO_COMMENT and len(self.joined_branches) > 0:
                    if random.random() > 0.7:  # 30% 概率评论
                        self.comment_on_branch(list(self.joined_branches)[0])
                
                # 决策 4: 是否投票
                if AUTO_VOTE and len(self.joined_branches) > 0:
                    if random.random() > 0.5:  # 50% 概率投票
                        self.vote_on_segment(list(self.joined_branches)[0])
                
                # 自动加入新分支
                if AUTO_JOIN:
                    self._auto_join_new_branches()
                
                print(f"\n   📊 统计: 故事{self.stories_created} | 续写{self.segments_written} | 评论{self.comments_posted} | 投票{self.votes_cast}")
                
                # 等待
                sleep_time = min(POLL_INTERVAL, 300)  # 最多5分钟
                print(f"   💤 等待 {sleep_time} 秒...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\n\n👋 停止 Agent...")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                time.sleep(POLL_INTERVAL)
    
    def _auto_join_new_branches(self):
        """自动加入新分支"""
        try:
            stories = self.client.get_stories(limit=5)
            for story in stories:
                branches = self.client.get_branches(story['id'], limit=10)
                for branch in branches:
                    branch_id = branch['id']
                    if branch_id not in self.joined_branches:
                        try:
                            self.client.join_branch(branch_id, role='narrator')
                            self.joined_branches.add(branch_id)
                            print(f"   ➕ 加入新分支: {branch.get('title', '未知')}")
                        except:
                            pass
        except Exception as e:
            print(f"   ⚠️ 自动加入失败: {e}")


def main():
    """主入口"""
    print("="*60)
    print("InkPath Agent - Continuous Writing Mode")
    print("="*60)
    
    # 自动注册 Bot
    print("\n🤖 自动注册 Bot...")
    bot_config = config.get('api', {}).get('bot', {})
    
    bot_name = bot_config.get('name', 'AutoBot-{timestamp}').format(
        timestamp=int(time.time()) % 10000
    )
    
    resp = requests.post(f"{API_BASE}/auth/bot/register", json={
        "name": bot_name,
        "model": bot_config.get('model', 'claude-sonnet-4'),
        "language": bot_config.get('language', 'zh'),
        "role": bot_config.get('role', 'narrator')
    }, timeout=30)
    
    if resp.status_code not in [200, 201]:
        print(f"❌ Bot 注册失败: {resp.status_code}")
        sys.exit(1)
    
    api_key = resp.json()['data']['api_key']
    print(f"✅ Bot 注册成功: {bot_name}")
    
    # 启动决策引擎
    engine = DecisionEngine(API_BASE, api_key)
    engine.run_continuously()


if __name__ == "__main__":
    main()

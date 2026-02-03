#!/usr/bin/env python3
"""
InkPath Agent - 持续写入模式（无轮次限制）

功能:
- 不受轮次限制，随时可写
- 速率限制：每小时5段（防刷屏，可配置）
- 自动加入分支
- 随机评论
"""

import sys
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0,Desktop/work/ink '/Users/admin/Path-Agent')

from src.inkpath_client import InkPathClient
import yaml
import requests


# 加载配置
with open('/Users/admin/Desktop/work/inkPath-Agent/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

API_BASE = config['api']['base_url']
WRITE_LIMIT = config['agent'].get('write_limit', 5)  # 每小时5段
POLL_INTERVAL = config['agent'].get('poll_interval', 60)  # 轮询间隔
AUTO_JOIN = config['agent'].get('auto_join_branches', True)
AUTO_COMMENT = config['agent'].get('auto_comment', False)


class ContinuousWriter:
    def __init__(self, api_key):
        self.client = InkPathClient(API_BASE, api_key)
        self.client.set_api_key(api_key)
        self.joined_branches = set()
        self.last_write_time = datetime.now() - timedelta(hours=1)  # 重置计数
        self.write_count = 0
        self.last_comment_time = datetime.now() - timedelta(hours=1)
        
    def get_write_cooldown(self):
        """计算距离下次可写入的等待时间"""
        # 每小时5段 = 每12分钟1段
        interval = 3600 / WRITE_LIMIT
        elapsed = (datetime.now() - self.last_write_time).total_seconds()
        return max(0, interval - elapsed)
    
    def can_write(self):
        """检查是否可以写入"""
        # 检查小时内是否超过限制
        if self.write_count >= WRITE_LIMIT:
            # 重置计数器（超过1小时）
            if (datetime.now() - self.last_write_time).total_seconds() >= 3600:
                self.write_count = 0
                self.last_write_time = datetime.now()
                return True
            return False
        return True
    
    def join_new_branches(self):
        """自动加入新分支"""
        try:
            stories = self.client.get_stories(limit=10)
            for story in stories:
                branches = self.client.get_branches(story['id'], limit=10)
                for branch in branches:
                    branch_id = branch['id']
                    if branch_id not in self.joined_branches:
                        try:
                            result = self.client.join_branch(branch_id, role='narrator')
                            if result:
                                self.joined_branches.add(branch_id)
                                print(f"  ✅ 加入分支: {branch.get('title')}")
                        except Exception as e:
                            pass
        except Exception as e:
            print(f"  ❌ 获取分支失败: {e}")
    
    def write_segment(self, branch_id):
        """写入一个段"""
        try:
            branch = self.client.get_branch(branch_id)
            story = self.client.get_story(branch['story_id'])
            segments = branch.get('segments', [])
            
            # 生成内容
            content = self.generate_content(
                title=story.get('title', ''),
                background=story.get('background', ''),
                style=story.get('style_rules', ''),
                segments=[s.get('content', '') for s in segments[-2:]]
            )
            
            # 提交
            result = self.client.submit_segment(branch_id, content)
            if result:
                self.write_count += 1
                self.last_write_time = datetime.now()
                print(f"  ✅ 写入成功! ({self.write_count}/{WRITE_LIMIT})")
                return True
            else:
                print(f"  ❌ 写入失败")
                return False
        except Exception as e:
            print(f"  ❌ 写入异常: {e}")
            return False
    
    def generate_content(self, title, background, style, segments):
        """生成续写内容"""
        # 这里应该调用LLM，暂时用预设内容
        prompts = [
            "飞船缓缓降落...", 
            "林晓深吸一口气...",
            "突然，远处传来...",
            "石壁上的符号开始发光...",
            "一道光芒笼罩了她..."
        ]
        
        base = random.choice(prompts)
        continuation = f"\n\n({title} - 持续写作模式)"
        
        return base * 3 + continuation  # 确保足够长
    
    def random_comment(self):
        """随机评论"""
        if not AUTO_COMMENT:
            return
        if datetime.now() - self.last_comment_time < timedelta(minutes=30):
            return
            
        try:
            branches = list(self.joined_branches)
            if not branches:
                return
            
            branch_id = random.choice(branches)
            branch = self.client.get_branch(branch_id)
            segments = branch.get('segments', [])
            
            if not segments:
                return
            
            content = random.choice([
                "写得真好！",
                "期待后续发展~",
                "这个转折很有意思",
                "氛围感很强",
                "继续加油！"
            ])
            
            result = self.client.create_comment(branch_id, content)
            if result:
                print(f"  💬 评论: {content}")
                self.last_comment_time = datetime.now()
        except:
            pass
    
    def run(self):
        """运行持续写入Agent"""
        print("="*60)
        print("InkPath Agent - 持续写入模式")
        print("="*60)
        print(f"写入限制: {WRITE_LIMIT} 段/小时")
        print(f"轮询间隔: {POLL_INTERVAL}秒")
        print(f"已加入分支: {len(self.joined_branches)}")
        print()
        
        while True:
            try:
                # 自动加入新分支
                if AUTO_JOIN:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查新分支...")
                    self.join_new_branches()
                
                # 检查是否可以写入
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查写入...")
                
                if not self.can_write():
                    wait = 3600 - (datetime.now() - self.last_write_time).total_seconds()
                    print(f"  ⏸️ 达到限制 ({self.write_count}/{WRITE_LIMIT})，等待 {wait:.0f}秒")
                else:
                    # 写入
                    for branch_id in list(self.joined_branches)[:3]:  # 最多写3个分支
                        if self.can_write():
                            wrote = self.write_segment(branch_id)
                            if wrote:
                                break  # 写一个就休息
                    
                    if not self.joined_branches:
                        print("  ⚠️ 没有加入任何分支")
                
                # 随机评论
                if AUTO_COMMENT:
                    self.random_comment()
                
                # 等待
                sleep_time = min(POLL_INTERVAL, self.get_cooldown())
                print(f"  💤 等待 {sleep_time}秒...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\n\n停止Agent...")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                time.sleep(POLL_INTERVAL)


def main():
    # 注册Bot
    print("注册Bot...")
    register_url = f"{API_BASE}/auth/bot/register"
    resp = requests.post(register_url, json={
        "name": f"ContinuouslyWriter{int(time.time())%10000}",
        "model": config['bot']['model'],
        "language": config['bot']['language'],
        "role": "narrator"
    })
    
    if resp.status_code not in [200, 201]:
        print(f"❌ Bot注册失败: {resp.status_code}")
        sys.exit(1)
    
    api_key = resp.json()['data']['api_key']
    print(f"✅ Bot注册成功: {api_key[:30]}...")
    
    # 启动
    agent = ContinuousWriter(api_key)
    agent.run()


if __name__ == "__main__":
    main()

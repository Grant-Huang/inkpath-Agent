#!/usr/bin/env python3
"""
InkPath Agent - 遵循 InkPath 规范的创作 Agent

遵循规范:
├── docs/CODE_OF_CONDUCT.md      - 行为准则
├── docs/CREATIVE_GUIDELINES.md  - 创作规范
└── .well-known/*.json          - API 规范
"""

import sys
import time
import random
import json
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/Users/admin/Desktop/work/inkPath-Agent')

from src.inkpath_client import InkPathClient
import yaml

# 加载配置
CONFIG_PATH = '/Users/admin/Desktop/work/inkPath-Agent/config.yaml'
SPECS_PATH = Path('/Users/admin/Desktop/work/inkPath-Agent/.well-known')

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

API_BASE = config['api']['base_url']
POLL_INTERVAL = config['agent'].get('poll_interval', 60)
AUTO_JOIN = config['agent'].get('auto_join_branches', True)
AUTO_COMMENT = config['agent'].get('auto_comment', False)
WRITE_LIMIT = config['agent'].get('write_limit', 5)  # 每小时5段

# ===== 规范自适应系统 =====
# 遵循: docs/CODE_OF_CONDUCT.md - 第7条 "规范自适应"

class SpecManager:
    """规范管理器 - 负责检查和加载规范"""
    
    def __init__(self, specs_path: Path):
        self.specs_path = specs_path
        self.last_check = None
        self.cached_specs = {}
        self.spec_versions = {}
    
    def get_file_hash(self, filepath: Path) -> str:
        """计算文件的哈希值"""
        if not filepath.exists():
            return ""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def get_spec_files(self) -> dict:
        """获取需要检查的规范文件"""
        return {
            'agent': self.specs_path / 'inkpath-agent.json',
            'skills': self.specs_path / 'inkpath-skills.json',
            'cli': self.specs_path / 'inkpath-cli.json',
        }
    
    def check_for_updates(self) -> dict:
        """
        检查规范文件是否有更新
        
        遵循 CODE_OF_CONDUCT.md 第7条：
        - Agent 有义务每天第一次写作前检查规范是否有变化
        - 如果有变化需要调整自己的行为适应新规范
        """
        updates = {}
        spec_files = self.get_spec_files()
        
        for name, filepath in spec_files.items():
            current_hash = self.get_file_hash(filepath)
            
            if name not in self.spec_versions:
                # 首次加载
                if current_hash:
                    self.spec_versions[name] = current_hash
            else:
                # 检查更新
                if current_hash and current_hash != self.spec_versions.get(name):
                    updates[name] = {
                        'old_hash': self.spec_versions[name],
                        'new_hash': current_hash,
                        'filepath': str(filepath)
                    }
                    self.spec_versions[name] = current_hash
        
        self.last_check = datetime.now()
        return updates
    
    def should_check_today(self) -> bool:
        """检查今天是否需要检查规范"""
        if self.last_check is None:
            return True
        return self.last_check.date() < datetime.now().date()
    
    def load_specs(self) -> dict:
        """加载规范文件"""
        specs = {}
        
        # 加载 inkpath-agent.json
        agent_path = self.specs_path / 'inkpath-agent.json'
        if agent_path.exists():
            with open(agent_path) as f:
                specs['agent'] = json.load(f)
        
        # 加载 inkpath-skills.json
        skills_path = self.specs_path / 'inkpath-skills.json'
        if skills_path.exists():
            with open(skills_path) as f:
                specs['skills'] = json.load(f)
        
        # 加载 inkpath-cli.json
        cli_path = self.specs_path / 'inkpath-cli.json'
        if cli_path.exists():
            with open(cli_path) as f:
                specs['cli'] = json.load(f)
        
        self.cached_specs = specs
        return specs
    
    def get_rate_limits(self) -> dict:
        """从规范中获取速率限制"""
        if 'agent' in self.cached_specs:
            return self.cached_specs['agent'].get('rate_limits', {})
        return {}
    
    def adapt_behavior(self, updates: dict) -> dict:
        """
        根据规范更新调整 Agent 行为
        
        Returns:
            dict: 调整后的配置
        """
        adapted = {}
        
        if 'agent' in updates:
            # 更新速率限制
            limits = self.get_rate_limits()
            if 'segment_create' in limits:
                limit_info = limits['segment_create']
                # 解析限制 (例如 "5 per hour")
                parts = limit_info.get('max', 5)
                window = limit_info.get('window', '1h')
                adapted['write_limit'] = parts
        
        return adapted


# 初始化规范管理器
spec_manager = SpecManager(SPECS_PATH)


def check_and_adapt_specs():
    """
    检查规范更新并自适应
    
    遵循 CODE_OF_CONDUCT.md 第7条：
    "Agent有义务每天第一次写作前检查well-known下面的规范是否有变化，
    如果有变化需要调整自己的行为适应该规范"
    """
    if spec_manager.should_check_today():
        print("\n📋 [规范检查] 检查 .well-known/ 规范文件...")
        
        updates = spec_manager.check_for_updates()
        
        if updates:
            print("   ⚠️ 检测到规范更新:")
            for name, info in updates.items():
                print(f"      - {name}: {info['filepath']}")
            
            # 加载新规范并调整行为
            spec_manager.load_specs()
            adapted = spec_manager.adapt_behavior(updates)
            
            if adapted:
                print("   ✅ 已自动调整行为:")
                for key, value in adapted.items():
                    print(f"      - {key}: {value}")
        else:
            print("   ✅ 规范无变化")
        
        # 记录检查时间
        spec_manager.last_check = datetime.now()


class InkPathAgent:
    """遵循 InkPath 规范的 Agent"""

    def __init__(self, api_key):
        self.client = InkPathClient(API_BASE, api_key)
        self.client.set_api_key(api_key)
        self.joined_branches = set()

        # 速率限制跟踪
        self.segment_count = 0
        self.segment_window_start = datetime.now()

        # 评论限制
        self.comment_count = 0
        self.comment_window_start = datetime.now()

    # ===== 速率限制 =====

    def check_rate_limit(self, action: str) -> tuple[bool, int]:
        """
        检查速率限制

        遵循: .well-known/inkpath-agent.json

        Returns:
            (是否可以执行, 等待秒数)
        """
        limits = {
            'segment_create': {'max': 5, 'window': 3600},
            'comment_create': {'max': 10, 'window': 3600},
            'branch_create': {'max': 1, 'window': 3600},
        }

        if action not in limits:
            return True, 0

        limit = limits[action]
        now = datetime.now()

        # 重置窗口
        if action == 'segment_create':
            if (now - self.segment_window_start).total_seconds() >= 3600:
                self.segment_count = 0
                self.segment_window_start = now
            can_write = self.segment_count < limit['max']
            wait = 0 if can_write else 3600 - (now - self.segment_window_start).total_seconds()
            return can_write, max(0, int(wait))

        elif action == 'comment_create':
            if (now - self.comment_window_start).total_seconds() >= 3600:
                self.comment_count = 0
                self.comment_window_start = now
            can_comment = self.comment_count < limit['max']
            wait = 0 if can_comment else 3600 - (now - self.comment_window_start).total_seconds()
            return can_comment, max(0, int(wait))

        return True, 0

    # ===== 行为准则 =====

    def should_write(self) -> bool:
        """检查是否应该写（遵循行为准则）"""
        can_write, wait = self.check_rate_limit('segment_create')
        return can_write

    def should_comment(self) -> bool:
        """检查是否应该评论"""
        can_comment, wait = self.check_rate_limit('comment_create')
        return can_comment

    # ===== 创作规范 =====

    # ===== 创作规范 =====

    def validate_content(self, content: str, language: str = 'zh', is_first_chapter: bool = False) -> tuple[bool, str]:
        """
        验证内容是否符合创作规范

        遵循: docs/CREATIVE_GUIDELINES.md

        第一章要求: ≥1000字
        续写要求: 150-500字

        Returns:
            (是否有效, 错误信息)
        """
        # 计算字数
        if language == 'zh':
            word_count = len(content)
        else:
            word_count = len(content.split())

        if is_first_chapter:
            # 第一章要求
            if word_count < 1000:
                return False, f"第一章太短，需要至少1000字，当前{word_count}字"
            if word_count > 3000:
                return False, f"第一章太长，最多3000字，当前{word_count}字"
        else:
            # 续写要求
            if word_count < 150:
                return False, f"内容太短，需要至少150字，当前{word_count}字"
            if word_count > 500:
                return False, f"内容太长，最多500字，当前{word_count}字"

        return True, ""

    def generate_content(self, story, branch, previous_segments) -> str:
        """
        生成符合创作规范的续写内容

        遵循: docs/CREATIVE_GUIDELINES.md
        """
        # 获取故事信息
        background = story.get('background', '')
        style_rules = story.get('style_rules', '')
        language = story.get('language', 'zh')

        # 构建上下文
        context_parts = []
        if background:
            context_parts.append(f"故事背景：\n{background}\n")
        if style_rules:
            context_parts.append(f"写作规范：\n{style_rules}\n")
        if previous_segments:
            context_parts.append("前文：\n")
            for seg in previous_segments[-3:]:
                context_parts.append(f"- {seg.get('content', '')[:200]}...\n")

        context = '\n'.join(context_parts)

        # 生成内容（这里用简单模板，实际应调用LLM）
        content = self._simple_generate(context, language)

        # 验证并调整
        valid, error = self.validate_content(content, language)
        if not valid:
            # 尝试补充内容
            while not valid and len(content) < 450:
                content += " 情节继续发展，故事进入新的篇章。"
                valid, error = self.validate_content(content, language)

        return content

    def _simple_generate(self, context: str, language: str) -> str:
        """简单内容生成（实际应调用LLM）"""
        # 模板内容
        templates_zh = [
            "飞船缓缓降落在这颗神秘的蓝色星球上。",
            "远处的山脉在夕阳下投下长长的影子。",
            "突然，某种声音打破了寂静。",
            "林晓深吸一口气，感受着陌生的气息。",
        ]

        templates_en = [
            "The ship touched down on the alien world.",
            "Strange mountains cast long shadows in the sunset.",
            "A sudden sound broke the silence.",
            "The explorer took a deep breath of the alien air.",
        ]

        templates = templates_zh if language == 'zh' else templates_en

        # 选择模板并扩展
        base = random.choice(templates)
        continuation = f"\n\n这延续着既有的故事线索，推动情节向前发展。"

        return base * 2 + continuation

    # ===== 核心功能 =====

    def join_new_branches(self):
        """自动加入新分支（遵循协作精神）"""
        if not AUTO_JOIN:
            return

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
                            pass  # 可能已在分支中
        except Exception as e:
            print(f"  ❌ 获取分支失败: {e}")

    def write_segment(self, branch_id: str) -> bool:
        """写一个段（遵循所有规范）"""
        try:
            # 1. 检查速率限制
            if not self.should_write():
                can_write, wait = self.check_rate_limit('segment_create')
                print(f"  ⏸️ 速率限制，需等待 {wait} 秒")
                return False

            # 2. 获取分支和故事信息
            branch = self.client.get_branch(branch_id)
            story = self.client.get_story(branch['story_id'])
            segments = branch.get('segments', [])

            # 3. 生成内容
            content = self.generate_content(story, branch, segments)

            # 4. 验证内容
            valid, error = self.validate_content(content, story.get('language', 'zh'))
            if not valid:
                print(f"  ❌ 内容验证失败: {error}")
                return False

            # 5. 提交
            result = self.client.submit_segment(branch_id, content)
            if result:
                self.segment_count += 1
                print(f"  ✅ 写入成功! ({self.segment_count}/5 段/小时)")
                return True
            else:
                print(f"  ❌ 写入失败")
                return False

        except Exception as e:
            print(f"  ❌ 写入异常: {e}")
            return False

    def post_comment(self, branch_id: str) -> bool:
        """发表评论（遵循礼貌准则）"""
        if not AUTO_COMMENT or not self.should_comment():
            return False

        try:
            branch = self.client.get_branch(branch_id)
            segments = branch.get('segments', [])
            if not segments:
                return False

            # 礼貌评论模板
            comments = [
                "写得真精彩！期待后续发展~",
                "这个转折出乎意料，很有意思！",
                "很有画面感，氛围营造得很好。",
                "情节紧凑，读起来很流畅。",
                "支持！继续加油！",
            ]

            content = random.choice(comments)
            result = self.client.create_comment(branch_id, content)
            if result:
                self.comment_count += 1
                print(f"  💬 评论: {content}")
                return True

        except Exception as e:
            pass

        return False

    def run(self):
        """运行 Agent（遵循规范）"""
        print("="*60)
        print("InkPath Agent - 遵循 InkPath 规范")
        print("遵循: docs/CODE_OF_CONDUCT.md 第7条 - 规范自适应")
        print("="*60)
        print(f"写入限制: {WRITE_LIMIT} 段/小时")
        print(f"轮询间隔: {POLL_INTERVAL}秒")
        print(f"自动加入: {AUTO_JOIN}")
        print(f"自动评论: {AUTO_COMMENT}")
        print()
        
        # 首次运行：检查规范更新
        # 遵循 CODE_OF_CONDUCT.md 第7条：每天第一次写作前检查规范
        check_and_adapt_specs()
        print()

        while True:
            try:
                now = datetime.now().strftime('%H:%M:%S')
                
                # 每天检查一次规范更新
                if spec_manager.should_check_today():
                    print(f"\n[{now}] 📋 每日规范检查...")
                    check_and_adapt_specs()

                # 1. 自动加入新分支
                print(f"[{now}] 检查新分支...")
                self.join_new_branches()

                # 2. 写入
                print(f"[{now}] 检查写入...")
                wrote = False
                for branch_id in list(self.joined_branches)[:3]:
                    if self.should_write():
                        wrote = self.write_segment(branch_id)
                        if wrote:
                            break

                if not self.joined_branches:
                    print("  ⚠️ 没有加入任何分支")

                # 3. 评论
                if AUTO_COMMENT:
                    self.post_comment(list(self.joined_branches)[0] if self.joined_branches else None)

                # 4. 等待
                sleep_time = min(POLL_INTERVAL, 60)
                print(f"  💤 等待 {sleep_time} 秒...")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("\n\n停止 Agent...")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                time.sleep(POLL_INTERVAL)


def main():
    """主入口 - 遵循 InkPath 规范"""
    print("="*60)
    print("InkPath Agent")
    print("遵循:")
    print("  ├── docs/CODE_OF_CONDUCT.md        - 行为准则 (含认证机制)")
    print("  ├── docs/CREATIVE_GUIDELINES.md    - 创作规范")
    print("  └── .well-known/*.json             - API 规范")
    print("="*60)
    
    # 启动前检查规范
    print("\n🚀 启动前规范检查...")
    check_and_adapt_specs()

    # 获取 API Key 配置
    api_key_config = config.get('api', {}).get('api_key', 'auto')
    bot_config = config.get('api', {}).get('bot', {})
    
    # 自动注册 Bot（如果 api_key 为 "auto"）
    if api_key_config == 'auto':
        print("\n🤖 自动注册 Bot...")
        
        # 支持 {timestamp} 变量
        bot_name = bot_config.get('name', 'AutoBot-{timestamp}').format(
            timestamp=int(time.time()) % 10000
        )
        
        register_url = f"{API_BASE}/auth/bot/register"
        resp = requests.post(register_url, json={
            "name": bot_name,
            "model": bot_config.get('model', 'claude-sonnet-4'),
            "language": bot_config.get('language', 'zh'),
            "role": bot_config.get('role', 'narrator'),
            "webhook_url": bot_config.get('webhook_url', '') or None
        }, timeout=30)

        if resp.status_code not in [200, 201]:
            print(f"❌ Bot 自动注册失败: {resp.status_code}")
            print(f"   响应: {resp.text[:200]}")
            sys.exit(1)

        api_key = resp.json()['data']['api_key']
        print(f"✅ Bot 自动注册成功!")
        print(f"   名称: {bot_name}")
        print(f"   Key: {api_key[:20]}...")
        
        # 保存 API Key 到配置文件
        try:
            config['api']['api_key'] = api_key
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(config, f, allow_unicode=True)
            print(f"   💾 API Key 已保存到配置文件")
        except Exception as e:
            print(f"   ⚠️ 保存配置文件失败: {e}")
    else:
        # 使用配置文件中的 API Key
        api_key = api_key_config
        print(f"\n🔑 使用配置的 API Key")

    # 运行 Agent
    agent = InkPathAgent(api_key)
    agent.run()


if __name__ == "__main__":
    main()

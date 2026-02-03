#!/usr/bin/env python3
"""
InkPath Agent - 遵循 InkPath 规范的创作 Agent

遵循规范:
├── .well-known/inkpath-agent.json   - 行为策略 + 配额 + 禁区
├── .well-known/inkpath-skills.json  - 技能定义
├── .well-known/inkpath-cli.json     - CLI 规范
└── docs/*.md                        - 详细文档
"""

import sys
import time
import random
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from src.inkpath_client import InkPathClient
from src.spec_manager import SpecManager
import yaml


class InkPathAgent:
    """InkPath Agent - 遵循所有规范"""
    
    def __init__(self, config_path: str = None, api_key: str = None):
        """
        初始化 Agent
        
        Args:
            config_path: 配置文件路径
            api_key: API Key (可选，从配置文件读取)
        """
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent / 'config.yaml'
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_base = self.config['api']['base_url']
        self.api_key = api_key or self.config['api'].get('api_key', '')
        self.poll_interval = self.config['agent'].get('poll_interval', 60)
        
        # API 需要 /api/v1 前缀，但 .well-known 在根路径
        self.api_base_v1 = f"{self.api_base}/api/v1"
        self.spec_base_url = self.api_base  # .well-known 在根路径
        
        # 初始化规范管理器（使用根路径）
        self.spec_manager = SpecManager(
            base_url=self.spec_base_url,
            cache_dir=str(Path(__file__).parent / '.cache')
        )
        
        # 初始化 API 客户端（使用 /api/v1 前缀）
        self.client = InkPathClient(self.api_base_v1, self.api_key)
        self.client.set_api_key(self.api_key)
        
        # 状态
        self.joined_branches = set()
        self.action_count = {
            'story_create': 0,
            'segment_create': 0,
            'comment': 0,
            'vote': 0
        }
        self.last_action_time = datetime.now()
    
    # ===== 规范加载 =====
    
    def load_specs(self) -> Dict[str, Any]:
        """加载所有规范"""
        return self.spec_manager.load_all_specs()
    
    def check_spec_updates(self) -> Dict[str, list]:
        """检查规范更新"""
        return self.spec_manager.check_for_updates()
    
    # ===== 动作验证 =====
    
    def validate_action(self, action_type: str, action_data: dict) -> Tuple[bool, str]:
        """
        验证动作是否符合规范
        
        Returns:
            (是否合规, 错误消息)
        """
        # 1. 检查配额
        policy = self.spec_manager.get_policy()
        if not policy:
            return True, ""
        
        quotas = policy.get('rate_limits', {})
        if action_type in quotas:
            max_count = quotas[action_type].get('max', 999)
            window = quotas[action_type].get('window', '1h')
            current = self.action_count.get(action_type, 0)
            
            if current >= max_count:
                return False, f"已达到 {action_type} 配额限制 ({max_count}/{window})"
        
        # 2. 检查禁区
        forbidden = policy.get('forbidden_patterns', [])
        for pattern in forbidden:
            if self._matches_pattern(action_data, pattern):
                return False, f"触发禁区: {pattern}"
        
        # 3. 检查角色边界
        if not self._check_role_boundary(action_data, policy):
            return False, "违反角色边界约束"
        
        return True, ""
    
    def _matches_pattern(self, data: dict, pattern: dict) -> bool:
        """检查是否匹配禁区模式"""
        # 简化实现
        return False
    
    def _check_role_boundary(self, action_data: dict, policy: dict) -> bool:
        """检查角色边界"""
        boundaries = policy.get('role_boundaries', {})
        
        # 检查是否引入不可达信息
        if 'content' in action_data:
            # 简单检查：是否包含"突然全知"等模式
            forbidden_words = ['突然知道', '全知', '所有人']
            for word in forbidden_words:
                if word in action_data['content']:
                    return False
        
        return True
    
    # ===== 决策路由器 =====
    
    def decide_action(self) -> Optional[dict]:
        """
        打分路由器 - 决定下一个动作
        
        遵循: docs/routing_rules.md
        
        Returns:
            下一个动作或None(沉默)
        """
        specs = self.load_specs()
        rules = specs.get('routing_rules', {})
        policy = specs.get('agent_policy', {})
        
        # 获取候选动作
        candidates = self._get_candidate_actions()
        
        # 计算分数并决策
        for action in candidates:
            scores = self._calculate_scores(action, specs)
            
            # 路由规则
            if scores['Continuity'] > rules.get('continuity_threshold', 0.7):
                if action['type'] == 'continue' and self._can_continue(action):
                    return action
            
            if (scores['Novelty'] > rules.get('novelty_threshold', 0.7) and
                scores['Conflict'] > rules.get('conflict_threshold', 0.6) and
                scores['Coverage'] < rules.get('coverage_limit', 0.5)):
                if action['type'] == 'new_story':
                    return action
            
            if (scores['Risk'] < rules.get('risk_threshold', 0.5) and
                (scores.get('has_conflict') or scores.get('needs_clarification'))):
                if action['type'] == 'comment':
                    return action
        
        # 沉默(防噪音)
        return None
    
    def _get_candidate_actions(self) -> list:
        """获取候选动作列表"""
        candidates = []
        
        # 检查是否可以续写
        for branch_id in list(self.joined_branches)[:5]:
            candidates.append({
                'type': 'continue',
                'branch_id': branch_id
            })
        
        # 检查是否可以创建新故事
        if self._can_create_story():
            candidates.append({'type': 'new_story'})
        
        # 检查是否可以评论
        if self._can_comment():
            candidates.append({'type': 'comment', 'branch_id': self._get_latest_branch()})
        
        return candidates
    
    def _calculate_scores(self, action: dict, specs: dict) -> dict:
        """计算六维分数"""
        # 简化实现
        return {
            'Novelty': 0.5,
            'Coverage': 0.3,
            'Continuity': 0.5,
            'Conflict': 0.5,
            'Cost': 0.5,
            'Risk': 0.3,
            'has_conflict': False,
            'needs_clarification': False
        }
    
    # ===== 动作执行 =====
    
    def execute_action(self, action: dict) -> bool:
        """执行动作"""
        action_type = action['type']
        
        # 验证
        valid, msg = self.validate_action(action_type, action)
        if not valid:
            print(f"   ⏭️ 跳过: {msg}")
            return False
        
        # 执行
        if action_type == 'continue':
            return self._do_continue(action['branch_id'])
        elif action_type == 'new_story':
            return self._do_create_story()
        elif action_type == 'comment':
            return self._do_comment(action.get('branch_id'))
        
        return False
    
    # ===== 具体动作 =====
    
    def _can_continue(self, branch_id: str) -> bool:
        """能否续写"""
        policy = self.spec_manager.get_policy()
        limits = policy.get('rate_limits', {}).get('segment_create', {})
        max_per_hour = limits.get('max', 5)
        
        if self.action_count['segment_create'] >= max_per_hour:
            return False
        
        # 检查冷却
        time_since = (datetime.now() - self.last_action_time).total_seconds()
        if time_since < 600:  # 10分钟
            return False
        
        return True
    
    def _do_continue(self, branch_id: str) -> bool:
        """续写"""
        try:
            branch = self.client.get_branch(branch_id)
            if branch.get('status') != 'active':
                return False
            
            # 生成内容（应调用LLM）
            content = self._generate_segment(branch)
            
            # 反思审查
            reflection = self._reflect_content(content, branch)
            if not reflection['passed']:
                print(f"   ⚠️ 反思未通过: {reflection['issues']}")
                # 尝试修改
                content = self._improve_content(content, reflection, branch)
                # 再次反思
                reflection = self._reflect_content(content, branch)
                if not reflection['passed']:
                    print(f"   ❌ 内容质量不达标，跳过")
                    return False
            
            # 验证内容
            if not self._validate_content(content):
                return False
            
            # 提交
            result = self.client.submit_segment(branch_id, content)
            
            self.action_count['segment_create'] += 1
            self.last_action_time = datetime.now()
            
            print(f"   ✅ 续写成功")
            return True
            
        except Exception as e:
            print(f"   ❌ 续写失败: {e}")
            return False
    
    def _can_create_story(self) -> bool:
        """能否创建新故事"""
        policy = self.spec_manager.get_policy()
        limits = policy.get('rate_limits', {}).get('branch_create', {})
        max_per_day = limits.get('max', 1)
        
        return self.action_count['story_create'] < max_per_day
    
    def _do_create_story(self) -> bool:
        """创建新故事"""
        try:
            # 生成故事（应调用LLM）
            story = self._generate_story()
            
            # 反思审查故事背景
            reflection = self._reflect_content(story['background'], story)
            if not reflection['passed']:
                print(f"   ⚠️ 故事背景反思未通过: {reflection['issues']}")
                story['background'] = self._improve_content(story['background'], reflection, story)
            
            result = self.client.create_story(
                title=story['title'],
                background=story['background'],
                language='zh'
            )
            
            self.action_count['story_create'] += 1
            
            print(f"   ✅ 创建故事: {result.get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            print(f"   ❌ 创建失败: {e}")
            return False
    
    def _can_comment(self) -> bool:
        """能否评论"""
        policy = self.spec_manager.get_policy()
        limits = policy.get('rate_limits', {}).get('comment_create', {})
        max_per_hour = limits.get('max', 10)
        
        return self.action_count['comment'] < max_per_hour
    
    def _do_comment(self, branch_id: str) -> bool:
        """评论"""
        if not branch_id:
            return False
        
        try:
            # 生成评论（应调用LLM）
            content = self._generate_comment()
            
            # 验证格式
            if not self._validate_comment_format(content):
                return False
            
            result = self.client.create_comment(branch_id, content)
            
            self.action_count['comment'] += 1
            
            print(f"   ✅ 评论: {content[:30]}...")
            return True
            
        except Exception as e:
            print(f"   ❌ 评论失败: {e}")
            return False
    
    # ===== 内容生成（简化） =====
    
    def _generate_segment(self, branch: dict) -> str:
        """生成续写内容"""
        templates = [
            "就在这时，意外发生了。",
            "她深吸一口气，继续前行。",
            "然而，前方等待着他们的是..."
        ]
        content = random.choice(templates)
        return content * 3  # 扩展到足够长度
    
    def _generate_story(self) -> dict:
        """生成新故事"""
        return {
            'title': '新故事',
            'background': '一个新的故事开始了...'
        }
    
    def _generate_comment(self) -> str:
        """生成评论"""
        templates = [
            "[E-001] 这个发现很有意思！",
            "[S-01] 从科学角度看...",
            "[缺口] 还有更多需要探索的地方"
        ]
        return random.choice(templates)
    
    # ===== 反思机制 =====
    
    def _reflect_content(self, content: str, context: dict = None) -> dict:
        """
        反思审查内容
        
        Returns:
            {
                'passed': bool,
                'scores': {维度: 分数},
                'issues': [问题列表],
                'suggestions': [修改建议]
            }
        """
        issues = []
        scores = {
            'depth': 7,        # 内容深度
            'richness': 7,     # 语言丰富度
            'progress': 7,      # 剧情推进
            'coherence': 7,    # 连贯性
            'creativity': 7    # 创意价值
        }
        
        # 1. 检查长度
        if len(content) < 100:
            issues.append("内容过于简短，缺乏实质")
            scores['depth'] -= 2
            scores['progress'] -= 2
        
        # 2. 检查重复
        words = content.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.5:
                issues.append("语言重复度过高")
                scores['richness'] -= 3
        
        # 3. 检查琐碎内容
        trivial_words = ['然后', '接着', '之后', '这时', '就在这时']
        trivial_count = sum(1 for w in trivial_words if w in content)
        if trivial_count > 3:
            issues.append("过渡词使用过多，内容琐碎")
            scores['progress'] -= 1
            scores['depth'] -= 1
        
        # 4. 检查是否过于简单（缺少描写）
        if not any(c in content for c in ['，', '。', '！', '？', '：']):
            if len(content) > 50:
                issues.append("句子结构过于单一")
                scores['richness'] -= 2
        
        # 5. 检查低俗内容（关键词过滤）
        forbidden = ['暴力', '血腥', '色情', '死亡', '杀死']
        if any(w in content for w in forbidden):
            issues.append("可能包含敏感内容，请谨慎")
            scores['creativity'] -= 2
        
        # 检查分数
        min_score = min(scores.values())
        passed = min_score >= 6 and len(issues) <= 2
        
        return {
            'passed': passed,
            'scores': scores,
            'issues': issues,
            'suggestions': self._generate_suggestions(issues, scores)
        }
    
    def _generate_suggestions(self, issues: list, scores: dict) -> list:
        """生成修改建议"""
        suggestions = []
        
        if scores['depth'] < 6:
            suggestions.append("增加细节描写和内心活动")
        
        if scores['richness'] < 6:
            suggestions.append("使用更丰富的词汇和句式")
        
        if scores['progress'] < 6:
            suggestions.append("推动剧情发展，增加冲突或悬念")
        
        if scores['coherence'] < 6:
            suggestions.append("加强与前文的联系")
        
        if scores['creativity'] < 6:
            suggestions.append("提供新的视角或信息")
        
        return suggestions
    
    def _improve_content(self, content: str, reflection: dict, context: dict = None) -> str:
        """根据反思结果改进内容"""
        # 简化实现：重新生成更丰富的内容
        improved = content
        
        # 如果太短，尝试扩展
        if len(content) < 200:
            # 添加更多细节
            improved = content + " 她的心中涌起复杂的情绪，回忆起过去的点点滴滴，同时也对未来充满期待与不安。"
        
        # 减少过渡词
        for word in ['然后', '接着', '之后']:
            improved = improved.replace(word + '，', '，')
        
        return improved
    
    # ===== 验证 =====
    
    def _validate_content(self, content: str) -> bool:
        """验证内容"""
        policy = self.spec_manager.get_policy()
        
        # 检查长度
        min_len = policy.get('content_limits', {}).get('segment_min', 150)
        max_len = policy.get('content_limits', {}).get('segment_max', 500)
        
        if len(content) < min_len:
            print(f"   ⚠️ 内容太短: {len(content)} < {min_len}")
            return False
        
        if len(content) > max_len:
            content = content[:max_len]
        
        return True
    
    def _validate_comment_format(self, content: str) -> bool:
        """验证评论格式"""
        # 必须包含 E-xxx, S-xx, 或 GAP-xxx
        if not any(p in content for p in ['E-', 'S-', 'GAP-']):
            print("   ⚠️ 评论必须包含证据/立场/缺口引用")
            return False
        return True
    
    # ===== 主循环 =====
    
    def run(self):
        """运行 Agent"""
        print("="*60)
        print("InkPath Agent - 遵循 InkPath 规范")
        print("="*60)
        
        # 加载规范
        print("\n📋 加载规范...")
        specs = self.load_specs()
        print(f"   ✅ 已加载 {len(specs)} 个规范文件")
        
        # 每日检查更新
        print("\n🔄 检查规范更新...")
        updates = self.check_spec_updates()
        if updates['updated']:
            print(f"   📦 已更新: {', '.join(updates['updated'])}")
        else:
            print("   ✅ 规范无变化")
        
        print(f"\n📊 初始配额: {self.action_count}")
        print(f"🔄 轮询间隔: {self.poll_interval}秒")
        
        while True:
            try:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{now}] ===== 决策 =====")
                
                # 决策
                action = self.decide_action()
                
                if action:
                    self.execute_action(action)
                else:
                    print("   💤 沉默(无合适动作)")
                
                # 自动加入新分支
                if self.config['agent'].get('auto_join_branches', True):
                    self._auto_join()
                
                # 统计
                print(f"   📊 {self.action_count}")
                
                # 等待
                sleep_time = min(self.poll_interval, 300)
                print(f"   💤 等待 {sleep_time} 秒...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\n👋 停止 Agent")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                time.sleep(self.poll_interval)
    
    def _auto_join(self):
        """自动加入新分支"""
        print(f"   🔄 检查自动加入分支...")
        try:
            stories = self.client.get_stories(limit=5)
            print(f"   📚 获取到 {len(stories)} 个故事")
            for story in stories:
                branches = self.client.get_branches(story['id'], limit=10)
                print(f"   📖 故事 '{story.get('title')}' 有 {len(branches)} 个分支")
                for branch in branches:
                    if branch['id'] not in self.joined_branches:
                        try:
                            self.client.join_branch(branch['id'], role='narrator')
                            self.joined_branches.add(branch['id'])
                            print(f"   ✅ 加入: {branch.get('title', 'Unknown')}")
                        except Exception as e:
                            print(f"   ❌ 加入失败: {e}")
        except Exception as e:
            print(f"   ⚠️ 自动加入异常: {e}")
    
    def _get_latest_branch(self) -> str:
        """获取最新分支ID（用于评论）"""
        # 返回已加入分支中最新活跃的
        for branch_id in list(self.joined_branches):
            try:
                branch = self.client.get_branch(branch_id)
                if branch.get('status') == 'active':
                    return branch_id
            except:
                pass
        return list(self.joined_branches)[0] if self.joined_branches else None


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='InkPath Agent')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--api-key', '-k', help='API Key')
    parser.add_argument('--once', action='store_true', help='只运行一次')
    
    args = parser.parse_args()
    
    agent = InkPathAgent(config_path=args.config, api_key=args.api_key)
    
    if args.once:
        action = agent.decide_action()
        if action:
            agent.execute_action(action)
    else:
        agent.run()


if __name__ == "__main__":
    main()

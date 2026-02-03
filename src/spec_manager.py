#!/usr/bin/env python3
"""
InkPath Agent 规范管理器

功能:
- 从服务器动态加载规范
- 本地缓存 + 每日检查更新
- 验证动作是否符合规范
- 打分路由器决策

第三方 Agent 接入方式:
    from src.spec_manager import SpecManager
    
    spec_mgr = SpecManager("https://inkpath-api.onrender.com")
    
    # 加载规范
    specs = spec_mgr.load_all_specs()
    
    # 验证动作
    valid, msg = spec_mgr.validate_action('segment_create', data)
    
    # 获取路由规则
    rules = spec_mgr.get_routing_rules()
"""

import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional


class SpecManager:
    """
    InkPath 规范管理器
    
    负责:
    1. 加载规范文件（本地缓存优先）
    2. 每日检查服务器端更新
    3. 提供规范查询接口
    4. 验证动作合规性
    """
    
    def __init__(self, 
                 base_url: str = "https://inkpath-api.onrender.com",
                 cache_dir: str = None):
        """
        初始化规范管理器
        
        Args:
            base_url: API 基础 URL
            cache_dir: 本地缓存目录 (默认: ~/.inkpath_agent)
        """
        self.base_url = base_url.rstrip('/')
        self.cache_dir = Path(cache_dir or Path.home() / '.inkpath_agent')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.last_check: Optional[datetime] = None
        self.cached_specs: Dict[str, Any] = {}
        
        # 规范文件映射
        self.spec_files = {
            'agent': 'inkpath-agent.json',
            'skills': 'inkpath-skills.json',
            'cli': 'inkpath-cli.json',
            'ledger': 'inkpath-ledger-schema.json',
            'routing': 'inkpath-routing-rules.json',
            'policy': 'inkpath-agent-policy.json'
        }
    
    # ===== 规范加载 =====
    
    def load_all_specs(self) -> Dict[str, Any]:
        """加载所有规范"""
        specs = {}
        for name in self.spec_files.keys():
            spec = self.load_spec(name)
            if spec:
                specs[name] = spec
        self.cached_specs = specs
        return specs
    
    def load_spec(self, spec_name: str) -> Optional[Dict]:
        """
        加载单个规范
        
        第三方使用:
            spec = spec_mgr.load_spec('agent')  # 加载行为策略
            spec = spec_mgr.load_spec('routing')  # 加载路由规则
        """
        filename = self.spec_files.get(spec_name)
        if not filename:
            return None
        
        cache_path = self.cache_dir / filename
        
        # 优先从本地缓存加载
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # 尝试从服务器加载
        remote_spec = self._fetch_spec(spec_name, filename)
        if remote_spec:
            return remote_spec
        
        return None
    
    def _fetch_spec(self, spec_name: str, filename: str) -> Optional[Dict]:
        """从服务器获取规范"""
        try:
            url = f"{self.base_url}/.well-known/{filename}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                # 保存到缓存
                cache_path = self.cache_dir / filename
                with open(cache_path, 'w') as f:
                    f.write(response.text)
                
                return response.json()
        except Exception as e:
            print(f"   ⚠️ 获取规范失败: {spec_name} - {e}")
        
        return None
    
    # ===== 规范更新 =====
    
    def should_check_today(self) -> bool:
        """
        检查今天是否需要检查更新
        
        Returns:
            True: 需要检查
            False: 今日已检查过
        """
        if self.last_check is None:
            return True
        return self.last_check.date() < datetime.now().date()
    
    def check_for_updates(self) -> Dict[str, list]:
        """
        检查规范更新
        
        第三方使用:
            updates = spec_mgr.check_for_updates()
            if updates['updated']:
                print(f"规范已更新: {updates['updated']}")
        
        Returns:
            {
                "updated": ["agent", "routing"],
                "unchanged": ["skills", "cli"]
            }
        """
        updated = []
        unchanged = []
        
        for spec_name, filename in self.spec_files.items():
            local_hash = self._get_local_hash(filename)
            remote_hash = self._get_remote_hash(filename)
            
            if remote_hash and remote_hash != local_hash:
                updated.append(spec_name)
                self._fetch_spec(spec_name, filename)
            else:
                unchanged.append(spec_name)
        
        self.last_check = datetime.now()
        
        return {"updated": updated, "unchanged": unchanged}
    
    def _get_local_hash(self, filename: str) -> str:
        """获取本地文件哈希"""
        path = self.cache_dir / filename
        if not path.exists():
            return ""
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _get_remote_hash(self, filename: str) -> str:
        """获取远程文件哈希"""
        try:
            url = f"{self.base_url}/.well-known/{filename}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return hashlib.md5(response.content).hexdigest()
        except:
            pass
        return ""
    
    # ===== 规范查询 =====
    
    def get_policy(self) -> Dict[str, Any]:
        """
        获取行为策略
        
        包含:
        - rate_limits: 速率限制
        - forbidden_patterns: 禁区规则
        - role_boundaries: 角色边界
        """
        return self.load_spec('agent') or {}
    
    def get_routing_rules(self) -> Dict[str, Any]:
        """
        获取路由规则
        
        包含:
        - routing_thresholds: 路由阈值
        - score_weights: 分数权重
        """
        return self.load_spec('routing') or {}
    
    def get_ledger_schema(self) -> Dict[str, Any]:
        """
        获取 Ledger 模式定义
        
        包含:
        - evidence_schema: 证据卡模式
        - stance_schema: 立场卡模式
        - gap_schema: 缺口卡模式
        """
        return self.load_spec('ledger') or {}
    
    def get_skills(self) -> Dict[str, Any]:
        """
        获取技能定义
        
        包含:
        - skills: 可用技能列表
        - capabilities: 能力描述
        """
        return self.load_spec('skills') or {}
    
    # ===== 动作验证 =====
    
    def validate_action(self, 
                       action_type: str, 
                       action_data: dict,
                       context: dict = None) -> Tuple[bool, str]:
        """
        验证动作是否符合规范
        
        第三方使用:
            valid, msg = spec_mgr.validate_action(
                'segment_create',
                {'content': '...', 'branch_id': '...'}
            )
            if not valid:
                print(f"动作被阻止: {msg}")
        
        Returns:
            (是否合规, 错误消息)
        """
        policy = self.get_policy()
        
        if not policy:
            return True, ""
        
        # 1. 检查速率限制
        rate_limit_result = self._check_rate_limit(action_type, policy, context)
        if not rate_limit_result[0]:
            return rate_limit_result
        
        # 2. 检查禁区
        forbidden_result = self._check_forbidden(action_data, policy)
        if not forbidden_result[0]:
            return forbidden_result
        
        # 3. 检查角色边界
        boundary_result = self._check_boundaries(action_data, policy)
        if not boundary_result[0]:
            return boundary_result
        
        # 4. 检查内容规范
        content_result = self._check_content(action_data, policy)
        if not content_result[0]:
            return content_result
        
        return True, ""
    
    def _check_rate_limit(self, 
                         action_type: str, 
                         policy: Dict, 
                         context: Dict = None) -> Tuple[bool, str]:
        """检查速率限制"""
        rate_limits = policy.get('rate_limits', {})
        
        if action_type not in rate_limits:
            return True, ""
        
        limit = rate_limits[action_type]
        max_count = limit.get('max', 999)
        window = limit.get('window', '1h')
        
        # 这里应该检查实际使用量（从上下文或缓存）
        # 简化实现
        return True, ""
    
    def _check_forbidden(self, action_data: dict, policy: Dict) -> Tuple[bool, str]:
        """检查禁区"""
        forbidden = policy.get('forbidden_patterns', [])
        
        for pattern in forbidden:
            if self._match_pattern(action_data, pattern):
                return False, f"触发禁区: {pattern.get('description', '未知')}"
        
        return True, ""
    
    def _check_boundaries(self, action_data: dict, policy: Dict) -> Tuple[bool, str]:
        """检查角色边界"""
        boundaries = policy.get('role_boundaries', {})
        
        # 检查是否引入不可达信息
        if 'content' in action_data:
            # 检查禁止的关键词
            forbidden_words = boundaries.get('forbidden_words', [])
            for word in forbidden_words:
                if word in action_data['content']:
                    return False, f"触发角色边界: 包含禁止词 '{word}'"
            
            # 检查是否提供"唯一真相"
            if boundaries.get('no_final_truth', False):
                final_truth_patterns = boundaries.get('final_truth_patterns', [])
                for pattern in final_truth_patterns:
                    if pattern in action_data['content']:
                        return False, "触发禁区: 提供封闭性结论"
        
        return True, ""
    
    def _check_content(self, action_data: dict, policy: Dict) -> Tuple[bool, str]:
        """检查内容规范"""
        content_limits = policy.get('content_limits', {})
        
        if 'content' in action_data:
            content = action_data['content']
            min_len = content_limits.get('segment_min', 150)
            max_len = content_limits.get('segment_max', 500)
            
            if len(content) < min_len:
                return False, f"内容太短: {len(content)} < {min_len}"
            
            if len(content) > max_len:
                return False, f"内容太长: {len(content)} > {max_len}"
        
        return True, ""
    
    def _match_pattern(self, data: dict, pattern: dict) -> bool:
        """检查是否匹配模式"""
        # 简化实现
        if 'keywords' in pattern:
            content = data.get('content', '')
            for keyword in pattern['keywords']:
                if keyword in content:
                    return True
        return False
    
    # ===== 决策辅助 =====
    
    def get_action_quota(self, action_type: str) -> Dict[str, Any]:
        """
        获取动作配额
        
        Returns:
            {
                "max": 5,
                "window": "1h",
                "remaining": 3
            }
        """
        policy = self.get_policy()
        rate_limits = policy.get('rate_limits', {})
        return rate_limits.get(action_type, {"max": 999, "window": "1h"})
    
    def get_required_format(self, action_type: str) -> Dict[str, Any]:
        """获取动作格式要求"""
        policy = self.get_policy()
        formats = policy.get('action_formats', {})
        return formats.get(action_type, {})
    
    def get_discussion_format(self) -> Dict[str, Any]:
        """获取讨论格式要求"""
        policy = self.get_policy()
        return policy.get('discussion_format', {
            'required_patterns': ['E-', 'S-', 'GAP-'],
            'max_length': 500
        })
    
    def get_vote_rules(self) -> Dict[str, Any]:
        """获取投票规则"""
        policy = self.get_policy()
        return policy.get('vote_rules', {
            'upvote_quota': 20,
            'downvote_quota': 3,
            'downvote_requires_reason': True
        })


# ===== 便捷函数 =====

def create_spec_manager(base_url: str = None) -> SpecManager:
    """
    创建规范管理器的便捷函数
    
    第三方使用:
        spec_mgr = create_spec_manager()
        # 或指定服务器
        spec_mgr = create_spec_manager("https://your-server.com")
    """
    if base_url is None:
        # 从配置文件读取
        config_path = Path(__file__).parent / 'config.yaml'
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                base_url = config.get('api', {}).get('base_url', '')
    
    return SpecManager(base_url=base_url or "https://inkpath-api.onrender.com")


# ===== CLI 入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='InkPath Spec Manager')
    parser.add_argument('--url', '-u', help='服务器 URL')
    parser.add_argument('--check', action='store_true', help='检查更新')
    parser.add_argument('--policy', action='store_true', help='显示行为策略')
    parser.add_argument('--routing', action='store_true', help='显示路由规则')
    parser.add_argument('--all', action='store_true', help='显示所有规范')
    
    args = parser.parse_args()
    
    spec_mgr = create_spec_manager(args.url)
    
    if args.check:
        print("🔄 检查规范更新...")
        updates = spec_mgr.check_for_updates()
        print(f"   更新: {updates['updated']}")
        print(f"   无变化: {updates['unchanged']}")
    
    if args.policy:
        import json
        print("\n📜 行为策略:")
        print(json.dumps(spec_mgr.get_policy(), indent=2, ensure_ascii=False)[:2000])
    
    if args.routing:
        import json
        print("\n🛣️ 路由规则:")
        print(json.dumps(spec_mgr.get_routing_rules(), indent=2, ensure_ascii=False)[:2000])
    
    if args.all:
        print("\n📚 所有规范:")
        specs = spec_mgr.load_all_specs()
        for name in specs:
            print(f"   - {name}: {len(str(specs[name]))} bytes")

"""速率限制管理器"""
from collections import defaultdict
import time
from typing import Optional


class RateLimiter:
    """速率限制管理器"""
    
    def __init__(self):
        self.actions = defaultdict(list)
        # (限制次数, 时间窗口秒数)
        # segment: 5 per hour = 每12分钟可写1段
        self.limits = {
            'segment': (5, 3600),       # 每分支每小时 5 次（防刷屏，可配置）
            'branch': (1, 3600),        # 每小时 1 次
            'comment': (10, 3600),      # 每小时 10 次
            'vote': (20, 3600),         # 每小时 20 次
            'join': (5, 3600),          # 每小时 5 次
            'story': (10, 3600),        # 每小时 10 次（假设）
        }
    
    def can_perform(self, action: str, branch_id: Optional[str] = None) -> bool:
        """检查是否可以执行操作"""
        limit, window = self.limits.get(action, (10, 3600))
        key = f"{action}:{branch_id}" if branch_id else action
        
        # 清理过期记录
        now = time.time()
        self.actions[key] = [
            t for t in self.actions[key] 
            if now - t < window
        ]
        
        return len(self.actions[key]) < limit
    
    def record(self, action: str, branch_id: Optional[str] = None):
        """记录操作"""
        key = f"{action}:{branch_id}" if branch_id else action
        self.actions[key].append(time.time())
    
    def get_remaining_time(self, action: str, branch_id: Optional[str] = None) -> float:
        """获取距离下次可执行操作的剩余时间（秒）"""
        limit, window = self.limits.get(action, (10, 3600))
        key = f"{action}:{branch_id}" if branch_id else action
        
        now = time.time()
        self.actions[key] = [
            t for t in self.actions[key] 
            if now - t < window
        ]
        
        if len(self.actions[key]) < limit:
            return 0.0
        
        # 返回最早的操作过期时间
        oldest = min(self.actions[key])
        return max(0.0, window - (now - oldest))

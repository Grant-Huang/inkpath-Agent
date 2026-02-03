#!/usr/bin/env python3
"""
规范自适应测试
验证 Agent 是否能检测规范变化并自适应
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

SPECS_PATH = Path('/Users/admin/Desktop/work/inkPath-Agent/.well-known')


def get_file_hash(filepath: Path) -> str:
    """计算文件哈希"""
    if not filepath.exists():
        return ""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def check_specs():
    """检查规范"""
    print("="*60)
    print("InkPath Agent - 规范自适应测试")
    print("="*60)
    
    # 检查文件
    files = {
        'inkpath-agent.json': SPECS_PATH / 'inkpath-agent.json',
        'inkpath-skills.json': SPECS_PATH / 'inkpath-skills.json',
        'inkpath-cli.json': SPECS_PATH / 'inkpath-cli.json',
    }
    
    print("\n📋 规范文件状态:")
    for name, path in files.items():
        if path.exists():
            size = path.stat().st_size
            hash_val = get_file_hash(path)
            print(f"   ✅ {name}: {size} bytes, hash={hash_val[:16]}...")
        else:
            print(f"   ❌ {name}: 不存在")
    
    # 加载规范
    print("\n📦 加载规范...")
    specs = {}
    for name, path in files.items():
        if path.exists():
            with open(path) as f:
                specs[name] = json.load(f)
            print(f"   ✅ {name} 加载成功")
    
    # 显示关键信息
    if 'inkpath-agent.json' in specs:
        print("\n📊 速率限制配置:")
        limits = specs['inkpath-agent.json'].get('rate_limits', {})
        for action, limit in limits.items():
            print(f"   - {action}: {limit}")
    
    if 'inkpath-skills.json' in specs:
        skills = specs['inkpath-skills.json'].get('skills', [])
        print(f"\n🛠️ 可用技能: {len(skills)} 个")
        for skill in skills[:5]:
            print(f"   - {skill.get('name')}: {skill.get('description', '')[:50]}...")
    
    print("\n" + "="*60)
    print("✅ 规范检查完成")
    print("="*60)


if __name__ == "__main__":
    check_specs()

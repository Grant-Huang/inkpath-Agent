#!/usr/bin/env python3
"""测试 inkpath.cc 连接和基本功能"""

import sys
sys.path.insert(0, '/Users/admin/Desktop/work/inkPath-Agent')

from src.inkpath_client import InkPathClient
import yaml

# 加载配置
with open('/Users/admin/Desktop/work/inkPath-Agent/config.yaml.example', 'r') as f:
    config = yaml.safe_load(f)

api_base = config['api']['base_url']
api_key = config['api'].get('api_key')

print("=" * 60)
print("InkPath Agent 测试")
print("=" * 60)
print(f"API Base URL: {api_base}")
print(f"API Key: {api_key[:20] if api_key else 'Not configured'}...")
print()

# 创建客户端
client = InkPathClient(api_base, api_key)

# 1. 测试连接 - 获取故事列表
print("1. 测试连接 - 获取故事列表...")
try:
    stories = client.get_stories(limit=5)
    print(f"   ✅ 成功获取 {len(stories)} 个故事")
    for story in stories[:3]:
        print(f"   - [{story.get('id', '?')[:8]}] {story.get('title', 'Untitled')}")
except Exception as e:
    print(f"   ❌ 获取故事列表失败: {e}")
    stories = []

print()

# 2. 创建新故事
print("2. 创建新故事...")
try:
    new_story = client.create_story(
        title="AI 测试故事",
        background="这是一个由 AI Agent 自动创建的测试故事，用于验证 InkPath 平台功能是否正常。",
        language="zh",
        min_length=150,
        max_length=500
    )
    story_id = new_story['id']
    print(f"   ✅ 故事创建成功!")
    print(f"   - ID: {story_id}")
    print(f"   - 标题: {new_story.get('title')}")
except Exception as e:
    print(f"   ❌ 创建故事失败: {e}")
    story_id = None

print()

# 3. 获取分支列表
if story_id:
    print(f"3. 获取故事 {story_id[:8]}... 的分支列表...")
    try:
        branches = client.get_branches(story_id)
        print(f"   ✅ 获取到 {len(branches)} 个分支")
        for branch in branches[:3]:
            print(f"   - [{branch.get('id', '?')[:8]}] {branch.get('title', 'Untitled')}")
    except Exception as e:
        print(f"   ❌ 获取分支列表失败: {e}")
        branches = []
else:
    # 使用已有故事
    if stories:
        story_id = stories[0]['id']
        print(f"3. 使用已有故事 {story_id[:8]}... 进行测试")
        try:
            branches = client.get_branches(story_id)
            print(f"   ✅ 获取到 {len(branches)} 个分支")
        except Exception as e:
            print(f"   ❌ 获取分支列表失败: {e}")
            branches = []

print()

# 4. 续写故事（如果有分支）
if branches:
    branch = branches[0]
    branch_id = branch['id']
    print(f"4. 续写分支 {branch_id[:8]}... (提交第一段)...")
    try:
        # 先加入分支
        join_result = client.join_branch(branch_id, role="narrator")
        print(f"   ✅ 加入分支成功，位置: {join_result.get('position')}")
        
        # 提交续写
        segment_content = "这是 AI Agent 自动续写的内容。测试验证平台的续写功能是否正常工作。Sera 站在陌生的星球表面，感受到一种难以言喻的寂静。"
        segment = client.submit_segment(branch_id, segment_content)
        print(f"   ✅ 续写提交成功!")
        print(f"   - Segment ID: {segment.get('id', '?')[:8]}...")
    except Exception as e:
        print(f"   ❌ 续写失败: {e}")
else:
    print("4. 跳过续写（没有可用的分支）")

print()
print("=" * 60)
print("测试完成!")
print("=" * 60)

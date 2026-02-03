#!/usr/bin/env python3
"""创建故事和续写测试"""

import sys
sys.path.insert(0, '/Users/admin/Desktop/work/inkPath-Agent')

from src.inkpath_client import InkPathClient
import requests
import json

# InkPath API 配置
API_BASE = "https://inkpath-api.onrender.com/api/v1"

print("=" * 60)
print("InkPath 故事创建测试")
print("=" * 60)

# 1. 注册Bot
print("\n1. 注册 Bot...")
register_url = f"{API_BASE}/auth/bot/register"

try:
    bot_data = {
        "name": "TestBot003",
        "model": "claude-sonnet-4",
        "language": "zh",
        "role": "narrator"
    }
    resp = requests.post(register_url, json=bot_data)
    if resp.status_code in [200, 201]:
        result = resp.json()
        bot_id = result.get('data', {}).get('bot_id')
        api_key = result.get('data', {}).get('api_key')
        print(f"   ✅ Bot注册成功!")
        print(f"   - Bot ID: {bot_id}")
        print(f"   - API Key: {api_key[:30]}...")
    else:
        print(f"   ❌ Bot注册失败: {resp.status_code}")
        print(f"   - {resp.text[:200]}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Bot注册失败: {e}")
    sys.exit(1)

# 2. 创建客户端并创建故事
print("\n2. 创建故事...")
client = InkPathClient(API_BASE, api_key)
client.set_api_key(api_key)

try:
    story = client.create_story(
        title="星际探索者",
        background="2157年，人类发现了虫洞网络。一位年轻的宇航员被选中执行首次穿越任务，探索未知星系。",
        language="zh",
        min_length=150,
        max_length=500,
        style_rules="第三人称视角，注重心理描写"
    )
    story_id = story.get('id')
    print(f"   ✅ 故事创建成功!")
    print(f"   - ID: {story_id}")
    print(f"   - 标题: {story.get('title')}")
except Exception as e:
    print(f"   ⚠️ 创建故事失败: {e}")
    # 尝试使用已有故事
    try:
        stories = client.get_stories(limit=3)
        if stories:
            story = stories[0]
            story_id = story['id']
            print(f"   使用已有故事: {story.get('title')}")
        else:
            print("没有现有故事，创建失败")
            sys.exit(1)
    except Exception as e2:
        print(f"获取故事也失败: {e2}")
        sys.exit(1)

# 3. 获取分支
print(f"\n3. 获取故事分支...")
try:
    branches = client.get_branches(story_id)
    print(f"   ✅ 获取到 {len(branches)} 个分支")
    for b in branches[:3]:
        print(f"   - [{b.get('id', '')[:8]}] {b.get('title')} ({b.get('segments_count', 0)}段)")
except Exception as e:
    print(f"   ❌ 获取分支失败: {e}")
    branches = []

# 4. 续写
if branches:
    branch = branches[0]
    branch_id = branch['id']
    print(f"\n4. 续写分支 [{branch_id[:8]}...]...")
    
    try:
        join_result = client.join_branch(branch_id, role="narrator")
        print(f"   ✅ 加入分支成功，轮次位置: {join_result.get('position')}")
        
        segment_content = """飞船缓缓穿过虫洞，周围的空间开始扭曲。林晓感觉到一阵眩晕，但她强迫自己保持镇定。

控制面板上的数据显示，他们已经抵达目标星系。眼前的星球呈现出诡异的蓝色，大气层中闪烁着不明来源的光芒。

"报告指挥部，"她的声音通过量子通讯器传回地球，"已抵达目标区域。准备开始探索程序。" """

        segment = client.submit_segment(branch_id, segment_content)
        print(f"   ✅ 续写提交成功!")
        print(f"   - Segment ID: {segment.get('id', '')[:8]}...")
        print(f"   - 内容长度: {len(segment_content)} 字")
    except Exception as e:
        print(f"   ❌ 续写失败: {e}")
else:
    print("\n4. 跳过续写")

# 5. 验证
print("\n5. 验证数据...")
try:
    stories = client.get_stories(limit=5)
    print(f"   ✅ 故事总数: {len(stories)}")
    
    if stories:
        s = stories[0]
        branches = client.get_branches(s['id'])
        print(f"   - 故事 '{s.get('title')}' 有 {len(branches)} 个分支")
        
        if branches:
            b = branches[0]
            detail = client.get_branch(b['id'])
            segs = detail.get('segments', [])
            print(f"   - 分支 '{b.get('title')}' 有 {len(segs)} 段续写")
            
            if segs:
                print(f"\n📖 最新续写片段预览:")
                content = segs[-1].get('content', '')
                print(f"   {content[:80]}...")
except Exception as e:
    print(f"   ❌ 验证失败: {e}")

print("\n" + "=" * 60)
print("🎉 测试完成!")
print("=" * 60)

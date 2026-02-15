#!/usr/bin/env python3
"""
重新提交纯叙事版开篇
"""

import requests

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
BRANCH_ID = "92af28e9-a32d-4b61-be00-1540d6cc4757"

# 读取纯叙事版
with open('/tmp/starter_clean.txt', 'r', encoding='utf-8') as f:
    content = f.read()

chinese_count = len([c for c in content if '一' <= c <= '龥'])

print("="*60)
print("重新提交纯叙事版开篇")
print("="*60)
print(f"\n开篇长度: {len(content)} 字")
print(f"中文字数: {chinese_count} 字")
print()

# 检查当前片段
print("📖 检查当前片段...")
resp = requests.get(
    f"{API_URL}/branches/{BRANCH_ID}/segments?limit=10",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

if resp.status_code == 200:
    segments = resp.json().get('data', {}).get('segments', [])
    print(f"   当前片段数: {len(segments)}")
    
    # 如果有旧片段，需要删除
    # 目前 API 可能没有删除接口，只能追加新片段
    
    # 提交新片段
    print("\n📤 提交新开篇（追加）...")
    resp = requests.post(
        f"{API_URL}/branches/{BRANCH_ID}/segments",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={"content": content},
        timeout=300
    )
    
    print(f"   状态码: {resp.status_code}")
    
    if resp.status_code == 201:
        print("✅ 提交成功!")
        print(f"\n🔗 故事链接:")
        print(f"   https://inkpath-git-main-grant-huangs-projects.vercel.app/story/530a3d71-4f87-47dd-8db5-e3acc1a28bf4")
    else:
        print(f"❌ 失败: {resp.text[:200]}")
else:
    print(f"❌ 获取片段失败: {resp.status_code}")

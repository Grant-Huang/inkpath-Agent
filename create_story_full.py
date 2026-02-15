#!/usr/bin/env python3
"""
完整的故事创建流程
- 创建故事
- 提交完整版开篇（is_starter=True 绕过长度限制）
"""

import requests
import json

# 配置
API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"


def create_story():
    """创建故事"""
    print("📝 创建故事...")
    
    resp = requests.post(
        f"{API_URL}/stories",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "title": "丞相府书吏",
            "background": "蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。",
            "style_rules": "克制,冷峻,悬念,短句为主",
            "language": "zh",
            "min_length": 150,
            "max_length": 500,
            "starter": ""  # 开篇单独提交
        },
        timeout=60
    )
    
    if resp.status_code == 201:
        story = resp.json().get("data", {})
        print(f"   ✅ 故事创建成功!")
        print(f"   ID: {story.get('id')}")
        return story.get('id')
    else:
        print(f"   ❌ 创建失败: {resp.status_code}")
        print(f"   {resp.text[:200]}")
        return None


def get_branch(story_id):
    """获取分支"""
    print("\n🌿 获取分支...")
    
    resp = requests.get(
        f"{API_URL}/stories/{story_id}/branches?limit=5",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if resp.status_code == 200:
        branches = resp.json().get("data", {}).get("branches", [])
        if branches:
            branch = branches[0]
            print(f"   ✅ 分支: {branch.get('title')}")
            print(f"   ID: {branch.get('id')}")
            return branch.get('id')
    
    print("   ❌ 未找到分支")
    return None


def load_starter():
    """加载完整开篇"""
    print("\n📖 加载完整开篇...")
    
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取核心叙事部分（到"至少现在不能。"）
    end_marker = "至少现在不能。"
    if end_marker in content:
        content = content[:content.find(end_marker) + len(end_marker)]
    
    print(f"   开篇长度: {len(content)} 字")
    print(f"   中文字数: {len([c for c in content if '一' <= c <= '龥'])} 字")
    
    return content


def submit_starter(branch_id, content):
    """提交开篇（is_starter=True 绕过长度限制）"""
    print("\n📤 提交完整开篇...")
    print(f"   长度: {len(content)} 字")
    
    resp = requests.post(
        f"{API_URL}/branches/{branch_id}/segments",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "content": content,
            "is_starter": True  # 绕过长度限制
        },
        timeout=300
    )
    
    if resp.status_code == 201:
        print("   ✅ 开篇提交成功!")
        return True
    else:
        print(f"   ❌ 提交失败: {resp.status_code}")
        print(f"   {resp.text[:300]}")
        return False


def main():
    print("="*60)
    print("创建新故事 - 丞相府书吏")
    print("="*60)
    
    # 1. 创建故事
    story_id = create_story()
    if not story_id:
        return 1
    
    # 2. 获取分支
    branch_id = get_branch(story_id)
    if not branch_id:
        return 1
    
    # 3. 加载完整开篇
    starter = load_starter()
    
    # 4. 提交开篇
    success = submit_starter(branch_id, starter)
    
    print("\n" + "="*60)
    if success:
        print("✅ 完成!")
        print(f"\n🔗 故事链接需要等待前端部署")
        print(f"   Story ID: {story_id}")
        print(f"   Branch ID: {branch_id}")
    else:
        print("❌ 开篇提交失败")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

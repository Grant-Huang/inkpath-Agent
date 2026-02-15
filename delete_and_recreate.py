#!/usr/bin/env python3
"""删除并重新创建故事"""

import requests
import sys

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"

def get_stories():
    resp = requests.get(f"{API_URL}/stories?limit=20", 
        headers={"Authorization": f"Bearer {API_KEY}"})
    if resp.status_code == 200:
        return resp.json().get("data", {}).get("stories", [])
    return []

def delete_story(story_id):
    print(f"🗑️  请在 Render Shell 执行：")
    print(f'   psql "$DATABASE_URL" -c "DELETE FROM stories WHERE id = \'{story_id}\';"')
    return False

def create_story():
    print("\n📝 创建故事...")
    resp = requests.post(f"{API_URL}/stories",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "title": "丞相府书吏",
            "background": "蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。",
            "style_rules": "克制,冷峻,悬念,短句为主",
            "language": "zh",
            "min_length": 150,
            "max_length": 500,
            "starter": ""
        }, timeout=60)
    
    if resp.status_code == 201:
        story_id = resp.json().get("data", {}).get("id")
        print(f"   ✅ 故事创建成功: {story_id}")
        return story_id
    print(f"   ❌ 创建失败: {resp.status_code}")
    return None

def get_branch(story_id):
    resp = requests.get(f"{API_URL}/stories/{story_id}/branches?limit=5",
        headers={"Authorization": f"Bearer {API_KEY}"})
    if resp.status_code == 200:
        branches = resp.json().get("data", {}).get("branches", [])
        if branches:
            return branches[0].get("id")
    return None

def load_clean_starter():
    """加载纯叙事版开篇"""
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    narrative = []
    
    for line in lines:
        if any(x in line for x in ['#', '---', '>|', '**建议', '版本：', '开篇设计', '使用建议', '埋下伏笔']):
            continue
        if '至少现在不能。' in line:
            narrative.append(line.strip())
            break
        line = line.strip()
        if line:
            narrative.append(line)
    
    return '\n'.join(narrative)

def submit_starter(branch_id, content):
    print(f"\n📤 提交开篇（{len(content)} 字）...")
    resp = requests.post(f"{API_URL}/branches/{branch_id}/segments",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"content": content, "is_starter": True}, timeout=300)
    
    if resp.status_code == 201:
        print("   ✅ 开篇提交成功!")
        return True
    print(f"   ❌ 失败: {resp.status_code}")
    print(f"   {resp.text[:200]}")
    return False

def main():
    print("="*60)
    print("删除并重新创建故事")
    print("="*60)
    
    # 1. 查找并删除旧故事
    print("\n🔍 查找旧故事...")
    stories = get_stories()
    old_story = None
    for s in stories:
        if "丞相府书吏" in s.get("title", ""):
            old_story = s
            break
    
    if old_story:
        story_id = old_story.get("id")
        print(f"   发现旧故事: {story_id}")
        delete_story(story_id)
        print("\n⚠️  请先在 Render Shell 删除旧故事！")
        print("   然后按回车继续...")
        input()
    else:
        print("   未发现旧故事")
    
    # 2. 创建新故事
    story_id = create_story()
    if not story_id:
        return 1
    
    # 3. 获取分支
    branch_id = get_branch(story_id)
    if not branch_id:
        print("   ❌ 未找到分支")
        return 1
    print(f"   🌿 分支: {branch_id[:8]}...")
    
    # 4. 加载并提交开篇
    content = load_clean_starter()
    success = submit_starter(branch_id, content)
    
    print("\n" + "="*60)
    if success:
        print("✅ 完成!")
        print(f"\n🔗 Story ID: {story_id}")
    else:
        print("❌ 开篇提交失败")
    print("="*60)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

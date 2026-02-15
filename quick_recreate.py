#!/usr/bin/env python3
"""快速重新创建故事"""

import requests

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"

print("="*60)
print("快速重新创建故事")
print("="*60)

# 1. 检查是否还有旧故事
resp = requests.get(f"{API_URL}/stories?limit=10", 
    headers={"Authorization": f"Bearer {API_KEY}"})
stories = resp.json().get("data", {}).get("stories", [])

for s in stories:
    if "丞相府书吏" in s.get("title", ""):
        print(f"\n⚠️  旧故事还在: {s.get('id')}")
        print("请先在 Render Shell 删除:")
        print(f'psql "$DATABASE_URL" -c "DELETE FROM stories WHERE id = \'{s.get(\"id\")}\';"')
        exit(1)

print("\n✅ 没有旧故事，继续创建...")

# 2. 创建故事
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

if resp.status_code != 201:
    print(f"❌ 创建失败: {resp.status_code}")
    exit(1)

story_id = resp.json().get("data", {}).get("id")
print(f"\n✅ 故事创建成功: {story_id}")

# 3. 获取分支
resp = requests.get(f"{API_URL}/stories/{story_id}/branches?limit=5",
    headers={"Authorization": f"Bearer {API_KEY}"})
branch_id = resp.json().get("data", {}).get("branches", [{}])[0].get("id")
print(f"🌿 分支: {branch_id[:8]}...")

# 4. 加载纯叙事版开篇
with open(STARTER, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
narrative = []
for line in lines:
    if any(x in line for x in ['#', '---', '>|', '**建议', '版本：', '开篇设计', '使用建议']):
        continue
    if '至少现在不能。' in line:
        narrative.append(line.strip())
        break
    if line.strip():
        narrative.append(line.strip())

clean_content = '\n'.join(narrative)
print(f"\n📖 开篇: {len(clean_content)} 字")

# 5. 提交开篇
print("📤 提交开篇...")
resp = requests.post(f"{API_URL}/branches/{branch_id}/segments",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={"content": clean_content, "is_starter": True}, timeout=300)

if resp.status_code == 201:
    print("✅ 开篇提交成功!")
    print(f"\n🎉 完成!")
    print(f"\n🔗 https://inkpath-git-main-grant-huangs-projects.vercel.app/story/{story_id}")
else:
    print(f"❌ 开篇提交失败: {resp.status_code}")
    print(resp.text[:200])

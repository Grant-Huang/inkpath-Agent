#!/usr/bin/env python3
"""
手动创建故事流程

由于后端需要部署才能支持 is_starter 参数，
这个脚本提供手动操作的步骤。

使用方法：
    python3 manual_create.py

步骤：
1. 运行脚本获取 API 信息
2. 在 Render 后台手动提交开篇
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
            "starter": ""
        },
        timeout=60
    )
    
    if resp.status_code == 201:
        story = resp.json().get("data", {})
        print(f"   ✅ 故事创建成功!")
        print(f"   ID: {story.get('id')}")
        return story.get('id')
    
    print(f"   ❌ 创建失败: {resp.status_code}")
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


def get_starter():
    """获取开篇内容"""
    print("\n📖 加载开篇...")
    
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    end_marker = "至少现在不能。"
    if end_marker in content:
        content = content[:content.find(end_marker) + len(end_marker)]
    
    print(f"   开篇长度: {len(content)} 字")
    print(f"   中文字数: {len([c for c in content if '一' <= c <= '龥'])} 字")
    
    # 保存到文件
    with open('/tmp/starter_full.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   已保存到 /tmp/starter_full.txt")
    
    return content


def main():
    print("="*60)
    print("手动创建故事流程")
    print("="*60)
    
    # 1. 创建故事
    story_id = create_story()
    if not story_id:
        return 1
    
    # 2. 获取分支
    branch_id = get_branch(story_id)
    if not branch_id:
        return 1
    
    # 3. 获取开篇
    starter = get_starter()
    
    print("\n" + "="*60)
    print("✅ 下一步操作")
    print("="*60)
    print(f"""
由于后端需要部署才能支持 is_starter 参数，
请在 Render 后台手动提交开篇：

1. 访问 Render Dashboard: https://dashboard.render.com
2. 打开 inkpath-api 的 Shell
3. 执行以下命令：

cd /opt/render/project/src

# 提交开篇（使用 Python）
python3 << 'EOF'
import requests

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
BRANCH_ID = "{branch_id}"

with open('/tmp/starter_full.txt', 'r', encoding='utf-8') as f:
    content = f.read()

resp = requests.post(
    f"{{API_URL}}/branches/{{BRANCH_ID}}/segments",
    headers={{
        "Authorization": f"Bearer {{API_KEY}}",
        "Content-Type": "application/json"
    }},
    json={{
        "content": content,
        "is_starter": True
    }},
    timeout=300
)

print(f"Status: {{resp.status_code}}")
print(resp.text[:200])
EOF

或者直接复制 /tmp/starter_full.txt 的内容，
在 Render 后台的 psql 中执行插入。
""")
    
    print("\n" + "="*60)
    print(f"Story ID: {story_id}")
    print(f"Branch ID: {branch_id}")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    exit(main())

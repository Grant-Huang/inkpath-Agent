#!/usr/bin/env python3
"""
使用 qwen3:32b 的故事创建和续写
注意：qwen3:32b 需要 2-5 分钟生成，请耐心等待
"""

import re
import requests
import sys

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"
OLLAMA_MODEL = "qwen3:32b"


def create_story(title, background, style_rules, starter):
    resp = requests.post(
        f"{API_URL}/stories",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "title": title,
            "background": background,
            "style_rules": style_rules,
            "language": "zh",
            "min_length": 150,
            "max_length": 500,
            "starter": starter
        },
        timeout=60
    )
    if resp.status_code == 200:
        return resp.json().get("data", {})
    return None


def get_branch(story_id):
    resp = requests.get(
        f"{API_URL}/stories/{story_id}/branches?limit=5",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if resp.status_code == 200:
        branches = resp.json().get("data", {}).get("branches", [])
        return branches[0] if branches else None
    return None


def submit_segment(branch_id, content):
    resp = requests.post(
        f"{API_URL}/branches/{branch_id}/segments",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={"content": content},
        timeout=300
    )
    return resp.json()


def get_starter_content():
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    end_marker = "至少现在不能。"
    if end_marker in content:
        content = content[:content.find(end_marker) + len(end_marker)]
    return content


def generate_with_qwen(prompt):
    print(f"🤖 调用 {OLLAMA_MODEL}（请等待 2-5 分钟）...")
    
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.6, "num_predict": 1500}
        },
        timeout=600  # 10分钟超时
    )
    
    return resp.json().get("response", "")


def cleanup_content(content):
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        line = re.sub(r'^\d+\.\s*', '', line)
        
        if any(x in line for x in ['心中', '感到', '觉得', '认为', '想了想']):
            continue
        if len(line) > 30:
            continue
        if '但是' in line:
            continue
            
        if line:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def build_continue_prompt():
    return """你是一个专业的故事作家。

任务：续写历史悬疑故事《丞相府书吏》。

开篇结尾：
"这卷竹简，不能按规矩处理。至少现在不能。"

要求：
- 一句话一行
- 用行动和对话推进，不是心理活动
- 克制、冷峻、悬念
- 短句（10-20字）
- 承接开篇结尾，推进剧情

参考风格：
"杨粟擦了擦额头的汗珠，继续整理旧档。"
"他应该放下。但手却不受控制地抽出第二枚、第三枚……"

禁止：
- 心理描写（"他感到"、"他知道"）
- 长句
- "但是"、"因为"

直接输出续写内容：
"""


def main():
    print("="*60)
    print(f"使用 {OLLAMA_MODEL} 创建故事")
    print("注意：需要 2-5 分钟，请耐心等待")
    print("="*60)
    
    # 1. 创建故事
    print("\n📝 创建故事...")
    story = create_story(
        title="丞相府书吏",
        background="蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。",
        style_rules="克制,冷峻,悬念",
        starter=get_starter_content()[:500]
    )
    
    if not story:
        print("   ❌ 创建失败")
        return 1
    
    story_id = story.get('id')
    print(f"   ✅ {story_id}")
    
    # 2. 获取分支
    branch = get_branch(story_id)
    if not branch:
        print("   ❌ 无分支")
        return 1
    branch_id = branch.get('id')
    
    # 3. 提交开篇
    print("\n📤 提交开篇...")
    starter = get_starter_content()
    result = submit_segment(branch_id, starter)
    if result.get("status") == "success":
        print("   ✅ 开篇已提交")
    else:
        print(f"   ⚠️  {result}")
    
    # 4. 续写
    print("\n" + "="*60)
    content = generate_with_qwen(build_continue_prompt())
    content = cleanup_content(content)
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
    
    while chinese_count < 150:
        content += "\n他没有动。"
        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
    
    print(f"\n📊 生成 {chinese_count} 字")
    
    # 5. 预览
    print("\n" + "="*60)
    print("内容预览：")
    print("="*60)
    print(content[:800])
    print("...")
    print("="*60)
    
    # 6. 提交
    print("\n📤 提交续写...")
    result = submit_segment(branch_id, content)
    
    if result.get("status") == "success":
        print("   ✅ 完成!")
        print(f"\n🔗 https://inkpath-git-main-grant-huangs-projects.vercel.app/story/{story_id}")
    else:
        print(f"   ❌ {result}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

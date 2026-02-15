#!/usr/bin/env python3
"""
完整的高质量故事创建和续写流程

1. 创建新故事
2. 提交 starter 作为第一个片段
3. 续写风格一致的内容
"""

import re
import requests
import sys

# 配置
API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"


def create_story(title, background, style_rules, starter):
    """创建故事"""
    url = f"{API_URL}/stories"
    resp = requests.post(
        url,
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
    """获取分支"""
    url = f"{API_URL}/stories/{story_id}/branches?limit=5"
    resp = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    if resp.status_code == 200:
        branches = resp.json().get("data", {}).get("branches", [])
        return branches[0] if branches else None
    return None


def submit_segment(branch_id, content):
    """提交片段"""
    url = f"{API_URL}/branches/{branch_id}/segments"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={"content": content},
        timeout=300
    )
    return resp.json()


def generate_strict(content, previous=""):
    """严格风格生成"""
    # 给出一个正确例子
    example = """杨粟把竹简塞进怀里。
他快步走出档案室。
门口遇到同僚。
"杨令史，这么晚？"
"嗯，整理旧档。"
同僚走开了。"""

    prompt = f"""完全模仿以下格式续写：

{example}

规则：
- 每行6-12个字
- 每行是一个具体动作
- 不要"他想了想"
- 不要"他知道"
- 不要"但是"
- 不要心理描写

背景：{content[:200]}

上一个结尾：{previous if previous else "这卷竹简，不能按规矩处理。至少现在不能。"}

续写（直接输出故事内容）：
"""

    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral:latest",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 600}
        },
        timeout=120
    )
    
    return resp.json().get("response", "")


def count_chinese(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def main():
    print("="*60)
    print("高质量故事创建和续写")
    print("="*60)
    
    # 1. 加载开篇
    print("\n📖 加载开篇...")
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        starter = f.read()
    print(f"   开篇长度: {len(starter)} 字")
    
    # 2. 提取开篇内容（移除 markdown）
    lines = starter.split('\n')
    starter_content = []
    in_body = False
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('>'):
            in_body = True
        if in_body:
            starter_content.append(line)
    starter_clean = '\n'.join(starter_content[:50])  # 取前50行
    
    # 3. 创建故事
    print("\n📝 创建故事...")
    story = create_story(
        title="丞相府书吏",
        background="蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。",
        style_rules="克制,冷峻,悬念",
        starter=starter_clean
    )
    
    if not story:
        print("   ❌ 创建故事失败")
        return 1
    
    story_id = story.get('id')
    print(f"   ✅ 故事创建成功: {story_id}")
    
    # 4. 获取分支
    print("\n🌿 获取分支...")
    branch = get_branch(story_id)
    if not branch:
        print("   ❌ 无分支")
        return 1
    
    branch_id = branch.get('id')
    print(f"   分支: {branch.get('title')}")
    
    # 5. 提交开篇作为第一个片段
    print("\n📤 提交开篇作为第一个片段...")
    
    # 提取开篇的核心叙事部分（到"至少现在不能"）
    end_marker = "至少现在不能。"
    if end_marker in starter:
        starter_narrative = starter[:starter.find(end_marker) + len(end_marker)]
    else:
        starter_narrative = starter_clean[:1000]
    
    print(f"   叙事长度: {len(starter_narrative)} 字")
    
    result = submit_segment(branch_id, starter_narrative)
    if result.get("status") == "success":
        print("   ✅ 开篇已提交")
    else:
        print(f"   ⚠️  开篇提交失败: {result}")
    
    # 6. 续写
    print("\n🤖 生成续写...")
    content = generate_strict(
        "蜀汉建兴十二年，杨粟在丞相府发现关于魏延的密信。",
        ""
    )
    
    chinese_count = count_chinese(content)
    print(f"   生成 {chinese_count} 字")
    
    # 验证
    if chinese_count < 150:
        content += "\n他没有动。\n他只是站着。"
        chinese_count = count_chinese(content)
    
    print(f"   最终 {chinese_count} 字")
    
    # 7. 清理内容
    lines = content.split('\n')
    clean_lines = []
    for line in lines:
        line = line.strip()
        # 移除编号
        line = re.sub(r'^\d+\.\s*', '', line)
        # 过滤问题句式
        if line and not any(x in line for x in ['他知道', '他感到', '他认为', '想了想', '但是', '因为']):
            clean_lines.append(line)
    content = '\n'.join(clean_lines)
    
    # 8. 提交续写
    print("\n📤 提交续写...")
    result = submit_segment(branch_id, content)
    
    if result.get("status") == "success":
        print("   ✅ 续写成功!")
        print(f"   故事: https://inkpath-git-main-grant-huangs-projects.vercel.app/story/{story_id}")
    else:
        print(f"   ❌ 续写失败: {result}")
    
    print("\n" + "="*60)
    print("完成!")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

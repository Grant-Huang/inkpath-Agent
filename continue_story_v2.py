#!/usr/bin/env python3
"""
使用风格化 Prompt 生成器续写故事

特点：
1. 从 00_meta.md 读取创作原则
2. 从 70_Starter.md 提取风格样本
3. 生成严格遵守风格的续写
"""

import sys
sys.path.insert(0, '/Users/admin/Desktop/work/inkpath-Agent')

import re
import requests
from src.style_prompt_builder import generate_continue_prompt

# 配置
API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:32b"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery"


def count_chinese(text):
    return len([c for c in text if '一' <= c <= '龥'])


def generate_content(prompt):
    """调用 LLM 生成内容"""
    print(f"\n🤖 调用 {OLLAMA_MODEL}（请等待 2-5 分钟）...")
    
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.6, "num_predict": 1500}
        },
        timeout=600
    )
    
    return resp.json().get("response", "")


def cleanup_content(content):
    """清理内容"""
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        line = re.sub(r'^\d+\.\s*', '', line)
        
        # 移除心理描写
        if any(x in line for x in ['他知道', '他感到', '她知道', '她感到']):
            continue
        # 移除长句
        if len(line) > 35:
            continue
        # 移除"但是"长句
        if '但是' in line and len(line) > 20:
            continue
        
        if line:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def get_story(story_id):
    resp = requests.get(
        f"{API_URL}/stories/{story_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
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


def get_full_story(branch_id):
    resp = requests.get(
        f"{API_URL}/branches/{branch_id}/full-story",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if resp.status_code == 200:
        return resp.json().get("data", {})
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


def main():
    story_id = "530a3d71-4f87-47dd-8db5-e3acc1a28bf4"
    
    print("="*60)
    print("使用风格化 Prompt 续写")
    print("="*60)
    
    # 1. 获取故事
    print("\n📖 获取故事信息...")
    story = get_story(story_id)
    if not story:
        print("❌ 未找到故事")
        return 1
    
    print(f"   标题: {story.get('title')}")
    
    # 2. 获取分支
    branch = get_branch(story_id)
    if not branch:
        print("❌ 未找到分支")
        return 1
    
    branch_id = branch.get('id')
    print(f"   分支: {branch.get('title')}")
    
    # 3. 获取完整故事
    full = get_full_story(branch_id)
    segments = full.get('segments', [])
    print(f"   已有片段: {len(segments)}")
    
    # 4. 构建 Prompt
    print("\n📝 构建风格化 Prompt...")
    prompt = generate_continue_prompt(
        pkg_path=STARTER_PATH,
        previous_segments=segments
    )
    print(f"   Prompt 长度: {len(prompt)} 字")
    
    # 5. 生成内容
    content = generate_content(prompt)
    content = cleanup_content(content)
    chinese_count = count_chinese(content)
    
    # 补充字数
    while chinese_count < 150:
        content += "\n他没有动。"
        chinese_count = count_chinese(content)
    
    print(f"\n📊 生成 {chinese_count} 字")
    
    # 6. 预览
    print("\n" + "="*60)
    print("内容预览：")
    print("="*60)
    print(content[:600])
    if len(content) > 600:
        print("...")
    print("="*60)
    
    # 7. 询问
    print("\n是否提交？(y/n)")
    answer = input().strip().lower()
    
    if answer != 'y':
        print("已取消")
        return 0
    
    # 8. 提交
    print("\n📤 提交续写...")
    result = submit_segment(branch_id, content)
    
    if result.get("status") == "success":
        print("✅ 续写成功!")
        print(f"\n🔗 https://inkpath-git-main-grant-huangs-projects.vercel.app/story/{story_id}")
    else:
        print(f"❌ 失败: {result}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

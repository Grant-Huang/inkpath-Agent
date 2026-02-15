#!/usr/bin/env python3
"""简单的故事续写"""

import json
import re
import requests

# 配置
API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STORY_ID = "aabd7b32-6c3b-4f8a-b113-f7ce22565f31"

def get_branch(story_id):
    """获取分支"""
    url = f"{API_URL}/stories/{story_id}/branches?limit=10"
    resp = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    data = resp.json()
    branches = data.get('data', {}).get('branches', [])
    return branches[-1] if branches else None

def get_full_story(branch_id):
    """获取完整故事"""
    url = f"{API_URL}/branches/{branch_id}/full-story"
    resp = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    return resp.json()

def generate_content(starter, previous=""):
    """调用 Ollama 生成内容"""
    prompt = f"""你是一个专业的故事作家。

故事背景：蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。

开篇：
{starter[:600]}

前文（如果有）：
{previous if previous else '无'}

要求：
- 风格：克制、冷峻、悬念
- 字数：300-500字
- 直接输出续写内容，不要有任何前缀

续写：
"""
    
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral:latest",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 800}
        },
        timeout=120
    )
    
    return resp.json().get("response", "")

def submit_segment(branch_id, content):
    """提交片段"""
    url = f"{API_URL}/branches/{branch_id}/segments"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"content": content},
        timeout=300
    )
    return resp.json()

def main():
    print("="*50)
    print("故事续写")
    print("="*50)
    
    # 获取分支
    branch = get_branch(STORY_ID)
    if not branch:
        print("❌ 无分支")
        return
    
    branch_id = branch.get('id')
    print(f"\n📖 分支: {branch.get('title')}")
    
    # 获取完整故事
    full = get_full_story(branch_id)
    data = full.get('data', {})
    segments = data.get('segments', [])
    print(f"📄 已有片段: {len(segments)}")
    
    # 前文
    previous = "\n\n---\n\n".join([s.get('content', '') for s in segments[-3:]])
    
    # 开篇
    with open('/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md', 'r') as f:
        starter = f.read()
    
    # 生成内容
    print("\n🤖 生成内容...")
    content = generate_content(starter, previous)
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
    print(f"   生成 {chinese_count} 字")
    
    # 验证字数
    while chinese_count < 150:
        content += "\n他陷入了沉思。"
        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
    
    print(f"   最终 {chinese_count} 字")
    
    # 提交
    print("\n📤 提交...")
    result = submit_segment(branch_id, content)
    
    if result.get('status') == 'success':
        print("✅ 续写成功!")
        print(f"   片段ID: {result.get('segment', {}).get('id', 'N/A')}")
    else:
        print(f"❌ 失败: {result}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    main()

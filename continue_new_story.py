#!/usr/bin/env python3
"""续写新创建的故事"""

import sys
sys.path.insert(0, 'src')

from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client
import re

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"

client = InkPathClient(API_URL, API_KEY)

# 故事信息
story_id = "aabd7b32-6c3b-4f8a-b113-f7ce22565f31"
story = client.get_story(story_id)
print(f"\n📖 故事: {story.get('title')}")

# 获取分支
branches = client.get_branches(story_id, limit=10)
if not branches:
    print("❌ 无分支，创建一个新分支")
    branch = client.create_branch(story_id, "主分支", "自动创建的主分支")
    branch_id = branch.get('id')
else:
    branch = branches[-1]
    branch_id = branch.get('id')
    print(f"🌿 使用分支: {branch.get('title')}")

print(f"   分支 ID: {branch_id}")

# 获取完整故事
full = client.get_branch_full_story(branch_id)
segments = full.get('segments', [])
print(f"📄 已有片段: {len(segments)}")

# 加载开篇
with open('../inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md', 'r') as f:
    starter = f.read()

# 构建 Prompt
prompt = f"""你是一个专业的故事作家。

故事背景：{story.get('background', '')}

开篇：
{starter[:800]}

前文（如果有）：
{[s.get('content', '') for s in segments[-3:]] if segments else '无'}

要求：
- 风格：克制、冷峻、悬念
- 字数：300-500字
- 直接输出续写内容，不要有任何前缀
"""

# 调用 LLM
print("\n🤖 调用 Ollama...")
llm = create_llm_client(provider='ollama')
content = llm._call_ollama(prompt)

# 验证字数
chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
print(f"📊 生成 {chinese_count} 字")

# 扩展如果太短
while chinese_count < 150:
    content += "\n他陷入了沉思。"
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))

# 提交
print(f"\n📤 提交续写...")
result = client.submit_segment(branch_id, content)

if result:
    print("✅ 续写成功!")
else:
    print("❌ 续写失败")

#!/usr/bin/env python3
"""用 qwen3:32b 续写故事"""

import requests
import re

API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
BRANCH_ID = "203a2d94-5a8d-4b39-a1e2-4c9072e18cef"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:32b"

# 开篇结尾
ENDING = """杨粟站在原地，后背已经被冷汗浸透。

这卷竹简，不能按规矩处理。

至少现在不能。"""

# Prompt
PROMPT = f"""你是一个专业的故事作家。

任务：续写历史悬疑故事《丞相府书吏》。

开篇结尾：
{ENDING}

要求：
- 一句话一行
- 用行动和对话推进故事，不是心理活动
- 克制、冷峻、悬念
- 短句（10-20字）
- 承接开篇结尾，推进剧情

参考开篇风格：
"杨粟擦了擦额头的汗珠，继续整理旧档。"
"他应该放下。但手却不受控制地抽出第二枚、第三枚……"

禁止：
- 心理描写（"他感到"、"他知道"）
- 长句
- "但是"、"因为"

直接输出续写内容（300-500字）：
"""

print("="*60)
print(f"使用 {MODEL} 续写故事")
print("注意：需要 2-5 分钟，请耐心等待")
print("="*60)

print("\n调用 LLM...")
resp = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.6, "num_predict": 1500}
    },
    timeout=600
)

print("处理响应...")
content = resp.json().get("response", "")

# 清理
lines = content.split('\n')
clean_lines = []
for line in lines:
    line = line.strip()
    line = re.sub(r'^\d+\.\s*', '', line)
    if any(x in line for x in ['心中', '感到', '觉得', '认为', '想了想']):
        continue
    if len(line) > 25:
        continue
    if '但是' in line:
        continue
    if line:
        clean_lines.append(line)

content = '\n'.join(clean_lines)
chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))

# 补充字数
while chinese_count < 150:
    content += "\n他没有动。"
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))

print(f"\n📊 生成 {chinese_count} 字")

# 预览
print("\n" + "="*60)
print("内容预览：")
print("="*60)
print(content[:600])
print("...")
print("="*60)

# 提交
print("\n提交续写...")
resp = requests.post(
    f"{API_URL}/branches/{BRANCH_ID}/segments",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={"content": content},
    timeout=300
)

result = resp.json()
print(f"状态码: {resp.status_code}")
print(f"结果: {result.get('status')}")

if result.get('status') == 'success':
    print("\n✅ 续写成功!")
    print(f"\n🔗 https://inkpath-git-main-grant-huangs-projects.vercel.app/story/7e57a174-5b72-43ba-ad1a-15b64034097d")
else:
    print(f"\n❌ 失败: {result}")

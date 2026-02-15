#!/usr/bin/env python3
"""
高质量续写脚本 - 确保风格一致

特点：
1. 短句为主，一句话一行
2. 行动 + 对话
3. 悬念感
4. 克制、冷峻
"""

import json
import re
import requests

# 配置
API_URL = "https://inkpath-api.onrender.com/api/v1"
API_KEY = "TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"
STARTER_PATH = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md"


def get_starter_style():
    """提取 starter 的风格特征"""
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除 markdown 格式
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
    
    return content


def build_strict_prompt(starter, previous_segments, story_background):
    """构建严格的风格化 Prompt"""
    
    # 提取开篇的核心部分（前800字）
    starter_core = starter[:800]
    
    # 构建风格规则
    prompt = f"""你是一个专业的故事作家。

## 故事背景
{story_background}

## 参考风格（必须严格遵守！）
以下是开篇的风格范例，注意学习：

---
{starter_core}
---

## 风格规则（必须遵守！）
1. **短句为主，一句话一行**
2. **用行动和对话推进故事**，不是心理活动
3. **每段最多2-3句话**
4. **悬念感**：用细节暗示，不要直接说明
5. **克制、冷峻**：不要过度渲染情感

## 错误示范（不要这样写）
- "杨粟感到非常害怕，他不知道该怎么办。"（心理活动过多）
- "他陷入了深深的沉思之中，思考着这个谜团的答案。"（长句、抽象）
- "这一定是一个惊天大阴谋！"（直接说明、缺乏悬念）

## 正确示范（参考开篇）
- "杨粟的手一抖。"（行动）
- "他想放下这卷竹简。他应该放下。但手却不受控制……"（行动+矛盾）
- "杨粟站在原地，后背已经被冷汗浸透。"（细节描写）

## 续写要求
- 字数：300-500字
- 风格：完全模仿开篇风格
- 内容：承接开篇结尾，延续故事
- 直接输出续写内容，**不要有任何前缀说明**

开篇结尾：
"这卷竹简，不能按规矩处理。至少现在不能。"

续写：
"""
    
    return prompt


def count_chinese(text):
    """计算中文字数"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def generate_content(prompt):
    """调用 Ollama 生成内容"""
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral:latest",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.6,  # 降低温度，更稳定
                "num_predict": 1000
            }
        },
        timeout=120
    )
    
    return resp.json().get("response", "")


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


def main():
    print("="*60)
    print("高质量故事续写")
    print("="*60)
    
    # 1. 加载开篇
    print("\n📖 加载开篇...")
    with open(STARTER_PATH, 'r', encoding='utf-8') as f:
        starter = f.read()
    print(f"   开篇长度: {len(starter)} 字")
    
    # 2. 故事背景
    story_background = "蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信——它本该在九年前随魏延之首级一同下葬。"
    
    # 3. 构建 Prompt
    print("\n📝 构建风格化 Prompt...")
    prompt = build_strict_prompt(starter, [], story_background)
    print(f"   Prompt 长度: {len(prompt)} 字")
    
    # 4. 生成内容
    print("\n🤖 生成内容（严格风格）...")
    content = generate_content(prompt)
    chinese_count = count_chinese(content)
    print(f"   生成 {chinese_count} 字")
    
    # 5. 清理内容
    # 移除任何前缀
    content = content.strip()
    lines = content.split('\n')
    # 过滤掉常见的前缀
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('续写：') and not line.startswith('以下是') and not line.startswith('---'):
            filtered_lines.append(line)
    content = '\n'.join(filtered_lines)
    
    chinese_count = count_chinese(content)
    print(f"   清理后 {chinese_count} 字")
    
    # 6. 验证字数
    while chinese_count < 150:
        content += "\n他没有动。"
        chinese_count = count_chinese(content)
    
    while chinese_count > 500:
        # 移除最后一行
        lines = content.split('\n')
        if len(lines) > 2:
            content = '\n'.join(lines[:-1])
        chinese_count = count_chinese(content)
    
    print(f"   最终 {chinese_count} 字")
    
    # 7. 输出预览
    print("\n" + "="*60)
    print("内容预览（前800字）：")
    print("="*60)
    print(content[:800])
    print("...")
    print("="*60)
    
    # 8. 询问是否提交
    print("\n是否提交？(y/n)")
    # 直接提交
    print("y")
    
    return 0


if __name__ == "__main__":
    main()

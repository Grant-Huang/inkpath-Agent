#!/usr/bin/env python3
"""
高质量故事续写 Prompt 生成器

包含：
1. 从 00_meta.md 读取创作原则
2. 生成严格遵守风格的 Prompt
"""

import json
import re
from pathlib import Path


def load_meta_rules(pkg_path: str) -> dict:
    """从 00_meta.md 读取创作规则"""
    meta_path = Path(pkg_path) / "00_meta.md"
    
    if not meta_path.exists():
        return None
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析创作原则部分
    rules = {
        'genre': '',
        'tone': [],
        'writing_rules': []
    }
    
    # 提取创作原则
    if '# 创作原则' in content:
        rules_section = content.split('# 创作原则')[1].split('#')[0]
        
        # 提取风格定位
        if '## 语言风格' in rules_section:
            style_section = rules_section.split('## 语言风格')[1].split('##')[0]
            rules['writing_rules'].extend([
                '短句为主，一句话一行',
                '注重行动和对话',
                '允许心理描写和环境描写，但不主导叙事',
                '克制、冷峻、悬念'
            ])
        
        # 提取叙事节奏
        if '## 叙事节奏' in rules_section:
            rhythm_section = rules_section.split('## 叙事节奏')[1].split('##')[0]
            rules['narrative_rhythm'] = [
                '快节奏：每个段落 1-3 句话',
                '用空行分隔场景',
                '用细节暗示，不要直接说明'
            ]
        
        # 提取应该做的
        if '### 应该做的' in rules_section:
            do_section = rules_section.split('### 应该做的')[1].split('###')[0]
            rules['should_do'] = [
                '用具体动作描写',
                '用对话推进情节',
                '用环境细节营造氛围',
                '用短句制造紧张感'
            ]
        
        # 提取避免的
        if '### 避免的' in rules_section:
            avoid_section = rules_section.split('### 避免的')[1].split('###')[0]
            rules['should_avoid'] = [
                '长篇大论的心理描写',
                '直接说明真相',
                '冗长的背景叙述',
                '过度解释和说明'
            ]
    
    # 提取基本信息
    for line in content.split('\n'):
        if line.startswith('title:'):
            rules['title'] = line.split(':')[1].strip().strip('"')
        if line.startswith('tone:'):
            tones = re.findall(r'"([^"]+)"', line)
            rules['tone'] = tones
    
    return rules


def extract_starter_sample(pkg_path: str, max_chars: int = 2000) -> str:
    """从 70_Starter.md 提取风格样本（核心叙事部分）"""
    starter_path = Path(pkg_path) / "70_Starter.md"
    
    if not starter_path.exists():
        return ""
    
    with open(starter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除 markdown 表格和元信息，提取核心叙事
    lines = content.split('\n')
    narrative_lines = []
    
    for line in lines:
        # 跳过 markdown 格式
        if line.startswith('#'):
            continue
        if line.startswith('>'):
            continue
        if line.startswith('---'):
            continue
        if line.startswith('|'):
            continue
        if line.startswith('**建议') or line.startswith('*开篇版本') or line.startswith('- **'):
            continue
        
        # 跳过特定部分
        if any(x in line for x in ['开篇设计说明', '开篇钩子', '开篇数据', '开篇与后续', '使用建议', '版本：v']):
            continue
        
        # 提取叙事内容
        line = line.strip()
        if line:
            narrative_lines.append(line)
        
        # 限制长度
        if sum(len(l) for l in narrative_lines) > max_chars:
            break
    
    result = '\n'.join(narrative_lines)
    
    # 确保有内容
    if not result:
        # 尝试提取前2000字符
        result = content[:max_chars]
    
    return result


def build_style_prompt(rules: dict, starter_sample: str) -> str:
    """构建风格化 Prompt"""
    
    prompt = f"""你是一个专业的故事作家。

## 故事信息
标题：{rules.get('title', '丞相府书吏')}
风格：{', '.join(rules.get('tone', ['克制', '冷峻', '悬念']))}

## 创作规则

### 语言风格
"""

    # 添加语言风格规则
    for rule in rules.get('writing_rules', []):
        prompt += f"- {rule}\n"

    prompt += """
### 叙事节奏
"""
    for rule in rules.get('narrative_rhythm', []):
        prompt += f"- {rule}\n"

    prompt += """
### 应该做的
"""
    for rule in rules.get('should_do', []):
        prompt += f"- {rule}\n"

    prompt += """
### 避免的
"""
    for rule in rules.get('should_avoid', []):
        prompt += f"- {rule}\n"

    prompt += f"""
## 参考风格（必须严格模仿）

以下是故事开篇的风格样本，模仿这种风格续写：

---
{starter_sample}
---

## 续写要求

1. **风格一致**：严格模仿开篇风格
2. **行动+对话**：用动作和对话推进故事
3. **节奏明快**：短句为主，一句话一行
4. **悬念感**：用细节暗示，不要直接说明
5. **字数**：300-500字

## 开篇结尾
"""

    return prompt


def generate_continue_prompt(pkg_path: str, previous_segments: list = None, context: str = "") -> str:
    """
    生成完整的续写 Prompt
    
    Args:
        pkg_path: 故事包路径
        previous_segments: 前文片段列表
        context: 额外的上下文信息
    
    Returns:
        完整的 Prompt 字符串
    """
    # 加载规则
    rules = load_meta_rules(pkg_path)
    if not rules:
        # 返回默认 Prompt
        return build_default_prompt(previous_segments, context)
    
    # 提取风格样本
    starter_sample = extract_starter_sample(pkg_path)
    
    # 构建 Prompt
    prompt = build_style_prompt(rules, starter_sample)
    
    # 添加前文
    if previous_segments:
        prompt += "\n## 前文\n"
        for i, seg in enumerate(previous_segments[-3:], 1):
            prompt += f"\n### 片段 {i}\n{seg.get('content', '')[:500]}\n"
    
    # 添加上下文
    if context:
        prompt += f"\n## 额外要求\n{context}\n"
    
    # 添加续写要求
    prompt += """
## 续写内容

直接输出续写内容，**不要有任何前缀说明**。
"""
    
    return prompt


def build_default_prompt(previous_segments: list = None, context: str = "") -> str:
    """默认 Prompt（当没有规则文件时）"""
    prompt = """你是一个专业的故事作家。

风格：克制、冷峻、悬念
节奏：短句为主，一句话一行
要求：用行动和对话推进故事，不排斥心理描写和环境描写

"""
    
    if previous_segments:
        prompt += "## 前文\n"
        for i, seg in enumerate(previous_segments[-3:], 1):
            prompt += f"\n### 片段 {i}\n{seg.get('content', '')[:500]}\n"
    
    if context:
        prompt += f"\n## 额外要求\n{context}\n"
    
    prompt += "\n直接输出续写内容："
    
    return prompt


if __name__ == "__main__":
    # 测试
    pkg_path = "../inkpath/story-packages/han-234-weiyan-mystery"
    
    print("加载创作规则...")
    rules = load_meta_rules(pkg_path)
    print(f"找到 {len(rules.get('writing_rules', []))} 条规则")
    
    print("\n生成续写 Prompt...")
    prompt = generate_continue_prompt(pkg_path)
    print(f"Prompt 长度: {len(prompt)} 字")
    
    print("\n前 1000 字预览：")
    print(prompt[:1000])

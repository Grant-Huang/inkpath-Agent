#!/usr/bin/env python3
"""
Story Package Reader - 简化版

直接读取故事包文件，构建续写 Prompt
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any


class StoryPackageReader:
    """故事包读取器 - 简化版"""
    
    def __init__(self, package_path: str):
        self.package_path = Path(package_path)
        self.cache = {}
    
    def read_file(self, filename: str) -> str:
        """读取文件"""
        filepath = self.package_path / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def parse_yaml_frontmatter(self, text: str) -> Dict:
        """解析 YAML 前置元数据"""
        pattern = r'^---\n(.*?)\n---'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                import yaml
                return yaml.safe_load(match.group(1)) or {}
            except:
                pass
        return {}
    
    def load_metadata(self) -> Dict:
        """加载元数据"""
        text = self.read_file('00_meta.md')
        meta = self.parse_yaml_frontmatter(text)
        self.cache['metadata'] = meta
        return meta
    
    def load_cast(self) -> Dict[str, Dict]:
        """加载角色包"""
        text = self.read_file('30_cast.md')
        cast = {}
        
        # 按 ## 分割
        blocks = re.split(r'\n## ', text)
        
        for block in blocks:
            if not block.strip():
                continue
            
            # 提取 ID
            id_match = re.search(r'(C-\d+)', block)
            if not id_match:
                continue
            
            cid = id_match.group(1)
            
            # 提取名称
            name_match = re.search(r'[｜|](\D+)（', block)
            name = name_match.group(1).strip() if name_match else ""
            
            # 提取立场
            stance_match = re.search(r'立场[：:]\s*(S-\d+)', block)
            stance = stance_match.group(1) if stance_match else ""
            
            # 提取可接触信息
            access = re.findall(r'[E|S]-\d+', block)
            
            cast[cid] = {
                'id': cid,
                'name': name,
                'stance': stance,
                'information_access': access,
                'content': block.strip()[:500]
            }
        
        self.cache['cast'] = cast
        return cast
    
    def load_evidence(self) -> Dict[str, Dict]:
        """加载证据包"""
        text = self.read_file('10_evidence_pack.md')
        evidence = {}
        
        blocks = re.split(r'\n## ', text)
        
        for block in blocks:
            if not block.strip():
                continue
            
            id_match = re.search(r'(E-\d+)', block)
            if not id_match:
                continue
            
            eid = id_match.group(1)
            
            title_match = re.search(r'[｜|](\D+)（', block)
            title = title_match.group(1).strip() if title_match else ""
            
            evidence[eid] = {
                'id': eid,
                'title': title,
                'content': block.strip()[:500]
            }
        
        self.cache['evidence'] = evidence
        return evidence
    
    def load_constraints(self) -> Dict:
        """加载约束包"""
        text = self.read_file('50_constraints.md')
        
        hard = re.findall(r'硬约束[：:]\s*([^\n]+)', text)
        soft = re.findall(r'软约束[：:]\s*([^\n]+)', text)
        boundaries = re.findall(r'内容边界[：:]\s*([^\n]+)', text)
        
        constraints = {
            'hard': [c.strip() for c in hard],
            'soft': [c.strip() for c in soft],
            'boundaries': [b.strip() for b in boundaries]
        }
        
        self.cache['constraints'] = constraints
        return constraints
    
    def load_outline(self) -> List[Dict]:
        """加载情节大纲"""
        text = self.read_file('40_plot_outline.md')
        
        outline = []
        blocks = re.split(r'\n## ', text)
        
        for block in blocks:
            if not block.strip():
                continue
            
            chapter_match = re.search(r'第(\d+)章', block)
            title_match = re.search(r'[（(](\D+)[）)]', block)
            summary_match = re.search(r'内容[：:]([^\n]+)', block)
            
            outline.append({
                'chapter': chapter_match.group(1) if chapter_match else "?",
                'title': title_match.group(1) if title_match else "",
                'summary': summary_match.group(1).strip() if summary_match else block[:100]
            })
        
        self.cache['outline'] = outline
        return outline
    
    def get_character(self, char_id: str) -> Dict:
        """获取角色"""
        cast = self.load_cast()
        return cast.get(char_id, {})
    
    def get_evidence_for_character(self, char_id: str) -> List[Dict]:
        """获取角色可接触的证据"""
        char = self.get_character(char_id)
        access = char.get('information_access', [])
        
        evidence = self.load_evidence()
        result = []
        
        for eid in access:
            if eid in evidence:
                result.append(evidence[eid])
        
        return result


def load_story_package(package_path: str) -> Dict:
    """便捷函数：加载故事包"""
    reader = StoryPackageReader(package_path)
    return {
        'metadata': reader.load_metadata(),
        'cast': reader.load_cast(),
        'evidence': reader.load_evidence(),
        'constraints': reader.load_constraints(),
        'outline': reader.load_outline()
    }


class StoryPromptBuilder:
    """故事续写 Prompt 构建器"""
    
    def __init__(self, package_path: str):
        self.reader = StoryPackageReader(package_path)
        self.pkg = load_story_package(package_path)
    
    def build_prompt(
        self,
        query: str,
        viewpoint_char: str,
        current_stage: str,
        previous_segments: List[str],
        segment_summary: str = ""
    ) -> str:
        """构建续写 Prompt"""
        
        meta = self.pkg['metadata']
        char = self.reader.get_character(viewpoint_char)
        evidence = self.reader.get_evidence_for_character(viewpoint_char)
        constraints = self.pkg['constraints']
        
        # 构建角色信息
        char_section = f"""## 三、角色约束

**视角角色**：{char.get('id', '')} {char.get('name', '')}
**立场**：{char.get('stance', '')}

**信息权限**：
- 可接触的信息：{', '.join(char.get('information_access', []))}

**原文内容**：
{char.get('content', '')}"""
        
        # 构建证据信息
        evidence_section = """## 四、证据与立场

**本段可引用的证据**："""
        for ev in evidence[:5]:
            evidence_section += f"\n- {ev['id']} {ev['title']}"
        
        evidence_section += f"""

**证据详情**：
"""
        for ev in evidence[:5]:
            evidence_section += f"""
### {ev['id']} {ev['title']}
{ev['content']}
"""
        
        # 构建约束
        hard = '\n'.join([f"- {c}" for c in constraints['hard'][:5]])
        soft = '\n'.join([f"- {c}" for c in constraints['soft'][:5]])
        
        constraints_section = f"""## 五、创作约束

**硬约束**（禁止打破）：
{hard if hard else '- 无硬约束'}

**软约束**（不建议违背）：
{soft if soft else '- 无软约束'}

**内容边界**：
- {', '.join(constraints['boundaries'][:3]) if constraints['boundaries'] else '无边界'}

**时代设定**：
- 基于三国蜀汉时期
- 丞相府官职制度
- 军令传达流程
"""
        
        # 构建前文
        prev_section = f"""## 六、前文

**前文 ({len(previous_segments)} 段）**：
"""
        for i, seg in enumerate(previous_segments[-5:], 1):
            prev_section += f"\n### 片段 {i}\n{seg[:200]}...\n"
        
        # 组合完整 Prompt
        prompt = f"""# 续写任务

## 一、故事基调

**标题**：{meta.get('title', '')}
**类型**：{', '.join(meta.get('genre', []))}
**基调**：{', '.join(meta.get('tone', []))}
**一句话梗概**：{meta.get('logline', '')}
**核心冲突**：{meta.get('核心冲突', '')}
**读者预期**：{meta.get('读者预期', '')}

## 二、当前阶段

**阶段**：{current_stage}

{segment_summary}

{char_section}

{evidence_section}

{constraints_section}

{prev_section}

## 七、续写要求

1. **字数**：300-500 字
2. **衔接**：自然承接上一段结尾
3. **视角**：严格遵循角色信息权限
4. **细节**：用证据、器物、环境推进
5. **张力**：利用信息差制造悬念
6. **禁止**：泄露未到时机信息、违反角色禁区

## 八、当前任务

{query}

请直接输出续写内容，不要有任何前缀说明。
"""
        
        return prompt


if __name__ == "__main__":
    # 测试
    package_path = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery"
    
    print("="*60)
    print("测试 Story Package Reader")
    print("="*60)
    
    reader = StoryPackageReader(package_path)
    pkg = load_story_package(package_path)
    
    print(f"\n标题: {pkg['metadata'].get('title', '')}")
    print(f"类型: {pkg['metadata'].get('genre', [])}")
    print(f"\n角色数: {len(pkg['cast'])}")
    print(f"证据数: {len(pkg['evidence'])}")
    
    # 测试角色
    char = reader.get_character("C-01")
    print(f"\n角色 C-01:")
    print(f"  名称: {char.get('name', '')}")
    print(f"  立场: {char.get('stance', '')}")
    
    # 测试证据
    ev = reader.get_evidence_for_character("C-01")
    print(f"\n可接触证据: {len(ev)} 个")
    for e in ev[:3]:
        print(f"  - {e['id']} {e['title']}")
    
    # 测试 Prompt 构建
    print("\n" + "="*60)
    print("测试 Prompt 构建")
    print("="*60)
    
    builder = StoryPromptBuilder(package_path)
    prompt = builder.build_prompt(
        query="续写下一段",
        viewpoint_char="C-01",
        current_stage="第二阶段：暗流涌动",
        previous_segments=["第一段内容...", "第二段内容..."],
        segment_summary="角色发现线索"
    )
    
    print(prompt[:1500])
    print("\n... (省略部分) ...")

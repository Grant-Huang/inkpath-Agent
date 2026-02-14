#!/usr/bin/env python3
"""
Story Continuator - 集成故事包的续写模块

使用：
1. 读取故事包 (evidence_pack, stance_pack, cast 等)
2. 构建符合要求的续写 prompt
3. 调用 LLM 生成续写内容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from story_package_reader import (
    StoryPackageReader,
    StoryPromptBuilder,
    load_story_package
)


class StoryContinuer:
    """故事续写器 - 集成故事包"""
    
    def __init__(self, story_package_path: str, llm_client):
        """
        初始化故事续写器
        
        Args:
            story_package_path: 故事包目录路径
            llm_client: LLM 客户端实例
        """
        self.story_package_path = story_package_path
        self.llm_client = llm_client
        self.reader = StoryPackageReader(story_package_path)
        self.pkg = self.reader.load()
        self.builder = StoryPromptBuilder(story_package_path)
    
    def continue_story(
        self,
        query: str,
        viewpoint_char: str,
        current_stage: str,
        previous_segments: list,
        segment_summary: str = ""
    ) -> str:
        """
        续写故事
        
        Args:
            query: 续写要求（如"续写下一段"）
            viewpoint_char: 视角角色ID（如"C-01"）
            current_stage: 当前阶段（如"第二阶段：暗流涌动"）
            previous_segments: 前文片段列表
            segment_summary: 阶段摘要
        
        Returns:
            续写内容
        """
        # 构建 prompt
        prompt = self.builder.build_continuation_prompt(
            query=query,
            viewpoint_char=viewpoint_char,
            current_stage=current_stage,
            previous_segments=previous_segments,
            segment_summary=segment_summary
        )
        
        # 调用 LLM
        return self.llm_client._call_ollama(prompt)
    
    def get_character(self, char_id: str):
        """获取角色信息"""
        return self.reader.get_character_by_viewpoint(char_id)
    
    def get_accessible_evidence(self, char_id: str):
        """获取角色可接触的证据"""
        return self.reader.get_evidence_for_segment(char_id)
    
    def get_stance_interpretations(self, stance_id: str):
        """获取立场的证据解读"""
        return self.reader.get_stance_interpretations(stance_id)


def create_story_continuer(
    story_package_path: str,
    llm_client
) -> StoryContinuer:
    """创建故事续写器"""
    return StoryContinuer(story_package_path, llm_client)


if __name__ == "__main__":
    # 测试
    from llm_client import create_llm_client
    
    print("="*60)
    print("测试 Story Continuator")
    print("="*60)
    
    # 创建 LLM 客户端
    llm = create_llm_client('ollama')
    
    # 故事包路径
    package_path = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery"
    
    # 创建续写器
    continuer = create_story_continuer(package_path, llm)
    
    # 测试角色获取
    char = continuer.get_character("C-01")
    if char:
        print(f"\n角色信息：{char.name}")
        print(f"立场：{char.stance}")
    
    # 测试证据获取
    evidence = continuer.get_accessible_evidence("C-01")
    print(f"\n可接触证据数：{len(evidence)}")
    
    print("\n✅ Story Continuator 测试完成")

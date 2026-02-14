#!/usr/bin/env python3
"""
InkPath Agent - 集成故事包续写模块

功能：
1. 读取故事包 (evidence_pack, stance_pack, cast 等)
2. 构建符合要求的续写 prompt
3. 调用 LLM 生成续写内容
4. 提交到 InkPath
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, Optional
from llm_client import create_llm_client


class StoryPackageAgent:
    """集成故事包的 Agent"""
    
    def __init__(
        self,
        story_package_path: str,
        inkpath_client,
        config: Dict[str, Any] = None
    ):
        """
        初始化
        
        Args:
            story_package_path: 故事包路径
            inkpath_client: InkPath 客户端
            config: 配置
        """
        self.story_package_path = story_package_path
        self.client = inkpath_client
        self.config = config or {}
        
        # LLM 客户端
        self.llm = create_llm_client(provider='ollama')
        
        # 加载故事包读取器
        from story_package_reader import StoryPackageReader, StoryPromptBuilder
        self.reader = StoryPackageReader(story_package_path)
        self.pkg = self.reader.load()
        self.builder = StoryPromptBuilder(story_package_path)
    
    def continue_with_package(
        self,
        query: str,
        viewpoint_char: str,
        current_stage: str,
        previous_segments: list,
        segment_summary: str = ""
    ) -> str:
        """
        使用故事包续写
        
        Args:
            query: 续写要求
            viewpoint_char: 视角角色
            current_stage: 当前阶段
            previous_segments: 前文
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
        result = self.llm._call_ollama(prompt)
        
        return result
    
    def get_character_info(self, char_id: str) -> Dict[str, Any]:
        """获取角色信息"""
        char = self.reader.get_character_by_viewpoint(char_id)
        if char:
            return {
                'id': char.id,
                'name': char.name,
                'stance': char.stance,
                'information_access': char.information_access,
                'forbidden_info': char.forbidden_info,
                'blind_spots': char.blind_spots,
                'forbidden_actions': char.forbidden_actions,
                'cost': char.cost
            }
        return {}
    
    def get_evidence_list(self, char_id: str) -> list:
        """获取角色可接触的证据"""
        evidence = self.reader.get_evidence_for_segment(char_id)
        return [
            {
                'id': e.id,
                'title': e.title,
                'carrier': e.carrier,
                'gaps': e.gaps,
                'reliability': e.reliability,
                'debatable_points': e.debatable_points
            }
            for e in evidence
        ]
    
    def run(
        self,
        branch_id: str,
        viewpoint_char: str = "C-01",
        current_stage: str = "第二阶段：暗流涌动"
    ):
        """
        运行一次续写任务
        
        Args:
            branch_id: 分支 ID
            viewpoint_char: 视角角色
            current_stage: 当前阶段
        """
        # 获取前文
        full_story = self.client.get_branch_full_story(branch_id)
        if not full_story:
            print(f"❌ 获取故事失败")
            return None
        
        segments = full_story.get("segments", [])
        previous = [s.get("content", "") for s in segments[-5:]]
        
        # 续写
        print(f"\n📝 续写中 (视角: {viewpoint_char})...")
        content = self.continue_with_package(
            query="续写下一段",
            viewpoint_char=viewpoint_char,
            current_stage=current_stage,
            previous_segments=previous,
            segment_summary=""
        )
        
        if content:
            print(f"✅ 生成 {len(content)} 字")
            
            # 提交
            result = self.client.submit_segment(branch_id, content)
            if result:
                print(f"✅ 提交成功")
                return content
        
        return None


def create_package_agent(
    story_package_path: str,
    inkpath_client,
    config: Dict[str, Any] = None
) -> StoryPackageAgent:
    """创建故事包 Agent"""
    return StoryPackageAgent(
        story_package_path=story_package_path,
        inkpath_client=inkpath_client,
        config=config
    )


if __name__ == "__main__":
    # 测试
    from inkpath_client import InkPathClient
    
    print("="*60)
    print("测试 Story Package Agent")
    print("="*60)
    
    # 创建客户端
    client = InkPathClient()
    
    # 故事包路径
    package_path = "/Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery"
    
    # 创建 Agent
    agent = create_package_agent(
        story_package_path=package_path,
        inkpath_client=client
    )
    
    # 测试角色信息
    char_info = agent.get_character_info("C-01")
    print(f"\n角色信息: {char_info.get('name', '未找到')}")
    print(f"立场: {char_info.get('stance', '')}")
    
    # 测试证据
    evidence = agent.get_evidence_list("C-01")
    print(f"\n可接触证据: {len(evidence)} 个")
    for e in evidence[:3]:
        print(f"  - {e['id']} {e['title']}")
    
    print("\n✅ 测试完成")

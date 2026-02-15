#!/usr/bin/env python3
"""
进度摘要更新脚本

功能：
1. 读取分配给 Agent 的所有故事
2. 生成每个故事的进展摘要
3. 更新到 InkPath API
4. 发送摘要给故事拥有者（可选）

用法：
    python progress_updater.py --api-key YOUR_API_KEY --agent-id YOUR_AGENT_ID

选项：
    --force     强制更新所有故事
    --dry-run   试运行，不实际更新
    --notify    发送摘要给用户
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "inkpath-agent" / "src"))

from inkpath_client import InkPathClient
from llm_client import LLMClient
from style_prompt_builder import StylePromptBuilder


class ProgressUpdater:
    """进度摘要更新器"""
    
    def __init__(self, api_url: str, api_key: str, agent_id: str):
        self.inkpath = InkPathClient(api_url, api_key)
        self.llm = LLMClient()
        self.builder = StylePromptBuilder()
        self.agent_id = agent_id
    
    async def get_assigned_stories(self) -> list:
        """获取分配给 Agent 的所有故事"""
        stories = await self.inkpath.get_stories()
        return [s for s in stories if s.get("owner_id") == self.agent_id]
    
    async def get_story_segments(self, story_id: str) -> list:
        """获取故事的所有片段"""
        branches = await self.inkpath.get_branches(story_id)
        if not branches:
            return []
        
        # 获取主分支的片段
        main_branch = branches[0]
        segments = await self.inkpath.get_segments(main_branch["id"])
        return segments
    
    async def generate_summary(self, story: dict, segments: list) -> str:
        """使用 LLM 生成进展摘要"""
        if not segments:
            return "暂无片段"
        
        # 提取关键信息
        segment_count = len(segments)
        last_segment = segments[-1]["content"]
        
        # 构建 Prompt
        prompt = f"""请为以下故事生成一个进展摘要（不超过200字）：

## 故事信息
标题: {story.get('title', '未命名')}
背景: {story.get('background', '无')}

## 最后片段
{last_segment[:500]}...

## 摘要要求
1. 当前阶段（第一幕发现/第二幕真相逼近/第三幕对峙等）
2. 主要冲突
3. 1-2个关键线索
4. 简洁明了，用中文

请直接输出摘要，不需要标题。"""
        
        # 调用 LLM
        summary = await self.llm.generate(prompt, max_tokens=300)
        return summary.strip()
    
    async def plan_next_action(self, story: dict, segments: list) -> str:
        """生成下一步行动计划"""
        if not segments:
            return "创建故事开篇"
        
        # 分析当前阶段
        segment_count = len(segments)
        
        if segment_count <= 3:
            stage = "第一幕"
            action = "继续建立冲突和角色"
        elif segment_count <= 8:
            stage = "第二幕"
            action = "推进真相揭示，引入更多线索"
        else:
            stage = "第三幕"
            action = "对峙高潮，揭示最终真相"
        
        return f"[{stage}] {action}"
    
    async def update_progress(self, story_id: str, force: bool = False):
        """更新单个故事的进度"""
        try:
            # 获取故事信息
            story = await self.inkpath.get_story(story_id)
            if not story:
                print(f"❌ 故事不存在: {story_id}")
                return False
            
            # 获取片段
            segments = await self.get_story_segments(story_id)
            
            # 生成摘要
            summary = await self.generate_summary(story, segments)
            next_action = await self.plan_next_action(story, segments)
            
            # 更新到 API
            success = await self.inkpath.update_progress(
                story_id=story_id,
                summary=summary,
                next_action=next_action,
                agent_id=self.agent_id
            )
            
            if success:
                print(f"✅ 更新成功: {story.get('title', '未命名')} ({len(segments)} 片段)")
                return True
            else:
                print(f"❌ 更新失败: {story_id}")
                return False
                
        except Exception as e:
            print(f"❌ 错误: {story_id} - {e}")
            return False
    
    async def run(self, force: bool = False, dry_run: bool = False, notify: bool = False):
        """运行进度更新"""
        print(f"\n🚀 进度摘要更新器启动")
        print(f"   Agent: {self.agent_id}")
        print(f"   Force: {force}")
        print(f"   Dry Run: {dry_run}")
        print("-" * 50)
        
        # 获取分配的故事
        stories = await self.get_assigned_stories()
        print(f"📚 发现 {len(stories)} 个分配的故事\n")
        
        success_count = 0
        fail_count = 0
        
        for story in stories:
            story_id = story.get("id")
            title = story.get("title", "未命名")
            
            if dry_run:
                print(f"🟡 [Dry Run] {title}")
                continue
            
            if await self.update_progress(story_id, force):
                success_count += 1
            else:
                fail_count += 1
        
        print("\n" + "=" * 50)
        print(f"📊 完成: 成功 {success_count}, 失败 {fail_count}")
        
        return success_count == 0 or fail_count == 0


async def main():
    parser = argparse.ArgumentParser(description="InkPath 进度摘要更新器")
    parser.add_argument("--api-url", default="https://inkpath-api.onrender.com",
                        help="InkPath API 地址")
    parser.add_argument("--api-key", required=True, help="API 密钥")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    parser.add_argument("--force", action="store_true", help="强制更新所有故事")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际更新")
    parser.add_argument("--notify", action="store_true", help="发送摘要给用户")
    
    args = parser.parse_args()
    
    updater = ProgressUpdater(args.api_url, args.api_key, args.agent_id)
    success = await updater.run(args.force, args.dry_run, args.notify)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

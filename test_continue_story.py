#!/usr/bin/env python3
"""测试续写故事 - 自动查找可续写的分支并续写"""
import os
import sys
from dotenv import load_dotenv

from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client

load_dotenv()


def test_continue_story():
    """测试续写故事"""
    print("=" * 60)
    print("测试续写故事")
    print("=" * 60)
    
    # 检查配置
    api_key = os.getenv("INKPATH_API_KEY", "")
    if not api_key or api_key == "your_inkpath_api_key_here":
        print("\n❌ 错误: INKPATH_API_KEY 未配置")
        print("请在 .env 文件中设置 INKPATH_API_KEY")
        return False
    
    api_base = os.getenv("INKPATH_BASE_URL", "https://inkpath-api.onrender.com/api/v1")
    
    print(f"\n✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"✅ API Base: {api_base}")
    
    # 初始化客户端
    client = InkPathClient(api_base, api_key)
    llm_client = create_llm_client(provider='auto')
    
    # 1. 获取故事列表
    print("\n" + "-" * 60)
    print("步骤 1: 获取故事列表")
    print("-" * 60)
    
    try:
        stories = client.get_stories(limit=10)
        print(f"✅ 找到 {len(stories)} 个故事")
        
        if not stories:
            print("❌ 没有可用的故事")
            return False
        
        # 显示前几个故事
        for i, story in enumerate(stories[:3], 1):
            print(f"\n{i}. {story.get('title', 'N/A')}")
            print(f"   ID: {story.get('id')}")
            print(f"   背景: {story.get('background', '')[:50]}...")
        
        # 选择第一个故事
        selected_story = stories[0]
        story_id = selected_story["id"]
        print(f"\n✅ 选择故事: {selected_story.get('title')} (ID: {story_id})")
    
    except Exception as e:
        print(f"❌ 获取故事列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 获取分支列表
    print("\n" + "-" * 60)
    print("步骤 2: 获取分支列表")
    print("-" * 60)
    
    try:
        branches = client.get_branches(story_id, limit=5)
        print(f"✅ 找到 {len(branches)} 个分支")
        
        if not branches:
            print("❌ 没有可用的分支")
            return False
        
        # 显示分支
        for i, branch in enumerate(branches[:3], 1):
            print(f"\n{i}. {branch.get('title', 'N/A')}")
            print(f"   ID: {branch.get('id')}")
            print(f"   活跃度: {branch.get('activity_score', 0)}")
        
        # 选择第一个分支
        selected_branch = branches[0]
        branch_id = selected_branch["id"]
        print(f"\n✅ 选择分支: {selected_branch.get('title')} (ID: {branch_id})")
    
    except Exception as e:
        print(f"❌ 获取分支列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 获取分支详情
    print("\n" + "-" * 60)
    print("步骤 3: 获取分支详情")
    print("-" * 60)
    
    try:
        branch_detail = client.get_branch(branch_id)
        segments = branch_detail.get("segments", [])
        active_bots = branch_detail.get("active_bots", [])
        
        print(f"✅ 当前有 {len(segments)} 段续写")
        print(f"✅ 活跃 Bot 数: {len(active_bots)}")
        
        if segments:
            print("\n最后几段续写:")
            for seg in segments[-3:]:
                content = seg.get("content", "")
                print(f"  - {content[:50]}...")
    
    except Exception as e:
        print(f"❌ 获取分支详情失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 加入分支
    print("\n" + "-" * 60)
    print("步骤 4: 加入分支")
    print("-" * 60)
    
    try:
        join_result = client.join_branch(branch_id, role="narrator")
        turn_order = join_result.get("your_turn_order", "N/A")
        print(f"✅ 加入成功，轮次位置: {turn_order}")
    
    except Exception as e:
        print(f"⚠️  加入分支失败或已加入: {e}")
        # 继续尝试续写
    
    # 5. 生成续写内容
    print("\n" + "-" * 60)
    print("步骤 5: 生成续写内容")
    print("-" * 60)
    
    try:
        # 获取分支摘要
        try:
            summary_data = client.get_branch_summary(branch_id)
            summary = summary_data.get("summary", "")
        except:
            summary = None
        
        # 构建续写上下文
        story_background = selected_story.get("background", "")
        style_rules = selected_story.get("style_rules", "")
        
        # 生成续写内容
        print("正在调用 LLM 生成续写内容...")
        
        try:
            # 获取分支摘要
            try:
                summary_data = client.get_branch_summary(branch_id)
                story_summary = summary_data.get("summary", "")
            except:
                story_summary = ""
            
            # 使用 LLM 客户端的专用方法
            content = llm_client.generate_story_continuation(
                story_title=selected_story.get("title", ""),
                story_background=story_background,
                style_rules=style_rules or "保持连贯、细节明确，中文 150-500 字续写。",
                previous_segments=segments,
                language="zh",
                story_summary=story_summary
            )
            
            print(f"✅ 生成续写内容成功，长度: {len(content)} 字符")
        
        except Exception as e:
            print(f"⚠️  LLM 生成失败: {e}")
            print("使用备用续写内容进行测试...")
            
            # 使用简单的备用内容
            if segments:
                last_content = segments[-1].get("content", "")
                content = f"继续着前行的脚步，{last_content[:50]}...新的发现等待着探索者。"
            else:
                content = "林晓深吸一口气，调整了防护服的面罩。未知的星球表面在脚下延伸，每一步都可能是新的发现。她启动了扫描设备，准备深入探索这个神秘的世界。"
            
            print(f"✅ 使用备用内容，长度: {len(content)} 字符")
        
        print(f"\n续写内容预览:")
        print("-" * 60)
        print(content[:200] + "..." if len(content) > 200 else content)
        print("-" * 60)
    
    except Exception as e:
        print(f"❌ 生成续写内容失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 提交续写
    print("\n" + "-" * 60)
    print("步骤 6: 提交续写")
    print("-" * 60)
    
    try:
        result = client.submit_segment(branch_id, content)
        segment = result.get("segment", {})
        
        print("✅ 续写提交成功！")
        print(f"- Segment ID: {segment.get('id')}")
        print(f"- 内容长度: {len(content)} 字符")
        
        next_bot = result.get("next_bot")
        if next_bot:
            print(f"- 下一位续写者: {next_bot.get('name')}")
        
        return True
    
    except Exception as e:
        error_msg = str(e)
        if "NOT_YOUR_TURN" in error_msg:
            print(f"⚠️  不是你的轮次: {error_msg}")
            print("提示: 需要等待轮到你才能续写")
        elif "COHERENCE_CHECK_FAILED" in error_msg:
            print(f"❌ 连续性校验失败: {error_msg}")
            print("提示: 续写内容需要与前文更连贯")
        else:
            print(f"❌ 提交续写失败: {e}")
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_continue_story()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

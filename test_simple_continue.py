#!/usr/bin/env python3
"""简单的续写测试 - 使用手动指定的分支 ID 和内容"""
import os
import sys
from dotenv import load_dotenv

from src.inkpath_client import InkPathClient

load_dotenv()


def test_simple_continue():
    """简单续写测试"""
    print("=" * 60)
    print("简单续写测试")
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
    
    # 测试 1: 验证 API Key 是否有效
    print("\n" + "-" * 60)
    print("测试 1: 验证 API Key")
    print("-" * 60)
    
    try:
        stories = client.get_stories(limit=1)
        print(f"✅ API Key 有效，找到 {len(stories)} 个故事")
        if stories:
            print(f"   示例故事: {stories[0].get('title', 'N/A')}")
    except Exception as e:
        print(f"❌ API Key 验证失败: {e}")
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n提示: API Key 可能无效或已过期，请检查 .env 文件中的配置")
        return False
    
    # 测试 2: 获取故事和分支
    print("\n" + "-" * 60)
    print("测试 2: 获取可续写的分支")
    print("-" * 60)
    
    try:
        stories = client.get_stories(limit=5)
        if not stories:
            print("❌ 没有可用的故事")
            return False
        
        # 选择第一个故事
        story = stories[0]
        story_id = story["id"]
        print(f"✅ 选择故事: {story.get('title')} (ID: {story_id})")
        
        # 获取分支
        branches = client.get_branches(story_id, limit=3)
        if not branches:
            print("❌ 没有可用的分支")
            return False
        
        branch = branches[0]
        branch_id = branch["id"]
        print(f"✅ 选择分支: {branch.get('title')} (ID: {branch_id})")
        
        # 获取分支详情
        branch_detail = client.get_branch(branch_id)
        segments = branch_detail.get("segments", [])
        active_bots = branch_detail.get("active_bots", [])
        
        print(f"✅ 当前续写段数: {len(segments)}")
        print(f"✅ 活跃 Bot 数: {len(active_bots)}")
        
        if segments:
            print("\n最后一段续写:")
            last_seg = segments[-1]
            print(f"  {last_seg.get('content', '')[:100]}...")
    
    except Exception as e:
        print(f"❌ 获取分支信息失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试 3: 加入分支（续写前必需步骤）
    print("\n" + "-" * 60)
    print("测试 3: 加入分支（续写前必需）")
    print("-" * 60)
    print("提示: 根据 InkPath 文档，续写前必须先加入分支")
    
    join_success = False
    try:
        join_result = client.join_branch(branch_id, role="narrator")
        turn_order = join_result.get("your_turn_order", "N/A")
        print(f"✅ 加入成功，轮次位置: {turn_order}")
        join_success = True
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print(f"❌ 加入失败: API Key 未授权")
            print("   请检查 API Key 是否正确，或重新注册 Bot 获取新的 API Key")
            return False
        elif "already" in error_msg.lower() or "已加入" in error_msg or "already joined" in error_msg.lower():
            print(f"⚠️  已加入该分支: {error_msg}")
            print("   继续尝试续写...")
            join_success = True  # 已加入也算成功
        else:
            print(f"❌ 加入分支失败: {e}")
            print("   无法继续，因为续写前必须先加入分支")
            return False
    
    if not join_success:
        print("❌ 未能成功加入分支，无法继续续写")
        return False
    
    # 测试 4: 生成并提交续写内容
    print("\n" + "-" * 60)
    print("测试 4: 生成续写内容")
    print("-" * 60)
    
    # 简单的续写内容（用于测试）
    if segments:
        last_content = segments[-1].get("content", "")
        # 基于前文生成简单的续写
        content = f"继续前行，{last_content[:30]}...新的发现等待着探索者。林晓调整了设备，准备深入探索这个神秘的世界。每一步都充满了未知，但她知道，只有继续前进，才能找到答案。"
    else:
        # 如果没有前文，使用故事背景生成
        content = "林晓深吸一口气，调整了防护服的面罩。未知的星球表面在脚下延伸，每一步都可能是新的发现。她启动了扫描设备，准备深入探索这个神秘的世界。空气中弥漫着一种奇异的气息，让她既兴奋又紧张。"
    
    # 确保长度符合要求
    if len(content) < 150:
        content = content + " " * (150 - len(content))
    if len(content) > 500:
        content = content[:500]
    
    print(f"✅ 生成续写内容，长度: {len(content)} 字符")
    print(f"\n续写内容:")
    print("-" * 60)
    print(content)
    print("-" * 60)
    
    # 测试 5: 提交续写（必须在 join 之后）
    print("\n" + "-" * 60)
    print("测试 5: 提交续写（已加入分支）")
    print("-" * 60)
    print("提示: 只有加入分支后才能提交续写，且必须按轮次顺序")
    
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
        if "401" in error_msg or "Unauthorized" in error_msg:
            print(f"❌ 提交失败: API Key 未授权")
            print("   请检查 API Key 是否正确")
        elif "NOT_YOUR_TURN" in error_msg:
            print(f"⚠️  不是你的轮次: {error_msg}")
            print("   提示: 需要等待轮到你才能续写")
        elif "COHERENCE_CHECK_FAILED" in error_msg:
            print(f"❌ 连续性校验失败: {error_msg}")
            print("   提示: 续写内容需要与前文更连贯")
        else:
            print(f"❌ 提交续写失败: {e}")
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_simple_continue()
        if success:
            print("\n" + "=" * 60)
            print("✅ 测试完成！续写成功提交")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  测试完成，但续写未成功提交")
            print("=" * 60)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

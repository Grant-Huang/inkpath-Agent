#!/usr/bin/env python3
"""测试 LLM (MiniMax) 功能"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from src.llm_client import get_llm_client

def test_llm():
    """测试 LLM 功能"""
    print("=" * 60)
    print("LLM (MiniMax) 功能测试")
    print("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv("MINIMAX_API_KEY", "")
    group_id = os.getenv("MINIMAX_GROUP_ID", "")
    
    if not api_key or api_key == "your_minimax_api_key_here":
        print("\n❌ 错误: MINIMAX_API_KEY 未配置")
        print("请在 .env 文件中设置 MINIMAX_API_KEY")
        return False
    
    if not group_id or group_id == "your_minimax_group_id_here":
        print("\n⚠️  警告: MINIMAX_GROUP_ID 未配置")
        print("某些 MiniMax API 可能需要 Group ID，将尝试不使用 Group ID 进行测试")
        use_group_id = False
    else:
        use_group_id = True
    
    print(f"\n✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"✅ Group ID: {group_id[:8]}...{group_id[-4:]}")
    
    # 初始化客户端
    print("\n正在初始化 MiniMax 客户端...")
    try:
        llm_client = get_llm_client()
        print("✅ 客户端初始化成功")
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        return False
    
    # 测试简单生成
    print("\n" + "-" * 60)
    print("测试 1: 简单对话")
    print("-" * 60)
    
    test_prompt = "请用一句话介绍你自己。"
    print(f"\n提示词: {test_prompt}")
    print("\n生成中...")
    
    try:
        response = llm_client.generate(test_prompt)
        print(f"\n✅ 响应成功:")
        print(f"{'=' * 60}")
        print(response)
        print(f"{'=' * 60}")
        print(f"\n响应长度: {len(response)} 字符")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试故事续写
    print("\n" + "-" * 60)
    print("测试 2: 故事续写（模拟实际使用场景）")
    print("-" * 60)
    
    story_background = "在一个遥远的未来，人类已经掌握了星际旅行技术。"
    style_rules = "保持科幻风格，注重细节描写"
    previous_segments = [
        {"content": "船长站在舰桥上，凝视着前方未知的星系。"},
        {"content": "突然，雷达上出现了一个异常信号。"}
    ]
    
    context_parts = []
    context_parts.append(f"故事背景：\n{story_background}\n")
    context_parts.append(f"写作规范：\n{style_rules}\n")
    context_parts.append("前文：\n")
    for seg in previous_segments:
        context_parts.append(f"- {seg['content']}\n")
    
    context = "\n".join(context_parts)
    
    prompt = f"""
{context}

请续写下一段（150-500 字），要求：
1. 保持与前文的连贯性
2. 符合写作规范
3. 推进故事情节
4. 保持风格一致
5. 内容生动有趣，有画面感

续写内容：
"""
    
    print(f"\n故事背景: {story_background}")
    print(f"前文段落数: {len(previous_segments)}")
    print("\n生成中...")
    
    try:
        response = llm_client.generate(prompt, system_prompt="你是一位专业的故事续写助手，擅长创作连贯、有趣的故事内容。")
        print(f"\n✅ 续写成功:")
        print(f"{'=' * 60}")
        print(response)
        print(f"{'=' * 60}")
        print(f"\n续写长度: {len(response)} 字符")
        
        # 检查长度是否符合要求
        if len(response) < 150:
            print(f"⚠️  警告: 续写内容过短 ({len(response)} 字)，建议至少 150 字")
        elif len(response) > 500:
            print(f"⚠️  警告: 续写内容过长 ({len(response)} 字)，建议不超过 500 字")
        else:
            print(f"✅ 长度符合要求 (150-500 字)")
        
    except Exception as e:
        print(f"\n❌ 续写失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_llm()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

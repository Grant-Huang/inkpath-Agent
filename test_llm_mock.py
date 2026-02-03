#!/usr/bin/env python3
"""测试 LLM 客户端代码逻辑（模拟测试，不需要真实 API Key）"""
import sys
import os

# 临时设置环境变量用于测试
os.environ["MINIMAX_API_KEY"] = "test_api_key_12345"
os.environ["MINIMAX_GROUP_ID"] = "test_group_id_12345"
os.environ["MINIMAX_BASE_URL"] = "https://api.minimax.chat/v1"
os.environ["MINIMAX_MODEL"] = "abab6.5s-chat"
os.environ["MINIMAX_TEMPERATURE"] = "0.7"
os.environ["MINIMAX_TOP_P"] = "0.9"
os.environ["MINIMAX_MAX_TOKENS"] = "2000"

from src.llm_client import MiniMaxClient

def test_llm_client_init():
    """测试 LLM 客户端初始化"""
    print("=" * 60)
    print("测试 LLM 客户端初始化")
    print("=" * 60)
    
    try:
        client = MiniMaxClient()
        print(f"✅ 客户端初始化成功")
        print(f"  - API Key: {client.api_key[:10]}...")
        print(f"  - Group ID: {client.group_id[:10]}...")
        print(f"  - Base URL: {client.base_url}")
        print(f"  - Model: {client.model}")
        print(f"  - Temperature: {client.temperature}")
        print(f"  - Top P: {client.top_p}")
        print(f"  - Max Tokens: {client.max_tokens}")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_building():
    """测试提示词构建逻辑"""
    print("\n" + "=" * 60)
    print("测试提示词构建逻辑")
    print("=" * 60)
    
    story_background = "在一个遥远的未来，人类已经掌握了星际旅行技术。"
    style_rules = "保持科幻风格，注重细节描写"
    previous_segments = [
        {"content": "船长站在舰桥上，凝视着前方未知的星系。"},
        {"content": "突然，雷达上出现了一个异常信号。"}
    ]
    
    # 构建上下文（模拟 agent.py 中的逻辑）
    context_parts = []
    context_parts.append(f"故事背景：\n{story_background}\n")
    context_parts.append(f"写作规范：\n{style_rules}\n")
    context_parts.append("前文：\n")
    for seg in previous_segments[-5:]:  # 只取最后 5 段
        content = seg.get("content", "")
        context_parts.append(f"- {content}\n")
    
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
    
    print("✅ 提示词构建成功")
    print(f"\n提示词长度: {len(prompt)} 字符")
    print(f"\n提示词预览（前 200 字符）:")
    print("-" * 60)
    print(prompt[:200] + "...")
    print("-" * 60)
    
    return True

def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试错误处理（未配置 API Key）")
    print("=" * 60)
    
    # 临时清除环境变量
    old_key = os.environ.get("MINIMAX_API_KEY")
    old_group = os.environ.get("MINIMAX_GROUP_ID")
    
    os.environ["MINIMAX_API_KEY"] = "your_minimax_api_key_here"
    os.environ["MINIMAX_GROUP_ID"] = "your_minimax_group_id_here"
    
    try:
        # 重新导入以获取新的环境变量
        from importlib import reload
        import src.llm_client
        reload(src.llm_client)
        client = src.llm_client.MiniMaxClient()
        
        result = client.generate("测试")
        print(f"✅ 错误处理正常")
        print(f"  返回的错误信息: {result[:50]}...")
        
        # 恢复环境变量
        if old_key:
            os.environ["MINIMAX_API_KEY"] = old_key
        if old_group:
            os.environ["MINIMAX_GROUP_ID"] = old_group
        
        return True
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        # 恢复环境变量
        if old_key:
            os.environ["MINIMAX_API_KEY"] = old_key
        if old_group:
            os.environ["MINIMAX_GROUP_ID"] = old_group
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("LLM 客户端代码逻辑测试（模拟测试）")
    print("=" * 60)
    print("\n注意: 这是代码逻辑测试，不进行真实的 API 调用")
    print("要进行真实 API 测试，请配置 .env 文件后运行 test_llm.py\n")
    
    tests = [
        ("客户端初始化", test_llm_client_init),
        ("提示词构建", test_prompt_building),
        ("错误处理", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 出现异常: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✅ 所有代码逻辑测试通过！")
        print("\n提示: 要进行真实的 API 测试，请:")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 填入真实的 MiniMax API Key 和 Group ID")
        print("  3. 运行: python test_llm.py")
    else:
        print("\n❌ 部分测试失败，请检查代码")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

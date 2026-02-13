#!/usr/bin/env python3
"""测试用 Qwen 续写故事并提交 - 显示完整提示词和 LLM 反馈"""
import os
import sys
from dotenv import load_dotenv

from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client

load_dotenv()


def main():
    print("=" * 70)
    print("测试：用 Qwen (Ollama) 续写故事并提交")
    print("=" * 70)

    # 1. 检查 Ollama/Qwen
    print("\n[1] 检查 Ollama / Qwen...")
    try:
        llm = create_llm_client(provider="ollama")
        print(f"    ✅ 使用 Ollama 模型: {llm.ollama_model}")
    except Exception as e:
        print(f"    ❌ Ollama 不可用: {e}")
        print("    请先安装并运行 Ollama，并拉取 qwen 模型: ollama pull qwen3:32b")
        sys.exit(1)

    # 2. 检查 InkPath
    api_key = os.getenv("INKPATH_API_KEY", "")
    if not api_key or api_key == "your_inkpath_api_key_here":
        print("\n❌ INKPATH_API_KEY 未配置")
        sys.exit(1)

    api_base = os.getenv("INKPATH_BASE_URL", "https://inkpath-api.onrender.com/api/v1")
    client = InkPathClient(api_base, api_key)

    # 3. 获取故事和分支
    print("\n[2] 获取故事和分支...")
    stories = client.get_stories(limit=5)
    if not stories:
        print("    ❌ 没有可用故事")
        sys.exit(1)

    story = stories[0]
    story_id = story["id"]
    branches = client.get_branches(story_id, limit=3)
    if not branches:
        print("    ❌ 没有可用分支")
        sys.exit(1)

    branch = branches[0]
    branch_id = branch["id"]
    branch_detail = client.get_branch(branch_id)
    segments = branch_detail.get("segments", [])

    print(f"    故事: {story.get('title')}")
    print(f"    分支: {branch.get('title')}")
    print(f"    片段数: {len(segments)}")

    # 4. 获取摘要
    story_summary = ""
    try:
        summary_data = client.get_branch_summary(branch_id)
        story_summary = summary_data.get("summary", "")
        print(f"    摘要: {len(story_summary)} 字")
    except Exception as e:
        print(f"    ⚠️ 获取摘要失败: {e}")

    # 5. 获取角色、大纲（若有 story_pack）
    story_pack = story.get("story_pack") or {}
    metadata = story_pack.get("metadata", {}) if isinstance(story_pack, dict) else {}
    characters = story_pack.get("characters", []) if isinstance(story_pack, dict) else []
    outline = story_pack.get("outline", []) if isinstance(story_pack, dict) else []

    # 6. 构建并显示提示词（手动构建，与 llm_client 一致）
    from src.llm_client import LLMClient
    _llm = LLMClient(provider="ollama")
    context = {
        "title": story.get("title", ""),
        "background": story.get("background", ""),
        "style": story.get("style_rules", "保持一致的叙事风格"),
        "previous_segments": "\n".join([s.get("content", "") for s in segments[-5:]]),
        "segment_count": len(segments),
        "summary": story_summary,
        "metadata": metadata,
        "characters": characters,
        "outline": outline,
    }
    prompt = _llm._build_prompt(context)

    print("\n" + "=" * 70)
    print("【发送给 Qwen 的完整提示词】")
    print("=" * 70)
    print(prompt)
    print("=" * 70)

    # 7. 调用 Qwen 生成
    print("\n[3] 调用 Qwen 生成续写...")
    try:
        content = llm.generate_story_continuation(
            story_title=story.get("title", ""),
            story_background=story.get("background", ""),
            style_rules=story.get("style_rules", ""),
            previous_segments=segments,
            language=story.get("language", "zh"),
            story_summary=story_summary,
            story_metadata=metadata,
            story_characters=characters,
            story_outline=outline,
        )
    except Exception as e:
        print(f"    ❌ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("【Qwen 的续写反馈】")
    print("=" * 70)
    print(content)
    print("=" * 70)
    print(f"\n    字数: {len(content)}")

    # 8. 加入分支并提交
    print("\n[4] 加入分支并提交续写...")
    try:
        client.join_branch(branch_id, role="narrator")
        print("    ✅ 已加入分支")
    except Exception as e:
        if "already" in str(e).lower() or "已加入" in str(e):
            print("    ⚠️ 已加入该分支，继续提交...")
        else:
            print(f"    ⚠️ 加入失败: {e}")

    try:
        result = client.submit_segment(branch_id, content)
        seg = result.get("segment", {})
        print(f"    ✅ 续写已提交! 段 ID: {seg.get('id', 'N/A')}")
        nb = result.get("next_bot")
        if nb:
            print(f"    下一位: {nb.get('name', 'N/A')}")
    except Exception as e:
        print(f"    ❌ 提交失败: {e}")
        if "NOT_YOUR_TURN" in str(e):
            print("    （不是你的轮次）")
        elif "COHERENCE" in str(e):
            print("    （连续性校验失败）")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()

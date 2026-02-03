#!/usr/bin/env python3
"""测试 InkPath：创建故事 或 加入分支并续写一段"""

from __future__ import annotations

import os
import sys
import argparse

from dotenv import load_dotenv

from src.inkpath_client import InkPathClient


def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val or val.startswith("your_"):
        raise SystemExit(f"缺少环境变量 {name}，请在本地 .env 中配置后再试。")
    return val


def cmd_create_story(client: InkPathClient, title: str, background: str) -> int:
    data = client.create_story(title=title, background=background, style_rules="保持连贯、细节明确，中文 150-500 字续写。")
    story_id = data.get("id")
    print("✅ 创建故事成功")
    print(f"- story_id: {story_id}")
    print(f"- title: {data.get('title')}")
    return 0


def cmd_continue_branch(client: InkPathClient, branch_id: str, content: str) -> int:
    # 先加入（如果已经加入，服务端可能返回成功或提示已加入）
    try:
        join_data = client.join_branch(branch_id=branch_id, role="narrator")
        print("✅ join_branch 成功")
        print(f"- your_turn_order: {join_data.get('your_turn_order')}")
    except Exception as e:
        print(f"⚠️ join_branch 失败或已加入：{e}")

    # 再提交续写
    seg_data = client.submit_segment(branch_id=branch_id, content=content)
    seg = seg_data.get("segment", {})
    print("✅ submit_segment 成功")
    print(f"- segment_id: {seg.get('id')}")
    nb = seg_data.get("next_bot")
    if nb:
        print(f"- next_bot: {nb.get('name')}")
    return 0


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("create_story", help="创建一个故事")
    p1.add_argument("--title", required=True)
    p1.add_argument("--background", required=True)

    p2 = sub.add_parser("continue_branch", help="加入分支并提交一段续写")
    p2.add_argument("--branch-id", required=True)
    p2.add_argument(
        "--content",
        required=True,
        help="续写内容（建议 150-500 字，且必须轮到你才会成功）",
    )

    args = parser.parse_args()

    api_base = os.getenv("INKPATH_BASE_URL", "https://inkpath-api.onrender.com/api/v1").strip()
    api_key = _require_env("INKPATH_API_KEY")

    client = InkPathClient(api_base=api_base, api_key=api_key)

    if args.cmd == "create_story":
        return cmd_create_story(client, title=args.title, background=args.background)

    if args.cmd == "continue_branch":
        return cmd_continue_branch(client, branch_id=args.branch_id, content=args.content)

    raise SystemExit("未知命令")


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
完整测试脚本：推送 story_pack 并续写故事

Usage:
    python3 run_test.py              # 运行测试
    python3 run_test.py --push-only  # 只推送 story_pack
    python3 run_test.py --continue-only  # 只续写
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.inkpath_client import InkPathClient
import yaml


def count_chinese(text: str) -> int:
    """计算中文字数"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def call_ollama(prompt: str, model: str = "mistral:latest", timeout: int = 120) -> str:
    """调用 Ollama API"""
    import requests
    
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 1000
        }
    }
    
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    
    return response.json().get("response", "")


def push_story_package(client, story_id: str, package_path: str) -> bool:
    """推送 story_pack 到故事"""
    pkg_path = Path(package_path)
    
    # Load all story package files
    files = {}
    file_map = {
        'meta': '00_meta.md',
        'evidence_pack': '10_evidence_pack.md',
        'stance_pack': '20_stance_pack.md',
        'cast': '30_cast.md',
        'plot_outline': '40_plot_outline.md',
        'constraints': '50_constraints.md',
        'sources': '60_sources.md',
        'starter': '70_Starter.md'
    }
    
    for key, filename in file_map.items():
        filepath = pkg_path / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                files[key] = f.read()
            print(f"   ✅ Loaded {filename}")
    
    # Push story package
    print(f"\n📤 Pushing story package...")
    try:
        result = client.update_story_metadata(story_id, {'story_pack': files})
        if result:
            print(f"   ✅ Story package pushed successfully!")
            return True
        else:
            print(f"   ❌ Failed to push story package")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def continue_story(client, story_id: str, package_path: str, model: str = "mistral:latest") -> bool:
    """续写故事"""
    # Get story
    story = client.get_story(story_id)
    if not story:
        print(f"   ❌ Story not found")
        return False
    
    print(f"\n📖 Story: {story.get('title', 'Unknown')}")
    
    # Get branches
    branches = client.get_branches(story_id, limit=10)
    if not branches:
        print(f"   ❌ No branches found")
        return False
    
    branch = branches[-1]
    branch_id = branch.get('id')
    print(f"   🌿 Branch: {branch_id[:12]}...")
    
    # Get full story
    full = client.get_branch_full_story(branch_id)
    if not full:
        print(f"   ❌ Failed to get branch story")
        return False
    
    segments = full.get('segments', [])
    print(f"   📄 Segments: {len(segments)}")
    
    # Build previous content
    previous = [s.get('content', '') for s in segments[-3:]]
    previous_text = '\n\n---\n\n'.join(previous)
    
    # Load story package for context
    pkg_path = Path(package_path)
    starter_path = pkg_path / '70_Starter.md'
    if starter_path.exists():
        with open(starter_path, 'r', encoding='utf-8') as f:
            starter = f.read()
    else:
        starter = ""
    
    # Build prompt
    prompt = f"""你是一个专业的故事作家，为协作故事平台续写内容。

## 故事背景
{story.get('background', '')[:500]}

## 开篇（故事起点）
{starter[:500] if starter else '无'}

## 前文（最近{len(previous)}段）
{previous_text if previous_text else '无前文'}

## 续写要求
- 字数：300-500字
- 风格：克制、冷峻、悬念
- 必须自然承接上一段结尾
- 推进剧情，不能原地踏步
- 保持与开篇风格一致

请直接输出续写内容，不要有任何前缀说明。
"""
    
    # Call Ollama
    print(f"\n🤖 Calling Ollama ({model})...")
    try:
        content = call_ollama(prompt, model=model, timeout=180)
    except Exception as e:
        print(f"   ❌ Ollama error: {e}")
        return False
    
    if not content:
        print(f"   ❌ Empty response from Ollama")
        return False
    
    # Validate length
    char_count = count_chinese(content)
    print(f"   📊 Generated: {char_count} Chinese chars")
    
    min_len = story.get('min_length', 150)
    max_len = story.get('max_length', 500)
    
    # Expand if too short
    while char_count < min_len:
        content += "\n他陷入了沉思。"
        char_count = count_chinese(content)
    
    # Truncate if too long
    if char_count > max_len:
        sentences = content.split('。')
        content = '。'.join(sentences[:-1]) + '。'
        char_count = count_chinese(content)
    
    print(f"   📊 Final: {char_count} Chinese chars")
    
    # Submit
    print(f"\n📤 Submitting segment...")
    try:
        result = client.submit_segment(branch_id, content)
        if result:
            print(f"   ✅ Story continued successfully!")
            
            # Log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'continue_story',
                'status': 'success',
                'story_id': story_id,
                'branch_id': branch_id,
                'segment_count': len(segments) + 1,
                'char_count': char_count,
                'model': model
            }
            
            log_dir = ROOT / 'logs'
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"continue_test_{datetime.now().strftime('%Y-%m-%d')}.md"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"## {log_entry['timestamp']} - continue_test\n")
                f.write(f"```json\n{json.dumps(log_entry, ensure_ascii=False, indent=2)}\n```\n\n")
            
            return True
        else:
            print(f"   ❌ Submission failed")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test story continuation')
    parser.add_argument('--push-only', action='store_true', help='Only push story package')
    parser.add_argument('--continue-only', action='store_true', help='Only continue story')
    parser.add_argument('--model', default='mistral:latest', help='LLM model')
    parser.add_argument('--story-id', help='Specific story ID')
    parser.add_argument('--package', default='../inkpath/story-packages/han-234-weiyan-mystery',
                       help='Story package path')
    
    args = parser.parse_args()
    
    print("="*60)
    print("InkPath - Story Continuation Test")
    print("="*60)
    
    # Load config
    with open(ROOT / 'config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Create client
    client = InkPathClient(
        api_base=config['api']['base_url'],
        api_key=config['api']['api_key']
    )
    
    # Find story
    print(f"\n🔍 Searching for '丞相府书吏' story...")
    
    if args.story_id:
        story_id = args.story_id
        story = client.get_story(story_id)
    else:
        stories = client.get_stories(limit=100)
        story = None
        for s in stories:
            if '丞相' in s.get('title', ''):
                story = s
                break
        story_id = story.get('id') if story else None
    
    if not story_id:
        print(f"   ❌ Story not found!")
        stories = client.get_stories(limit=10)
        print(f"   Available stories:")
        for s in stories:
            print(f"      - {s.get('title', 'Unknown')} ({s.get('id', 'N/A')[:8]}...)")
        return 1
    
    print(f"   ✅ Found: {story.get('title', 'Unknown')} ({story_id[:12]}...)")
    
    # Push story package
    if not args.continue_only:
        push_story_package(client, story_id, args.package)
    
    # Continue story
    if not args.push_only:
        continue_story(client, story_id, args.package, model=args.model)
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Push Story Package and Run Agent

This script:
1. Pushes story package (including starter) to Render
2. Runs the agent to continue the story

Usage:
    python3 run_full.py              # Run now
    python3 run_full.py --wait      # Wait for rate limit
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.inkpath_client import InkPathClient
from src.agent import InkPathAgent


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent / "config.yaml"
    import yaml
    with open(config_path) as f:
        return yaml.safe_load(f)


def find_target_story(client, keyword="丞相府书吏"):
    """Find the target story"""
    stories = client.get_stories(limit=100)
    
    for s in stories:
        if keyword in s.get("title", ""):
            return s
    
    # Try partial match
    for s in stories[:10]:
        if "丞相" in s.get("title", "") or "书吏" in s.get("title", ""):
            return s
    
    return None


def push_story_package(client, story_id, package_path):
    """Push story package to the story"""
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
    result = client.update_story_metadata(
        story_id,
        {
            'story_pack': files
        }
    )
    
    if result:
        print(f"   ✅ Story package pushed successfully!")
        return True
    else:
        print(f"   ❌ Failed to push story package")
        return False


def run_agent(client, config, story_id):
    """Run the agent to continue the story"""
    print(f"\n🤖 Starting agent...")
    
    agent = InkPathAgent(
        client=client,
        config=config.get('agent', {}),
        task_logger=type('Logger', (), {'info': print, 'error': print, 'warning': print})()
    )
    
    # Get story and continue
    story = client.get_story(story_id)
    if not story:
        print(f"   ❌ Story not found")
        return False
    
    branches = client.get_branches(story_id, limit=10)
    if not branches:
        print(f"   ❌ No branches found")
        return False
    
    # Use the latest branch
    branch = branches[-1]
    branch_id = branch.get('id')
    
    print(f"   📖 Using branch: {branch_id[:12]}...")
    
    # Get full story
    full = client.get_branch_full_story(branch_id)
    if not full:
        print(f"   ❌ Failed to get branch story")
        return False
    
    # Continue
    success = agent._do_continue(
        story=full.get('story', {}),
        branch=full.get('branch', {}),
        segments=full.get('segments', [])
    )
    
    if success:
        print(f"   ✅ Story continued successfully!")
    else:
        print(f"   ❌ Failed to continue story")
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Push story package and run agent')
    parser.add_argument('--wait', action='store_true', help='Wait for rate limit to clear')
    parser.add_argument('--package', default='../inkpath/story-packages/han-234-weiyan-mystery',
                       help='Story package path')
    args = parser.parse_args()
    
    print("="*60)
    print("InkPath - Push Package & Run Agent")
    print("="*60)
    
    # Load config
    config = load_config()
    
    # Create client
    client = InkPathClient(
        api_base=config['api']['base_url'],
        api_key=config['api']['api_key']
    )
    
    # Find target story
    print(f"\n🔍 Searching for '丞相府书吏' story...")
    story = find_target_story(client)
    
    if not story:
        print(f"   ❌ Story not found!")
        print(f"   Available stories:")
        stories = client.get_stories(limit=10)
        for s in stories:
            print(f"      - {s.get('title', 'Unknown')} ({s.get('id', 'N/A')[:8]}...)")
        return 1
    
    story_id = story.get('id')
    print(f"   ✅ Found: {story.get('title')} ({story_id[:12]}...)")
    
    # Push story package
    push_success = push_story_package(client, story_id, args.package)
    
    # Run agent
    if push_success:
        run_agent(client, config, story_id)
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

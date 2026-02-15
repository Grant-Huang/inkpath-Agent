#!/usr/bin/env python3
"""
使用故事包创建新故事

Usage:
    python3 create_from_package.py
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.inkpath_client import InkPathClient
import yaml


def load_story_package(pkg_path: str) -> dict:
    """加载故事包"""
    pkg_path = Path(pkg_path)
    
    files = {}
    file_map = {
        'meta': '00_meta.md',
        'evidence_pack': '10_evidence_pack.md',
        'stance_pack': '20_stance_pack.md',
        'cast': '30_cast.md',
        'locations': '31_locations.md',
        'objects_terms': '32_objects_terms.md',
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
    
    return files


def extract_meta(files: dict) -> dict:
    """从 meta 文件提取故事信息"""
    import re
    
    content = files.get('meta', '')
    
    # 提取 title
    title_match = re.search(r'title:\s*"([^"]+)"', content)
    title = title_match.group(1) if title_match else "丞相府书吏"
    
    # 提取 logline
    logline_match = re.search(r'logline:\s*"([^"]+)"', content)
    logline = logline_match.group(1) if logline_match else ""
    
    # 提取 tone
    tone_match = re.search(r'tone:\s*\[([^\]]+)\]', content)
    tone = tone_match.group(1).replace('"', '') if tone_match else "克制,冷峻,悬念"
    
    # 提取 genre
    genre_match = re.search(r'genre:\s*\[([^\]]+)\]', content)
    genre = genre_match.group(1).replace('"', '') if genre_match else "历史悬疑"
    
    # 提取 era
    era_match = re.search(r'era:\s*"([^"]+)"', content)
    era = era_match.group(1) if era_match else "蜀汉后期"
    
    return {
        'title': title,
        'background': logline,
        'style_rules': tone,
        'language': 'zh',
        'min_length': 150,
        'max_length': 500,
        'era': era,
        'genre': genre
    }


def main():
    print("="*60)
    print("使用故事包创建新故事")
    print("="*60)
    
    # Load config
    with open(ROOT / 'config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Create client
    client = InkPathClient(
        api_base=config['api']['base_url'],
        api_key=config['api']['api_key']
    )
    
    # Load story package
    pkg_path = ROOT / '../inkpath/story-packages/han-234-weiyan-mystery'
    print(f"\n📦 加载故事包: {pkg_path}")
    
    files = load_story_package(pkg_path)
    
    if not files:
        print("   ❌ 未找到故事包文件")
        return 1
    
    # Extract story info
    story_info = extract_meta(files)
    print(f"\n📖 故事信息:")
    for k, v in story_info.items():
        print(f"   {k}: {v}")
    
    # Create story
    print(f"\n📤 创建故事...")
    story = client.create_story(
        title=story_info['title'],
        background=story_info['background'],
        style_rules=story_info['style_rules'],
        language=story_info['language'],
        min_length=story_info['min_length'],
        max_length=story_info['max_length'],
        starter=files.get('starter', '')
    )
    
    if not story:
        print("   ❌ 创建故事失败")
        return 1
    
    story_id = story.get('id')
    print(f"   ✅ 故事创建成功!")
    print(f"   ID: {story_id}")
    
    # Push story pack
    print(f"\n📦 推送故事包...")
    result = client.update_story_metadata(story_id, {
        'story_pack': files,
        'story_pack_json': json.dumps({
            'meta': files.get('meta', ''),
            'cast': files.get('cast', ''),
            'plot_outline': files.get('plot_outline', ''),
            'constraints': files.get('constraints', ''),
            'evidence_pack': files.get('evidence_pack', ''),
            'stance_pack': files.get('stance_pack', ''),
            'locations': files.get('locations', ''),
            'objects_terms': files.get('objects_terms', ''),
            'sources': files.get('sources', ''),
            'starter': files.get('starter', '')
        })
    })
    
    if result:
        print(f"   ✅ 故事包推送成功!")
    else:
        print(f"   ⚠️  故事包推送失败，但故事已创建")
    
    print("\n" + "="*60)
    print(f"完成! 故事 ID: {story_id}")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

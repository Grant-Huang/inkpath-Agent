#!/usr/bin/env python3
"""
故事包生成器使用示例

展示如何：
1. 从提示词生成故事包
2. 使用 LLM 增强生成
3. 在 InkPath 上创建故事
"""

import sys
import os

# 添加项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def example_1_basic():
    """示例 1: 基础模板生成（无需 LLM）"""
    print("\n" + "=" * 60)
    print("📝 示例 1: 基础模板生成")
    print("=" * 60)
    
    from src.story_package_generator import StoryPackageGenerator
    
    # 创建生成器
    generator = StoryPackageGenerator(
        llm_client=None,  # 不使用 LLM
        story_packages_dir="./output-basic",
        research_enabled=False
    )
    
    # 提示词
    prompt = """写一个关于唐朝贞观之治的故事。
类型：历史正剧
风格：参考《明朝那些事儿》
"""
    
    # 生成
    result = generator.generate_from_prompt(
        prompt=prompt,
        save_to_disk=True,
        create_on_inkpath=False
    )
    
    print(f"✅ 标题: {result['requirements'].title}")
    print(f"✅ 时代: {result['requirements'].era}")
    print(f"✅ 生成文件: {result['files']}")


def example_2_with_llm():
    """示例 2: 使用 LLM 增强生成"""
    print("\n" + "=" * 60)
    print("🤖 示例 2: 使用 LLM 增强生成")
    print("=" * 60)
    
    try:
        from src.llm_client import create_llm_client
        from src.story_package_generator import StoryPackageGenerator
        
        # 创建 LLM 客户端
        llm = create_llm_client(provider='ollama')
        
        # 创建生成器
        generator = StoryPackageGenerator(
            llm_client=llm,
            story_packages_dir="./output-llm",
            research_enabled=False
        )
        
        # 提示词
        prompt = """参考马伯庸的《风起陇西》，
写一个三国时期诸葛亮北伐的故事。
从一个小兵的视角看这场战争。
核心冲突是：明知不可为而为之。
类型：历史战争、史诗
"""
        
        # 生成
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=False
        )
        
        print(f"✅ 标题: {result['requirements'].title}")
        print(f"✅ 时代: {result['requirements'].era}")
        print(f"✅ 类型: {result['requirements'].genre}")
        print(f"✅ 风格: {result['requirements'].style_reference}")
        print(f"✅ 生成文件: {result['files']}")
        
    except Exception as e:
        print(f"⚠️ 需要 Ollama 运行: {e}")


def example_3_full():
    """示例 3: 完整生成（含研究）"""
    print("\n" + "=" * 60)
    print("🔍 示例 3: 完整生成（含背景研究）")
    print("=" * 60)
    
    try:
        from src.llm_client import create_llm_client
        from src.story_package_generator import StoryPackageGenerator
        
        # 创建 LLM 客户端
        llm = create_llm_client(provider='ollama')
        
        # 创建生成器（启用研究）
        generator = StoryPackageGenerator(
            llm_client=llm,
            story_packages_dir="./output-full",
            research_enabled=True  # 启用背景研究
        )
        
        # 提示词
        prompt = """写一个民国时期的谍战故事。
参考《潜伏》的风格。
主角是一个地下工作者，在敌占区收集情报。
核心冲突是：身份暴露的危机。
类型：谍战、悬疑
"""
        
        # 生成
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=False
        )
        
        print(f"✅ 标题: {result['requirements'].title}")
        print(f"✅ 时代: {result['requirements'].era}")
        print(f"✅ 类型: {result['requirements'].genre}")
        print(f"✅ 研究发现: {len(result.get('research', {}).get('findings', []))} 条")
        print(f"✅ 生成文件: {result['files']}")
        
    except Exception as e:
        print(f"⚠️ 需要 Ollama: {e}")


def example_4_inkpath():
    """示例 4: 在 InkPath 上创建故事"""
    print("\n" + "=" * 60)
    print("🌐 示例 4: 在 InkPath 上创建故事")
    print("=" * 60)
    
    api_key = input("请输入 InkPath API Key: ").strip()
    
    if not api_key:
        print("⚠️ 跳过: 需要 API Key")
        return
    
    try:
        from src.inkpath_client import InkPathClient
        from src.story_package_generator import StoryPackageGenerator
        
        # 创建 InkPath 客户端
        client = InkPathClient(
            api_base="https://inkpath-api.onrender.com/api/v1",
            api_key=api_key
        )
        
        # 创建生成器
        generator = StoryPackageGenerator(
            llm_client=None,
            inkpath_client=client,
            story_packages_dir="./output-inkpath",
            research_enabled=False
        )
        
        # 提示词
        prompt = """写一个科幻故事。
讲述人类在火星建立基地的故事。
类型：科幻、冒险
"""
        
        # 生成并创建
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=True  # 在 InkPath 上创建
        )
        
        print(f"✅ 标题: {result['requirements'].title}")
        print(f"✅ InkPath 故事ID: {result['story_id']}")
        print(f"✅ 保存路径: {result['package_path']}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


def example_5_custom():
    """示例 5: 自定义使用"""
    print("\n" + "=" * 60)
    print("⚙️ 示例 5: 自定义使用")
    print("=" * 60)
    
    from src.story_package_generator import (
        StoryPackageGenerator,
        StoryRequirements
    )
    
    # 直接创建需求对象
    requirements = StoryRequirements(
        title="新三国",
        subtitle="诸葛亮的最后一战",
        era="三国",
        time_window="234年",
        genre=["历史", "战争", "史诗"],
        tone=["悲壮", "史诗"],
        core_conflict="诸葛亮六出祁山，明知不可为而为之",
        logline="丞相最后一次北伐，一个小兵的视角",
        main_characters=["诸葛亮", "姜维", "一个小兵"],
        setting="五丈原",
        style_reference="马伯庸+指环王",
        canon_policy="respect_major_events",
        rating="PG-13",
        target_word_count=50000
    )
    
    print(f"✅ 需求对象创建成功:")
    print(f"   - 标题: {requirements.title}")
    print(f"   - 副标题: {requirements.subtitle}")
    print(f"   - 时代: {requirements.era}")
    print(f"   - 类型: {requirements.genre}")
    print(f"   - 风格: {requirements.style_reference}")
    print(f"   - 核心冲突: {requirements.core_conflict}")


def main():
    """主函数"""
    print("\n🚀 故事包生成器使用示例")
    print("=" * 60)
    
    examples = [
        ("基础模板生成", example_1_basic),
        ("LLM 增强生成", example_2_with_llm),
        ("完整生成（含研究）", example_3_full),
        ("在 InkPath 创建故事", example_4_inkpath),
        ("自定义使用", example_5_custom),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
        except Exception as e:
            print(f"❌ 示例 {i} 失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)
    print("\n📁 输出目录：")
    print("  - ./output-basic/")
    print("  - ./output-llm/")
    print("  - ./output-full/")
    print("  - ./output-inkpath/")


if __name__ == "__main__":
    main()

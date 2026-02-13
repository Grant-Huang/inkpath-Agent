#!/usr/bin/env python3
"""
故事包生成器测试脚本

演示如何使用 StoryPackageGenerator 从提示词生成故事包
"""

import sys
import os
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_simple_generation():
    """测试简单故事包生成（不使用 LLM）"""
    print("=" * 60)
    print("🧪 测试 1: 简单故事包生成（模板模式）")
    print("=" * 60)
    
    # 直接导入并实例化（不使用 LLM）
    from src.story_package_generator import StoryPackageGenerator
    
    # 创建生成器
    generator = StoryPackageGenerator(
        llm_client=None,  # 不使用 LLM
        story_packages_dir="./test-story-packages",
        research_enabled=False
    )
    
    # 测试提示词
    prompt = """参考马伯庸风格，写一个明朝锦衣卫的故事。
从一个小校尉的视角，看明朝末期的政治阴谋。
核心冲突是东厂与锦衣卫的权力斗争。
主角是一个刚入职的锦衣卫校尉，无意中发现了东厂的秘密。
"""
    
    # 生成故事包
    result = generator.generate_from_prompt(
        prompt=prompt,
        save_to_disk=True,
        create_on_inkpath=False
    )
    
    # 输出结果
    print(f"\n📋 结果摘要：")
    print(f"   - 标题: {result['requirements'].title}")
    print(f"   - 时代: {result['requirements'].era}")
    print(f"   - 类型: {result['requirements'].genre}")
    print(f"   - 风格: {result['requirements'].style_reference}")
    print(f"   - 核心冲突: {result['requirements'].core_conflict}")
    print(f"   - 保存路径: {result['package_path']}")
    print(f"   - 生成文件数: {len(result['files'])}")
    
    # 显示生成的文件
    print(f"\n📁 生成的文件：")
    for f in result['files']:
        print(f"   - {f}")
    
    return result


def test_with_llm():
    """测试使用 LLM 生成故事包"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 使用 LLM 生成故事包")
    print("=" * 60)
    
    try:
        # 导入 LLM 客户端
        from src.llm_client import create_llm_client
        
        # 创建 LLM 客户端
        llm = create_llm_client(provider='ollama')
        print("✅ LLM 客户端初始化成功")
        
        # 创建生成器
        generator = StoryPackageGenerator(
            llm_client=llm,
            story_packages_dir="./llm-story-packages",
            research_enabled=False
        )
        
        # 测试提示词
        prompt = """写一个科幻故事。
参考《三体》的风格，讲述人类第一次接收到外星信号的故事。
从地球上最后一个射电望远镜操作员的视角展开。
核心冲突是：要不要回应这个信号？
类型：科幻悬疑
"""
        
        # 生成故事包
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=False
        )
        
        print(f"\n📋 结果摘要：")
        print(f"   - 标题: {result['requirements'].title}")
        print(f"   - 时代: {result['requirements'].era or '未来'}")
        print(f"   - 类型: {result['requirements'].genre}")
        print(f"   - 风格: {result['requirements'].style_reference}")
        print(f"   - 核心冲突: {result['requirements'].core_conflict}")
        print(f"   - 生成文件数: {len(result['files'])}")
        
        return result
        
    except Exception as e:
        print(f"   ⚠️ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_full_package():
    """测试完整的故事包生成"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 完整故事包生成（魏延故事）")
    print("=" * 60)
    
    try:
        from src.llm_client import create_llm_client
        
        # 创建 LLM 客户端
        llm = create_llm_client(provider='ollama')
        
        # 创建生成器
        generator = StoryPackageGenerator(
            llm_client=llm,
            story_packages_dir="./full-story-packages",
            research_enabled=False
        )
        
        # 测试提示词（用户之前创建的魏延故事）
        prompt = """参考马伯庸的风起陇西的写作风格，参考指环王的史诗视角，
从小人物角度看三国后期魏延被杀事件（魏延有反骨），
按照inkpath要求写一个在蜀国由盛转衰的历史大事件中的小人物跌宕起伏，悬念迭起的故事。
"""
        
        # 生成故事包
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=False
        )
        
        print(f"\n📋 结果摘要：")
        print(f"   - 标题: {result['requirements'].title}")
        print(f"   - 时代: {result['requirements'].era}")
        print(f"   - 类型: {result['requirements'].genre}")
        print(f"   - 风格: {result['requirements'].style_reference}")
        print(f"   - 核心冲突: {result['requirements'].core_conflict}")
        print(f"   - 保存路径: {result['package_path']}")
        print(f"   - 生成文件数: {len(result['files'])}")
        
        # 显示生成的文件内容摘要
        print(f"\n📁 生成的文件：")
        for f in result['files']:
            filepath = os.path.join(result['package_path'], f)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"   - {f} ({size} bytes)")
        
        # 显示部分内容
        meta_file = os.path.join(result['package_path'], '00_meta.md')
        if os.path.exists(meta_file):
            print(f"\n📄 元数据文件内容预览：")
            with open(meta_file, 'r', encoding='utf-8') as file:
                content = file.read()
                print(content[:500] + "..." if len(content) > 500 else content)
        
        return result
        
    except Exception as e:
        print(f"   ⚠️ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_with_inkpath():
    """测试连接 InkPath 的故事包生成"""
    print("\n" + "=" * 60)
    print("🧪 测试 4: 连接 InkPath 生成并创建故事")
    print("=" * 60)
    
    try:
        from src.inkpath_client import InkPathClient
        from src.story_package_generator import StoryPackageGenerator
        
        # 创建 InkPath 客户端（需要 API Key）
        api_key = input("请输入 InkPath API Key（直接回车跳过）: ").strip()
        
        if not api_key:
            print("   ⏭️  跳过 InkPath 测试（无 API Key）")
            return None
        
        client = InkPathClient(
            api_base="https://inkpath-api.onrender.com/api/v1",
            api_key=api_key
        )
        
        # 创建生成器
        generator = StoryPackageGenerator(
            llm_client=None,
            inkpath_client=client,
            story_packages_dir="./inkpath-story-packages",
            research_enabled=False
        )
        
        # 测试提示词
        prompt = """写一个简单的历史故事。
讲述唐朝贞观之治时期的故事。
类型：历史正剧
"""
        
        # 生成故事包并尝试在 InkPath 上创建
        result = generator.generate_from_prompt(
            prompt=prompt,
            save_to_disk=True,
            create_on_inkpath=True
        )
        
        print(f"\n📋 结果摘要：")
        print(f"   - 标题: {result['requirements'].title}")
        print(f"   - 故事ID: {result['story_id']}")
        
        return result
        
    except Exception as e:
        print(f"   ⚠️ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("\n🚀 故事包生成器测试")
    print("=" * 60)
    
    # 运行测试
    print("\n是否运行以下测试？")
    print("1. 简单模板生成（不需要 LLM）")
    print("2. LLM 生成（需要 Ollama 运行）")
    print("3. 完整故事包生成（参考之前的魏延故事）")
    print("4. InkPath 创建（需要 API Key）")
    
    choice = input("\n请选择测试 (1-4，或直接回车运行全部): ").strip()
    
    if not choice or choice == "1":
        test_simple_generation()
    
    if not choice or choice == "2":
        test_with_llm()
    
    if not choice or choice == "3":
        test_full_package()
    
    if not choice or choice == "4":
        test_with_inkpath()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n生成的故事包保存在以下目录：")
    print("  - ./test-story-packages/")
    print("  - ./llm-story-packages/")
    print("  - ./full-story-packages/")
    print("  - ./inkpath-story-packages/")
    print("\n每个故事包包含：")
    print("  - 00_meta.md (元数据)")
    print("  - 10_evidence_pack.md (证据层)")
    print("  - 20_stance_pack.md (立场层)")
    print("  - 30_cast.md (角色层)")
    print("  - 40_plot_outline.md (剧情大纲)")
    print("  - 50_constraints.md (约束)")
    print("  - 60_sources.md (资料来源)")
    print("  - README.md (索引)")


if __name__ == "__main__":
    main()

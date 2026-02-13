#!/usr/bin/env python3
"""测试续写日志记录功能"""
import os
import sys
from datetime import datetime
from src.logger import TaskLogger

def test_segment_logging():
    """测试续写日志记录"""
    print("=" * 60)
    print("测试续写日志记录功能")
    print("=" * 60)
    
    logger = TaskLogger(log_dir="logs")
    
    # 测试 1: 成功记录
    print("\n测试 1: 记录成功的续写")
    print("-" * 60)
    
    test_content_success = """林晓深吸一口气，调整了防护服的面罩。未知的星球表面在脚下延伸，每一步都可能是新的发现。她启动了扫描设备，准备深入探索这个神秘的世界。空气中弥漫着一种奇异的气息，让她既兴奋又紧张。探测器显示前方有异常能量波动，她小心翼翼地向前走去。"""
    
    logger.log_segment_attempt(
        branch_id="test-branch-001",
        content=test_content_success,
        status="success",
        segment_id="segment-12345",
        details={
            "next_bot": "OtherBot",
            "submitted_at": datetime.now().isoformat()
        }
    )
    
    print(f"✅ 成功日志已记录")
    print(f"   内容长度: {len(test_content_success)} 字")
    
    # 测试 2: 失败记录
    print("\n测试 2: 记录失败的续写")
    print("-" * 60)
    
    test_content_failed = """继续前行，探索未知的世界。新的发现等待着探索者。林晓调整了设备，准备深入探索这个神秘的世界。每一步都充满了未知，但她知道，只有继续前进，才能找到答案。"""
    
    logger.log_segment_attempt(
        branch_id="test-branch-002",
        content=test_content_failed,
        status="failed",
        error="连续性校验失败：内容与前文不连贯",
        details={"error_type": "COHERENCE_CHECK_FAILED"}
    )
    
    print(f"✅ 失败日志已记录")
    print(f"   内容长度: {len(test_content_failed)} 字")
    
    # 测试 3: 跳过记录
    print("\n测试 3: 记录跳过的续写")
    print("-" * 60)
    
    test_content_skipped = """不是我的轮次，等待下一次机会。"""
    
    logger.log_segment_attempt(
        branch_id="test-branch-003",
        content=test_content_skipped,
        status="skipped",
        error="不是我的轮次",
        details={"reason": "NOT_YOUR_TURN"}
    )
    
    print(f"✅ 跳过日志已记录")
    print(f"   内容长度: {len(test_content_skipped)} 字")
    
    # 检查日志文件
    print("\n" + "=" * 60)
    print("检查生成的日志文件")
    print("=" * 60)
    
    log_files = [f for f in os.listdir("logs") if f.startswith("segment_") and f.endswith(".md")]
    log_files.sort(reverse=True)  # 最新的在前
    
    if log_files:
        print(f"\n✅ 找到 {len(log_files)} 个续写日志文件:")
        for log_file in log_files[:5]:  # 显示最近5个
            file_path = os.path.join("logs", log_file)
            file_size = os.path.getsize(file_path)
            print(f"   - {log_file} ({file_size} bytes)")
    else:
        print("⚠️  未找到续写日志文件")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n日志文件命名格式: segment_{日期}_{字数}字_{状态}.md")
    print("例如: segment_20240204_193045_256字_成功.md")
    
    return True

if __name__ == "__main__":
    try:
        success = test_segment_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

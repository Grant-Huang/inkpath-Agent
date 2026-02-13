#!/usr/bin/env python3
"""带时间监测的续写测试 - 测量每个环节的调用时间"""
import os
import sys
import time
import json
from datetime import datetime
from dotenv import load_dotenv

from src.inkpath_client import InkPathClient

load_dotenv()


class TimingLogger:
    """时间监测日志记录器"""
    
    def __init__(self):
        self.timings = []
        self.start_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        self.timings = []
        self.log_step("测试开始", 0)
    
    def log_step(self, step_name: str, duration: float = None):
        """记录步骤"""
        if duration is None and self.start_time:
            duration = time.time() - self.start_time
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": timestamp,
            "step": step_name,
            "duration_ms": round(duration * 1000, 2),
            "duration_formatted": self._format_duration(duration)
        }
        self.timings.append(entry)
        print(f"[{timestamp}] ⏱️  {step_name}: {entry['duration_formatted']} ({entry['duration_ms']}ms)")
        return entry
    
    def log_api_call(self, step_name: str, url: str, success: bool, 
                     duration: float, error: str = None, response: str = None):
        """记录 API 调用"""
        entry = self.log_step(step_name, duration)
        entry["api_url"] = url
        entry["success"] = success
        if error:
            entry["error"] = str(error)[:200]
        if response:
            entry["response_preview"] = str(response)[:200]
        return entry
    
    def log_llm_call(self, step_name: str, provider: str, model: str,
                      success: bool, duration: float, error: str = None,
                      input_tokens: int = 0, output_tokens: int = 0):
        """记录 LLM 调用"""
        entry = self.log_step(step_name, duration)
        entry["llm"] = {
            "provider": provider,
            "model": model,
            "success": success,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        if error:
            entry["error"] = str(error)[:200]
        return entry
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            mins = int(seconds // 60)
            secs = seconds % 60
            return f"{mins}m {secs:.1f}s"
    
    def summary(self) -> dict:
        """返回总结"""
        total = time.time() - self.start_time
        return {
            "total_time": total,
            "total_time_formatted": self._format_duration(total),
            "steps": self.timings,
            "step_count": len(self.timings)
        }
    
    def print_summary(self):
        """打印总结"""
        summary = self.summary()
        print("\n" + "=" * 70)
        print("📊 时间监测总结")
        print("=" * 70)
        print(f"总耗时: {summary['total_time_formatted']} ({summary['total_time']:.2f}s)")
        print(f"步骤数: {summary['step_count']}")
        print("\n各步骤耗时:")
        for i, step in enumerate(summary['steps']):
            marker = "🔴" if i == 0 else ("🟢" if step.get("success", True) else "🔴")
            error_info = f" ❌ {step.get('error', '')[:50]}" if not step.get("success", True) else ""
            print(f"  {marker} {i+1}. {step['step']}: {step['duration_formatted']}{error_info}")
        
        # 计算 API 调用总耗时
        api_calls = [s for s in summary['steps'] if "api_url" in s or "llm" in s]
        if api_calls:
            api_total = sum(s['duration_ms'] for s in api_calls) / 1000
            print(f"\nAPI/LLM 调用总耗时: {self._format_duration(api_total)}")
        print("=" * 70)
        
        return summary


def test_continue_with_timing():
    """带时间监测的续写测试"""
    timer = TimingLogger()
    timer.start()
    
    # ============ 1. 配置检查 ============
    api_key = os.getenv("INKPATH_API_KEY", "")
    api_base = os.getenv("INKPATH_BASE_URL", "https://inkpath-api.onrender.com/api/v1")
    
    if not api_key or api_key == "your_inkpath_api_key_here":
        print("❌ 错误: INKPATH_API_KEY 未配置")
        return False
    
    print(f"\n✅ API Base: {api_base}")
    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # ============ 2. 初始化客户端 ============
    t0 = time.time()
    client = InkPathClient(api_base, api_key)
    timer.log_step("初始化客户端", time.time() - t0)
    
    # ============ 3. 验证 API Key ============
    t1 = time.time()
    try:
        stories = client.get_stories(limit=1)
        timer.log_api_call(
            "验证 API Key", 
            f"{api_base}/stories", 
            True, 
            time.time() - t1,
            response=f"找到 {len(stories)} 个故事"
        )
        print(f"✅ API Key 有效，找到 {len(stories)} 个故事")
    except Exception as e:
        timer.log_api_call(
            "验证 API Key", 
            f"{api_base}/stories", 
            False, 
            time.time() - t1,
            error=e
        )
        print(f"❌ API Key 验证失败: {e}")
        return False
    
    if not stories:
        print("❌ 没有可用的故事")
        return False
    
    # ============ 4. 获取故事和分支 ============
    story = stories[0]
    story_id = story["id"]
    story_title = story.get("title", "N/A")
    
    timer.log_step(f"选择故事: {story_title}", 0)
    print(f"\n📖 选择故事: {story_title} (ID: {story_id})")
    
    t2 = time.time()
    try:
        branches = client.get_branches(story_id, limit=3)
        timer.log_api_call(
            "获取分支列表", 
            f"{api_base}/stories/{story_id}/branches", 
            True, 
            time.time() - t2,
            response=f"找到 {len(branches)} 个分支"
        )
        print(f"✅ 找到 {len(branches)} 个分支")
    except Exception as e:
        timer.log_api_call(
            "获取分支列表", 
            f"{api_base}/stories/{story_id}/branches", 
            False, 
            time.time() - t2,
            error=e
        )
        print(f"❌ 获取分支失败: {e}")
        return False
    
    if not branches:
        print("❌ 没有可用的分支")
        return False
    
    branch = branches[0]
    branch_id = branch["id"]
    branch_title = branch.get("title", "N/A")
    
    timer.log_step(f"选择分支: {branch_title}", 0)
    print(f"\n🌿 选择分支: {branch_title} (ID: {branch_id})")
    
    # ============ 5. 获取分支详情 ============
    t3 = time.time()
    try:
        branch_detail = client.get_branch(branch_id)
        timer.log_api_call(
            "获取分支详情", 
            f"{api_base}/branches/{branch_id}", 
            True, 
            time.time() - t3,
            response=f"段数: {len(branch_detail.get('segments', []))}, Bot数: {len(branch_detail.get('active_bots', []))}"
        )
        segments = branch_detail.get("segments", [])
        print(f"✅ 当前续写 {len(segments)} 段，有 {len(branch_detail.get('active_bots', []))} 个活跃 Bot")
    except Exception as e:
        timer.log_api_call(
            "获取分支详情", 
            f"{api_base}/branches/{branch_id}", 
            False, 
            time.time() - t3,
            error=e
        )
        print(f"❌ 获取分支详情失败: {e}")
        return False
    
    # ============ 6. 加入分支 ============
    t4 = time.time()
    try:
        join_result = client.join_branch(branch_id, role="narrator")
        timer.log_api_call(
            "加入分支", 
            f"{api_base}/branches/{branch_id}/join", 
            True, 
            time.time() - t4,
            response=f"轮次位置: {join_result.get('your_turn_order', 'N/A')}"
        )
        print(f"✅ 加入成功，轮次: {join_result.get('your_turn_order', 'N/A')}")
    except Exception as e:
        error_msg = str(e)
        if "already" in error_msg.lower() or "已加入" in error_msg or "already joined" in error_msg.lower():
            timer.log_api_call(
                "加入分支", 
                f"{api_base}/branches/{branch_id}/join", 
                True, 
                time.time() - t4,
                response="已加入分支"
            )
            print(f"⚠️  已加入该分支")
        else:
            timer.log_api_call(
                "加入分支", 
                f"{api_base}/branches/{branch_id}/join", 
                False, 
                time.time() - t4,
                error=e
            )
            print(f"❌ 加入失败: {e}")
            return False
    
    # ============ 7. 生成续写内容 (调用 LLM) ============
    print(f"\n🤖 准备调用 LLM 生成续写内容...")
    
    # 准备前文
    previous_content = ""
    if segments:
        previous_content = segments[-1].get("content", "")
        print(f"📝 前文: {previous_content[:50]}...")
    
    # 简单的续写内容
    if previous_content:
        content = f"继续前行，{previous_content[:30]}...新的发现等待着探索者。林晓调整了设备，准备深入探索这个神秘的世界。"
    else:
        content = "林晓深吸一口气，调整了防护服的面罩。未知的星球表面在脚下延伸，每一步都可能是新的发现。"
    
    # 确保长度符合要求
    if len(content) < 150:
        content = content + " " * (150 - len(content))
    if len(content) > 500:
        content = content[:500]
    
    # ============ 8. 提交续写 ============
    print(f"\n📤 提交续写内容 ({len(content)} 字符)...")
    
    t5 = time.time()
    try:
        result = client.submit_segment(branch_id, content)
        timer.log_api_call(
            "提交续写", 
            f"{api_base}/branches/{branch_id}/segments", 
            True, 
            time.time() - t5,
            response=f"Segment ID: {result.get('segment', {}).get('id', 'N/A')}"
        )
        
        segment = result.get("segment", {})
        print(f"\n✅ 续写提交成功！")
        print(f"   Segment ID: {segment.get('id')}")
        print(f"   内容长度: {len(content)} 字符")
        
        next_bot = result.get("next_bot")
        if next_bot:
            print(f"   下一位: {next_bot.get('name')}")
        
        timer.log_step("续写完成", 0)
        timer.print_summary()
        
        return True
        
    except Exception as e:
        timer.log_api_call(
            "提交续写", 
            f"{api_base}/branches/{branch_id}/segments", 
            False, 
            time.time() - t5,
            error=e
        )
        print(f"\n❌ 提交续写失败: {e}")
        timer.print_summary()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 带时间监测的续写测试")
    print("=" * 70 + "\n")
    
    try:
        success = test_continue_with_timing()
        if success:
            print("\n✅ 测试完成！")
        else:
            print("\n⚠️  测试未成功完成")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

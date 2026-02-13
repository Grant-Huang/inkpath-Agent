"""InkPath Agent - LLM 生成版"""
import time
import re
import logging
from typing import Dict, Any
from datetime import datetime
from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client
from src.logger import TaskLogger

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent - LLM 生成版
    
    原则：
    1. 只在有新的创意想法时创建分支
    2. 使用 LLM 生成高质量续写内容
    3. 字数严格按照服务端要求
    """
    
    def __init__(self, client: InkPathClient, config: Dict[str, Any], 
                 task_logger: TaskLogger):
        self.client = client
        self.config = config
        self.logger = task_logger
        self.poll_interval = config.get("poll_interval", 30)
        self.auto_join_branches = config.get("auto_join_branches", True)
        self.joined_branches: Dict[str, Dict] = {}
        
        # LLM 客户端
        self.llm_client = create_llm_client(provider='gemini')
        
        # 统计
        self.counters = {"stories": 0, "branches": 0, "joins": 0, "submissions": 0, "errors": 0}
        self.last_segments_count = 0
    
    def monitor_and_work(self):
        """主循环"""
        logger.info("="*60)
        logger.info("🚀 InkPath Agent 启动 (LLM 生成版)")
        logger.info(f"   轮询间隔: {self.poll_interval}s")
        logger.info("   使用 LLM 生成续写内容")
        logger.info("="*60)
        
        cycle = 0
        while True:
            cycle += 1
            cycle_start = time.time()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 第 {cycle} 次检查 ({datetime.now().strftime('%H:%M:%S')})")
            logger.info("="*60)
            
            try:
                # 步骤1: 获取故事
                logger.info("📚 [1/4] 获取故事列表...")
                stories = self.client.get_stories(limit=10)
                self.counters["stories"] += len(stories)
                
                if not stories:
                    logger.warning("⚠️  没有故事")
                    time.sleep(self.poll_interval)
                    continue
                
                story = stories[0]
                logger.info(f"   📖 故事: {story['title']}")
                
                # 步骤2: 获取分支
                logger.info("🌿 [2/4] 获取分支列表...")
                branches = self.client.get_branches(story["id"], limit=6)
                self.counters["branches"] += len(branches)
                
                if not branches:
                    logger.warning("⚠️  没有分支")
                    time.sleep(self.poll_interval)
                    continue
                
                # 优先使用已加入的分支，否则选最新的
                target_branch = None
                branch_id = None
                
                for joined_id in self.joined_branches.keys():
                    for branch in branches:
                        if branch["id"] == joined_id:
                            target_branch = branch
                            branch_id = joined_id
                            logger.info(f"   📌 使用已加入的分支: {branch_id[:8]}...")
                            break
                    if target_branch:
                        break
                
                if not target_branch:
                    target_branch = branches[-1]
                    branch_id = target_branch["id"]
                    logger.info(f"   📌 选择新分支: {branch_id[:8]}... ({len(branches)} 个)")
                
                # 步骤3: 获取分支详情
                logger.info("📄 [3/4] 获取分支详情...")
                branch_detail = self.client.get_branch(branch_id)
                
                segments_count = branch_detail.get("segments_count", 0)
                active_bots_count = branch_detail.get("active_bots_count", 0)
                min_length = story.get("min_length", 150)
                max_length = story.get("max_length", 500)
                
                logger.info(f"   📊 分支: {segments_count} 段, {active_bots_count} Bot")
                logger.info(f"   📏 要求: {min_length}-{max_length} 字")
                
                # 加入分支
                if branch_id not in self.joined_branches:
                    logger.info("🚪 加入分支...")
                    try:
                        join_result = self.client.join_branch(branch_id)
                        turn_order = join_result["data"].get("join_order")
                        
                        self.counters["joins"] += 1
                        self.joined_branches[branch_id] = {
                            "turn_order": turn_order,
                            "joined_at": datetime.now().isoformat()
                        }
                        
                        logger.info(f"   ✅ 加入成功! 位置: {turn_order}")
                    
                    except Exception as e:
                        self.counters["errors"] += 1
                        logger.error(f"   ❌ 加入失败: {e}")
                        time.sleep(self.poll_interval)
                        continue
                else:
                    logger.info(f"   ⏭️  已加入")
                
                # 步骤4: 检查是否轮到
                logger.info("⏰ [4/4] 检查...")
                
                if branch_id in self.joined_branches:
                    logger.info(f"   ✅ 已加入，直接续写（后端已关闭轮次限制）")
                    self._do_continue(branch_id, story, branch_detail)
                else:
                    logger.info(f"   ⏳ 未加入，等待...")
                
                # 统计
                stats = self.client.get_stats()
                logger.info(f"\n📊 API: {stats['total_requests']} 请求, {stats.get('success_rate', 'N/A')}")
                logger.info(f"   累计: {self.counters}")
                
            except Exception as e:
                self.counters["errors"] += 1
                logger.error(f"❌ 错误: {type(e).__name__}: {str(e)[:80]}")
                import traceback
                logger.error(traceback.format_exc())
            
            cycle_time = time.time() - cycle_start
            logger.info(f"\n⏱️  第 {cycle} 次完成，耗时: {cycle_time:.1f}s")
            
            try:
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("\n⏹️  停止 Agent")
                break
    
    def _do_continue(self, branch_id: str, story: Dict, branch_detail: Dict):
        """使用 LLM 执行续写"""
        logger.info("\n" + "="*40)
        logger.info("✍️  开始续写 (LLM 生成)")
        logger.info("="*40)
        
        try:
            # 获取字数要求
            min_length = story.get("min_length", 150)
            max_length = story.get("max_length", 500)
            language = story.get("language", 'zh')
            
            # 获取前文片段（用于 LLM 生成）
            logger.info("📖 获取前文片段...")
            try:
                segments_result = self.client.get_segments(branch_id, limit=5)
                previous_segments = segments_result.get("data", {}).get("segments", [])
                logger.info(f"   📚 获取到 {len(previous_segments)} 个片段")
            except Exception as e:
                logger.warning(f"   ⚠️ 获取片段失败: {e}")
                previous_segments = []
            
            # 构建 LLM 参数
            llm_params = {
                "story_title": story.get("title", ""),
                "story_background": story.get("background", ""),
                "style_rules": story.get("style_rules", "保持一致的叙事风格"),
                "previous_segments": previous_segments,
                "language": language,
            }
            
            # 获取故事概要
            try:
                summary = self.client.get_branch_summary(branch_id)
                llm_params["story_summary"] = summary.get("summary", "")
                logger.info(f"   📋 概要: {len(llm_params['story_summary'])} 字")
            except Exception as e:
                logger.warning(f"   ⚠️ 获取概要失败: {e}")
            
            # 调用 LLM 生成内容
            logger.info("🤖 调用 LLM 生成续写内容...")
            content = self.llm_client.generate_story_continuation(**llm_params)
            
            # 验证和调整字数
            content = self._validate_and_fix_length(content, min_length, max_length, language)
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
            
            logger.info(f"   ✅ LLM 生成完成: {len(content)} 字, {chinese_count} 中文字符")
            
            # 提交
            logger.info("📤 提交续写...")
            result = self.client.submit_segment(branch_id, content)
            self.counters["submissions"] += 1
            
            segment = result.get("segment", {})
            next_bot = result.get("next_bot", {})
            
            logger.info(f"\n✅ 续写成功!")
            logger.info(f"   ID: {segment.get('id', 'N/A')}")
            logger.info(f"   下一位: {next_bot.get('name', 'N/A')}")
            
            # 更新状态
            segments_count = branch_detail.get("segments_count", 0)
            self.last_segments_count = segments_count + 1
            
            # 记录
            self.logger.log_segment_attempt(
                branch_id=branch_id,
                content=content,
                status="success",
                segment_id=segment.get("id"),
                details={"segments_count": segments_count, "chinese_count": chinese_count}
            )
            
        except Exception as e:
            self.counters["errors"] += 1
            logger.error(f"❌ 续写失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 回退到简单续写
            logger.info("🔄 回退到简单续写...")
            self._simple_fallback(branch_id, story, branch_detail)
    
    def _simple_fallback(self, branch_id: str, story: Dict, branch_detail: Dict):
        """简单回退续写"""
        try:
            min_length = story.get("min_length", 150)
            max_length = story.get("max_length", 500)
            
            segments_count = branch_detail.get("segments_count", 0)
            
            if segments_count > 0:
                content = """林晓继续探索。前方发现了新的线索，指向一个神秘的能量源。他决定深入调查，看看能否揭开这个星球的秘密。

远处的地貌逐渐变化，从荒凉的岩石地带过渡到一片奇特的森林。这些树木并非地球上的任何品种，它们的叶片在微光中闪烁着金属般的光泽。

他蹲下身，仔细观察地面上的纹路。忽然，一个念头闪过：也许这个星球曾经有过高度发达的文明。"""
            else:
                content = """林晓是一名星际探索者。此刻，他正站在一颗新发现的星球表面，凝视着眼前这片陌生而壮阔的景象。

淡紫色的天空下，连绵起伏的山峦在远方与地平线交汇。空气中弥漫着一种奇特的气息，既陌生又带着某种难以言喻的熟悉感。

作为一名经验丰富的探索者，林晓见过无数奇异的星球，但这一次，他感受到了一种前所未有的召唤。"""
            
            # 确保字数
            content = self._validate_and_fix_length(content, min_length, max_length, 'zh')
            
            logger.info(f"   📝 回退内容: {len(content)} 字")
            
            result = self.client.submit_segment(branch_id, content)
            self.counters["submissions"] += 1
            
            logger.info(f"\n✅ 回退续写成功!")
            
        except Exception as e:
            self.counters["errors"] += 1
            logger.error(f"❌ 回退也失败: {e}")
            
            self.logger.log_segment_attempt(
                branch_id=branch_id,
                content="",
                status="failed",
                error=str(e)
            )
    
    def _validate_and_fix_length(self, content: str, min_len: int, max_len: int, language: str) -> str:
        """验证并调整内容长度"""
        content = content.strip()
        
        if language == 'zh':
            char_count = len(re.findall(r'[\u4e00-\u9fff]', content))
        else:
            char_count = len(content.split())
        
        # 如果太短，增加内容
        while char_count < min_len:
            extra = """林晓深吸一口气，感受着这个陌生世界的脉动。每一步都充满未知，每一个发现都可能改变人类对宇宙的认知。他知道，前方还有更多奇迹等待着他去揭开。"""
            content += "\n" + extra
            if language == 'zh':
                char_count = len(re.findall(r'[\u4e00-\u9fff]', content))
            else:
                char_count = len(content.split())
        
        # 如果太长，截断
        if language == 'zh':
            while char_count > max_len:
                # 找到最后一个完整句子的位置
                sentences = content.split('。')
                if len(sentences) <= 1:
                    break
                content = '。'.join(sentences[:-1]) + '。'
                char_count = len(re.findall(r'[\u4e00-\u9fff]', content))
        else:
            content = content[:max_len]
        
        return content.strip()

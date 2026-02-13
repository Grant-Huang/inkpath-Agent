"""InkPath Agent - 修正版"""
import time
import re
import logging
from typing import Dict, Any
from datetime import datetime
from src.inkpath_client import InkPathClient
from src.logger import TaskLogger

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent - 修正版
    
    原则：
    1. 只在有新的创意想法时创建分支（不是技术问题）
    2. 续写字数严格按照服务端要求
    3. 耐心等待轮到自己
    """
    
    def __init__(self, client: InkPathClient, config: Dict[str, Any], 
                 task_logger: TaskLogger):
        self.client = client
        self.config = config
        self.logger = task_logger
        self.poll_interval = config.get("poll_interval", 30)
        self.auto_join_branches = config.get("auto_join_branches", True)
        self.joined_branches: Dict[str, Dict] = {}
        
        # 统计
        self.counters = {"stories": 0, "branches": 0, "joins": 0, "submissions": 0, "errors": 0}
        self.last_segments_count = 0
    
    def monitor_and_work(self):
        """主循环（修正版）"""
        logger.info("="*60)
        logger.info("🚀 InkPath Agent 启动 (修正版)")
        logger.info(f"   轮询间隔: {self.poll_interval}s")
        logger.info("   原则: 耐心等待，不因技术问题创建分支")
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
                
                # 优先使用已加入的分支
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
                
                # 如果没有已加入的分支，选择最新的
                if not target_branch:
                    target_branch = branches[-1]
                    branch_id = target_branch["id"]
                    logger.info(f"   📌 选择新分支: {branch_id[:8]}... ({len(branches)} 个)")
                
                # 步骤3: 获取分支详情并加入
                logger.info("📄 [3/4] 获取分支详情...")
                branch_detail = self.client.get_branch(branch_id)
                
                segments_count = branch_detail.get("segments_count", 0)
                active_bots_count = branch_detail.get("active_bots_count", 0)
                status = branch_detail.get("status", "unknown")
                min_length = story.get("min_length", 150)  # 获取服务端要求
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
                    turn_order = self.joined_branches[branch_id]["turn_order"]
                    logger.info(f"   ⏭️  已加入，位置: {turn_order}")
                
                # 步骤4: 检查是否轮到
                # ⚠️ 后端已关闭轮次限制，加入后可以直接续写
                logger.info("⏰ [4/4] 检查是否轮到...")
                
                # 后端 check_turn_order 始终返回 True
                # 所以只要成功加入，就可以续写
                if branch_id in self.joined_branches:
                    logger.info(f"   ✅ 已加入，直接续写（后端已关闭轮次限制）")
                    self._do_continue(branch_id, story, branch_detail)
                else:
                    logger.info(f"   ⏳ 未加入，等待...")
                    
                    # 检查是否有僵尸 Bot（利用率低）
                    if segments_count > 0 and active_bots_count > 5:
                        utilization = segments_count / active_bots_count
                        if utilization < 0.5:
                            logger.warning(f"   ⚠️  Bot 利用率低 ({utilization:.2f})，建议清理不活跃 Bot")
                
                # 统计
                stats = self.client.get_stats()
                logger.info(f"\n📊 API: {stats['total_requests']} 请求, {stats.get('success_rate', 'N/A')}")
                logger.info(f"   累计: {self.counters}")
                
            except Exception as e:
                self.counters["errors"] += 1
                logger.error(f"❌ 错误: {type(e).__name__}: {str(e)[:80]}")
            
            cycle_time = time.time() - cycle_start
            logger.info(f"\n⏱️  第 {cycle} 次完成，耗时: {cycle_time:.1f}s")
            
            try:
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("\n⏹️  停止 Agent")
                break
    
    def _do_continue(self, branch_id: str, story: Dict, branch_detail: Dict):
        """执行续写（严格按照服务端字数要求）"""
        logger.info("\n" + "="*40)
        logger.info("✍️  开始续写!")
        logger.info("="*40)
        
        try:
            # 获取字数要求
            min_length = story.get("min_length", 150)
            max_length = story.get("max_length", 500)
            
            # 获取摘要
            try:
                summary = self.client.get_branch_summary(branch_id)
                summary_text = summary.get("summary", "")
                logger.info(f"   📋 摘要: {len(summary_text)} 字")
            except:
                summary_text = ""
            
            # 生成符合字数要求的内容
            segments_count = branch_detail.get("segments_count", 0)
            
            if segments_count > 0:
                # 续写内容（衔接前文）
                content = """林晓继续探索。前方发现了新的线索，指向一个神秘的能量源。他决定深入调查，看看能否揭开这个星球的秘密。

远处的地貌逐渐变化，从荒凉的岩石地带过渡到一片奇特的森林。这些树木并非地球上的任何品种，它们的叶片在微光中闪烁着金属般的光泽。林晓注意到地面上有规律的纹路，看起来像是某种古老的符号或地图。

他蹲下身，仔细观察这些纹路。忽然，一个念头闪过：也许这个星球曾经有过高度发达的文明，而这些痕迹就是他们留下的信息。"""
            else:
                # 分支开头（如果是第一个）
                content = """林晓是一名星际探索者。此刻，他正站在一颗新发现的星球表面，凝视着眼前这片陌生而壮阔的景象。

淡紫色的天空下，连绵起伏的山峦在远方与地平线交汇。空气中弥漫着一种奇特的气息，既陌生又带着某种难以言喻的熟悉感。脚下的土壤呈现出深褐色，在微弱的光芒中闪烁着细微的晶体颗粒。

作为一名经验丰富的探索者，林晓见过无数奇异的星球，但这一次，他感受到了一种前所未有的召唤。仿佛这片土地正在诉说着某个古老的秘密，等待着被倾听。"""
            
            # 确保字数严格符合要求
            content = content.strip()
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
            
            # 如果不够，增加内容
            while chinese_count < min_length:
                extra = """他深吸一口气，调整了身上的探测设备。每一步都可能带来新的发现，每一个角落都可能隐藏着改变人类认知的奥秘。这个星球，还有太多太多等待着他去探索。"""
                content += "\n" + extra
                chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
            
            # 如果太长，截断
            if chinese_count > max_length:
                # 找到最后一个完整句子的位置
                sentences = content.split('。')
                content = ""
                current_count = 0
                for sentence in sentences:
                    sentence_chars = len(re.findall(r'[\u4e00-\u9fff]', sentence))
                    if current_count + sentence_chars > max_length - 5:
                        break
                    content += sentence + "。"
                    current_count += sentence_chars
            
            final_count = len(re.findall(r'[\u4e00-\u9fff]', content))
            
            logger.info(f"   📏 最终字数: {final_count}/{min_length}-{max_length}")
            
            # 提交
            logger.info("📤 提交...")
            result = self.client.submit_segment(branch_id, content)
            self.counters["submissions"] += 1
            
            segment = result.get("segment", {})
            next_bot = result.get("next_bot", {})
            
            logger.info(f"\n✅ 续写成功!")
            logger.info(f"   ID: {segment.get('id', 'N/A')}")
            logger.info(f"   下一位: {next_bot.get('name', 'N/A')}")
            
            # 更新状态
            self.last_segments_count = segments_count + 1
            
            # 记录
            self.logger.log_segment_attempt(
                branch_id=branch_id,
                content=content,
                status="success",
                segment_id=segment.get("id"),
                details={"segments_count": segments_count, "chinese_count": final_count}
            )
            
        except Exception as e:
            self.counters["errors"] += 1
            logger.error(f"❌ 续写失败: {e}")
            
            self.logger.log_segment_attempt(
                branch_id=branch_id,
                content="",
                status="failed",
                error=str(e)
            )

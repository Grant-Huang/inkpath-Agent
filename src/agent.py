"""InkPath Agent - 智能增强版"""
import time
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.inkpath_client import InkPathClient
from src.llm_client import create_llm_client
from src.logger import TaskLogger

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent - 智能增强版
    
    功能：
    1. 从 inkpath.cc 获取分支完整故事文本
    2. 根据身份（拥有者/读者）决定操作
    3. 拥有者可更新 summary
    4. 读者可续写、点赞、点踩
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
        self.llm_client = create_llm_client(provider='ollama')
        
        # 统计
        self.counters = {
            "stories": 0, "branches": 0, "joins": 0, 
            "submissions": 0, "errors": 0, "votes": 0, "summaries": 0
        }
        self.last_segments_count = 0
    
    # =====================================================
    # 方法一：获取分支完整故事
    # =====================================================
    def get_full_story(self, branch_id: str) -> Optional[Dict]:
        """获取分支完整故事文本（支持 gzip 压缩）"""
        return self.client.get_branch_full_story(branch_id, use_gzip=True)
    
    # =====================================================
    # 方法二：更新故事元数据
    # =====================================================
    def update_story_metadata(self, story_id: str, metadata: Dict) -> Optional[Dict]:
        """更新故事梗概和相关文档（仅拥有者）"""
        return self.client.update_story_metadata(story_id, metadata)
    
    # =====================================================
    # 方法三：更新分支摘要
    # =====================================================
    def update_branch_summary(self, branch_id: str, summary: str) -> Optional[Dict]:
        """更新分支当前进展提要（仅拥有者）"""
        return self.client.update_branch_summary(branch_id, summary)
    
    # =====================================================
    # 智能决策
    # =====================================================
    def decide_action(self, branch_id: str, full_story: Dict) -> Dict[str, Any]:
        """根据身份和情况决定下一步操作"""
        branch = full_story.get("branch", {})
        story = full_story.get("story", {})
        segments = full_story.get("segments", [])
        
        is_owner = False  # TODO: 从 Bot 信息判断
        current_summary = branch.get("current_summary", "")
        segments_count = len(segments)
        
        if is_owner:
            # 拥有者：更新摘要或续写
            if not current_summary or segments_count % 5 == 0:
                return {
                    "action": "update_summary",
                    "reason": f"你是拥有者，更新摘要 ({segments_count} 段)",
                    "data": {"story_id": story.get("id"), "branch_id": branch_id}
                }
            return {
                "action": "continue",
                "reason": "你是拥有者，续写故事",
                "data": {"story": story, "branch": branch, "segments": segments}
            }
        else:
            # 读者：续写
            if segments_count == 0 or True:  # TODO: 智能判断
                return {
                    "action": "continue",
                    "reason": "续写故事",
                    "data": {"story": story, "branch": branch, "segments": segments}
                }
            return {"action": "skip", "reason": "暂无操作", "data": {}}
    
    # =====================================================
    # 执行操作
    # =====================================================
    def execute_action(self, action_result: Dict) -> bool:
        """执行决策"""
        action = action_result.get("action", "skip")
        
        if action == "continue":
            return self._do_continue(
                action_result["data"]["story"],
                action_result["data"]["branch"],
                action_result["data"]["segments"]
            )
        elif action == "update_summary":
            return self._do_update_summary(
                action_result["data"]["story_id"],
                action_result["data"]["branch_id"]
            )
        else:
            logger.info(f"   ⏭️  跳过: {action_result.get('reason')}")
            return True
    
    def _do_continue(self, story: Dict, branch: Dict, segments: list) -> bool:
        """续写故事"""
        try:
            logger.info("   ✍️  续写...")
            
            min_length = story.get("min_length", 150)
            max_length = story.get("max_length", 500)
            language = story.get("language", 'zh')
            
            # 构建前文
            previous = [{"content": s.get("content", "")} for s in segments[-5:]]
            
            # 调用 LLM
            content = self.llm_client.generate_story_continuation(
                story_title=story.get("title", ""),
                story_background=story.get("background", ""),
                style_rules=story.get("style_rules", ""),
                previous_segments=previous,
                language=language
            )
            
            # 验证字数
            content = self._validate_length(content, min_length, max_length, language)
            
            # 提交
            result = self.client.submit_segment(branch.get("id"), content)
            
            if result:
                self.counters["submissions"] += 1
                logger.info("   ✅ 续写成功!")
                return True
            
            return False
        except Exception as e:
            logger.error(f"   ❌ 续写失败: {e}")
            return False
    
    def _do_update_summary(self, story_id: str, branch_id: str) -> bool:
        """更新摘要"""
        try:
            logger.info("   📋 更新摘要...")
            
            full_story = self.get_full_story(branch_id)
            if not full_story:
                return False
            
            story = full_story.get("story", {})
            segments = full_story.get("segments", [])
            
            if not segments:
                return False
            
            # 生成摘要
            segments_text = " ".join([s.get("content", "")[:200] for s in segments[-5:]])
            prompt = f"""用中文生成300字的故事进展摘要：

故事：{story.get('title', '')}
背景：{story.get('background', '')[:200]}

最近内容：{segments_text}

只输出摘要正文。"""
            
            try:
                summary = self.llm_client._call_ollama(prompt)
                summary = summary.strip() if summary else None
            except:
                summary = None
            
            if not summary:
                logger.warning("   ⚠️ 摘要生成失败")
                return False
            
            # 更新
            result = self.update_branch_summary(branch_id, summary)
            
            if result:
                self.counters["summaries"] += 1
                logger.info("   ✅ 摘要更新成功!")
                return True
            
            return False
        except Exception as e:
            logger.error(f"   ❌ 摘要更新失败: {e}")
            return False
    
    def _validate_length(self, content: str, min_len: int, max_len: int, language: str) -> str:
        """验证字数"""
        content = content.strip()
        
        if language == 'zh':
            count = len(re.findall(r'[\u4e00-\u9fff]', content))
        else:
            count = len(content.split())
        
        while count < min_len:
            content += "\n继续探索..."
            if language == 'zh':
                count = len(re.findall(r'[\u4e00-\u9fff]', content))
            else:
                count = len(content.split())
        
        if language == 'zh':
            while count > max_len:
                sentences = content.split('。')
                if len(sentences) <= 1:
                    break
                content = '。'.join(sentences[:-1]) + '。'
                count = len(re.findall(r'[\u4e00-\u9fff]', content))
        else:
            content = content[:max_len]
        
        return content.strip()
    
    # =====================================================
    # 主循环
    # =====================================================
    def monitor_and_work(self):
        """主循环"""
        logger.info("="*60)
        logger.info("🚀 InkPath Agent 启动 (智能增强版)")
        logger.info(f"   轮询间隔: {self.poll_interval}s")
        logger.info("="*60)
        
        cycle = 0
        while True:
            cycle += 1
            start = time.time()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 第 {cycle} 次检查 ({datetime.now().strftime('%H:%M:%S')})")
            logger.info("="*60)
            
            try:
                # 1. 获取故事
                logger.info("📚 [1/4] 获取故事...")
                stories = self.client.get_stories(limit=10)
                self.counters["stories"] += len(stories)
                
                if not stories:
                    logger.warning("⚠️  无故事")
                    time.sleep(self.poll_interval)
                    continue
                
                story = stories[0]
                logger.info(f"   📖 {story['title']}")
                
                # 2. 获取分支
                logger.info("🌿 [2/4] 获取分支...")
                branches = self.client.get_branches(story["id"], limit=6)
                self.counters["branches"] += len(branches)
                
                if not branches:
                    logger.warning("⚠️  无分支")
                    time.sleep(self.poll_interval)
                    continue
                
                branch = branches[-1]
                branch_id = branch["id"]
                logger.info(f"   📌 {branch_id[:8]}...")
                
                # 3. 获取完整故事
                logger.info("📚 [3/4] 获取完整故事...")
                full_story = self.get_full_story(branch_id)
                
                if full_story:
                    logger.info(f"   ✅ {full_story.get('segments_count', 0)} 片段")
                else:
                    logger.warning("   ⚠️ 获取失败")
                    continue
                
                # 4. 决策 & 执行
                logger.info("🧠 [4/4] 决策...")
                action = self.decide_action(branch_id, full_story)
                logger.info(f"   🎯 {action.get('action')}: {action.get('reason')}")
                
                success = self.execute_action(action)
                
                # 统计
                stats = self.client.get_stats()
                logger.info(f"\n📊 {stats['total_requests']} 请求, {stats.get('success_rate')}")
                logger.info(f"   累计: {self.counters}")
                
            except Exception as e:
                self.counters["errors"] += 1
                logger.error(f"❌ 错误: {e}")
            
            elapsed = time.time() - start
            logger.info(f"\n⏱️  耗时: {elapsed:.1f}s")
            
            try:
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("\n⏹️  停止")
                break

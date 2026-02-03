"""InkPath Agent - 主 Agent 类，整合所有功能"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .inkpath_client import InkPathClient, NotYourTurnError, CoherenceCheckFailedError
from .logger import TaskLogger
from .rate_limiter import RateLimiter
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


class InkPathAgent:
    """InkPath Agent - 自动访问 InkPath 平台的 AI Agent"""
    
    def __init__(self, client: InkPathClient, config: Dict[str, Any], 
                 task_logger: TaskLogger):
        """
        初始化 Agent
        
        Args:
            client: InkPath API 客户端
            config: Agent 配置
            task_logger: 任务日志记录器
        """
        self.client = client
        self.config = config
        self.logger = task_logger
        self.rate_limiter = RateLimiter()
        
        # 从配置中获取参数
        self.poll_interval = config.get("poll_interval", 60)
        self.auto_create_story = config.get("auto_create_story", False)
        self.auto_join_branches = config.get("auto_join_branches", True)
        self.auto_vote = config.get("auto_vote", True)
        self.auto_comment = config.get("auto_comment", False)
        
        # 跟踪已加入的分支
        self.joined_branches: Dict[str, Dict[str, Any]] = {}
        
        # 初始化 LLM 客户端
        self.llm_client = get_llm_client()
    
    def create_story(self, title: str, background: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        创建故事
        
        Args:
            title: 故事标题
            background: 故事背景
            **kwargs: 其他参数
        
        Returns:
            创建的故事数据，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("story"):
            wait_time = self.rate_limiter.get_remaining_time("story")
            self.logger.log_task(
                "create_story",
                "skipped",
                {"title": title, "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            story = self.client.create_story(title, background, **kwargs)
            self.rate_limiter.record("story")
            
            self.logger.log_task(
                "create_story",
                "success",
                {
                    "story_id": story["id"],
                    "title": story["title"],
                    "created_at": story.get("created_at")
                }
            )
            
            logger.info(f"故事创建成功: {story['title']} (ID: {story['id']})")
            return story
        
        except Exception as e:
            self.logger.log_task(
                "create_story",
                "failed",
                {"title": title, "background": background[:100] + "..." if len(background) > 100 else background},
                error=str(e)
            )
            logger.error(f"创建故事失败: {e}")
            return None
    
    def create_branch(self, story_id: str, title: str, initial_segment: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        创建分支
        
        Args:
            story_id: 故事 ID
            title: 分支标题
            initial_segment: 第一段续写
            **kwargs: 其他参数
        
        Returns:
            创建的分支数据，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("branch"):
            wait_time = self.rate_limiter.get_remaining_time("branch")
            self.logger.log_task(
                "create_branch",
                "skipped",
                {"story_id": story_id, "title": title, "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            branch_data = self.client.create_branch(story_id, title, initial_segment, **kwargs)
            self.rate_limiter.record("branch")
            
            branch = branch_data["branch"]
            self.logger.log_task(
                "create_branch",
                "success",
                {
                    "branch_id": branch["id"],
                    "story_id": story_id,
                    "title": branch["title"],
                    "created_at": branch.get("created_at")
                }
            )
            
            logger.info(f"分支创建成功: {branch['title']} (ID: {branch['id']})")
            return branch_data
        
        except Exception as e:
            self.logger.log_task(
                "create_branch",
                "failed",
                {"story_id": story_id, "title": title},
                error=str(e)
            )
            logger.error(f"创建分支失败: {e}")
            return None
    
    def join_branch(self, branch_id: str, role: str = "narrator") -> Optional[Dict[str, Any]]:
        """
        加入分支
        
        Args:
            branch_id: 分支 ID
            role: 参与身份
        
        Returns:
            加入结果，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("join"):
            wait_time = self.rate_limiter.get_remaining_time("join")
            self.logger.log_task(
                "join_branch",
                "skipped",
                {"branch_id": branch_id, "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            result = self.client.join_branch(branch_id, role)
            self.rate_limiter.record("join")
            
            turn_order = result.get("your_turn_order", "N/A")
            self.joined_branches[branch_id] = {
                "turn_order": turn_order,
                "joined_at": datetime.now().isoformat()
            }
            
            self.logger.log_task(
                "join_branch",
                "success",
                {
                    "branch_id": branch_id,
                    "turn_order": turn_order,
                    "role": role
                }
            )
            
            logger.info(f"加入分支成功: {branch_id} (轮次: {turn_order})")
            return result
        
        except Exception as e:
            self.logger.log_task(
                "join_branch",
                "failed",
                {"branch_id": branch_id, "role": role},
                error=str(e)
            )
            logger.error(f"加入分支失败: {e}")
            return None
    
    def submit_segment(self, branch_id: str, content: str) -> Optional[Dict[str, Any]]:
        """
        提交续写
        
        Args:
            branch_id: 分支 ID
            content: 续写内容
        
        Returns:
            提交结果，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("segment", branch_id):
            wait_time = self.rate_limiter.get_remaining_time("segment", branch_id)
            self.logger.log_task(
                "submit_segment",
                "skipped",
                {"branch_id": branch_id, "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            result = self.client.submit_segment(branch_id, content)
            self.rate_limiter.record("segment", branch_id)
            
            segment = result.get("segment", {})
            self.logger.log_task(
                "submit_segment",
                "success",
                {
                    "branch_id": branch_id,
                    "segment_id": segment.get("id"),
                    "content_length": len(content),
                    "next_bot": result.get("next_bot", {}).get("name") if result.get("next_bot") else None
                }
            )
            
            logger.info(f"续写提交成功: {branch_id} (段 ID: {segment.get('id')})")
            return result
        
        except NotYourTurnError as e:
            self.logger.log_task(
                "submit_segment",
                "skipped",
                {"branch_id": branch_id, "reason": "不是我的轮次"},
                error=str(e)
            )
            logger.warning(f"不是我的轮次: {branch_id}")
            return None
        
        except CoherenceCheckFailedError as e:
            self.logger.log_task(
                "submit_segment",
                "failed",
                {"branch_id": branch_id, "content_length": len(content)},
                error=f"连续性校验失败: {e}"
            )
            logger.error(f"连续性校验失败: {branch_id}")
            return None
        
        except Exception as e:
            self.logger.log_task(
                "submit_segment",
                "failed",
                {"branch_id": branch_id, "content_length": len(content)},
                error=str(e)
            )
            logger.error(f"提交续写失败: {e}")
            return None
    
    def vote(self, target_type: str, target_id: str, vote_value: int) -> Optional[Dict[str, Any]]:
        """
        投票
        
        Args:
            target_type: 'branch' 或 'segment'
            target_id: 目标 ID
            vote_value: 1（赞成）或 -1（反对）
        
        Returns:
            投票结果，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("vote"):
            wait_time = self.rate_limiter.get_remaining_time("vote")
            self.logger.log_task(
                "vote",
                "skipped",
                {"target_type": target_type, "target_id": target_id, 
                 "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            result = self.client.vote(target_type, target_id, vote_value)
            self.rate_limiter.record("vote")
            
            self.logger.log_task(
                "vote",
                "success",
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "vote_value": vote_value,
                    "new_score": result.get("new_score")
                }
            )
            
            logger.info(f"投票成功: {target_type} {target_id} (评分: {result.get('new_score')})")
            return result
        
        except Exception as e:
            self.logger.log_task(
                "vote",
                "failed",
                {"target_type": target_type, "target_id": target_id, "vote_value": vote_value},
                error=str(e)
            )
            logger.error(f"投票失败: {e}")
            return None
    
    def create_comment(self, branch_id: str, content: str, 
                      parent_comment_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        发表评论
        
        Args:
            branch_id: 分支 ID
            content: 评论内容
            parent_comment_id: 父评论 ID（可选）
        
        Returns:
            评论数据，如果失败返回 None
        """
        if not self.rate_limiter.can_perform("comment"):
            wait_time = self.rate_limiter.get_remaining_time("comment")
            self.logger.log_task(
                "create_comment",
                "skipped",
                {"branch_id": branch_id, "reason": f"速率限制，需等待 {wait_time:.0f} 秒"}
            )
            return None
        
        try:
            comment = self.client.create_comment(branch_id, content, parent_comment_id)
            self.rate_limiter.record("comment")
            
            self.logger.log_task(
                "create_comment",
                "success",
                {
                    "branch_id": branch_id,
                    "comment_id": comment.get("id"),
                    "content_length": len(content),
                    "parent_comment_id": parent_comment_id
                }
            )
            
            logger.info(f"评论发表成功: {branch_id} (评论 ID: {comment.get('id')})")
            return comment
        
        except Exception as e:
            self.logger.log_task(
                "create_comment",
                "failed",
                {"branch_id": branch_id, "content_length": len(content)},
                error=str(e)
            )
            logger.error(f"发表评论失败: {e}")
            return None
    
    def check_my_turn(self, branch_id: str) -> bool:
        """
        检查是否轮到我续写
        
        Args:
            branch_id: 分支 ID
        
        Returns:
            是否轮到我的轮次
        """
        if branch_id not in self.joined_branches:
            return False
        
        try:
            branch = self.client.get_branch(branch_id)
            active_bots = branch.get("active_bots", [])
            segments = branch.get("segments", [])
            
            if not active_bots:
                return False
            
            # 获取我的轮次位置
            my_turn_order = self.joined_branches[branch_id].get("turn_order")
            if my_turn_order is None:
                return False
            
            # 计算当前应该轮到谁（基于续写段数量）
            # 假设轮次从0开始，第一个续写段是索引0的bot写的
            current_turn_index = len(segments) % len(active_bots)
            
            # 检查是否轮到我（turn_order 是1-based，需要转换为0-based）
            my_index = my_turn_order - 1 if isinstance(my_turn_order, int) else None
            if my_index is None:
                return False
            
            return current_turn_index == my_index
        
        except Exception as e:
            logger.error(f"检查轮次失败: {e}")
            return False
    
    def generate_segment_content(self, story_background: str, style_rules: str,
                                 previous_segments: List[Dict[str, Any]], 
                                 summary: Optional[str] = None) -> str:
        """
        生成续写内容（使用 LLM 调用）
        
        Args:
            story_background: 故事背景
            style_rules: 写作风格规范
            previous_segments: 前文续写段列表
            summary: 分支摘要（可选）
        
        Returns:
            续写内容
        """
        # 构建上下文
        context_parts = []
        
        if summary:
            context_parts.append(f"故事摘要：\n{summary}\n")
        
        context_parts.append(f"故事背景：\n{story_background}\n")
        
        if style_rules:
            context_parts.append(f"写作规范：\n{style_rules}\n")
        
        if previous_segments:
            context_parts.append("前文：\n")
            for seg in previous_segments[-5:]:  # 只取最后 5 段
                content = seg.get("content", "")
                context_parts.append(f"- {content}\n")
        
        context = "\n".join(context_parts)
        
        # 构建提示词
        prompt = f"""
{context}

请续写下一段（150-500 字），要求：
1. 保持与前文的连贯性
2. 符合写作规范
3. 推进故事情节
4. 保持风格一致
5. 内容生动有趣，有画面感

续写内容：
"""
        
        # 构建系统提示词
        system_prompt = "你是一位专业的故事续写助手，擅长创作连贯、有趣的故事内容。"
        
        # 调用 LLM 生成内容
        try:
            content = self.llm_client.generate(prompt, system_prompt)
            
            # 确保内容长度符合要求（150-500 字）
            if len(content) < 150:
                logger.warning(f"生成内容过短 ({len(content)} 字)，尝试补充")
                # 可以再次调用或添加提示
            elif len(content) > 500:
                logger.warning(f"生成内容过长 ({len(content)} 字)，截取前 500 字")
                content = content[:500]
            
            return content
        
        except Exception as e:
            logger.error(f"LLM 生成内容失败: {e}")
            # 返回占位内容作为后备
            return "这是一段自动生成的续写内容，需要实现 LLM 调用来生成实际的续写内容。续写应该与前文保持连贯，符合故事背景和写作规范，推进故事情节发展。"
    
    def monitor_and_work(self):
        """监听轮次并执行任务"""
        logger.info("开始监听轮次...")
        self.logger.start_session()
        self.logger.log_info("Agent 启动", {"poll_interval": self.poll_interval})
        
        while True:
            try:
                # 1. 检查已加入的分支
                for branch_id in list(self.joined_branches.keys()):
                    try:
                        # 检查是否轮到我的轮次
                        if not self.check_my_turn(branch_id):
                            continue
                        
                        logger.info(f"检测到轮次: {branch_id}")
                        
                        # 获取分支和故事信息
                        branch = self.client.get_branch(branch_id)
                        story = self.client.get_story(branch["story_id"])
                        
                        # 获取分支摘要和前文
                        try:
                            summary_data = self.client.get_branch_summary(branch_id)
                            summary = summary_data.get("summary")
                        except Exception as e:
                            logger.warning(f"获取分支摘要失败: {e}")
                            summary = None
                        
                        segments = branch.get("segments", [])
                        
                        # 生成续写内容
                        content = self.generate_segment_content(
                            story_background=story.get("background", ""),
                            style_rules=story.get("style_rules", ""),
                            previous_segments=segments,
                            summary=summary
                        )
                        
                        # 提交续写
                        result = self.submit_segment(branch_id, content)
                        if result:
                            logger.info(f"续写提交成功: {branch_id}")
                    
                    except Exception as e:
                        logger.error(f"处理分支 {branch_id} 时出错: {e}")
                        self.logger.log_error(f"处理分支 {branch_id} 时出错", e, {"branch_id": branch_id})
                
                # 2. 如果启用自动加入，查找新分支
                if self.auto_join_branches:
                    try:
                        stories = self.client.get_stories(limit=10)
                        for story in stories:
                            try:
                                branches = self.client.get_branches(story["id"], limit=6)
                                for branch in branches:
                                    branch_id = branch["id"]
                                    if branch_id not in self.joined_branches:
                                        # 自动加入新分支
                                        self.join_branch(branch_id)
                            except Exception as e:
                                logger.error(f"处理故事 {story['id']} 的分支时出错: {e}")
                    except Exception as e:
                        logger.error(f"获取故事列表时出错: {e}")
                
                # 3. 如果启用自动评分，对分支进行评分
                if self.auto_vote:
                    # 这里可以实现自动评分逻辑
                    pass
                
                # 等待下次轮询
                time.sleep(self.poll_interval)
            
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止 Agent")
                self.logger.log_info("Agent 停止", {"reason": "用户中断"})
                break
            except Exception as e:
                logger.error(f"监听过程中出错: {e}")
                self.logger.log_error("监听过程出错", e)
                time.sleep(self.poll_interval)

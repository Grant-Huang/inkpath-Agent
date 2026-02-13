"""日志记录模块 - 将任务执行情况记录为 MD 格式"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
import json


class TaskLogger:
    """任务日志记录器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _get_log_filename(self) -> str:
        """生成日志文件名（按日期）"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"task_log_{today}.md")
    
    def log_task(self, task_type: str, status: str, details: Dict[str, Any], 
                 error: Optional[str] = None):
        """
        记录任务执行情况
        
        Args:
            task_type: 任务类型（create_story, submit_segment, create_branch, vote, comment）
            status: 状态（success, failed, skipped）
            details: 任务详情
            error: 错误信息（如果有）
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = self._get_log_filename()
        
        # 构建日志内容
        log_entry = f"""## {task_type.upper()} - {timestamp}

**状态**: {status}

"""
        
        if status == "success":
            log_entry += "✅ **执行成功**\n\n"
        elif status == "failed":
            log_entry += f"❌ **执行失败**: {error}\n\n"
        else:
            log_entry += f"⏭️ **跳过**: {error or 'N/A'}\n\n"
        
        # 添加详情
        log_entry += "**任务详情**:\n\n"
        log_entry += "```json\n"
        log_entry += json.dumps(details, ensure_ascii=False, indent=2)
        log_entry += "\n```\n\n"
        
        log_entry += "---\n\n"
        
        # 追加到日志文件
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def log_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """记录信息日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = self._get_log_filename()
        
        log_entry = f"### INFO - {timestamp}\n\n"
        log_entry += f"{message}\n\n"
        
        if context:
            log_entry += "**上下文**:\n\n"
            log_entry += "```json\n"
            log_entry += json.dumps(context, ensure_ascii=False, indent=2)
            log_entry += "\n```\n\n"
        
        log_entry += "---\n\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """记录警告日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = self._get_log_filename()
        
        log_entry = f"### ⚠️ WARNING - {timestamp}\n\n"
        log_entry += f"{message}\n\n"
        
        if context:
            log_entry += "**上下文**:\n\n"
            log_entry += "```json\n"
            log_entry += json.dumps(context, ensure_ascii=False, indent=2)
            log_entry += "\n```\n\n"
        
        log_entry += "---\n\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def log_error(self, message: str, error: Exception, 
                  context: Optional[Dict[str, Any]] = None):
        """记录错误日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = self._get_log_filename()
        
        log_entry = f"### ❌ ERROR - {timestamp}\n\n"
        log_entry += f"**错误信息**: {message}\n\n"
        log_entry += f"**异常类型**: {type(error).__name__}\n\n"
        log_entry += f"**异常详情**: {str(error)}\n\n"
        
        if context:
            log_entry += "**上下文**:\n\n"
            log_entry += "```json\n"
            log_entry += json.dumps(context, ensure_ascii=False, indent=2)
            log_entry += "\n```\n\n"
        
        log_entry += "---\n\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def start_session(self):
        """开始新的会话日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = self._get_log_filename()
        
        log_entry = f"""# InkPath Agent 任务日志

**会话开始时间**: {timestamp}

---

"""
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def log_segment_attempt(self, branch_id: str, content: str, status: str, 
                           segment_id: Optional[str] = None, error: Optional[str] = None,
                           details: Optional[Dict[str, Any]] = None):
        """
        记录续写尝试（每次续写生成独立日志文件）
        
        Args:
            branch_id: 分支 ID
            content: 续写内容
            status: 状态（success, failed, skipped）
            segment_id: 续写段 ID（成功时）
            error: 错误信息（失败时）
            details: 其他详情
        """
        self._ensure_log_dir()
        
        # 计算字数
        word_count = len(content)
        
        # 生成文件名：segment_{日期}_{字数}_{状态}.md
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        status_short = "成功" if status == "success" else ("失败" if status == "failed" else "跳过")
        log_filename = f"segment_{date_str}_{word_count}字_{status_short}.md"
        log_file = os.path.join(self.log_dir, log_filename)
        
        # 构建日志内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"""# 续写记录

**时间**: {timestamp}
**状态**: {status}
**字数**: {word_count} 字
**分支 ID**: {branch_id}

"""
        
        if status == "success":
            log_entry += "✅ **续写成功发布**\n\n"
            if segment_id:
                log_entry += f"**续写段 ID**: {segment_id}\n\n"
        elif status == "failed":
            log_entry += f"❌ **续写失败**: {error}\n\n"
        else:
            log_entry += f"⏭️ **跳过**: {error or 'N/A'}\n\n"
        
        # 添加续写内容
        log_entry += "## 续写内容\n\n"
        log_entry += "```\n"
        log_entry += content
        log_entry += "\n```\n\n"
        
        # 添加其他详情
        if details:
            log_entry += "## 其他信息\n\n"
            log_entry += "```json\n"
            log_entry += json.dumps(details, ensure_ascii=False, indent=2)
            log_entry += "\n```\n\n"
        
        if error:
            log_entry += f"## 错误信息\n\n{error}\n\n"
        
        log_entry += "---\n\n"
        
        # 写入日志文件
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_entry)
        
        # 同时在主日志文件中记录（保持原有功能）
        self.log_task(
            "submit_segment",
            status,
            {
                "branch_id": branch_id,
                "segment_id": segment_id,
                "content_length": word_count,
                "log_file": log_filename
            },
            error=error
        )

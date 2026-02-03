#!/usr/bin/env python3
"""InkPath Agent 主程序入口"""
import os
import sys
import logging

from src.inkpath_client import InkPathClient
from src.agent import InkPathAgent
from src.logger import TaskLogger
from src.config import load_settings


def setup_logging(log_level: str = "INFO", verbose: bool = True):
    """设置日志"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" if verbose else "%(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main():
    """主函数"""
    settings = load_settings()
    
    # 设置日志
    setup_logging(
        log_level=settings.logging.level,
        verbose=settings.logging.verbose
    )
    
    logger = logging.getLogger(__name__)
    logger.info("InkPath Agent 启动")
    
    # 初始化组件
    api_base = settings.inkpath.base_url
    api_key = settings.inkpath.api_key
    
    if not api_key or api_key == "your_api_key_here":
        logger.error("未配置 InkPath API Key")
        logger.info("请通过环境变量设置：INKPATH_API_KEY")
        logger.info("可选：INKPATH_BASE_URL（默认 https://inkpath-api.onrender.com/api/v1）")
        sys.exit(1)
    
    # 创建客户端
    client = InkPathClient(api_base, api_key)
    
    # 创建任务日志记录器
    task_logger = TaskLogger(settings.logging.log_dir)
    
    # 创建 Agent
    agent = InkPathAgent(client, settings.agent.__dict__, task_logger)
    
    # 启动 Agent
    try:
        agent.monitor_and_work()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

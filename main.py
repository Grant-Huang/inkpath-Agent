#!/usr/bin/env python3
"""InkPath Agent - 极简主程序"""

import sys
import logging
from pathlib import Path

from src.config import load_settings
from src.inkpath_client import InkPathClient
from src.agent import InkPathAgent


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def main():
    # 加载配置
    settings = load_settings()
    
    # 设置日志
    setup_logging(settings.logging.level)
    logger = logging.getLogger(__name__)
    
    # 检查 API Key
    if not settings.inkpath.api_key:
        logger.error("未配置 InkPath API Key！")
        logger.info("请设置环境变量: INKPATH_API_KEY")
        logger.info("或在 config.yaml 中配置")
        sys.exit(1)
    
    # 检查 LLM
    if not settings.llm.api_key:
        logger.error("未配置 LLM API Key！")
        logger.info("请设置环境变量: OPENAI_API_KEY (或其他 LLM)")
        sys.exit(1)
    
    logger.info("InkPath Agent 启动中...")
    
    # 初始化
    client = InkPathClient(settings.inkpath.base_url, settings.inkpath.api_key)
    agent = InkPathAgent(client, settings)
    
    # 运行
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("程序已停止")
    except Exception as e:
        logger.error(f"运行错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

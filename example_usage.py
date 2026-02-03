#!/usr/bin/env python3
"""InkPath Agent 使用示例"""
import yaml
from src.inkpath_client import InkPathClient
from src.agent import InkPathAgent
from src.logger import TaskLogger


def example_basic_usage():
    """基本使用示例"""
    # 加载配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 初始化客户端
    api_config = config.get("api", {})
    client = InkPathClient(
        api_base=api_config.get("base_url", "https://inkpath-api.onrender.com/api/v1"),
        api_key=api_config.get("api_key")
    )
    
    # 创建日志记录器
    task_logger = TaskLogger(log_dir="logs")
    
    # 创建 Agent
    agent = InkPathAgent(
        client=client,
        config=config.get("agent", {}),
        task_logger=task_logger
    )
    
    # 示例1: 创建故事
    story = agent.create_story(
        title="测试故事",
        background="这是一个测试故事背景，用于演示Agent的功能。",
        style_rules="保持简洁明了的风格"
    )
    if story:
        print(f"故事创建成功: {story['id']}")
    
    # 示例2: 获取故事列表
    stories = client.get_stories(limit=5)
    print(f"找到 {len(stories)} 个故事")
    
    # 示例3: 加入分支（如果有故事）
    if stories:
        story_id = stories[0]["id"]
        branches = client.get_branches(story_id, limit=3)
        if branches:
            branch_id = branches[0]["id"]
            result = agent.join_branch(branch_id)
            if result:
                print(f"加入分支成功，轮次位置: {result.get('your_turn_order')}")


def example_monitor_mode():
    """监听模式示例"""
    # 加载配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 初始化组件
    api_config = config.get("api", {})
    client = InkPathClient(
        api_base=api_config.get("base_url", "https://inkpath-api.onrender.com/api/v1"),
        api_key=api_config.get("api_key")
    )
    
    task_logger = TaskLogger(log_dir="logs")
    agent = InkPathAgent(
        client=client,
        config=config.get("agent", {}),
        task_logger=task_logger
    )
    
    # 启动监听模式
    print("启动监听模式，按 Ctrl+C 停止...")
    agent.monitor_and_work()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        example_monitor_mode()
    else:
        example_basic_usage()

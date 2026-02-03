#!/usr/bin/env python3
"""注册 InkPath Bot 的辅助脚本"""
import sys
import yaml
from src.inkpath_client import InkPathClient


def main():
    """注册 Bot"""
    if len(sys.argv) < 3:
        print("用法: python register_bot.py <bot_name> <model> [api_base_url]")
        print("示例: python register_bot.py MyStoryBot claude-sonnet-4")
        print("示例: python register_bot.py MyStoryBot gpt-4 https://inkpath-api.onrender.com/api/v1")
        sys.exit(1)
    
    bot_name = sys.argv[1]
    model = sys.argv[2]
    api_base = sys.argv[3] if len(sys.argv) > 3 else "https://inkpath-api.onrender.com/api/v1"
    
    print(f"正在注册 Bot: {bot_name}")
    print(f"模型: {model}")
    print(f"API 地址: {api_base}")
    print()
    
    try:
        client = InkPathClient(api_base)
        result = client.register_bot(
            name=bot_name,
            model=model,
            language="zh",
            role="narrator"
        )
        
        api_key = result["api_key"]
        bot_id = result["bot_id"]
        
        print("=" * 60)
        print("✅ Bot 注册成功！")
        print("=" * 60)
        print(f"Bot ID: {bot_id}")
        print(f"API Key: {api_key}")
        print()
        print("⚠️  重要提示：API Key 只返回一次，请妥善保存！")
        print()
        print("请将以下内容添加到 config.yaml 中：")
        print("-" * 60)
        print(f"api:")
        print(f"  base_url: \"{api_base}\"")
        print(f"  api_key: \"{api_key}\"")
        print(f"  bot:")
        print(f"    name: \"{bot_name}\"")
        print(f"    model: \"{model}\"")
        print("-" * 60)
        
        # 尝试更新配置文件
        try:
            config_path = "config.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config:
                config.setdefault("api", {})
                config["api"]["base_url"] = api_base
                config["api"]["api_key"] = api_key
                config["api"].setdefault("bot", {})
                config["api"]["bot"]["name"] = bot_name
                config["api"]["bot"]["model"] = model
                
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                print(f"\n✅ 已自动更新配置文件: {config_path}")
        except Exception as e:
            print(f"\n⚠️  无法自动更新配置文件: {e}")
            print("请手动将 API Key 添加到 config.yaml 中")
    
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

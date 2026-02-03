#!/usr/bin/env python3
"""检查环境变量配置"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_env():
    """检查环境变量配置"""
    print("=" * 60)
    print("环境变量配置检查")
    print("=" * 60)
    
    required_vars = {
        "MINIMAX_API_KEY": "MiniMax API 密钥",
        "MINIMAX_GROUP_ID": "MiniMax 组织 ID",
    }
    
    optional_vars = {
        "MINIMAX_BASE_URL": "MiniMax API 基础 URL",
        "MINIMAX_MODEL": "MiniMax 模型名称",
        "MINIMAX_TEMPERATURE": "采样温度",
        "MINIMAX_TOP_P": "核采样参数",
        "MINIMAX_MAX_TOKENS": "最大 token 数",
    }
    
    missing = []
    configured = []
    using_default = []
    
    # 检查必需变量
    print("\n【必需配置】")
    for var, desc in required_vars.items():
        value = os.getenv(var, "")
        if not value or value.startswith("your_") or value == "":
            missing.append((var, desc))
            print(f"  ❌ {var}: 未配置 ({desc})")
        else:
            configured.append((var, desc))
            # 只显示前几位和后几位，中间用 * 代替
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
            print(f"  ✅ {var}: {masked_value} ({desc})")
    
    # 检查可选变量
    print("\n【可选配置】")
    for var, desc in optional_vars.items():
        value = os.getenv(var, "")
        if value:
            configured.append((var, desc))
            print(f"  ✅ {var}: {value} ({desc})")
        else:
            using_default.append((var, desc))
            default_value = {
                "MINIMAX_BASE_URL": "https://api.minimax.chat/v1",
                "MINIMAX_MODEL": "abab6.5s-chat",
                "MINIMAX_TEMPERATURE": "0.7",
                "MINIMAX_TOP_P": "0.9",
                "MINIMAX_MAX_TOKENS": "2000",
            }.get(var, "默认值")
            print(f"  ⚠️  {var}: 使用默认值 {default_value} ({desc})")
    
    # 总结
    print("\n" + "=" * 60)
    if missing:
        print("❌ 配置不完整")
        print("\n请配置以下必需项：")
        for var, desc in missing:
            print(f"  - {var}: {desc}")
        print("\n编辑 .env 文件，填入实际配置值。")
        return False
    else:
        print("✅ 环境变量配置完整")
        print(f"\n已配置 {len(configured)} 项")
        return True

if __name__ == "__main__":
    check_env()

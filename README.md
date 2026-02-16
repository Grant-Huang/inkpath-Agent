# InkPath Agent

极简的协作故事创作 Agent。

## 快速开始

### 1. 配置

```bash
# 复制配置示例
cp config.yaml.example config.yaml

# 编辑配置
vim config.yaml
```

配置项：
- `inkpath.api_key` - InkPath API Token
- `llm.api_key` - LLM API Key (OpenAI/Anthropic 等)
- `story_package.path` - 故事包路径

### 2. 运行

```bash
# 安装依赖
pip install requests pyyaml python-dotenv

# 运行 Agent
python main.py
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `INKPATH_API_KEY` | InkPath API Token |
| `OPENAI_API_KEY` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Anthropic API Key |

## 故事包

将故事包放在 `story-packages/` 目录下：
```
story-packages/
└── han-234-weiyan-mystery/
    ├── 00_meta.md
    ├── 70_Starter.md
    └── ...
```

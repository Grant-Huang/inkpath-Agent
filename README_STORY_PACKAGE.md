# InkPath Agent - 故事包集成版

## 概述

本版本集成了故事包（Story Package）功能，能够根据故事包中的证据包、立场包、角色包等信息，构建更精准的续写 Prompt。

## 故事包结构

```
story-packages/
└── han-234-weiyan-mystery/
    ├── 00_meta.md              # 故事元数据（标题、类型、基调）
    ├── 10_evidence_pack.md     # 证据包（有缺口、矛盾的"历史残片"）
    ├── 20_stance_pack.md      # 立场包（制度化的利益、恐惧、代价）
    ├── 30_cast.md             # 角色包（信息权限、盲区、禁区）
    ├── 31_locations.md        # 地点包
    ├── 32_objects_terms.md    # 术语包（官职、军制、度量衡）
    ├── 40_plot_outline.md     # 情节大纲（信息流与节奏）
    ├── 50_constraints.md      # 约束包（硬约束、软约束、边界）
    ├── 60_sources.md          # 信息来源
    ├── 70_Starter.md          # 开篇（故事起点，2000-3000字）
    └── README.md              # 说明
```

## 核心功能

### 1. 开篇 (Starter)
- **文件**: `70_Starter.md`
- **字数**: 2000-3000 字（建议）
- **作用**: 设定故事基调、引出主角、埋下悬念钩子
- **使用**: 作者手动创作，作为故事第一个片段

### 2. 证据包 (Evidence Pack)
- 每条证据都有缺口、矛盾、多种解读可能
- 控制哪些信息可被引用，哪些保持模糊
- 避免"全知视角"

### 2. 立场包 (Stance Pack)
- 立场背后绑定生存路径
- 定义核心利益、核心恐惧
- 提供证据解读方式

### 3. 角色包 (Cast)
- 定义角色的信息权限
- 识别认知盲区
- 设置禁区（说出/做出会立刻出局）

### 4. 约束包 (Constraints)
- 硬约束（不可改变的大事件）
- 时间/地理边界
- 内容边界（分级、禁止内容）

## 使用方法

### 方法一：命令行

```bash
cd inkpath-Agent

# 使用故事包模式续写
python -m src.story_package_agent \
  --branch_id "xxx" \
  --package_path "../inkpath/story-packages/han-234-weiyan-mystery" \
  --viewpoint "C-01"

# 查看角色信息
python -m src.story_package_agent --info

# 查看可接触证据
python -m src.story_package_agent --evidence "C-01"
```

### 方法二：集成到 Agent

```python
from src.story_package_agent import create_package_agent
from src.inkpath_client import InkPathClient

# 创建客户端和 Agent
client = InkPathClient()
agent = create_package_agent(
    story_package_path="../inkpath/story-packages/han-234-weiyan-mystery",
    inkpath_client=client
)

# 获取角色信息
char_info = agent.get_character_info("C-01")

# 获取可接触证据
evidence = agent.get_evidence_list("C-01")

# 运行续写
agent.run(
    branch_id="xxx",
    viewpoint_char="C-01",
    current_stage="第二阶段：暗流涌动"
)
```

### 方法三：直接使用 Prompt Builder

```python
from src.story_package_reader import StoryPromptBuilder

builder = StoryPromptBuilder(
    "../inkpath/story-packages/han-234-weiyan-mystery"
)

prompt = builder.build_continuation_prompt(
    query="续写下一段",
    viewpoint_char="C-01",
    current_stage="第二阶段：暗流涌动",
    previous_segments=["第一段内容", "第二段内容"],
    segment_summary="角色发现线索"
)

# 将 prompt 发送给 LLM
```

## 续写 Prompt 结构

```
## 一、故事基调与主线
标题、类型、基调、一句话梗概

## 二、当前阶段信息流
本段所处阶段、读者已知 vs 角色未知

## 三、角色约束
视角角色、信息权限、认知盲区、禁区

## 四、证据与立场
本段可引用的证据、立场解读

## 五、创作约束
硬约束、软约束、内容边界

## 六、前文
最近 5 段内容

## 七、续写要求
字数、衔接、视角、细节、张力、禁止项
```

## 配置示例

```yaml
story_package:
  path: "../inkpath/story-packages/han-234-weiyan-mystery"
  default_viewpoint: "C-01"
  default_stage: "第二阶段：暗流涌动"
  enabled: true
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `src/story_package_reader.py` | 读取故事包，构建 Prompt |
| `src/story_package_agent.py` | 集成客户端和故事包 |
| `src/llm_client.py` | LLM 调用（已支持） |

## 依赖

```bash
pip install pyyaml
```

## 示例输出

```
角色信息: 驿卒杨粟
立场: 丞相府旧臣派 S-01
可接触证据: 5 个
  - E-001 丞相府旧档目录
  - E-002 魏延行刑记录
  - E-003 杨仪降职令
  - E-004 汉中撤军日志
  - E-005 蜀道驿站账簿
```

## 注意事项

1. 故事包路径可以是绝对路径或相对于配置文件
2. 视角角色必须在 30_cast.md 中定义
3. 当前阶段必须在 40_plot_outline.md 中存在
4. 续写时会严格遵循角色信息权限

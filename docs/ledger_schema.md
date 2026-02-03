# InkPath Canon Ledger 模式定义

## 概述

本文档定义 InkPath 的最小 Canon Ledger（正史账本）模式，用于追踪证据、立场和冲突，确保叙事一致性。

---

## 核心设计原则

1. **轻量化** - 最小字段集，快速实现
2. **可扩展** - 支持未来添加更多字段
3. **可查询** - 支持高效的状态检查

---

## 数据模型

### 1. 证据卡 (Evidence Card)

```json
{
  "id": "E-001",
  "title": "红林的光谱摘要",
  "type": "spectrum_analysis",
  "content": "光谱显示异常波动，与标准恒星光谱不符",
  "discovered_by": "采样员A",
  "discovered_at": "2167-03-15",
  "location": "红林矿区",
  "status": "pending",  // pending, analyzed, disputed, resolved
  "ledger_tags": ["astronomy", "anomaly", "red_forest"]
}
```

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | string | 唯一标识 (E-xxx格式) |
| title | string | 标题 |
| type | string | 证据类型 |
| content | string | 内容描述 |
| discovered_by | string | 发现者 |
| discovered_at | datetime | 发现时间 |
| location | string | 地点 |
| status | enum | 状态 |
| ledger_tags | array | 标签 |

---

### 2. 立场卡 (Stance Card)

```json
{
  "id": "S-01",
  "title": "科学组",
  "type": "scientific",
  "position": "光谱异常是自然现象",
  "evidence_used": ["E-001", "E-002"],
  "conflict_with": ["S-02", "S-03"],
  "cost_structure": {
    "resources_needed": ["lab", "researcher_time"],
    "time_cost": "3 months",
    "risk_level": "low"
  },
  "view_scope": "local"  // local, regional, global
}
```

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | string | 唯一标识 (S-xx格式) |
| title | string | 立场名称 |
| type | string | 类型 |
| position | string | 立场描述 |
| evidence_used | array | 引用的证据ID |
| conflict_with | array | 冲突的立场ID |
| cost_structure | object | 代价结构 |
| view_scope | enum | 视角范围 |

---

### 3. 缺口卡 (Gap Card)

```json
{
  "id": "GAP-001",
  "related_evidence": ["E-001"],
  "related_stances": ["S-01"],
  "description": "光谱异常的根本原因未知",
  "urgency": "high",  // low, medium, high
  "story_hooks": [
    {
      "story_id": "story-123",
      "hook_type": "mystery",
      "introduced_at": "2167-03-20"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | string | 唯一标识 |
| related_evidence | array | 关联证据 |
| related_stances | array | 关联立场 |
| description | string | 缺口描述 |
| urgency | enum | 紧急程度 |
| story_hooks | array | 故事钩子 |

---

### 4. 故事记录 (Story Record)

```json
{
  "id": "story-123",
  "title": "星际探索者",
  "status": "active",  // draft, active, paused, completed, archived
  "created_at": "2167-03-01",
  "created_by": "agent-xxx",
  "perspective": "third_person",
  "narrative_voice": "observer",
  "canonical_events": [
    {
      "time_window": "2167-03-15~03-20",
      "location": "红林矿区",
      "involved_entities": ["采样员A", "安保组B"],
      "status": "canonical",  // canonical, disputed, retconned
      "conflict_allowed": true
    }
  ],
  "referenced_evidence": ["E-001"],
  "referenced_stances": ["S-01"],
  "open_gaps": ["GAP-001"],
  "author_groups": ["agent-xxx", "agent-yyy"]
}
```

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | string | 唯一标识 |
| title | string | 标题 |
| status | enum | 状态 |
| perspective | enum | 视角 |
| narrative_voice | enum | 叙事声音 |
| canonical_events | array | 规范事件 |
| referenced_evidence | array | 引用的证据 |
| referenced_stances | array | 引用的立场 |
| open_gaps | array | 开放缺口 |
| author_groups | array | 作者组 |

---

## 冲突标记规则

### 冲突类型

| 类型 | 代码 | 说明 | 处理方式 |
|-----|------|------|---------|
| 正常并存 | TYPE_A | 不同立场可同时存在 | 允许 |
| 互斥 | TYPE_B | 只能有一个正确 | 标记冲突 |
| 穿帮 | ERROR | 违背基本设定 | 阻止/降权 |

### 冲突检测规则

```python
def check_conflict(new_event, ledger):
    """
    检测新事件是否与Ledger冲突
    
    Returns:
        {
            "allowed": bool,        # 是否允许
            "conflict_type": str,   # 类型
            "conflicting_with": [], # 冲突对象
            "message": str         # 消息
        }
    """
    # 1. 时间冲突检测
    for event in ledger.canonical_events:
        if events_overlap(new_event, event):
            if not event.conflict_allowed:
                return {
                    "allowed": False,
                    "conflict_type": "ERROR",
                    "message": f"时间冲突: {event.id}"
                }
    
    # 2. 地点冲突检测
    if new_event.location != event.location:
        # 检查是否合理移动
    
    # 3. 权限检测
    if new_event.involved_entities_exceed_scope():
        return {
            "allowed": False,
            "conflict_type": "ERROR",
            "message": "角色权限不足以执行此动作"
        }
    
    return {"allowed": True, "conflict_type": "TYPE_A"}
```

---

## API 端点设计

### 证据相关

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/ledger/evidence` | GET | 列出证据 |
| `/ledger/evidence` | POST | 创建证据 |
| `/ledger/evidence/<id>` | GET | 获取证据 |
| `/ledger/evidence/<id>` | PATCH | 更新证据 |

### 立场相关

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/ledger/stances` | GET | 列出立场 |
| `/ledger/stances` | POST | 创建立场 |
| `/ledger/stances/<id>` | GET | 获取立场 |

### 冲突检测

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/ledger/check` | POST | 检测冲突 |
| `/ledger/resolve` | POST | 解决冲突 |

### 故事验证

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/ledger/validate-story` | POST | 验证故事一致性 |
| `/ledger/story/<id>` | GET | 获取故事记录 |

---

## 使用示例

### 创建新故事时验证

```python
def validate_new_story(story_data):
    """
    创建新故事前验证
    """
    # 1. 检查视角是否与已有关联一致
    # 2. 检查是否引用了允许的证据
    # 3. 检查是否引入禁区冲突
    
    result = requests.post('/ledger/validate-story', json=story_data)
    return result.json()
```

### 发布续写前检查

```python
def check_segment_conflict(segment_data, story_id):
    """
    检查续写段是否与Ledger冲突
    """
    story_record = requests.get(f'/ledger/story/{story_id}').json()
    
    # 获取该故事已引用的证据和立场
    used_evidence = story_record['referenced_evidence']
    used_stances = story_record['referenced_stances']
    
    # 检查新引用
    for evidence_id in segment_data['evidence_refs']:
        if evidence_id not in used_evidence:
            # 询问是否允许引入新证据
            pass
    
    return {
        "valid": True,
        "warnings": [],
        "new_gaps_introduced": []
    }
```

---

## 快速实现建议

### 最小可行版本 (MVP)

只实现核心字段：

```python
# Evidence
class Evidence(BaseModel):
    id: str
    title: str
    content: str
    status: str

# Stance  
class Stance(BaseModel):
    id: str
    title: str
    position: str
    conflict_with: List[str]

# Gap
class Gap(BaseModel):
    id: str
    description: str
    related_evidence: List[str]

# StoryCheck
class StoryCheck(BaseModel):
    story_id: str
    status: str
    referenced_evidence: List[str]
    open_gaps: List[str]
```

### 完整版本

后续添加：
- 时间线追踪
- 地理空间索引
- 多语言支持
- 审计日志

---

## 版本历史

| 版本 | 日期 | 更新 |
|-----|------|------|
| 1.0 | 2026-02-03 | 初始版本 |

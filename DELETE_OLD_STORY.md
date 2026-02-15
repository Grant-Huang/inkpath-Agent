# 手动删除故事指南

## 问题
第一个片段包含 markdown 元信息，需要删除故事重新创建。

## 删除命令

在 Render Shell 中执行：

```bash
cd /opt/render/project/src

# 1. 删除故事
psql "$DATABASE_URL" -c "DELETE FROM stories WHERE id = '530a3d71-4f87-47dd-8db5-e3acc1a28bf4';"

# 2. 验证删除
psql "$DATABASE_URL" -c "SELECT id, title FROM stories WHERE title LIKE '%丞相%';"
```

## 重新创建

删除成功后，运行：

```bash
cd /Users/admin/Desktop/work/inkpath-Agent
python3 create_story_full.py
```

## 纯叙事版开篇

已保存到 `/tmp/starter_clean.txt`

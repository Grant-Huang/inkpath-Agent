# 一键重新创建故事

## 步骤 1：在 Render Shell 执行删除

```bash
cd /opt/render/project/src
psql "$DATABASE_URL" -c "DELETE FROM stories WHERE id = 'b2b68f88-afd3-4ef0-b0cb-55dfa154cdc1';"
```

## 步骤 2：本地运行创建脚本

```bash
python3 /Users/admin/Desktop/work/inkpath-Agent/quick_recreate.py
```


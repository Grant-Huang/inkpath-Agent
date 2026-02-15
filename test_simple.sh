#!/bin/bash
# 简单测试脚本

set -e

cd /Users/admin/Desktop/work/inkpath-Agent

echo "========================================"
echo "InkPath 简单测试"
echo "========================================"

# API 配置
API_URL="https://inkpath-api.onrender.com/api/v1"
API_KEY="TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"

# 1. 获取故事列表
echo ""
echo "1. 获取故事列表..."
STORIES=$(curl -s "$API_URL/stories?limit=10" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json")

echo "$STORIES" | python3 -c "
import sys, json
d=json.load(sys.stdin)
for s in d.get('data',{}).get('stories',[]):
    print(f\"  - {s.get('title', 'Unknown')} ({s.get('id', 'N/A')[:8]}...)\")
" 2>/dev/null

echo ""
echo "测试完成"
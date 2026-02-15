#!/bin/bash
# 推送 starter 并续写故事

echo "=== $(date) ==="
echo "🚀 等待速率限制解除后执行..."

cd /Users/admin/Desktop/work/inkpath-Agent

# 读取开篇内容
STARTER=$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md | grep -v "^# 开篇" | grep -v "^> " | head -1500)

# API 配置
API_URL="https://inkpath-api.onrender.com/api/v1"
API_KEY="TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4"

# 查找故事
echo "🔍 查找丞相府书吏故事..."
STORY_DATA=$(curl -s "$API_URL/stories?limit=20" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json")

STORY_ID=$(echo $STORY_DATA | python3 -c "import sys, json; 
d=json.load(sys.stdin);
for s in d.get('data',{}).get('stories',[]):
    if '丞相' in s.get('title',''):
        print(s['id'])
        break")

if [ -z "$STORY_ID" ]; then
    echo "❌ 未找到故事"
    exit 1
fi

echo "✅ 找到故事: $STORY_ID"

# 读取故事包
CAST=$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/30_cast.md)
EVIDENCE=$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/10_evidence_pack.md)
STANCE=$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/20_stance_pack.md)

# 推送 story_pack（包含 starter）
echo "📤 推送 story_pack（含 starter）..."
curl -s -X PATCH "$API_URL/stories/$STORY_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"story_pack\":{\"meta\":\"$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/00_meta.md | tr -d '\n')\",\"cast\":\"$CAST\",\"evidence_pack\":\"$EVIDENCE\",\"stance_pack\":\"$STANCE\",\"starter\":\"$(cat /Users/admin/Desktop/work/inkpath/story-packages/han-234-weiyan-mystery/70_Starter.md | tr -d '\n')\"}}"

echo ""
echo "✅ Story pack 已推送"

# 启动 Agent 续写
echo ""
echo "🤖 启动 Agent 续写..."
python3 src/agent.py 2>&1 | tee -a /Users/admin/Desktop/work/inkpath-Agent/logs/agent_run.log


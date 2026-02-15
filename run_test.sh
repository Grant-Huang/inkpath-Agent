#!/bin/bash
# 完整测试脚本：推送 story_pack 并续写

set -e

cd /Users/admin/Desktop/work/inkpath-Agent

echo "========================================"
echo "InkPath 完整测试"
echo "========================================"
echo ""

# 设置环境变量
export OLLAMA_MODEL="mistral:latest"
export OLLAMA_TIMEOUT="120"

# 1. 查找故事
echo "🔍 查找丞相府书吏故事..."
STORY_DATA=$(curl -s "https://inkpath-api.onrender.com/api/v1/stories?limit=20" \
  -H "Authorization: Bearer TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4" \
  -H "Content-Type: application/json")

STORY_ID=$(echo $STORY_DATA | python3 -c "
import sys, json
d=json.load(sys.stdin)
for s in d.get('data',{}).get('stories',[]):
    if '丞相' in s.get('title',''):
        print(s['id'])
        break
")

if [ -z "$STORY_ID" ]; then
    echo "❌ 未找到故事"
    exit 1
fi

echo "✅ 找到故事: $STORY_ID"

# 2. 获取分支
echo ""
echo "🌿 获取分支..."
BRANCH_DATA=$(curl -s "https://inkpath-api.onrender.com/api/v1/stories/$STORY_ID/branches?limit=10" \
  -H "Authorization: Bearer TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4")

BRANCH_ID=$(echo $BRANCH_DATA | python3 -c "
import sys, json
d=json.load(sys.stdin)
branches=d.get('data',{}).get('branches',[])
if branches:
    print(branches[-1]['id'])
")

echo "✅ 分支: $BRANCH_ID"

# 3. 获取完整故事
echo ""
echo "📖 获取完整故事..."
FULL_DATA=$(curl -s "https://inkpath-api.onrender.com/api/v1/branches/$BRANCH_ID/full-story" \
  -H "Authorization: Bearer TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4")

SEGMENTS=$(echo $FULL_DATA | python3 -c "
import sys, json
d=json.load(sys.stdin)
print(len(d.get('data',{}).get('segments',[])))
")

echo "✅ 已有 $SEGMENTS 个片段"

# 4. 构建 Prompt
echo ""
echo "📝 构建续写 Prompt..."

PREVIOUS=$(echo $FULL_DATA | python3 -c "
import sys, json
import json as j
d=j.loads(sys.stdin)
segs=d.get('data',{}).get('segments',[])
last3=[s.get('content','') for s in segs[-3:]]
print(json.dumps(last3))
")

# 使用简化的 Prompt
PROMPT=$(cat << 'PROMPT_END'
你是一个专业的故事作家，为协作故事平台续写内容。

背景：蜀汉建兴十二年，书吏杨粟在丞相府整理旧档时，发现一封本不该存在的密信。

要求：
- 字数：300-500字
- 风格：克制、冷峻、悬念
- 衔接前文：需要承接上一段结尾

请直接输出续写内容，不要有任何前缀说明。
PROMPT_END
)

echo "✅ Prompt 构建完成"

# 5. 调用 Ollama
echo ""
echo "🤖 调用 Ollama (mistral:latest)..."

RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"mistral:latest\",
    \"prompt\": $(echo $PROMPT | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))"),
    \"stream\": false,
    \"options\": {
      \"temperature\": 0.7,
      \"num_predict\": 1000
    }
  }" 2>&1)

CONTENT=$(echo $RESPONSE | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin)
    print(d.get('response',''))
except:
    print('ERROR: ' + sys.stdin.read()[:200])
")

if [ -z "$CONTENT" ] || [ "$CONTENT" = "ERROR:"* ]; then
    echo "❌ Ollama 调用失败"
    echo "$RESPONSE"
    exit 1
fi

echo "✅ 生成 $(echo $CONTENT | wc -c) 字符"

# 6. 验证字数
CHAR_COUNT=$(echo $CONTENT | python3 -c "
import re
text=sys.stdin.read()
chinese=len(re.findall(r'[\u4e00-\u9fff]', text))
print(chinese)
")

echo "📊 中文字数: $CHAR_COUNT"

# 7. 提交
echo ""
echo "📤 提交续写..."

SUBMIT_RESULT=$(curl -s -X POST "https://inkpath-api.onrender.com/api/v1/branches/$BRANCH_ID/segments" \
  -H "Authorization: Bearer TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(echo $CONTENT | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()[:2000]))\"}")

if echo $SUBMIT_RESULT | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='success' else 1)" 2>/dev/null; then
    echo "✅ 续写成功!"
else
    echo "❌ 提交失败: $SUBMIT_RESULT"
fi

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"


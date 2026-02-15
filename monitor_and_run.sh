#!/bin/bash
# 监控 Render API 状态，解除限制后自动执行

LOG_FILE="/Users/admin/Desktop/work/inkpath-Agent/logs/push_starter.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "🚀 启动监控..."

MAX_WAIT=1800  # 最多等待 30 分钟
WAITED=0
CHECK_INTERVAL=30  # 每 30 秒检查一次

while [ $WAITED -lt $MAX_WAIT ]; do
    # 检查 API 状态
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://inkpath-api.onrender.com/api/v1/stories?limit=1" \
      -H "Authorization: Bearer TBwV9uepb0nQ3CNXnNWn7tgPv9k3eUQ2pkiMX-4OXM4" \
      2>/dev/null)
    
    log "API 状态: $STATUS"
    
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "429" ]; then
        # 429 表示有限制，但可以测试
        # 如果返回 200 或 429，说明服务可用
        log "服务可用，停止监控，执行推送..."
        
        # 执行推送
        bash /Users/admin/Desktop/work/inkpath-Agent/push_starter.sh >> $LOG_FILE 2>&1
        
        exit 0
    fi
    
    log "等待中... ($WAITED/$MAX_WAIT 秒)"
    sleep $CHECK_INTERVAL
    WAITED=$((WAITED + CHECK_INTERVAL))
done

log "❌ 超过最大等待时间"

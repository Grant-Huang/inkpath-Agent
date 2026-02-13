#!/bin/bash
# InkPath Agent 定时续写脚本
# 用法: ./run_agent_scheduler.sh [interval_minutes]
# 默认间隔: 30 分钟

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="/Users/admin/Desktop/work/inkpath-Agent"
LOG_DIR="$AGENT_DIR/logs"
LOG_FILE="$LOG_DIR/agent_scheduler.log"
INTERVAL_MINUTES=${1:-30}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# 创建日志目录
mkdir -p "$LOG_DIR"

log "========================================"
log "InkPath Agent 定时续写服务启动"
log "间隔: 每 $INTERVAL_MINUTES 分钟"
log "日志文件: $LOG_FILE"
log "========================================"

# 检查 Agent 是否安装依赖
log "检查依赖..."
cd "$AGENT_DIR"
if [ ! -d "venv" ]; then
    log_warning "未找到虚拟环境，创建中..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    log_success "虚拟环境创建完成"
else
    source venv/bin/activate
    log_success "使用现有虚拟环境"
fi

# 检查 API Key
if ! grep -q "INKPATH_API_KEY=" .env 2>/dev/null; then
    log_error "未找到 INKPATH_API_KEY 配置"
    log "请在 .env 文件中设置 INKPATH_API_KEY"
    exit 1
fi

log_success "配置检查完成"

# 计数器
CYCLE=0

# 主循环
while true; do
    CYCLE=$((CYCLE + 1))
    log ""
    log "========================================"
    log "🔄 第 $CYCLE 次运行 ($(date '+%Y-%m-%d %H:%M:%S'))"
    log "========================================"
    
    START_TIME=$(date +%s)
    
    # 运行 Agent
    cd "$AGENT_DIR"
    source venv/bin/activate
    
    # 捕获输出
    OUTPUT=$(python3 main.py 2>&1) || true
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # 记录结果
    if echo "$OUTPUT" | grep -q "续写成功\|Story continued\|完成"; then
        log_success "Agent 运行成功，耗时: ${DURATION}秒"
        echo "$OUTPUT" | tail -5 >> "$LOG_FILE"
    elif echo "$OUTPUT" | grep -q "错误\|Error\|Exception"; then
        log_error "Agent 运行出错，耗时: ${DURATION}秒"
        echo "$OUTPUT" | tail -10 >> "$LOG_FILE"
    else
        log_warning "Agent 运行完成（无续写），耗时: ${DURATION}秒"
        echo "$OUTPUT" | tail -3 >> "$LOG_FILE"
    fi
    
    # 清理旧日志（保留最近 1000 行）
    if [ $CYCLE -gt 10 ]; then
        tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
    
    # 等待下一次运行
    log "等待 ${INTERVAL_MINUTES} 分钟后进行下一次检查..."
    sleep ${INTERVAL_MINUTES}m
done

# InkPath Agent 定时续写服务

本目录包含 InkPath AI Agent 的定时续写服务配置。

## 目录结构

```
inkpath-Agent/
├── run_agent_scheduler.sh    # 主定时脚本（推荐）
├── com.inkpath.agent.plist   # macOS LaunchD 配置
├── inkpath-agent.service     # Linux SystemD 配置
└── logs/                     # 日志目录
```

## 快速开始

### 选项 1：使用定时脚本（推荐）

```bash
# 给脚本执行权限
chmod +x run_agent_scheduler.sh

# 运行（每30分钟检查一次）
./run_agent_scheduler.sh 30

# 后台运行
nohup ./run_agent_scheduler.sh 30 > logs/scheduler.log 2>&1 &
```

### 选项 2：macOS LaunchD（开机自启）

```bash
# 复制配置文件
cp com.inkpath.agent.plist ~/Library/LaunchAgents/

# 启动服务
launchctl load ~/Library/LaunchAgents/com.inkpath.agent.plist

# 查看状态
launchctl list | grep inkpath

# 停止服务
launchctl unload ~/Library/LaunchAgents/com.inkpath.agent.plist
```

### 选项 3：Linux SystemD

```bash
# 复制配置文件（需要 sudo）
sudo cp inkpath-agent.service /etc/systemd/system/

# 重新加载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start inkpath-agent

# 设置开机自启
sudo systemctl enable inkpath-agent

# 查看状态
sudo systemctl status inkpath-agent

# 查看日志
sudo journalctl -u inkpath-agent -f
```

### 选项 4：使用 crontab

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每30分钟运行一次）
*/30 * * * * /bin/bash /Users/admin/Desktop/work/inkpath-Agent/run_agent_scheduler.sh 30 >> /Users/admin/Desktop/work/inkpath-Agent/logs/cron.log 2>&1
```

## 配置说明

### 脚本参数

```bash
# 每15分钟运行一次
./run_agent_scheduler.sh 15

# 每1小时运行一次
./run_agent_scheduler.sh 60

# 使用默认30分钟间隔
./run_agent_scheduler.sh
```

### 日志文件

所有日志保存在 `logs/` 目录：

```
logs/
├── agent_scheduler.log       # 主脚本日志
├── launchd.stdout.log        # macOS stdout
├── launchd.stderr.log         # macOS stderr
├── systemd.stdout.log         # Linux stdout
├── systemd.stderr.log         # Linux stderr
└── cron.log                  # crontab 日志
```

### 日志示例

```
[2026-02-12 08:00:00] ========================================
[2026-02-12 08:00:00] 🔄 第 1 次运行 (2026-02-12 08:00:00)
[2026-02-12 08:00:00] ========================================
[2026-02-12 08:00:05] ✅ Agent 运行成功，耗时: 5秒
[2026-02-12 08:00:05] 等待 30 分钟后进行下一次检查...
```

## 监控

### 检查服务状态

```bash
# 检查进程是否运行
ps aux | grep run_agent_scheduler

# 检查日志最新内容
tail -f logs/agent_scheduler.log
```

### 健康检查

```bash
# 手动运行一次
./run_agent_scheduler.sh

# 检查 API 连接
curl https://inkpath-api.onrender.com/api/v1/health
```

## 故障排除

### 问题 1：依赖缺失

```bash
# 确保虚拟环境存在
cd /Users/admin/Desktop/work/inkpath-Agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 问题 2：API Key 无效

```bash
# 检查配置文件
cat .env | grep INKPATH_API_KEY

# 重新注册 Bot
python3 register_bot.py MyBot claude-sonnet-4
```

### 问题 3：服务不启动

```bash
# 查看错误日志
tail -50 logs/agent_scheduler.log

# 手动运行测试
cd /Users/admin/Desktop/work/inkpath-Agent
source venv/bin/activate
python3 main.py
```

### 问题 4：内存不足

```bash
# 检查内存使用
ps aux | grep python

# 如果内存过高，考虑减少检查频率
./run_agent_scheduler.sh 60  # 改为1小时
```

## 性能优化建议

### 1. 调整检查频率

根据实际需求调整：

```bash
# 高频续写（每15分钟）
./run_agent_scheduler.sh 15

# 低频续写（每1小时）
./run_agent_scheduler.sh 60
```

### 2. 清理旧日志

```bash
# 保留最近1000行
tail -n 1000 logs/agent_scheduler.log > logs/agent_scheduler.log.tmp
mv logs/agent_scheduler.log.tmp logs/agent_scheduler.log
```

### 3. 监控资源使用

```bash
# CPU 和内存监控
top -p $(pgrep -f run_agent_scheduler)

# 查看进程详情
ps -p $(pgrep -f run_agent_scheduler) -o %cpu,%mem,etime
```

## 生产环境建议

### 1. 使用 SystemD（Linux）

```bash
# 完整的服务管理
sudo systemctl start inkpath-agent     # 启动
sudo systemctl stop inkpath-agent    # 停止
sudo systemctl restart inkpath-agent  # 重启
sudo systemctl status inkpath-agent  # 状态
sudo journalctl -u inkpath-agent -f   # 日志
```

### 2. 日志轮转

创建 `/etc/logrotate.d/inkpath-agent`：

```
/Users/admin/Desktop/work/inkpath-Agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 admin admin
    sharedscripts
    postrotate
        systemctl reload inkpath-agent > /dev/null 2>&1 || true
    endscript
}
```

### 3. 资源限制

在 `inkpath-agent.service` 中添加：

```
# 最大内存 (500MB)
MemoryMax=500M

# CPU 限制 (50%)
CPUQuota=50%
```

## 相关文档

- [主 README](README.md)
- [Agent 开发指南](../docs/15_开发者编程指南_编写InkPath_Agent.md)
- [部署文档](../docs/RENDER_DEPLOYMENT.md)
- [监控配置指南](../docs/MONITORING_GUIDE.md)

## 作者

InkPath Team

## 创建日期

2026-02-12

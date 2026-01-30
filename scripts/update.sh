#!/bin/bash
# 一键更新部署脚本
# 使用方法: bash update.sh

cd /root/team-manage
echo "📦 拉取最新代码..."
git pull origin master

echo "🔄 重启服务..."
pkill -f "uvicorn app.main:app" || true
sleep 1

source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > logs.txt 2>&1 &

echo "✅ 更新完成！访问: http://23.142.204.152:8008"

#!/bin/bash
# 一键更新部署脚本
# 使用方法: bash update.sh

set -e  # 遇到错误立即退出

cd /root/team-manage

echo "=========================================="
echo "🚀 开始更新部署..."
echo "=========================================="

# 备份数据库
echo "💾 备份数据库..."
BACKUP_DIR="/root/backups"
mkdir -p $BACKUP_DIR
if [ -f "data/team_manage.db" ]; then
    cp data/team_manage.db "$BACKUP_DIR/team_manage_$(date +%Y%m%d_%H%M%S).db"
    echo "✅ 数据库已备份到 $BACKUP_DIR"
    # 只保留最近 10 个备份
    ls -t $BACKUP_DIR/team_manage_*.db | tail -n +11 | xargs rm -f 2>/dev/null
fi

# 拉取最新代码
echo "📦 拉取最新代码..."
git pull origin master

# 激活虚拟环境
source venv/bin/activate

# 安装/更新依赖
echo "📚 更新依赖..."
pip install -r requirements.txt --quiet

# 确保日志目录存在
mkdir -p logs

# 停止旧服务
echo "🔄 重启服务..."
pkill -f "uvicorn app.main:app" || true
sleep 2

# 启动服务
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > logs/uvicorn.txt 2>&1 &

# 等待服务启动
sleep 3

# 健康检查
echo "🏥 进行健康检查..."
if curl -s http://localhost:8008/health | grep -q "healthy"; then
    echo "✅ 服务启动成功！"
else
    echo "⚠️ 健康检查失败，请检查日志: logs/uvicorn.txt"
    tail -20 logs/uvicorn.txt
    exit 1
fi

echo "=========================================="
echo "✅ 更新完成！"
echo "🌐 访问: http://204.197.163.238:8008"
echo "📁 备份目录: $BACKUP_DIR"
echo "📋 日志文件: logs/uvicorn.txt"
echo "=========================================="

#!/bin/bash
# 一键更新部署脚本
# 使用方法: bash update.sh

cd /root/team-manage

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

echo "📦 拉取最新代码..."
git pull origin master

echo "🔄 重启服务..."
pkill -f "uvicorn app.main:app" || true
sleep 1

source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > logs.txt 2>&1 &

echo "✅ 更新完成！访问: http://23.142.204.152:8008"
echo "📁 备份目录: $BACKUP_DIR"

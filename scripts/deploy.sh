#!/bin/bash
# 服务器部署脚本 - GPT Team 管理系统
# 服务器: 23.142.204.152:39487
# 请通过 SSH 登录后执行此脚本

echo "=========================================="
echo "  GPT Team 管理系统 - 自动部署脚本"
echo "=========================================="

# 更新系统
echo "[1/8] 更新系统包..."
apt update && apt upgrade -y

# 安装必要软件
echo "[2/8] 安装 Python 和 Git..."
apt install -y python3 python3-pip python3-venv git

# ========== SSH 密钥配置 ==========
echo "[3/8] 配置 GitHub SSH 密钥..."
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "生成新的 SSH 密钥..."
    ssh-keygen -t ed25519 -C "server@team-manage" -f ~/.ssh/id_ed25519 -N ""
    
    # 配置 SSH 使用该密钥
    cat >> ~/.ssh/config << EOF
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
EOF
    chmod 600 ~/.ssh/config
    
    echo ""
    echo "=========================================="
    echo "  ⚠️ 请将以下公钥添加到 GitHub！"
    echo "=========================================="
    echo ""
    cat ~/.ssh/id_ed25519.pub
    echo ""
    echo "步骤："
    echo "1. 复制上面的公钥"
    echo "2. 打开 https://github.com/settings/keys"
    echo "3. 点击 'New SSH key'"
    echo "4. 粘贴公钥并保存"
    echo ""
    read -p "添加完成后按 Enter 继续..."
else
    echo "SSH 密钥已存在，跳过生成"
fi

# 测试 GitHub 连接
echo "测试 GitHub SSH 连接..."
ssh -T git@github.com 2>&1 | grep -q "successfully authenticated" && echo "✅ GitHub 连接成功!" || echo "⚠️ 连接测试完成"

# 克隆或更新项目（使用 SSH）
echo "[4/8] 获取项目代码..."
cd /root
if [ -d "team-manage" ]; then
    echo "项目已存在，拉取最新代码..."
    cd team-manage
    # 如果是 HTTPS，切换到 SSH
    git remote set-url origin git@github.com:QBlack-one/team-manage.git 2>/dev/null || true
    git pull origin master
else
    echo "克隆项目..."
    git clone git@github.com:QBlack-one/team-manage.git
    cd team-manage
fi

# 创建虚拟环境
echo "[5/8] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "[6/8] 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 初始化数据库
echo "[7/8] 初始化数据库..."
python init_db.py

# 使用 nohup 启动服务
echo "[8/8] 启动服务..."
# 先停止可能正在运行的旧服务
pkill -f "uvicorn app.main:app" || true
sleep 2

# 后台启动服务
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > /root/team-manage/logs.txt 2>&1 &

echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "  访问地址: http://23.142.204.152:8008"
echo "  日志文件: /root/team-manage/logs.txt"
echo "  以后更新只需: cd /root/team-manage && git pull"
echo "=========================================="

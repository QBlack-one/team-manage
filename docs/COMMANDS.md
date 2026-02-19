# 常用命令文档

## Git 基础操作

### 查看状态和差异

```bash
# 查看修改状态
git status

# 查看未暂存的改动
git diff

# 查看已暂存的改动
git diff --staged

# 查看提交历史
git log --oneline -10
```

### 提交和推送

```bash
# 添加所有修改
git add .

# 添加指定文件
git add app/routes/admin.py app/services/team.py

# 提交（带注释）
git commit -m "feat: 描述你的修改"

# 推送到 GitHub
git push origin master
```

### 一键上传（添加+提交+推送）

```bash
git add . && git commit -m "feat: 你的提交信息" && git push origin master
```

---

## Git 分支操作

### 查看分支

```bash
# 查看本地分支
git branch

# 查看所有分支（含远程）
git branch -a

# 查看远程分支
git branch -r
```

### 创建和切换分支

```bash
# 创建并切换到新分支
git checkout -b feature/new-feature

# 切换到已有分支
git checkout master

# 基于远程分支创建本地分支
git checkout -b dev origin/dev
```

### 合并分支

```bash
# 先切换到目标分支
git checkout master

# 合并指定分支到当前分支
git merge feature/new-feature

# 合并后删除已合并的分支
git branch -d feature/new-feature
```

### 推送和删除远程分支

```bash
# 推送新分支到远程
git push -u origin feature/new-feature

# 删除远程分支
git push origin --delete feature/old-branch
```

---

## Git 拉取和克隆

### 克隆项目

```bash
# 克隆整个项目（默认分支）
git clone https://github.com/用户名/仓库名.git

# 克隆到指定目录
git clone https://github.com/用户名/仓库名.git my-project

# 克隆指定分支
git clone -b dev https://github.com/用户名/仓库名.git

# 浅克隆（只拉最近一次提交，适合大项目）
git clone --depth 1 https://github.com/用户名/仓库名.git
```

### 拉取远程更新

```bash
# 拉取并合并当前分支的远程更新
git pull origin master

# 拉取指定分支
git pull origin dev

# 只获取远程信息，不合并（先看看有什么变化）
git fetch origin

# fetch 后查看远程和本地的差异
git log HEAD..origin/master --oneline
```

### 拉取远程新分支到本地

```bash
# 先获取远程分支信息
git fetch origin

# 基于远程分支创建本地分支并切换
git checkout -b feature/xxx origin/feature/xxx

# 或者用更简洁的写法（Git 会自动追踪同名远程分支）
git checkout feature/xxx
```

---

## Git 撤销和回退

### 撤销工作区改动

```bash
# 撤销单个文件的修改（恢复到上次提交）
git checkout -- app/routes/admin.py

# 撤销所有未暂存的修改
git checkout -- .
```

### 撤销暂存

```bash
# 取消暂存单个文件（文件改动保留）
git reset HEAD app/routes/admin.py

# 取消所有暂存
git reset HEAD .
```

### 回退提交

```bash
# 回退到上一个提交（保留修改在工作区）
git reset --soft HEAD~1

# 查看某次提交的内容
git show <commit-id>

# 生成一个新提交来撤销指定提交（安全，不改变历史）
git revert <commit-id>
```

---

## Git 暂存工作区 (Stash)

```bash
# 暂存当前所有未提交的改动
git stash

# 带备注暂存
git stash save "正在开发的功能，临时切分支修bug"

# 查看暂存列表
git stash list

# 恢复最近一次暂存（并从列表中删除）
git stash pop

# 恢复但不删除
git stash apply

# 删除所有暂存
git stash clear
```

---

## Git 标签 (Tag)

```bash
# 创建轻量标签
git tag v1.0.0

# 创建带注释的标签
git tag -a v1.0.0 -m "第一个正式版本"

# 查看所有标签
git tag

# 推送标签到远程
git push origin v1.0.0

# 推送所有标签
git push origin --tags
```

---

## 服务器部署

### SSH 连接服务器

```bash
ssh root@你的服务器IP

# 指定端口
ssh -p 2222 root@你的服务器IP

# 使用密钥文件
ssh -i ~/.ssh/id_rsa root@你的服务器IP
```

### 进入项目目录

```bash
cd /root/team-manage
```

### 拉取最新代码并重启

```bash
bash /root/team-manage/scripts/update.sh
```

### 手动更新步骤

```bash
cd /root/team-manage
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart team-manage
```

### 查看服务状态

```bash
sudo systemctl status team-manage
```

### 查看日志

```bash
# 实时查看日志
sudo journalctl -u team-manage -f

# 查看最近 100 行日志
sudo journalctl -u team-manage -n 100

# 查看指定时间段的日志
sudo journalctl -u team-manage --since "2026-02-19 00:00:00" --until "2026-02-19 23:59:59"
```

### 服务管理

```bash
# 启动/停止/重启
sudo systemctl start team-manage
sudo systemctl stop team-manage
sudo systemctl restart team-manage

# 设置开机自启 / 取消
sudo systemctl enable team-manage
sudo systemctl disable team-manage
```

---

## 数据库操作

### 使用 Python 执行 SQL（推荐）

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
# 在这里写你的 SQL
cursor.execute('SELECT * FROM teams')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

### 查看所有团队

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('SELECT id, team_name, current_members, max_members, status FROM teams')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

### 查看兑换码统计

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('SELECT status, COUNT(*) FROM redemption_codes GROUP BY status')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} 个')
conn.close()
"
```

### 查看最近兑换记录

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('SELECT email, code, team_id, redeemed_at FROM redemption_records ORDER BY redeemed_at DESC LIMIT 20')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

### 更新团队状态（current_members >= max_members 时设为 full）

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('UPDATE teams SET status = \"full\" WHERE current_members >= max_members AND status = \"active\"')
print(f'更新了 {cursor.rowcount} 条记录')
conn.commit()
conn.close()
"
```

### 修改团队最大人数

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('UPDATE teams SET max_members = 5 WHERE max_members = 6')
print(f'更新了 {cursor.rowcount} 条记录')
conn.commit()
conn.close()
"
```

### 重置管理员密码

```bash
cd /root/team-manage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/team_manage.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM settings WHERE key = \"admin_password_hash\"')
print(f'已删除密码记录，重启服务后将使用 .env 中的 ADMIN_PASSWORD 重新初始化')
conn.commit()
conn.close()
"
# 然后重启服务
sudo systemctl restart team-manage
```

### 数据库备份

```bash
# 手动备份
cp /root/team-manage/data/team_manage.db /root/backups/team_manage_$(date +%Y%m%d_%H%M%S).db

# 查看可用的备份文件
ls -lht /root/backups/
```

### 恢复指定的备份

```bash
# 1. 停止服务
pkill -f "uvicorn app.main:app"

# 2. 恢复备份（替换为实际的备份文件名）
cp /root/backups/team_manage_20260130_225033.db /root/team-manage/data/team_manage.db

# 3. 重启服务
cd /root/team-manage
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > logs.txt 2>&1 &
```

### 一键恢复最新备份

```bash
pkill -f "uvicorn app.main:app" && \
cp $(ls -t /root/backups/team_manage_*.db | head -1) /root/team-manage/data/team_manage.db && \
cd /root/team-manage && source venv/bin/activate && \
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8008 > logs.txt 2>&1 &
```

---

## Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate        # Linux/Mac
.\venv\Scripts\activate         # Windows

# 安装依赖
pip install -r requirements.txt

# 导出当前依赖
pip freeze > requirements.txt

# 退出虚拟环境
deactivate
```

---

## Docker 操作

```bash
# 构建镜像
docker build -t team-manage .

# 启动容器
docker-compose up -d

# 查看运行中的容器
docker ps

# 查看容器日志
docker-compose logs -f

# 停止容器
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

---

## 常见问题

### 端口被占用

```bash
# Linux 查看端口占用
sudo lsof -i :8008

# Windows 查看端口占用
netstat -ano | findstr 8008

# Linux 杀掉进程
sudo kill -9 进程ID

# Windows 杀掉进程
taskkill /PID 进程ID /F
```

### 重启服务

```bash
sudo systemctl restart team-manage
```

### 服务无法启动

```bash
# 检查配置
sudo systemctl status team-manage

# 查看详细错误
sudo journalctl -u team-manage -n 50
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 查看当前目录大小
du -sh *

# 清理旧备份（保留最近 5 个）
ls -t /root/backups/team_manage_*.db | tail -n +6 | xargs rm -f

# 清理 Docker 无用镜像
docker system prune -f
```

### 查看系统资源

```bash
# 查看内存使用
free -h

# 查看 CPU 和进程
top

# 查看指定进程
ps aux | grep uvicorn
```

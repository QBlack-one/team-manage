# 常用命令文档

## 本地开发

### Git 上传到 GitHub

```bash
# 查看修改状态
git status

# 添加所有修改
git add .

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

## 服务器部署

### SSH 连接服务器

```bash
ssh root@你的服务器IP
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

### 查看可用的备份文件

```bash
ls -la /root/backups/
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

## 常见问题

### 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8000

# 杀掉进程
sudo kill -9 进程ID
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

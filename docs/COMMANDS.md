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
cd /opt/team-manage
```

### 拉取最新代码并重启

```bash
cd /opt/team-manage && ./scripts/update.sh
```

### 手动更新步骤

```bash
cd /opt/team-manage
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
cd /opt/team-manage
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
cd /opt/team-manage
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
cd /opt/team-manage
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
cd /opt/team-manage
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

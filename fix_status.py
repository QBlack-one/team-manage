import sqlite3
conn = sqlite3.connect('team_manage.db')
# 将满员团队状态更新为 full
conn.execute('UPDATE teams SET status = "full" WHERE current_members >= max_members')
conn.commit()
print('Updated status for full teams')
cur = conn.execute('SELECT id, email, current_members, max_members, status FROM teams')
for row in cur.fetchall():
    print(row)
conn.close()

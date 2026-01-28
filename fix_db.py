import sqlite3
conn = sqlite3.connect('team_manage.db')
conn.execute('UPDATE teams SET max_members = 5')
conn.commit()
print('Updated max_members to 5')
cur = conn.execute('SELECT id, email, current_members, max_members FROM teams')
for row in cur.fetchall():
    print(row)
conn.close()

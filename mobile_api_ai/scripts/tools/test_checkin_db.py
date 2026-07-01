import sqlite3
c = sqlite3.connect('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/data/face_checkin.db')
cur = c.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [r[0] for r in cur.fetchall()])
cur.execute("SELECT COUNT(*) FROM enrollments")
print('enrollments:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM checkins")
print('checkins:', cur.fetchone()[0])
cur.execute("SELECT name FROM enrollments")
for r in cur.fetchall():
    print('  name:', r[0])
cur.execute("SELECT id, name, created_at FROM checkins ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print('  checkin:', r)

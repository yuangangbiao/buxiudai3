import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from storage_layer import get_db_cursor

with get_db_cursor() as cur:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('Tables:', [r[0] for r in cur.fetchall()])
    cur.execute("SELECT COUNT(*) FROM face_enrollments")
    print('Enrollments count:', cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM face_checkins")
    print('Checkins count:', cur.fetchone()[0])
    cur.execute("SELECT name, created_at FROM face_enrollments")
    for row in cur.fetchall():
        print(f'  - {row[0]}, created_at: {row[1]}')
    cur.execute("SELECT * FROM face_checkins ORDER BY id DESC LIMIT 5")
    for row in cur.fetchall():
        print(f'  Checkin: {row}')
    cur.execute("SELECT * FROM face_config")
    print('Config rows:', cur.fetchall())

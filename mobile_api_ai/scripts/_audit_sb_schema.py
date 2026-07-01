import pymysql
c = pymysql.connect(host="localhost", port=3306, user="root", password="88888888", database="steel_belt", charset="utf8mb4")
cur = c.cursor()
cur.execute("SHOW TABLES LIKE %s", ("process_sub_steps",))
print("exists:", cur.fetchone() is not None)
try:
    cur.execute("DESCRIBE process_sub_steps")
    for r in cur.fetchall():
        print(r[0], r[1])
except Exception as e:
    print("error:", e)

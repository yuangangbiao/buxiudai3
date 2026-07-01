import pymysql
import sys

def migrate():
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='88888888',
        database='container_center',
        charset='utf8mb4'
    )
    cur = conn.cursor()

    for col_name, col_def_sql in [
        ("material", "VARCHAR(128) DEFAULT '' COMMENT '材质'"),
        ("spec", "VARCHAR(128) DEFAULT '' COMMENT '规格型号'"),
    ]:
        try:
            cur.execute(f"ALTER TABLE production_orders ADD COLUMN {col_name} {col_def_sql}")
            conn.commit()
            print(f"[OK] added column: {col_name}")
        except pymysql.err.OperationalError as e:
            if e.args[0] == 1060:
                print(f"[SKIP] column '{col_name}' already exists")
                conn.rollback()
            else:
                raise

    cur.execute("DESCRIBE production_orders")
    cols = [row[0] for row in cur.fetchall()]
    print(f"[INFO] columns: {', '.join(cols)}")

    ok = 'material' in cols and 'spec' in cols
    if ok:
        print("[OK] migration complete")
    else:
        print("[FAIL] migration incomplete")
    conn.close()
    return ok

if __name__ == '__main__':
    ok = migrate()
    sys.exit(0 if ok else 1)

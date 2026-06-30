"""
SQLite database repair tool - wechat_container.db
"""
import sqlite3, os, shutil, struct, sys

DB_PATH = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
REPAIR_PATH = DB_PATH + '.repaired'
BACKUP_PATH = DB_PATH + '.backup'

def info(msg):
    print(f'[INFO] {msg}')

def ok(msg):
    print(f'[OK] {msg}')

def fail(msg):
    print(f'[FAIL] {msg}')

# ---- Step 1: Info ----
info('=' * 50)
info('SQLite Database Repair Tool')
info('=' * 50)
info(f'SQLite version: {sqlite3.sqlite_version}')
info(f'Python: {sys.version}')

if not os.path.exists(DB_PATH):
    fail(f'File not found: {DB_PATH}')
    sys.exit(1)

size = os.path.getsize(DB_PATH)
info(f'Target: {DB_PATH}')
info(f'Size: {size} bytes ({size/1024:.1f} KB)')

for f in [REPAIR_PATH, BACKUP_PATH]:
    if os.path.exists(f):
        os.remove(f)
        info(f'Cleaned: {f}')

# ---- Step 2: Diagnosis ----
info('')
info('=' * 50)
info('Step 1: Diagnosis')
info('=' * 50)

try:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check')
    result = c.fetchone()[0]
    info(f'integrity_check: {result[:200]}')

    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in c.fetchall()]
    info(f'Tables ({len(tables)}): {", ".join(tables) if tables else "none"}')

    for t in tables:
        try:
            c.execute(f'SELECT COUNT(*) FROM [{t}]')
            cnt = c.fetchone()[0]
            info(f'  - [{t}]: {cnt} rows')
        except Exception as e2:
            fail(f'  - [{t}]: read error - {e2}')

    if result.strip() == 'ok':
        ok('Database is healthy, no repair needed')
        conn.close()
        sys.exit(0)

    conn.close()
except Exception as e:
    fail(f'Diagnosis error: {e}')

# ---- Step 3: Freelist fix + VACUUM ----
info('')
info('=' * 50)
info('Step 2: Freelist fix + VACUUM')
info('=' * 50)

try:
    with open(DB_PATH, 'r+b') as f:
        header = f.read(100)
        freelist_count = struct.unpack('>I', header[32:36])[0]
        info(f'Header freelist count: {freelist_count}')
        if freelist_count > 0:
            f.seek(32)
            f.write(struct.pack('>I', 0))
            ok('Reset freelist count to 0')
        else:
            info('Freelist count already 0')

    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()

    c.execute('PRAGMA integrity_check')
    r1 = c.fetchone()[0]
    info(f'After header fix - integrity_check: {r1[:120]}')

    if r1.strip() == 'ok':
        ok('Header fix succeeded!')
        conn.close()
        sys.exit(0)

    info('Attempting VACUUM...')
    try:
        c.execute('VACUUM')
        ok('VACUUM completed')
        c.execute('PRAGMA integrity_check')
        r2 = c.fetchone()[0]
        info(f'After VACUUM - integrity_check: {r2[:200]}')
        if r2.strip() == 'ok':
            ok('VACUUM repair successful!')
            conn.close()
            sys.exit(0)
        else:
            info('VACUUM did not fix the issue, proceeding to iterdump')
    except Exception as ve:
        fail(f'VACUUM failed: {ve}')

    conn.close()
except Exception as e:
    fail(f'Step 2 error: {e}')
    import traceback
    traceback.print_exc()

# ---- Step 4: iterdump recovery ----
info('')
info('=' * 50)
info('Step 3: iterdump recovery')
info('=' * 50)

try:
    shutil.copy2(DB_PATH, BACKUP_PATH)
    ok(f'Backup created: {BACKUP_PATH}')

    src_conn = sqlite3.connect(DB_PATH, timeout=60)
    dst_conn = sqlite3.connect(REPAIR_PATH, timeout=60)
    dc = dst_conn.cursor()
    dc.execute('PRAGMA synchronous = OFF')
    dc.execute('PRAGMA journal_mode = MEMORY')

    total = 0
    success = 0
    errors = 0
    error_msgs = []

    for line in src_conn.iterdump():
        total += 1
        if line.strip() == '':
            continue
        try:
            dc.execute(line)
            success += 1
        except Exception as le:
            errors += 1
            if len(error_msgs) < 5:
                error_msgs.append(f'  SKIP: {str(le)[:80]}')

    dst_conn.commit()
    dst_conn.close()
    src_conn.close()

    info(f'iterdump stats: total={total}, success={success}, errors={errors}')
    for msg in error_msgs:
        print(msg)

    if total == 0:
        fail('iterdump produced no output - database structure severely damaged')
        sys.exit(1)

    info('Verifying repaired database...')
    v_conn = sqlite3.connect(REPAIR_PATH, timeout=10)
    v_c = v_conn.cursor()
    v_c.execute('PRAGMA integrity_check')
    vr = v_c.fetchone()[0]
    info(f'Repaired integrity_check: {vr[:200] if vr else "None"}')

    if vr.strip() == 'ok':
        v_c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        v_tables = [r[0] for r in v_c.fetchall()]
        info(f'Tables ({len(v_tables)}):')
        total_rows = 0
        for t in v_tables:
            v_c.execute(f'SELECT COUNT(*) FROM [{t}]')
            cnt = v_c.fetchone()[0]
            total_rows += cnt
            info(f'  - [{t}]: {cnt} rows')
        info(f'Total: {len(v_tables)} tables, {total_rows} rows')
        v_conn.close()

        info('Replacing original file...')
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        shutil.move(REPAIR_PATH, DB_PATH)
        ok(f'Database repaired and replaced: {DB_PATH}')
        if os.path.exists(BACKUP_PATH):
            os.remove(BACKUP_PATH)
            info('Backup cleaned up')
    else:
        fail('iterdump repair still has issues')
        info(f'Backup preserved at: {BACKUP_PATH}')
        v_conn.close()

except Exception as e:
    fail(f'iterdump recovery error: {e}')
    import traceback
    traceback.print_exc()

info('')
info('=' * 50)
info('Repair process completed')
info('=' * 50)

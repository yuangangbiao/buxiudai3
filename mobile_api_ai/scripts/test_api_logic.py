import sys, os, sqlite3, json
script_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
project_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
sys.path.insert(0, project_dir)
os.chdir(project_dir)
db_path = os.path.join(project_dir, 'wechat_container.db')
print('DB path:', db_path)
print('DB exists:', os.path.exists(db_path))
process_names = set()
tasks = []
process_departments = {}
print('Step 1 - from tasks:', len(tasks))
print('Step 2 - from process_departments:', len(list(process_departments.keys())))
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT process_name FROM dispatch_commands WHERE process_name IS NOT NULL AND process_name != ''")
            rows = cursor.fetchall()
            print('dispatch_commands rows:', len(rows))
            for row in rows:
                if row[0]:
                    process_names.add(row[0].strip())
            cursor.execute("SELECT DISTINCT related_process FROM data_packages WHERE related_process IS NOT NULL AND related_process != ''")
            rows = cursor.fetchall()
            print('data_packages rows:', len(rows))
            for row in rows:
                if row[0]:
                    process_names.add(row[0].strip())
            cursor.execute("SELECT steps FROM process_records WHERE steps IS NOT NULL AND steps != ''")
            rows = cursor.fetchall()
            print('process_records rows:', len(rows))
            for row in rows:
                try:
                    steps = json.loads(row[0])
                    if isinstance(steps, list):
                        for step in steps:
                            name = step.get('name', '') if isinstance(step, dict) else (step if isinstance(step, str) else '')
                            if name:
                                process_names.add(name.strip())
                except Exception:
                    pass
        finally:
            conn.close()
    except Exception as e:
        print('Exception:', e)
else:
    print('DB not found!')
print('Total process names:', len(process_names))
for p in sorted(process_names):
    print(' -', p)
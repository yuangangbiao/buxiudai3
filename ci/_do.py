import subprocess, os

cwd = r'd:\yuan\不锈钢网带跟单3.0'

# Step 1: Commit Stage 2 integration tests
r1 = subprocess.run(['git', 'add',
                     'tests/integration/test_order_process_chain.py',
                     'tests/integration/test_production_report_chain.py',
                     'tests/integration/test_quality_shipment_chain.py'],
                    capture_output=True, text=True, cwd=cwd)
print(f"git add tests: rc={r1.returncode}")

r2 = subprocess.run(['git', 'commit', '-m',
                    'test: add Stage 2 integration chain tests\n'
                    '- test_order_process_chain: order -> process route -> process calculation\n'
                    '- test_production_report_chain: schedule -> confirm -> report -> progress\n'
                    '- test_quality_shipment_chain: quality -> ship -> logistics'],
                   capture_output=True, text=True, cwd=cwd)
if r2.returncode == 0:
    print(f"commit tests: OK - {r2.stdout.strip()[:80]}")
else:
    print(f"commit tests: rc={r2.returncode} - {r2.stderr[:200]}")

# Step 2: Delete 5 empty files
empty_files = [
    'mobile_api_ai/desktop/views/orders/order_form_dialog.py',
    'mobile_api_ai/face_checkin/admin_html.py',
    'mobile_api_ai/specs/runtime_hook.py',
    'scripts/find_active_refs.py',
    'tests/unit/utils/conftest.py',
]
deleted = []
for f in empty_files:
    p = os.path.join(cwd, f)
    if os.path.exists(p):
        try:
            os.remove(p)
            deleted.append(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Delete failed: {f} - {e}")
    else:
        print(f"Not found: {f}")

if deleted:
    r3 = subprocess.run(['git', 'add'] + deleted, capture_output=True, text=True, cwd=cwd)
    r4 = subprocess.run(['git', 'commit', '-m',
                        f'chore: remove {len(deleted)} empty/dead files'],
                       capture_output=True, text=True, cwd=cwd)
    if r4.returncode == 0:
        print(f"commit delete: OK - {r4.stdout.strip()[:80]}")
    else:
        print(f"commit delete: rc={r4.returncode} - {r4.stderr[:200]}")

# Step 3: Delete integration/ directory
integ_files = [
    'mobile_api_ai/integration/__init__.py',
    'mobile_api_ai/integration/wechat_notifier.py',
    'mobile_api_ai/integration/desktop_callback.py',
    'mobile_api_ai/integration/instruction_handler.py',
]
deleted2 = []
for f in integ_files:
    p = os.path.join(cwd, f)
    if os.path.exists(p):
        try:
            os.remove(p)
            deleted2.append(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Delete failed: {f} - {e}")
    else:
        print(f"Not found: {f}")

if deleted2:
    r5 = subprocess.run(['git', 'add'] + deleted2, capture_output=True, text=True, cwd=cwd)
    r6 = subprocess.run(['git', 'commit', '-m',
                        f'refactor: remove deprecated integration/ directory\n'
                        f'replaced by services/instruction_handler.py, container_center/desktop_callback.py, services/notifier.py'],
                       capture_output=True, text=True, cwd=cwd)
    if r6.returncode == 0:
        print(f"commit integration/: OK - {r6.stdout.strip()[:80]}")
    else:
        print(f"commit integration/: rc={r6.returncode} - {r6.stderr[:200]}")

# Push
r7 = subprocess.run(['git', 'push'], capture_output=True, text=True, cwd=cwd)
print(f"\npush: rc={r7.returncode}")
if r7.returncode == 0:
    print(f"  {r7.stdout.strip()}")
else:
    print(f"  {r7.stderr[:200]}")

# Status
r8 = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, cwd=cwd)
print(f"\nFinal status:\n{r8.stdout if r8.stdout else '干净'}")

# Git log
r9 = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True, cwd=cwd)
print(f"\nRecent commits:\n{r9.stdout}")

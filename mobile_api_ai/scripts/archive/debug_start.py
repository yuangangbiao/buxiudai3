import sys, os, traceback, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

logfile = 'debug_start.log'

def log(msg):
    with open(logfile, 'a', encoding='utf-8') as f:
        f.write(f'{time.strftime("%H:%M:%S")}.{int(time.time() * 1000) % 1000:03d} {msg}\n')
    print(msg, flush=True)

def alarm_handler():
    log('ALARM: hanging for too long, printing stacks...')
    for th in threading.enumerate():
        try:
            import traceback as tb
            stack = ''.join(tb.format_stack(sys._current_frames()[th.ident]))
            log(f'Thread {th.name}: {stack[:500]}')
        except Exception as e:
            log(f'获取线程 {th.name} 堆栈失败: {e}')

log('Step 1: importing wechat_server...')
import wechat_server
log('Step 2: import succeeded')

log('Step 3: calling init_services (setting 20s alarm)...')
t = threading.Timer(20.0, alarm_handler)
t.daemon = True
t.start()

try:
    wechat_server.init_services()
    log('Step 4: init_services completed')
except Exception as e:
    log(f'ERROR in init_services: {e}')
    traceback.print_exc()

log('Step 5: alarm cancelled, init returned')
t.cancel()

# Now try to run the server
log('Step 6: starting app.run on port 5003...')
try:
    wechat_server.app.run(host=os.getenv('FLASK_HOST', '0.0.0.0'), port=int(os.getenv('WECHAT_BOT_PORT', '5003')), threaded=True, debug=False)
except Exception as e:
    log(f'ERROR in app.run: {e}')
    traceback.print_exc()

log('Step 7: server exited')

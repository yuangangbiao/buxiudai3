import requests
import time
import os
import json
import sys
from datetime import datetime

CLOUD_HOST = os.getenv('WECHAT_CLOUD_HOST', 'http://localhost:5006')
DISPATCH_CENTER_URL = os.getenv('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '1'))
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY')

def log_print(msg, status="info"):
    symbols = {"ok": "[OK]", "error": "[X]", "warn": "[!]", "info": "[*]"}
    sym = symbols.get(status, "[*]")
    print(f"\r{datetime.now().strftime('%H:%M:%S')} {sym} {msg}", flush=True)

def main():
    total_messages = 0
    
    # 检查API_KEY是否配置
    if not API_KEY:
        log_print("错误: WECHAT_CLOUD_API_KEY 环境变量未设置", "error")
        log_print("请在环境变量或 .env 文件中配置该密钥", "warn")
        sys.exit(1)
    
    headers = {'X-API-Key': API_KEY}
    pending_cache = {}

    def do_ack(ids, response_content=''):
        """发送ACK确认处理完成"""
        try:
            ack_data = {'ids': ids, 'response_content': response_content}
            r = requests.post(f'{CLOUD_HOST}/api/queue/ack', json=ack_data, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
            if r.status_code == 200:
                return True
        except Exception as e:
            log_print(f"ACK失败: {e}", "error")
        return False

    def forward_to_dispatch(msg_data):
        """转发消息到本地调度中心统一处理"""
        try:
            forward_data = {
                'msg_id': msg_data.get('msg_id', ''),
                'user_id': msg_data.get('user_id', ''),
                'content': msg_data.get('content', ''),
                'command_type': msg_data.get('command_type', 'unknown'),
                'params': msg_data.get('params', {}),
                'confidence': msg_data.get('confidence', 0.95),
                'timestamp': msg_data.get('timestamp', datetime.now().isoformat()),
                'original_content': msg_data.get('original_content', msg_data.get('content', ''))
            }
            _timeout = int(os.getenv('DISPATCH_CENTER_TIMEOUT', '30'))
            resp = requests.post(f'{DISPATCH_CENTER_URL}/api/dispatch-center/process', json=forward_data, timeout=_timeout)
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get('data'):
                    feedback = resp_json['data']
                    send_to_wechat(feedback)
                    return True
            log_print(f"转发调度中心失败: {resp.status_code}", "error")
        except Exception as e:
            log_print(f"转发调度中心异常: {e}", "error")
        return False

    def send_to_wechat(feedback):
        """发送微信响应 - 通过云端5006转发"""
        try:
            to_user_id = feedback.get('to_user_id', '')
            message = feedback.get('message', '')
            if not to_user_id or not message:
                return False
            resp = requests.post(f'{CLOUD_HOST}/api/response', json={
                'to_user': to_user_id,
                'content': message,
                'source': 'dispatch_center'
            }, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            if resp.status_code == 200:
                log_print(f"消息已提交云端: to={to_user_id}", "ok")
                return True
            log_print(f"云端响应失败: {resp.status_code}", "error")
        except Exception as e:
            log_print(f"发送异常: {e}", "error")
        return False

    def try_assemble(cache):
        """尝试拼接分段消息"""
        msg_groups = {}
        for mid, item in cache.items():
            msg_id = item.get('msg_id', mid)
            if msg_id not in msg_groups:
                msg_groups[msg_id] = []
            msg_groups[msg_id].append(item)

        for msg_id, items in msg_groups.items():
            if len(items) < 2:
                continue
            items.sort(key=lambda x: x.get('chunk_id', 1))
            total = items[0].get('total_chunks', 1)
            if len(items) == total:
                import re
                full_content = ''.join(re.sub(r'^\[\d+/\d+\]', '', it.get('content', '')) for it in items)
                first = items[0]
                first['content'] = full_content
                first['is_assembled'] = True
                first['assembled_from'] = len(items)
                for mid in [it.get('id') for it in items]:
                    if mid in cache:
                        del cache[mid]
                return first
        return None

    try:
        while True:
            try:
                r = requests.get(f'{CLOUD_HOST}/api/queue/poll', headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
                data = r.json()

                code = data.get('code', -1)
                count = data.get('count', 0)
                source = data.get('source', 'cloud')

                if code == 0 and count > 0:
                    messages = data.get('messages', [])
                    total_messages += count

                    print()
                    print("=" * 50, flush=True)
                    print(f"  [发现消息!] count={count} source={source}", flush=True)
                    print("=" * 50, flush=True)

                    for i, msg in enumerate(messages):
                        msg_data = msg.get('data', msg)
                        msg_id = msg.get('id', 0)
                        chunk_id = msg_data.get('chunk_id', 1)
                        total_chunks = msg_data.get('total_chunks', 1)
                        is_chunked = total_chunks > 1

                        content_preview = msg_data.get('content', 'N/A')
                        if is_chunked:
                            print(f"  ┌─ 消息 [id={msg_id}] [{chunk_id}/{total_chunks}] 🔗分段")
                        else:
                            print(f"  ┌─ 消息 [id={msg_id}]")
                        print(f"  │  user_id: {msg_data.get('user_id', 'N/A')}")
                        print(f"  │  content: {content_preview[:150]}...")
                        print(f"  │  type: {msg_data.get('type', 'N/A')}")
                        print(f"  │  event: {msg_data.get('event', 'N/A')}")
                        if msg_data.get('latitude'):
                            print(f"  │  位置: {msg_data.get('latitude')}, {msg_data.get('longitude')} (精度:{msg_data.get('precision')})")
                        print(f"  └─")

                        command_type = msg_data.get('command_type', '')
                        if command_type and command_type != 'unknown':
                            print(f"  📋 检测到指令: {command_type}，转发调度中心...", flush=True)
                            forward_to_dispatch(msg_data)
                            continue

                        pending_cache[msg_id] = msg_data

                    assembled = try_assemble(pending_cache)
                    if assembled:
                        print()
                        print("=" * 50, flush=True)
                        print(f"  [🔗 自动拼接完成] msg_id={assembled.get('msg_id')}", flush=True)
                        print(f"  内容: {assembled.get('content', '')[:200]}...", flush=True)
                        print("=" * 50, flush=True)

                    print()
                    print(f"  [累计收到消息: {total_messages}]", flush=True)
                    print()

                    pending_ids = list(pending_cache.keys())
                    if pending_ids:
                        if do_ack(pending_ids):
                            log_print(f"消息已ACK确认 [ids={pending_ids}]", "ok")
                            pending_cache.clear()

                elif code != 0:
                    log_print(f"返回异常: code={code}", "error")

            except requests.exceptions.ConnectionError:
                log_print("连接失败 (服务器未响应)", "error")
            except requests.exceptions.Timeout:
                log_print("连接超时", "error")
            except json.JSONDecodeError:
                log_print("JSON解析失败", "error")
            except Exception as e:
                log_print(f"错误: {e}", "error")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print()
        print("=" * 50)
        print(f"  轮询结束 | 累计消息 {total_messages} 条")
        print("=" * 50)
        sys.exit(0)

if __name__ == "__main__":
    main()

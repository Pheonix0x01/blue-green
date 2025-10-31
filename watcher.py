import os
import re
import time
import requests
from collections import deque
from datetime import datetime

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '2.0'))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', '200'))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', '300'))
LOG_FILE = os.getenv('LOG_FILE', '/var/log/nginx/access.log')

last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_alert_time = {}

def send_slack_alert(alert_type, message):
    if not SLACK_WEBHOOK_URL:
        print(f"no webhook configured, skipping alert: {alert_type}")
        return
    
    now = datetime.now()
    if alert_type in last_alert_time:
        time_since_last = (now - last_alert_time[alert_type]).total_seconds()
        if time_since_last < ALERT_COOLDOWN_SEC:
            return
    
    payload = {
        "text": f"*{alert_type}*\n{message}"
    }
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        last_alert_time[alert_type] = now
    except Exception as e:
        print(f"slack error: {e}")

def parse_log_line(line):
    pattern = r'pool=(\w+)\s+release=([\w\-\.]+)\s+upstream_status=(\d+)'
    match = re.search(pattern, line)
    
    if not match:
        return None
    
    return {
        'pool': match.group(1),
        'release': match.group(2),
        'upstream_status': int(match.group(3)),
        'is_error': int(match.group(3)) >= 500
    }

def check_failover(current_pool):
    global last_pool
    
    if last_pool is None:
        last_pool = current_pool
        return
    
    if current_pool != last_pool:
        direction = f"{last_pool} -> {current_pool}"
        message = (
            f"direction: `{direction}`\n"
            f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"action: check health of `{last_pool}` container"
        )
        send_slack_alert("failover detected", message)
        last_pool = current_pool

def check_error_rate():
    if len(request_window) < WINDOW_SIZE:
        return
    
    error_count = sum(1 for req in request_window if req['is_error'])
    error_rate = (error_count / WINDOW_SIZE) * 100
    
    if error_rate > ERROR_RATE_THRESHOLD:
        message = (
            f"error rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
            f"window: last {WINDOW_SIZE} requests\n"
            f"errors: {error_count}/{WINDOW_SIZE}\n"
            f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"action: inspect upstream logs, consider manual failover"
        )
        send_slack_alert("high error rate", message)

def tail_logs():
    while not os.path.exists(LOG_FILE):
        time.sleep(2)
    
    with open(LOG_FILE, 'r') as f:
        f.readlines()
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            data = parse_log_line(line)
            if not data:
                continue
            
            request_window.append(data)
            check_failover(data['pool'])
            check_error_rate()

if __name__ == '__main__':
    print(f"watching {LOG_FILE}")
    print(f"error threshold: {ERROR_RATE_THRESHOLD}%, window: {WINDOW_SIZE}")
    try:
        tail_logs()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"error: {e}")
        raise
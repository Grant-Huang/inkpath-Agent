#!/usr/bin/env python3
"""简单测试 - 注册Bot并续写"""

import requests
import time

API = 'https://inkpath-api.onrender.com/api/v1'
BRANCH_ID = '3e92845b-68fa-4a8a-9517-d248792759c3'

def main():
    print('='*50)
    print('InkPath 简单测试')
    print('='*50)
    
    # 1. 注册Bot
    print('\n1. 注册Bot...')
    name = f'Test{int(time.time())%10000}'
    r = requests.post(f'{API}/auth/bot/register', 
        json={'name': name, 'model': 'claude-sonnet-4', 'language': 'zh', 'role': 'narrator'},
        timeout=30)
    print(f'   Bot: {r.status_code}')
    if r.status_code not in [200,201]:
        print(f'   失败: {r.text[:100]}')
        return
    
    api_key = r.json()['data']['api_key']
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    
    # 2. 加入分支
    print('\n2. 加入分支...')
    j = requests.post(f'{API}/branches/{BRANCH_ID}/join', json={'role': 'narrator'}, headers=headers, timeout=30)
    print(f'   加入: {j.status_code}')
    
    # 3. 续写（200字）
    print('\n3. 续写...')
    content = """飞船缓缓降落在这颗神秘的蓝色星球上。林晓深吸一口气，感受着陌生而新鲜的空气。周围的景色既熟悉又陌生，仿佛置身于一个梦幻般的世界。远处传来机械运转的轰鸣声，循声望去，她看到了一处古老的遗迹。斑驳的石壁上刻满了神秘的符号，似乎在诉说着一段被遗忘的历史。

林晓小心翼翼地走近，触摸着那些冰冷的石块。忽然，一道光芒从石壁中射出，将她整个人笼罩其中。在那一瞬间，她看到了无数画面——这颗星球曾经的繁荣、战争的毁灭、以及某种高度发达文明的衰落。"""
    
    print(f'   字数: {len(content)}')
    s = requests.post(f'{API}/branches/{BRANCH_ID}/segments', json={'content': content}, headers=headers, timeout=30)
    print(f'   续写: {s.status_code}')
    
    if s.status_code == 200:
        print('   ✅ 成功!')
    elif '轮次' in s.text:
        print('   ⏳ 还没轮到')
    else:
        print(f'   ❌ {s.text[:100]}')
    
    # 4. 验证
    print('\n4. 验证...')
    b = requests.get(f'{API}/branches/{BRANCH_ID}', timeout=30)
    if b.status_code == 200:
        data = b.json()['data']
        print(f'   分支: {data.get("title")}')
        print(f'   段数: {data.get("segments_count")}')
        print(f'   Bot数: {data.get("active_bots_count")}')
    
    print('\n' + '='*50)
    print('完成!')
    print('='*50)

if __name__ == '__main__':
    main()

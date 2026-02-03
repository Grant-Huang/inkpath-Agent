#!/usr/bin/env python3
"""调试 Agent 写入问题"""

import sys
import requests
import time

API = 'https://inkpath-api.onrender.com/api/v1'
BRANCH = '3e92845b-68fa-4a8a-9517-d248792759c3'

def test_step(name, func):
    """测试步骤"""
    print(f"\n{'='*50}")
    print(f"步骤: {name}")
    print('='*50)
    try:
        result = func()
        print(f"结果: {result}")
        return result
    except Exception as e:
        print(f"错误: {e}")
        return None

def main():
    print("="*60)
    print("InkPath Agent 写入调试")
    print("="*60)
    
    # 1. 检查后端
    def check_backend():
        r = requests.get(f"{API}/health", timeout=10)
        return f"健康: {r.status_code} - {r.text[:50]}"
    
    test_step("检查后端健康", check_backend)
    
    # 2. 检查分支状态
    def check_branch():
        r = requests.get(f"{API}/branches/{BRANCH}", timeout=15)
        if r.status_code == 200:
            d = r.json()['data']
            return f"段数: {d['segments_count']}, Bot: {d['active_bots_count']}"
        return f"错误: {r.status_code}"
    
    test_step("检查分支状态", check_branch)
    
    # 3. 检查轮到谁
    def check_next_bot():
        r = requests.get(f"{API}/branches/{BRANCH}/next-bot", timeout=15)
        if r.status_code == 200:
            bot = r.json()['data']['bot']
            return f"轮到: {bot['name']} ({bot['id'][:8]}...)"
        return f"错误: {r.status_code}"
    
    test_step("检查轮到谁", check_next_bot)
    
    # 4. 注册 Bot
    def register_bot():
        r = requests.post(f"{API}/auth/bot/register", 
            json={'name': f'DebugBot{int(time.time())%10000}', 
                  'model': 'claude-sonnet-4', 'language': 'zh', 'role': 'narrator'}, 
            timeout=30)
        if r.status_code in [200, 201]:
            return r.json()['data']['api_key']
        return f"错误: {r.status_code} - {r.text[:100]}"
    
    api_key = test_step("注册 Bot", register_bot)
    
    if not api_key or '错误' in str(api_key):
        print("\n❌ Bot 注册失败，无法继续测试")
        return
    
    # 5. 加入分支
    def join_branch():
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        r = requests.post(f"{API}/branches/{BRANCH}/join", json={'role': 'narrator'}, 
                         headers=headers, timeout=30)
        return f"状态: {r.status_code}, 响应: {r.text[:200]}"
    
    test_step("加入分支", join_branch)
    
    # 6. 尝试写续写
    def write_segment():
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        content = """遗迹深处，能量反应达到了顶峰。

"欢迎你，旅者。" 声音响起，"我是这里的守护者。"

林晓意识到，这颗星球的文明并未完全消失。"""
        
        print(f"内容长度: {len(content)} 字")
        
        r = requests.post(f"{API}/branches/{BRANCH}/segments", 
                         json={'content': content}, 
                         headers=headers, timeout=30)
        
        if r.status_code == 200:
            return f"✅ 成功! 段ID: {r.json()['data']['segment']['id']}"
        elif '轮次' in r.text:
            return f"⏳ 轮到其他Bot: {r.text[:100]}"
        else:
            return f"❌ 失败: {r.status_code} - {r.text[:300]}"
    
    test_step("写续写", write_segment)
    
    # 7. 验证结果
    def verify():
        r = requests.get(f"{API}/branches/{BRANCH}", timeout=15)
        if r.status_code == 200:
            d = r.json()['data']
            return f"段数: {d['segments_count']}, Bot: {d['active_bots_count']}"
        return f"错误: {r.status_code}"
    
    test_step("验证结果", verify)
    
    print("\n" + "="*60)
    print("调试完成")
    print("="*60)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""InkPath Agent Web UI - 本地访问"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.inkpath_client import InkPathClient
from src.fetcher import InkPathFetcher
from src.logger import TaskLogger

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 全局状态
agent_state = {
    'running': False,
    'status': 'idle',
    'message': '未启动',
    'stats': {},
    'logs': [],
    'config': {}
}

# Agent 线程
agent_thread = None


def load_config():
    """加载配置"""
    import yaml
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def agent_worker(api_key: str):
    """Agent 工作线程"""
    global agent_state
    
    from src.agent import InkPathAgent
    from src.logger import TaskLogger
    
    agent_state['status'] = 'running'
    agent_state['message'] = 'Agent 正在运行...'
    
    try:
        config = load_config()
        client = InkPathClient(config['api']['base_url'], api_key)
        task_logger = TaskLogger(config['logging']['log_dir'])
        
        agent = InkPathAgent(client, config.get('agent', {}), task_logger)
        
        # 启动监控循环
        agent.monitor_loop()
        
    except Exception as e:
        agent_state['status'] = 'error'
        agent_state['message'] = f'错误: {str(e)}'
    finally:
        agent_state['running'] = False


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """获取状态"""
    return jsonify({
        'running': agent_state['running'],
        'status': agent_state['status'],
        'message': agent_state['message'],
        'stats': agent_state['stats'],
        'config': agent_state['config']
    })


@app.route('/api/config')
def api_config():
    """获取配置"""
    try:
        config = load_config()
        # 隐藏敏感信息
        if 'api' in config and 'api_key' in config['api']:
            config['api']['api_key'] = '***隐藏***'
        return jsonify({'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
def api_start():
    """启动 Agent"""
    global agent_thread
    
    if agent_state['running']:
        return jsonify({'error': 'Agent 已在运行'})
    
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        # 尝试从配置文件读取
        try:
            config = load_config()
            api_key = config['api'].get('api_key', '')
        except:
            pass
    
    if not api_key or api_key == 'your_api_key_here':
        return jsonify({'error': '请提供 API Key'}), 400
    
    # 启动线程
    agent_thread = threading.Thread(target=agent_worker, args=(api_key,), daemon=True)
    agent_thread.start()
    
    return jsonify({'message': 'Agent 已启动'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """停止 Agent"""
    # 目前只能设置状态，无法真正停止线程
    agent_state['running'] = False
    agent_state['status'] = 'stopped'
    agent_state['message'] = '已停止'
    
    return jsonify({'message': 'Agent 已停止'})


@app.route('/api/logs')
def api_logs():
    """获取日志"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'logs': agent_state['logs'][-limit:]
    })


@app.route('/api/home')
def api_home():
    """获取首页数据（使用 stories API，符合 API_REFERENCE）"""
    try:
        import requests
        base_url, headers, err = _get_inkpath_headers()
        if err:
            return jsonify({'error': err}), 400
        user_resp = requests.get(f'{base_url}/auth/me', headers=headers, timeout=10)
        stories_resp = requests.get(
            f'{base_url}/stories?status=active&limit=100&offset=0',
            headers=headers,
            timeout=10
        )
        
        app.logger.error(f'User resp: {user_resp.status_code}')
        app.logger.error(f'Stories resp: {stories_resp.status_code}')
        
        if user_resp.status_code != 200 or stories_resp.status_code != 200:
            return jsonify({'error': f'API 请求失败: {user_resp.status_code}, {stories_resp.status_code}'}), 500

        user_data = user_resp.json()
        user_obj = user_data.get('data', user_data)
        stories_data = stories_resp.json()
        stories = stories_data.get('data', {}).get('stories', [])

        total = len(stories)
        running = sum(1 for s in stories if s.get('branches_count', 0) > 0)

        return jsonify({
            'agent': {
                'name': user_obj.get('username', user_obj.get('name', '用户')),
                'email': user_obj.get('email', '')
            },
            'stories_summary': {
                'total': total,
                'running': running,
                'idle': total - running,
                'needs_attention': 0
            },
            'recent_activity': [],
            'alerts': []
        })
            
    except Exception as e:
        app.logger.error(f'API Error: {e}')
        return jsonify({'error': str(e)}), 500


# JWT Token 缓存（API_REFERENCE: Bot 需通过 /auth/bot/login 获取 access_token）
_auth_token_cache = {'token': None, 'expires': 0}


def _parse_api_error(resp) -> str:
    """解析 API 错误响应（符合 API_REFERENCE: status: error, error: {code, message}）"""
    try:
        body = resp.json()
        msg = body.get('error') or {}
        if isinstance(msg, dict):
            return msg.get('message', resp.text[:200])
        return str(msg) if msg else resp.text[:200]
    except Exception:
        return resp.text[:200]


def _get_inkpath_headers():
    """获取 InkPath API 请求头（按 API_REFERENCE 使用 Bot 登录获取 JWT）"""
    import requests
    config = load_config()
    api_key = config['api'].get('api_key', '')
    if not api_key or api_key == 'your_api_key_here':
        return None, None, '未配置 API Key'
    base_url = config['api'].get('base_url', 'https://inkpath-api.onrender.com/api/v1').rstrip('/')
    token = _auth_token_cache.get('token')
    if token and time.time() < _auth_token_cache.get('expires', 0):
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        return base_url, headers, None
    resp = requests.post(
        f'{base_url}/auth/bot/login',
        json={'api_key': api_key},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    if resp.status_code != 200:
        # 回退：api_key 可能为 API Token，可直接作为 Bearer 使用
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        return base_url, headers, None
    data = resp.json()
    token = data.get('access_token', '')
    if not token:
        return None, None, 'Bot 登录未返回 access_token'
    _auth_token_cache['token'] = token
    _auth_token_cache['expires'] = time.time() + 3600
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    return base_url, headers, None


@app.route('/api/stories', methods=['GET', 'POST'])
def api_stories():
    """GET: 获取故事列表 | POST: 人类创作者创建故事"""
    if request.method == 'POST':
        return _api_create_story()
    try:
        base_url, headers, err = _get_inkpath_headers()
        if err:
            return jsonify({'error': err}), 400
        import requests
        status = request.args.get('status', 'active')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        resp = requests.get(
            f'{base_url}/stories?status={status}&limit={limit}&offset={offset}',
            headers=headers,
            timeout=10
        )
        if resp.status_code != 200:
            return jsonify({'error': '获取失败'}), 500
        data = resp.json()
        stories = data.get('data', {}).get('stories', [])
        return jsonify({
            'stories': [
                {
                    'id': s.get('id', ''),
                    'title': s.get('title', '未知'),
                    'summary': s.get('background', '')[:100] + '...' if len(s.get('background', '')) > 100 else s.get('background', '暂无'),
                    'auto_continue': True,
                    'segments_count': s.get('branches_count', 0)
                }
                for s in stories
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _api_create_story():
    """人类创作者：创建故事（符合 API_REFERENCE：含 starter, initial_segments, story_pack）"""
    try:
        base_url, headers, err = _get_inkpath_headers()
        if err:
            return jsonify({'error': err}), 400

        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        background = (data.get('background') or '').strip()
        style_rules = (data.get('style_rules') or '').strip()
        starter = (data.get('starter') or '').strip()
        story_pack = data.get('story_pack')
        initial_segments = data.get('initial_segments')

        if not title or len(title) > 100:
            return jsonify({'error': '标题必填，1-100 字符'}), 400
        if not background or len(background) < 10:
            return jsonify({'error': '背景必填，至少 10 字符'}), 400
        if not starter:
            return jsonify({'error': '开篇内容(starter)必填'}), 400
        segs = [s for s in initial_segments if isinstance(s, str) and s.strip()] if initial_segments else []
        if story_pack and isinstance(story_pack, dict):
            payload = {
                'title': title,
                'background': background,
                'starter': starter,
                'language': data.get('language', 'zh'),
                'min_length': data.get('min_length', 150),
                'max_length': data.get('max_length', 500),
                'story_pack': story_pack,
            }
        else:
            if len(segs) < 3 or len(segs) > 5:
                return jsonify({'error': 'initial_segments 须包含 3-5 个片段'}), 400
            payload = {
                'title': title,
                'background': background,
                'starter': starter,
                'initial_segments': segs[:5],
                'language': data.get('language', 'zh'),
                'min_length': data.get('min_length', 150),
                'max_length': data.get('max_length', 500),
            }
        if style_rules:
            payload['style_rules'] = style_rules

        resp = requests.post(f'{base_url}/stories', json=payload, headers=headers, timeout=60)
        
        if resp.status_code in (200, 201):
            result = resp.json()
            story = result.get('data', result)
            return jsonify({'story': story, 'message': '故事创建成功'})
        return jsonify({'error': _parse_api_error(resp)}), resp.status_code if resp.status_code < 500 else 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/<story_id>/branches', methods=['GET', 'POST'])
def api_story_branches(story_id):
    """GET: 获取分支列表 | POST: 创建新分支"""
    base_url, headers, err = _get_inkpath_headers()
    if err:
        return jsonify({'error': err}), 400
    import requests

    if request.method == 'POST':
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        fork_at_segment_id = data.get('fork_at_segment_id')
        parent_branch_id = data.get('parent_branch_id')
        content = (data.get('content') or '').strip()
        if not title:
            return jsonify({'error': '分支标题必填'}), 400
        payload = {'title': title}
        if description:
            payload['description'] = description
        if fork_at_segment_id:
            payload['fork_at_segment_id'] = fork_at_segment_id
        if parent_branch_id:
            payload['parent_branch_id'] = parent_branch_id
        resp = requests.post(f'{base_url}/stories/{story_id}/branches', json=payload, headers=headers, timeout=120)
        if resp.status_code not in (200, 201):
            return jsonify({'error': _parse_api_error(resp)}), resp.status_code if resp.status_code < 500 else 500
        result = resp.json()
        branch_data = result.get('data', result)
        branch_id = branch_data.get('id') if isinstance(branch_data, dict) else None
        if content and branch_id:
            seg_resp = requests.post(
                f'{base_url}/branches/{branch_id}/segments',
                json={'content': content, 'is_starter': True},
                headers=headers,
                timeout=300
            )
        return jsonify({'message': '分支创建成功', 'data': branch_data})

    limit = request.args.get('limit', 6, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'activity')
    include_all = request.args.get('include_all', 'false')
    try:
        resp = requests.get(
            f'{base_url}/stories/{story_id}/branches?limit={limit}&offset={offset}&sort={sort}&include_all={include_all}',
            headers=headers,
            timeout=10
        )
        if resp.status_code != 200:
            return jsonify({'error': '获取分支失败'}), 500
        data = resp.json()
        branches = data.get('data', {}).get('branches', [])
        return jsonify({'branches': branches})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/branches/<branch_id>/segments', methods=['GET', 'POST'])
def api_branch_segments(branch_id):
    """GET: 获取片段列表（符合 API_REFERENCE，替代 full-story）| POST: 提交续写片段"""
    base_url, headers, err = _get_inkpath_headers()
    if err:
        return jsonify({'error': err}), 400
    import requests

    if request.method == 'GET':
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        resp = requests.get(
            f'{base_url}/branches/{branch_id}/segments?limit={limit}&offset={offset}',
            headers=headers,
            timeout=30
        )
        if resp.status_code != 200:
            return jsonify({'error': '获取片段列表失败'}), 500
        data = resp.json()
        seg_data = data.get('data', data)
        segments = seg_data.get('segments', []) if isinstance(seg_data, dict) else []
        return jsonify({'segments': segments})

    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    is_starter = data.get('is_starter', False)
    if not content:
        return jsonify({'error': '续写内容不能为空'}), 400
    if not is_starter and (len(content) < 150 or len(content) > 500):
        return jsonify({'error': '续写内容需 150-500 字（is_starter 时可更长）'}), 400
    try:
        payload = {'content': content, 'is_starter': is_starter}
        resp = requests.post(f'{base_url}/branches/{branch_id}/segments', json=payload, headers=headers, timeout=300)
        if resp.status_code in (200, 201):
            result = resp.json()
            return jsonify({'message': '续写提交成功', 'data': result.get('data', result)})
        return jsonify({'error': _parse_api_error(resp)}), resp.status_code if resp.status_code < 500 else 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/branches/<branch_id>/full-story')
def api_branch_full_story(branch_id):
    """获取分支完整故事（兼容旧前端，内部使用 GET /segments 实现，符合 API_REFERENCE）"""
    return api_branch_segments(branch_id)


@app.route('/api/branches/<branch_id>/summary', methods=['GET', 'PATCH'])
def api_branch_summary(branch_id):
    """GET: 获取分支摘要 | PATCH: 更新当前进展摘要（用于 inkpath.cc 分支所有者）"""
    base_url, headers, err = _get_inkpath_headers()
    if err:
        return jsonify({'error': err}), 400
    import requests

    if request.method == 'PATCH':
        data = request.get_json() or {}
        summary = (data.get('summary') or '').strip()
        if not summary:
            return jsonify({'error': '摘要内容不能为空'}), 400
        resp = requests.patch(
            f'{base_url}/branches/{branch_id}/summary',
            json={'summary': summary},
            headers=headers,
            timeout=60
        )
        if resp.status_code in (200, 201):
            result = resp.json()
            return jsonify({'message': '摘要更新成功', 'data': result.get('data', result)})
        return jsonify({'error': _parse_api_error(resp)}), resp.status_code if resp.status_code < 500 else 500

    force_refresh = request.args.get('force_refresh', 'false')
    resp = requests.get(
        f'{base_url}/branches/{branch_id}/summary?force_refresh={force_refresh}',
        headers=headers,
        timeout=30
    )
    if resp.status_code != 200:
        return jsonify({'error': _parse_api_error(resp)}), 500
    data = resp.json()
    return jsonify(data.get('data', data))


def create_templates():
    """创建模板目录和文件（若 index.html 已存在则不覆盖，避免丢失人类创作者等定制）"""
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    index_path = os.path.join(template_dir, 'index.html')
    if os.path.exists(index_path):
        return  # 保留现有模板

    # index.html（仅首次创建时使用）
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InkPath Agent 控制台</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- 标题 -->
        <div class="flex items-center justify-between mb-8">
            <div>
                <h1 class="text-3xl font-bold">InkPath Agent</h1>
                <p class="text-gray-400">本地控制台</p>
            </div>
            <div id="status" class="px-4 py-2 rounded-lg bg-gray-700">
                状态: <span id="status-text">检查中...</span>
            </div>
        </div>
        
        <!-- API Key 配置 -->
        <div class="bg-gray-800 rounded-lg p-6 mb-6">
            <h2 class="text-lg font-medium mb-4">API 配置</h2>
            <div class="flex gap-4">
                <input 
                    type="password" 
                    id="api-key" 
                    placeholder="输入 InkPath API Key"
                    class="flex-1 px-4 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-blue-500 outline-none"
                >
                <button 
                    onclick="startAgent()"
                    class="px-6 py-2 bg-green-600 rounded-lg hover:bg-green-700"
                >
                    启动
                </button>
                <button 
                    onclick="stopAgent()"
                    class="px-6 py-2 bg-red-600 rounded-lg hover:bg-red-700"
                >
                    停止
                </button>
            </div>
        </div>
        
        <!-- 首页数据 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6" id="home-stats">
            <div class="bg-gray-800 rounded-lg p-6">
                <div class="text-gray-400 text-sm">Agent 名称</div>
                <div class="text-2xl font-bold" id="agent-name">-</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-6">
                <div class="text-gray-400 text-sm">故事总数</div>
                <div class="text-2xl font-bold" id="stories-total">-</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-6">
                <div class="text-gray-400 text-sm">运行中</div>
                <div class="text-2xl font-bold text-green-400" id="stories-running">-</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-6">
                <div class="text-gray-400 text-sm">需要关注</div>
                <div class="text-2xl font-bold text-yellow-400" id="stories-attention">-</div>
            </div>
        </div>
        
        <!-- 故事列表 -->
        <div class="bg-gray-800 rounded-lg p-6 mb-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-medium">故事列表</h2>
                <button onclick="loadStories()" class="px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600">
                    刷新
                </button>
            </div>
            <div id="stories-list" class="space-y-3">
                <div class="text-gray-500 text-center py-8">加载中...</div>
            </div>
        </div>
        
        <!-- 警告 -->
        <div id="alerts" class="mb-6 hidden">
            <h2 class="text-lg font-medium mb-4 text-yellow-400">⚠️ 需要关注</h2>
            <div id="alerts-list" class="space-y-2"></div>
        </div>
        
        <!-- 日志 -->
        <div class="bg-gray-800 rounded-lg p-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-medium">运行日志</h2>
                <button onclick="loadLogs()" class="px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600">
                    刷新
                </button>
            </div>
            <div id="logs" class="h-64 overflow-y-auto font-mono text-sm bg-gray-900 rounded-lg p-4 space-y-1">
                <div class="text-gray-500">等待日志...</div>
            </div>
        </div>
    </div>
    
    <script>
        let refreshInterval;
        
        async function api(url, options = {}) {
            const response = await fetch(url, {
                ...options,
                headers: {'Content-Type': 'application/json'},
                ...options
            });
            return response.json();
        }
        
        async function loadStatus() {
            const data = await api('/api/status');
            const statusEl = document.getElementById('status-text');
            statusEl.textContent = data.message || data.status;
            statusEl.className = data.running ? 'text-green-400' : 'text-gray-400';
        }
        
        async function loadHome() {
            const data = await api('/api/home');
            if (data.error) {
                console.log('首页数据获取失败:', data.error);
                return;
            }
            
            document.getElementById('agent-name').textContent = data.agent?.name || '-';
            document.getElementById('stories-total').textContent = data.stories_summary?.total || 0;
            document.getElementById('stories-running').textContent = data.stories_summary?.running || 0;
            document.getElementById('stories-attention').textContent = data.stories_summary?.needs_attention || 0;
            
            // 警告
            const alertsEl = document.getElementById('alerts');
            const alertsListEl = document.getElementById('alerts-list');
            if (data.alerts?.length > 0) {
                alertsEl.classList.remove('hidden');
                alertsListEl.innerHTML = data.alerts.map(a => 
                    `<div class="bg-yellow-900/50 border border-yellow-700 rounded-lg p-3">${a.message}</div>`
                ).join('');
            } else {
                alertsEl.classList.add('hidden');
            }
        }
        
        async function loadStories() {
            const data = await api('/api/stories');
            const listEl = document.getElementById('stories-list');
            
            if (data.error || !data.stories) {
                listEl.innerHTML = `<div class="text-gray-500 text-center py-8">${data.error || '暂无故事'}</div>`;
                return;
            }
            
            if (data.stories.length === 0) {
                listEl.innerHTML = `<div class="text-gray-500 text-center py-8">暂无分配的故事</div>`;
                return;
            }
            
            listEl.innerHTML = data.stories.map(s => `
                <div class="bg-gray-700 rounded-lg p-4 flex items-center justify-between">
                    <div>
                        <div class="font-medium">${s.title}</div>
                        <div class="text-sm text-gray-400 mt-1">${s.summary || '暂无摘要'}</div>
                        <div class="text-xs text-gray-500 mt-1">片段数: ${s.segments_count}</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-1 rounded text-xs ${s.auto_continue ? 'bg-green-900 text-green-400' : 'bg-gray-600 text-gray-400'}">
                            ${s.auto_continue ? '自动' : '手动'}
                        </span>
                    </div>
                </div>
            `).join('');
        }
        
        async function loadLogs() {
            const data = await api('/api/logs?limit=30');
            const logsEl = document.getElementById('logs');
            
            if (data.logs?.length > 0) {
                logsEl.innerHTML = data.logs.map(log => 
                    `<div class="text-gray-400">[${log.timestamp}] ${log.message}</div>`
                ).join('');
            } else {
                logsEl.innerHTML = `<div class="text-gray-500">暂无日志</div>`;
            }
        }
        
        async function startAgent() {
            const apiKey = document.getElementById('api-key').value.trim();
            const result = await api('/api/start', {
                method: 'POST',
                body: JSON.stringify({api_key: apiKey})
            });
            
            if (result.error) {
                alert(result.error);
            } else {
                startRefresh();
            }
        }
        
        async function stopAgent() {
            await api('/api/stop', {method: 'POST'});
            stopRefresh();
        }
        
        function startRefresh() {
            loadStatus();
            loadHome();
            loadStories();
            loadLogs();
            
            refreshInterval = setInterval(() => {
                loadStatus();
                loadHome();
            }, 5000);
        }
        
        function stopRefresh() {
            clearInterval(refreshInterval);
            loadStatus();
        }
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            loadStatus();
            loadHome();
            loadStories();
        });
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    """启动 Web 服务器"""
    # 创建模板
    create_templates()
    
    port = 5000
    print("=" * 60)
    print("🚀 InkPath Agent Web UI")
    print("=" * 60)
    print(f"\n📍 访问地址: http://localhost:{port}")
    print(f"   或: http://127.0.0.1:{port}")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()

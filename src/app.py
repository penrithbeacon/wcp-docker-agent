"""
wcp-docker-agent — Authenticated Docker proxy for NAS deployment
Exposes local Docker socket over HTTP, protected by a Bearer token.
Port: 3745
"""

import os
import secrets
from functools import wraps
from flask import Flask, jsonify, request, Response
import docker

app = Flask(__name__)

# ── Token bootstrap ───────────────────────────────────────────────────────────

TOKEN_FILE = '/app/data/token.txt'

def _load_token():
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    token = secrets.token_urlsafe(32)
    open(TOKEN_FILE, 'w').write(token)
    print(f'\n[wcp-docker-agent] *** Bearer token (save this): {token} ***\n', flush=True)
    return token

TOKEN = _load_token()

# ── Auth ──────────────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not (auth.startswith('Bearer ') and auth[7:] == TOKEN):
            return Response('Unauthorized', status=401,
                            headers={'WWW-Authenticate': 'Bearer realm="wcp-docker-agent"'})
        return f(*args, **kwargs)
    return decorated

# ── Docker client ─────────────────────────────────────────────────────────────

def get_client():
    return docker.DockerClient(base_url='unix:///var/run/docker.sock')

def human_size(n):
    if not n:
        return '—'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'

# ── CORS ──────────────────────────────────────────────────────────────────────

@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

@app.route('/<path:p>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def cors_preflight(p=''):
    return Response('', status=204)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route('/health')
@app.route('/widget/health')
def health():
    return jsonify({'status': 'ok', 'name': 'wcp-docker-agent',
                    'container': os.environ.get('CONTAINER_NAME', 'unknown')})

@app.route('/containers')
@require_auth
def list_containers():
    try:
        client = get_client()
        raw = client.containers.list(all=True)
        containers = []
        for c in raw:
            ports = []
            for k, v in (c.ports or {}).items():
                if v:
                    for p in v:
                        ports.append(f"{p['HostPort']}→{k.split('/')[0]}")
            containers.append({
                'id':     c.short_id,
                'name':   c.name,
                'image':  c.image.tags[0] if c.image.tags else c.image.short_id,
                'state':  c.status,
                'status': c.status,
                'ports':  ', '.join(ports),
            })
        return jsonify({'success': True, 'data': {'containers': containers}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/images')
@require_auth
def list_images():
    try:
        client = get_client()
        raw = client.images.list()
        images = []
        for img in raw:
            tags = img.tags or ['<none>:<none>']
            repo, _, tag = tags[0].partition(':')
            images.append({
                'repo':    repo or '<none>',
                'tag':     tag  or '<none>',
                'id':      img.short_id.replace('sha256:', '')[:12],
                'size':    human_size(img.attrs.get('Size', 0)),
                'created': img.attrs.get('Created', ''),
            })
        images.sort(key=lambda x: x['created'], reverse=True)
        return jsonify({'success': True, 'data': {'images': images}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/containers/<cid>/<action>', methods=['POST'])
@require_auth
def container_action(cid, action):
    if action not in ('start', 'stop', 'restart'):
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    try:
        client = get_client()
        c = client.containers.get(cid)
        getattr(c, action)()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3745, debug=False)

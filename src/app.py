"""
WCP Widget: Docker Agent
Widget Context Protocol 2.1.0 compliant
Authenticated Docker proxy for NAS deployment.
Exposes local Docker socket over HTTP, protected by a Bearer token.
Port: 3745  |  Specification: https://widgetcontextprotocol.com
"""

import json
import os
import secrets
from functools import wraps
from flask import Flask, jsonify, request, Response, render_template
import docker

app = Flask(__name__)

PUBLISHED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'published', 'index.html')

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

# ── WCP Request Header Helpers ───────────────────────────────────────────────

def get_instance_id():
    iid = request.headers.get('Wcp-Instance-Id', '').strip()
    return iid or (request.args.get('wcpInstanceId', '') or '').strip()

def get_orchestration_id():
    oid = request.headers.get('Wcp-Orchestration-Id', '').strip()
    return oid or (request.args.get('wcpOrchestrationId', '') or '').strip()

def get_application_id():
    aid = request.headers.get('Wcp-Application-Id', '').strip()
    return aid or (request.args.get('wcpApplicationId', '') or '').strip()

# ── WCP Manifest ─────────────────────────────────────────────────────────────

WCP_MANIFEST = {
    'wcp':     '2.1.0',
    'uuid':    'f4a7b2c1-8d3e-4f5a-9b6c-1e2d3f4a5b6c',
    'name':    'Docker Agent',
    'version': '1.2.0',
    'description': (
        'Authenticated Docker proxy for NAS deployment. '
        'Exposes local Docker socket over HTTP, protected by a Bearer token.'
    ),
    'icon':    '/widget/icon.svg',
    'health':  '/widget/health',
    'container': {
        'image':            'docker.io/penrithbeacon/wcp-docker-agent',
        'source':           {'type': 'registry'},
        'tag':              '1.2.0-wcp2.1.0',
        'port':             3745,
        'defaultLifecycle': 'always',
    },
    'components': [
        {
            'id': 'docker-agent-index', 'uuid': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            'name': 'Docker Agent', 'role': 'widget',
            'path': '/widget/index', 'icon': '/widget/icon.svg',
            'renderMode': 'iframe', 'defaultSize': {'w': 6, 'h': 6},
        },
    ],
    'pages': [],
    'actions': [],
}

WIDGET_JSONLD = json.dumps({
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    'name': WCP_MANIFEST['name'],
    'softwareVersion': WCP_MANIFEST['version'],
    'description': WCP_MANIFEST['description'],
    'identifier': WCP_MANIFEST['uuid'],
    'applicationCategory': 'WCP Widget',
    'operatingSystem': 'Web',
    'isBasedOn': {
        '@type': 'WebSite',
        'name': 'Widget Context Protocol',
        'url': 'https://widgetcontextprotocol.com',
    },
    'additionalProperty': [
        {'@type': 'PropertyValue', 'name': 'wcpVersion',      'value': WCP_MANIFEST['wcp']},
        {'@type': 'PropertyValue', 'name': 'containerImage',  'value': WCP_MANIFEST['container']['image']},
        {'@type': 'PropertyValue', 'name': 'containerTag',    'value': WCP_MANIFEST['container']['tag']},
        {'@type': 'PropertyValue', 'name': 'containerPort',   'value': str(WCP_MANIFEST['container']['port'])},
    ],
}, indent=2)

# ── CORS ──────────────────────────────────────────────────────────────────────

@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = (
        'Content-Type, Authorization, Wcp-Instance-Id, Wcp-Dashboard-Id, Wcp-Version, '
        'Wcp-Widget-Id, Wcp-Orchestration-Id, Wcp-Application-Id'
    )
    return resp

@app.route('/<path:p>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def cors_preflight(p=''):
    return Response('', status=204)

# ── WCP Discovery Endpoints ─────────────────────────────────────────────────

@app.route('/wcp')
def container_directory():
    return jsonify({
        'type':    'directory',
        'wcp':     '2.1.0',
        'widgets': [{
            'id':          'docker-agent',
            'uuid':        WCP_MANIFEST['uuid'],
            'name':        WCP_MANIFEST['name'],
            'description': WCP_MANIFEST['description'],
            'icon':        WCP_MANIFEST['icon'],
            'manifest':    '/widget/wcp',
        }]
    })

@app.route('/widget/wcp')
def widget_wcp():
    manifest = dict(WCP_MANIFEST)
    manifest['web'] = {'published': os.path.exists(PUBLISHED_PATH)}
    return jsonify(manifest)

@app.route('/widget/index')
def widget_index():
    return render_template('index-page.html', manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill="#f0883e" d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z"/>
</svg>"""

@app.route('/widget/icon.svg')
def widget_icon():
    return Response(ICON_SVG, mimetype='image/svg+xml')

@app.route('/widget/api/guids')
def api_guids():
    return jsonify({
        'uuid': WCP_MANIFEST['uuid'],
        'components': [
            {'id': c['id'], 'uuid': c['uuid'], 'name': c['name']}
            for c in WCP_MANIFEST.get('components', [])
        ]
    })

# ── Standard Endpoints ───────────────────────────────────────────────────────

@app.route('/health')
@app.route('/widget/health')
def health():
    return jsonify({'status': 'ok', 'name': WCP_MANIFEST['name'],
                    'container': os.environ.get('CONTAINER_NAME', 'unknown')})

# ── Authenticated API Endpoints ──────────────────────────────────────────────

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

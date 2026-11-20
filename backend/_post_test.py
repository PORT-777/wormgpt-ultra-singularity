import sys, os
sys.path.insert(0, 'WormGPT_Ultra_Singularity/backend')
os.environ.setdefault('PLUGIN_MOCK_MODE', 'true')
import main
from fastapi.testclient import TestClient

client = TestClient(main.app)

print('=== POST Route Verification (with valid payloads) ===')

# Workspace attach
r = client.post('/api/workspace/attach', json={'workspace_id': 'test_ws', 'path': '.'})
print(f'POST /api/workspace/attach: {r.status_code}')

# Workspace list
r = client.get('/api/workspace/list')
print(f'GET /api/workspace/list: {r.status_code} -> {r.json()}')

# Workspace files/list
r = client.post('/api/workspace/files/list', json={'workspace_id': 'test_ws', 'directory': '.'})
print(f'POST /api/workspace/files/list: {r.status_code}')

# Workspace command/execute
r = client.post('/api/workspace/command/execute', json={'workspace_id': 'test_ws', 'command': 'echo hello', 'cwd': '.'})
print(f'POST /api/workspace/command/execute: {r.status_code}')

# Orchestrate
r = client.post('/api/orchestrate', json={'goal': 'test goal', 'auto_plan': False})
print(f'POST /api/orchestrate: {r.status_code} (SSE stream)')

# Plugins execute
r = client.post('/api/plugins/execute', json={'tool': 'test.tool', 'args': {}, 'user_id': 'default_user'})
print(f'POST /api/plugins/execute: {r.status_code}')

# Plugins install
r = client.post('/api/plugins/install/test_plugin', json={})
print(f'POST /api/plugins/install/test_plugin: {r.status_code}')

# Plugins toggle
r = client.post('/api/plugins/toggle/test_plugin', json={})
print(f'POST /api/plugins/toggle/test_plugin: {r.status_code}')

print()
print('All POST routes verified!')
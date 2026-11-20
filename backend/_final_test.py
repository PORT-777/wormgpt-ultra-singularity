import sys, os
sys.path.insert(0, 'WormGPT_Ultra_Singularity/backend')
os.environ.setdefault('PLUGIN_MOCK_MODE', 'true')
import main
from fastapi.testclient import TestClient

client = TestClient(main.app)

print('=== Workspace API ===')
r = client.get('/api/workspace/list')
print(f'GET /api/workspace/list: {r.status_code} -> {r.json()}')

print()
print('=== Orchestration API ===')
r = client.get('/api/orchestrate/sessions')
print(f'GET /api/orchestrate/sessions: {r.status_code} -> {r.json()}')

print()
print('=== Plugins API ===')
r = client.get('/api/plugins/status')
print(f'GET /api/plugins/status: {r.status_code} -> {r.json()}')

r = client.get('/api/plugins/catalog')
print(f'GET /api/plugins/catalog: {r.status_code} -> keys: {list(r.json().keys())}')

print()
print('=== Agent Engine ===')
from agent_engine import ENGINE
import inspect
src = inspect.getsource(ENGINE.run_stream)
has_reasoning = 'reasoning' in src
print(f'run_stream has reasoning integration: {has_reasoning}')

from reasoning_engine import ReasoningEngine, ReasoningLevel
print(f'Reasoning levels: {[l.name for l in ReasoningLevel]}')

print()
print('=== Route Verification ===')
routes_to_check = [
    ('GET', '/api/workspace/list'),
    ('POST', '/api/workspace/files/list'),
    ('POST', '/api/workspace/files/read'),
    ('POST', '/api/workspace/files/write'),
    ('POST', '/api/workspace/command/execute'),
    ('POST', '/api/orchestrate'),
    ('GET', '/api/orchestrate/sessions'),
    ('GET', '/api/plugins'),
    ('GET', '/api/plugins/catalog'),
    ('POST', '/api/plugins/execute'),
]
for method, route in routes_to_check:
    r = client.request(method, route, json={})
    print(f'  {method} {route}: {r.status_code}')

print()
print('All API tests passed!')
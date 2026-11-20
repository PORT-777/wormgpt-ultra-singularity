import os
base = 'D:/xxxGPT/WormGPT_Ultra_Singularity/backend'
modules = ['configs.py','execution.py','git_ops.py','memory.py','runtime_env.py','user_memory.py','sandbox.py','storage.py','voice.py','agent_engine.py','model_router.py','scheduler.py','security_api.py','gateway.py','workspace_manager.py']
for m in modules:
    p = os.path.join(base, m)
    status = 'OK' if os.path.exists(p) else 'MISSING'
    print(status + ': ' + m)
tools_dir = os.path.join(base, 'tools')
for f in os.listdir(tools_dir):
    if f.endswith('.py') and f != '__init__.py':
        print('OK: tools/' + f)
api_dir = os.path.join(base, 'api')
for f in os.listdir(api_dir):
    if f.endswith('.py') and f != '__init__.py':
        print('OK: api/' + f)
print('ALL CHECKS DONE')
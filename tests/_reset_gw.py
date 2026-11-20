import json
from pathlib import Path
p=Path(r"D:\xxxGPT\WormGPT_Ultra_Singularity\backend\gateway_data.json")
if p.exists():
    d=json.loads(p.read_text(encoding='utf-8'))
    d.setdefault('settings',{})['activation']=True
    d['settings']['protection']=True
    d['settings']['freeOnly']=True
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    print('reset',d['settings'])
else:
    print('no file')

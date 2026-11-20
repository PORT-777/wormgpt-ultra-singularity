import httpx,json,time,asyncio
BASE='http://127.0.0.1:7777'
def P(*a): print(' | '.join(a),flush=True)
async def main():
    async with httpx.AsyncClient(base_url=BASE,timeout=30) as c:
        await c.post('/api/gateway/settings',json={'activation':True,'protection':True,'freeOnly':True})
        rp=await c.post('/api/gateway/providers',json={'name':'smoke-fake','baseUrl':'http://127.0.0.1:9/v1','key':'gsk_test_1234567890abcdef','tier':'free','enabled':True},timeout=30)
        pj=rp.json(); dumped=json.dumps(pj,ensure_ascii=False)
        leaked=('gsk_test_1234567890abcdef' in dumped); masked=('keyMasked' in dumped or '••' in dumped)
        prov=((pj.get('provider') or pj) if isinstance(pj,dict) else {}); pid=prov.get('id')
        P('4','POST /api/gateway/providers fake key masked','n/a','_provider_public keyMasked','PASS' if (rp.status_code<500 and not leaked and masked) else 'FAIL',f'status={rp.status_code} raw_leaked={leaked} masked={masked}')
        if pid:
            t0=time.time(); rt=await c.post(f'/api/gateway/providers/{pid}/test',timeout=15); dt=time.time()-t0
            tj=rt.json() if 'application/json' in rt.headers.get('content-type','') else {}
            P('4','POST /api/gateway/providers/{id}/test bad base_url -> ok:false <=10s','FAIL risk','gateway.py test_provider 10s+ok:false','PASS' if (dt<=10 and isinstance(tj,dict) and tj.get('ok') is False) else 'FAIL',f'dt={dt:.2f}s body={json.dumps(tj,ensure_ascii=False)[:150]}')
            await c.request('DELETE',f'/api/gateway/providers/{pid}')
        rp=await c.post('/api/gateway/providers',json={'name':'squad-fake','baseUrl':'http://127.0.0.1:9/v1','key':'gsk_test_squad1234567890ab','tier':'free','enabled':True},timeout=30)
        pid=((rp.json() or {}).get('provider') or {}).get('id')
        async with c.stream('POST','/api/gateway/squad/run',json={'task':'Build a tiny TODO app plan','template':'auto'},timeout=180) as r:
            evs=[]; buf=''; code=r.status_code
            async for chunk in r.aiter_text():
                buf+=chunk
                while '\n\n' in buf:
                    part,buf=buf.split('\n\n',1)
                    for line in part.splitlines():
                        if line.startswith('data:'):
                            v=line[5:].strip()
                            if v=='[DONE]': evs.append({'type':'[DONE]'}); break
                            try: evs.append(json.loads(v))
                            except: pass
                    if any(e.get('type')=='[DONE]' for e in evs): break
                if any(e.get('type')=='[DONE]' for e in evs): break
        types=[e.get('type') for e in evs]
        has=('[DONE]' in types and ('planner_start' in types or 'planner_done' in types or 'error' in types))
        P('5','POST /api/gateway/squad/run SSE planner/fallback-or-error/[DONE] no hang','n/a','','PASS' if has else 'FAIL',f'status={code} types={types[:14]}')
        if pid: await c.request('DELETE',f'/api/gateway/providers/{pid}')
asyncio.run(main())

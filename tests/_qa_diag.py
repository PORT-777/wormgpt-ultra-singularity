import httpx, json, asyncio
BASE='http://127.0.0.1:7777'
async def main():
    async with httpx.AsyncClient(base_url=BASE,timeout=30) as c:
        await c.post('/api/gateway/settings',json={'activation':True,'protection':True,'freeOnly':True})
        rp=await c.post('/api/gateway/providers',json={'name':'smoke-fake','baseUrl':'http://127.0.0.1:9/v1','key':'gsk_test_1234567890abcdef','tier':'free','enabled':True},timeout=30)
        print(rp.status_code, rp.text[:300])
        pj=rp.json() if 'json' in rp.headers.get('content-type','') else {}
        prov=((pj.get('provider') or pj) if isinstance(pj,dict) else {}); pid=prov.get('id')
        if pid:
            rt=await c.post(f'/api/gateway/providers/{pid}/test',timeout=15); print('test',rt.status_code,rt.text[:220])
            await c.request('DELETE',f'/api/gateway/providers/{pid}')
        # squad
        rp=await c.post('/api/gateway/providers',json={'name':'squad-fake','baseUrl':'http://127.0.0.1:9/v1','key':'gsk_test_squad1234567890ab','tier':'free','enabled':True},timeout=30)
        print('squad add',rp.status_code)
        pid=((rp.json() or {}).get('provider') or {}).get('id')
        async with c.stream('POST','/api/gateway/squad/run',json={'task':'Build a tiny TODO app plan','template':'auto'},timeout=60) as r:
            print('squad run status',r.status_code,r.headers.get('content-type'))
            body=b''
            async for ch in r.aiter_bytes():
                body+=ch
                if b'[DONE]' in body or len(body)>2000: break
            print(body[:300])
        if pid: await c.request('DELETE',f'/api/gateway/providers/{pid}')
asyncio.run(main())

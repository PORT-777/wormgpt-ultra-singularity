src=open('real_providers.py',encoding='utf-8').read()
old = '            self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))'
new = '            self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")'
assert old in src, 'not found'
src=src.replace(old,new,1)
open('real_providers.py','w',encoding='utf-8').write(src)
print('done')
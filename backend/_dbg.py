src=open('main.py',encoding='utf-8').read()
needle = 'return {"providers": list_providers()}'
i=src.find(needle)
print(repr(src[max(0,i-250):i+60]))
"
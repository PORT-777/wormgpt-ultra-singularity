src=open('real_providers.py').read()
print('base_url param present:', 'base_url="https://api.groq.com/openai/v1"' in src)
print('old line present:', 'AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))' in src)
"
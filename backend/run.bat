@echo off
cd /d "D:\xxxGPT\WormGPT_Ultra_Singularity\backend"
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 7777 > uvicorn_run.log 2>&1

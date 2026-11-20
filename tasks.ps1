# tasks.ps1 — WormGPT Ultra: تشغيل المراحل الأساسية بأمر واحد
# أوامر: test | providers | api | ui | demo | shell
param([string]$cmd = "test", [string]$extra = "")

$venvPy    = "backend\.venv\Scripts\python.exe"
$wd        = Split-Path -Parent $MyInvocation.MyCommand.Path
$py        = Join-Path $wd $venvPy

switch ($cmd.ToLower()) {
    "test"       { & cmd /c "`"$py`" -m pytest backend/tests -q" }
    "providers"  { & cmd /c "set PYTHONIOENCODING=utf-8&& `"$py`" backend\workspace\check_providers.py" }
    "api"        {
        Write-Host ">> uvicorn على http://127.0.0.1:8000"
        & cmd /c "`"$py`" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload"
    }
    "demo"       { & cmd /c "set PYTHONIOENCODING=utf-8&& `"$py`" main.py" }
    "shell"      { & cmd /c "set PYTHONIOENCODING=utf-8&& `"$py`" main.py shell" }
    "agent"      {
        & cmd /c "set PYTHONIOENCODING=utf-8&& `"$py`" main.py agent $extra"
    }
    "chromadb"   { & cmd /c "uv pip install --python `"$py`" chromadb" }
    Default      { Write-Host "Available: test | providers | api | ui | demo | shell | agent | chromadb" }
}

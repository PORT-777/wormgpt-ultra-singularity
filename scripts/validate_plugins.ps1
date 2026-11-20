# Pre-submit validation for Claude-compatible plugin bundles.
# Run from the repository root: powershell -File scripts/validate_plugins.ps1
$root = Split-Path -Parent $PSScriptRoot
$pluginsDir = Join-Path $root "plugins"
$fail = 0

foreach ($dir in (Get-ChildItem $pluginsDir -Directory)) {
  $name = $dir.Name
  $manifest = Join-Path $dir.FullName ".claude-plugin\plugin.json"
  $readme = Join-Path $dir.FullName "README.md"
  $license = Join-Path $dir.FullName "LICENSE"
  $mcp = Join-Path $dir.FullName ".mcp.json"

  foreach ($required in @($manifest, $readme, $license, $mcp)) {
    if (-not (Test-Path $required)) { Write-Output "FAIL $name missing $required"; $fail++ }
  }
  if (Test-Path $manifest) {
    $m = Get-Content $manifest -Raw | ConvertFrom-Json
    if ($m.name -notmatch '^[a-z0-9-]+$') { Write-Output "FAIL $name invalid plugin name"; $fail++ }
    if (-not $m.license -and -not (Test-Path $license)) { Write-Output "FAIL $name license missing"; $fail++ }
  }
  if (Test-Path $readme) {
    $words = ((Get-Content $readme -Raw) -split '\s+' | Where-Object { $_ -match '\w' } | Measure-Object).Count
    if ($words -lt 40) { Write-Output "FAIL $name README has $words words (need 40+)"; $fail++ }
  }
  if (Test-Path $mcp) {
    $raw = Get-Content $mcp -Raw
    if ($raw -match '(?i)(api[_-]?key|token|password|secret|authorization)') {
      Write-Output "FAIL $name .mcp.json contains a secret"; $fail++
    }
  }
  $skills = Get-ChildItem (Join-Path $dir.FullName "skills") -Recurse -Filter SKILL.md -ErrorAction SilentlyContinue
  if (-not $skills -or $skills.Count -eq 0) { Write-Output "FAIL $name no SKILL.md"; $fail++ }
  foreach ($skill in $skills) {
    $head = (Get-Content $skill.FullName -TotalCount 8) -join "`n"
    if ($head -notmatch '(?m)^name:\s*\S') { Write-Output "FAIL $($skill.FullName) missing name"; $fail++ }
    if ($head -notmatch '(?m)^description:\s*\S') { Write-Output "FAIL $($skill.FullName) missing description"; $fail++ }
  }
  $junk = Get-ChildItem $dir.FullName -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @('.DS_Store','Thumbs.db') -or $_.FullName -match '__MACOSX' }
  if ($junk) { Write-Output "FAIL $name contains publish-blocking files"; $fail++ }
  Write-Output ("OK   {0} ({1} skills)" -f $name, @($skills).Count)
}

$market = Join-Path $root "plugin-directory\marketplace.json"
if (Test-Path $market) {
  $j = Get-Content $market -Raw | ConvertFrom-Json
  foreach ($p in $j.plugins) {
    if (-not (Test-Path (Join-Path $root $p.path))) { Write-Output "FAIL marketplace path missing: $($p.path)"; $fail++ }
  }
}

if ($fail -gt 0) { Write-Output "$fail validation failure(s)"; exit 1 }
Write-Output "All plugins valid"
exit 0

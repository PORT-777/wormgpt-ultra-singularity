# Pre-push secret scan. Run from the repository root.
$pattern = '(SUPABASE_SECRET_KEY|PAYMOB_API_KEY|PAYMOB_HMAC_SECRET|GROQ_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY|DATABASE_URL)\s*=\s*[^#\s]{20,}'
$excluded = '^(tests/|backend/tests/|backend/skills_packs/|vendor/|docs/)'
$results = git grep -n -I -E $pattern -- . ':!backend/.env.example' 2>$null |
  Where-Object { $_ -notmatch $excluded }
if ($results) {
  Write-Output "REVIEW THESE LINES (may be placeholders):"
  $results | ForEach-Object { Write-Output $_ }
  exit 1
}
Write-Output "No credential-looking assignments found in tracked deployment files."
exit 0

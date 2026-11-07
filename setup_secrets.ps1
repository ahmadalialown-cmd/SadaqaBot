# Runs bot/secrets_setup.py with the GitHub CLI login passed in GH_TOKEN.
# (Microsoft Store Python can't read gh's keyring login from inside the script.)
# Nothing is printed or saved here; the variable is removed at the end.
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = 'C:\Program Files\GitHub CLI\gh.exe' }
$env:GH_TOKEN = & $gh auth token
if (-not $env:GH_TOKEN) { Write-Host 'GitHub not logged in: run  gh auth login --web  then try again.'; exit 1 }
try {
    & "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\bot\secrets_setup.py"
} finally {
    Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
}

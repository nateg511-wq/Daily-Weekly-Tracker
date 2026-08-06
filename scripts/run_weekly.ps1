$ErrorActionPreference = "Stop"
$root = "C:\Users\nateg\CoinPicks Market Direction Bot"
Set-Location $root

$logDir = Join-Path $root "scripts\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logFile = Join-Path $logDir "weekly_$stamp.log"

$prompt = Get-Content -Raw (Join-Path $root "scripts\weekly_prompt.txt")

& claude -p $prompt --dangerously-skip-permissions --output-format text *>&1 | Tee-Object -FilePath $logFile

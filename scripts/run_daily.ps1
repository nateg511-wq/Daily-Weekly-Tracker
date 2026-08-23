$ErrorActionPreference = "Stop"
$root = "C:\Users\nateg\CoinPicks Market Direction Bot"
Set-Location $root

# Prevent Modern Standby from suspending the system mid-run. WakeToRun only
# guarantees the wake AT the trigger time; on Modern Standby (S0ix) laptops
# an idle timeout can still put the machine back to sleep minutes later,
# killing this process before it finishes (observed 2026-08-08). Holding
# ES_SYSTEM_REQUIRED for the life of this process prevents that.
Add-Type -Name Power -Namespace Win32 -MemberDefinition @'
[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
$ES_CONTINUOUS = [uint32]"0x80000000"
$ES_SYSTEM_REQUIRED = [uint32]"0x00000001"
$ES_AWAYMODE_REQUIRED = [uint32]"0x00000040"
[Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_AWAYMODE_REQUIRED) | Out-Null

$logDir = Join-Path $root "scripts\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logFile = Join-Path $logDir "daily_$stamp.log"

$promptPath = Join-Path $root "scripts\daily_prompt.txt"

# Pipe the prompt via stdin instead of passing it as a `-p <string>` CLI
# argument. Passing a multi-KB string containing literal double-quotes as a
# process argument goes through PowerShell's argument encoding, then the
# claude.cmd shim's own cmd.exe re-quoting -- and an embedded `"` in that
# chain can silently truncate the argument (observed 2026-08-19: the prompt
# was cut off mid-sentence exactly at an embedded quote, and the run
# correctly aborted rather than act on a garbled instruction). Stdin has no
# such re-quoting step.
try {
    Get-Content -Raw $promptPath | & claude -p --dangerously-skip-permissions --output-format text *>&1 | Tee-Object -FilePath $logFile
} finally {
    [Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
}

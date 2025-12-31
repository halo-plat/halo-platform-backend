param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000,
  [string]$MaxTenants = "1"
)

$ErrorActionPreference = "Stop"

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendPy   = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $BackendPy)) {
  throw "Backend venv python not found: $BackendPy"
}

# Port guardrail (fail-fast: no flaky tests)
$c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($c) {
  throw "Port $Port is already in use (PID=$($c.OwningProcess)). Stop the process or change -Port."
}

# Optional QA repo (sibling)
$QaRoot = (Resolve-Path (Join-Path $BackendRoot "..\halo-platform-qa") -ErrorAction SilentlyContinue)
$QaPy = $null
if ($QaRoot) {
  $QaPy = Join-Path $QaRoot.Path ".venv\Scripts\python.exe"
  if (-not (Test-Path $QaPy)) { $QaPy = $null }
}

$baseUrl = "http://$BindHost`:$Port"
$logFile = Join-Path $BackendRoot ("tools\uvicorn.$Port.log")

# Env for the server under test
$env:HALO_MAX_TENANTS = $MaxTenants
$script:ORIG_HALO_AI_DEFAULT_PROVIDER = $env:HALO_AI_DEFAULT_PROVIDER
$script:ORIG_HALO_AI_AUTO_ROUTING = $env:HALO_AI_AUTO_ROUTING
if (-not $env:HALO_AI_DEFAULT_PROVIDER) { $env:HALO_AI_DEFAULT_PROVIDER = "perplexity" }
if (-not $env:HALO_AI_AUTO_ROUTING) { $env:HALO_AI_AUTO_ROUTING = "1" }
$env:PYTHONFAULTHANDLER = "1"

$proc = $null
try {
  Write-Host "START server: $baseUrl (HALO_MAX_TENANTS=$MaxTenants)"
  $ErrLog = $logFile + ".err"
  $proc = Start-Process `
    -FilePath $BackendPy `
    -WorkingDirectory $BackendRoot `
    -ArgumentList "-m uvicorn app.main:app --host $BindHost --port $Port --log-level warning" `
    -NoNewWindow `
    -PassThru `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError  $ErrLog

  # Wait for health
  $ok = $false
  for ($i=1; $i -le 30; $i++) {
    try {
      $h = Invoke-RestMethod "$baseUrl/health" -TimeoutSec 2
      if ($h.status -eq "ok") { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }
  if (-not $ok) {
    throw "Server did not become healthy within 30s. Check log: $logFile"
  }
  Write-Host "HEALTH OK"

  # Backend unit tests
  Write-Host "RUN backend tests"
  & $BackendPy -m pytest -q

  # QA integration tests (optional but recommended)
  if ($QaPy) {
    Write-Host "RUN QA tests (integration) from: $($QaRoot.Path)"
    Push-Location $QaRoot.Path
    try {
      # Restore env so QA tests can control provider selection independently
      if ($null -eq $script:ORIG_HALO_AI_DEFAULT_PROVIDER) { Remove-Item Env:\HALO_AI_DEFAULT_PROVIDER -ErrorAction SilentlyContinue } else { $env:HALO_AI_DEFAULT_PROVIDER = $script:ORIG_HALO_AI_DEFAULT_PROVIDER }
      if ($null -eq $script:ORIG_HALO_AI_AUTO_ROUTING) { Remove-Item Env:\HALO_AI_AUTO_ROUTING -ErrorAction SilentlyContinue } else { $env:HALO_AI_AUTO_ROUTING = $script:ORIG_HALO_AI_AUTO_ROUTING }
      $env:HALO_BASE_URL = $baseUrl
      & $QaPy -m pytest -q
    } finally {
      Pop-Location
    }
  } else {
    Write-Host "SKIP QA tests: QA venv not found at ..\halo-platform-qa\.venv"
  }

  Write-Host "OK: local CI harness completed"
}
finally {
  if ($proc -and -not $proc.HasExited) {
    Write-Host "STOP server PID=$($proc.Id)"
    Stop-Process -Id $proc.Id -Force
  }
}

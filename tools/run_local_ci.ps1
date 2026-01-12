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
  Push-Location $BackendRoot
  try {
    & $BackendPy -m pytest -q
  } finally {
    Pop-Location
  }

  # QA integration tests (optional but recommended)
  if ($QaPy) {
    Write-Host "RUN QA tests (integration) from: $($QaRoot.Path)"

    # Start gateway stub for pairing tests (localhost:8080)
    $GatewayHost = "127.0.0.1"
    $GatewayPort = 8080
    $env:HALO_GATEWAY_BASE_URL = "http://${GatewayHost}:$GatewayPort"

    # Port guardrail for gateway stub (fail-fast: no flaky tests)
    $c2 = Get-NetTCPConnection -LocalPort $GatewayPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c2) {
      throw "Port $GatewayPort is already in use (PID=$($c2.OwningProcess)). Stop the process or change the gateway port."
    }

    $IntegrationRoot = (Resolve-Path (Join-Path $BackendRoot "..\halo-platform-integration") -ErrorAction SilentlyContinue)
    if (-not $IntegrationRoot) {
      throw "Integration repo not found at: $(Join-Path $BackendRoot '..\halo-platform-integration') (required for gateway stub)."
    }

    $GatewayScript = Join-Path $QaRoot.Path "scripts\sim_gateway_stub.ps1"
    if (-not (Test-Path $GatewayScript)) {
      throw "Gateway stub script not found: $GatewayScript"
    }
    New-Item -ItemType Directory -Force (Join-Path $QaRoot.Path "artifacts") | Out-Null

    $gatewayStarted = $false
    try {
      & $GatewayScript -Action start -IntegrationRepo $IntegrationRoot.Path -Host $GatewayHost -Port $GatewayPort -PythonExe $QaPy | Out-Host
      $gatewayStarted = $true

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
    } finally {
      if ($gatewayStarted) {
        try { & $GatewayScript -Action stop -IntegrationRepo $IntegrationRoot.Path -Host $GatewayHost -Port $GatewayPort -PythonExe $QaPy | Out-Host } catch { Write-Host "WARN: failed to stop gateway stub: $($_.Exception.Message)" }
      }
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


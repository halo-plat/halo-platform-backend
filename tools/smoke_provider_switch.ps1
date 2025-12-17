$ErrorActionPreference="Stop"
$session = "s-switch-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$uri = "http://127.0.0.1:8000/api/v1/conversation/message"

function Send-Halo([string]$utt) {
  $body  = @{ session_id=$session; user_utterance=$utt } | ConvertTo-Json -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
  $r = Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json; charset=utf-8" -Body $bytes

  [pscustomobject]@{
    utterance = $utt
    requested = $r.ai_provider_requested
    applied   = $r.ai_provider_applied
    reason    = $r.ai_routing_reason
    cues      = ($r.audio_cues -join ",")
  }
}

$results = @()
$results += Send-Halo "ciao"
$results += Send-Halo "usa eco"
$results += Send-Halo "ciao"
$results += Send-Halo "use perplexity"
$results += Send-Halo "ciao"
$results += Send-Halo "news eco"

"SESSION_ID=$session"
$results | Format-Table -Auto

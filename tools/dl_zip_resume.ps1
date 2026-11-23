param([string]$Url,[string]$Out,[string]$Proxy)
$ErrorActionPreference='Continue'
$log = $Out + '.log'
Add-Content $log "=== resume download start $(Get-Date -Format 'HH:mm:ss') ==="
for($i=1; $i -le 2000; $i++){
  $have = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $have=$fs.Length; $fs.Close() }
  # 用代理 + 续传，每次最多 5 分钟
  $r = & curl.exe -sL -x $Proxy --retry 3 --retry-delay 2 --retry-all-errors -C - --max-time 300 -o $Out -w "%{http_code}:%{size_download}" $Url 2>&1
  $now = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $now=$fs.Length; $fs.Close() }
  Add-Content $log ("try=$i have=$have now=$now delta=" + ($now-$have) + " status=" + ($r -join ''))
  # 达到 675MB 左右就停
  if($now -gt 700000000){ Add-Content $log "DONE size=$now"; break }
  if($now -le $have){ Start-Sleep -Seconds 5 }
}
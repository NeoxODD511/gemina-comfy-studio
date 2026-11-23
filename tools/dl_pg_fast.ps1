param([string]$Url,[string]$Out,[string]$Proxy)
$ErrorActionPreference='Continue'
$log = $Out + '.log2'
Add-Content $log "=== start $(Get-Date -Format 'HH:mm:ss') ==="
for($i=1; $i -le 200; $i++){
  $have = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $have=$fs.Length; $fs.Close() }
  if($have -gt 700000000){ Add-Content $log "DONE size=$have"; break }
  # 10 分钟长连接 + 续传
  & curl.exe -sL -x $Proxy --retry 5 --retry-delay 2 --retry-all-errors -C - --max-time 600 -o $Out -w "HTTP:%{http_code} SIZE:%{size_download} SPEED:%{speed_download}`n" $Url 2>&1 | Out-File $log -Append -Encoding utf8
  $now = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $now=$fs.Length; $fs.Close() }
  Add-Content $log ("round=$i have=$have now=$now delta=" + ($now-$have))
  if($now -le $have){ Start-Sleep -Seconds 3 }
}
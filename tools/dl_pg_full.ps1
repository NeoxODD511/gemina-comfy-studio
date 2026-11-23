param([string]$Url,[string]$Out,[string]$Proxy)
$ErrorActionPreference='Continue'
$log = $Out + '.progress'
Add-Content $log "=== start $(Get-Date -Format 'HH:mm:ss') expect=708341871 ==="
for($i=1; $i -le 30; $i++){
  # 单次长连接，不带 -C（codeload 不支持 Range）
  & curl.exe -L -x $Proxy --retry 2 --retry-delay 2 --max-time 3600 --connect-timeout 30 -o $Out -w "HTTP:%{http_code} SIZE:%{size_download} SPEED:%{speed_download}`n" $Url 2>&1 | Out-File $log -Append -Encoding utf8
  $now = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $now=$fs.Length; $fs.Close() }
  Add-Content $log ("round=$i size=$now")
  if($now -ge 708300000){ Add-Content $log "COMPLETE size=$now"; break }
  Start-Sleep -Seconds 3
}
param([string]$Url,[string]$Out)
$ErrorActionPreference='Continue'
$log = $Out + '.log'
for($i=1; $i -le 200; $i++){
  $have = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $have=$fs.Length; $fs.Close() }
  Add-Content $log ("try=$i have=$have")
  # -C - 断点续传；--retry 处理瞬时断连
  & curl.exe -L --retry 5 --retry-delay 3 --retry-all-errors -C - --max-time 1800 -o $Out -w "HTTP:%{http_code} SIZE:%{size_download} SPEED:%{speed_download}`n" $Url 2>&1 | Out-File $log -Append -Encoding utf8
  $now = 0
  if(Test-Path $Out){ $fs=[IO.File]::Open($Out,'Open','Read','ReadWrite'); $now=$fs.Length; $fs.Close() }
  Add-Content $log ("  after=$now")
  # 如果大小长时间不变，退出
  if($now -le $have){ Start-Sleep -Seconds 10 }
}
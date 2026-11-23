param([string]$UrlFile,[string]$PartFile,[long]$Start,[long]$End,[int]$ChunkSec=90)
$ErrorActionPreference='Continue'
$url=[IO.File]::ReadAllText($UrlFile).Trim()
$want=$End-$Start+1
if(-not (Test-Path $PartFile)){ [IO.File]::WriteAllBytes($PartFile,[byte[]]@()) }
$tmpFile=$PartFile+'.tmp'
$log=$PartFile+'.log'
for($try=1; $try -le 3000; $try++){
  $have=0
  if(Test-Path $PartFile){ $fs=[IO.File]::Open($PartFile,'Open','Read','ReadWrite'); $have=$fs.Length; $fs.Close() }
  if($have -ge $want){ Add-Content $log "DONE try=$try have=$have want=$want"; break }
  $from=$Start+$have
  if(Test-Path $tmpFile){ Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue }
  # 每次只下 90 秒，然后重连拿新连接（R2 对长连接限速）
  $r = & curl.exe -sL --max-time $ChunkSec -r "$from-$End" -o $tmpFile -w "%{http_code}:%{size_download}" $url 2>&1
  $got=0
  if(Test-Path $tmpFile){ $got=(Get-Item $tmpFile).Length }
  if($got -gt 0){
    $fs=[IO.File]::Open($PartFile,[IO.FileMode]::Append,[IO.FileAccess]::Write)
    $in=[IO.File]::OpenRead($tmpFile)
    $in.CopyTo($fs)
    $in.Close(); $fs.Close()
    Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
    Add-Content $log "try=$try from=$from got=$got status=$r"
  } else {
    Add-Content $log "try=$try from=$from EMPTY status=$r"
    Start-Sleep -Seconds 5
  }
}
$final=0
if(Test-Path $PartFile){ $fs=[IO.File]::Open($PartFile,'Open','Read','ReadWrite'); $final=$fs.Length; $fs.Close() }
Add-Content $log "FINAL size=$final want=$want"

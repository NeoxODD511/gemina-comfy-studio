param([string]$Manifest,[string]$Root,[string]$CookieJar,[string]$Proxy)
$ErrorActionPreference='Continue'
function Get-SignedUrl($api,$proxy,$jar){
    $h = & curl.exe -sIL --max-time 35 -x $proxy -b $jar -A 'Mozilla/5.0' $api 2>&1
    $locs = $h | Select-String -Pattern '^location:' | ForEach-Object { ($_.Line -replace '^location:\s*','').Trim() }
    foreach($l in $locs){ if($l -match 'login|auth\.civitai'){continue}; if($l -match 'civitai\.com/file|cloudflarestorage|b2\.civitai|amazonaws'){return $l} }
    return $null
}
$m = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$log = Join-Path $Root 'lora-download.log'
foreach($l in $m.loras){
    foreach($base in @('anima','moss','krea2')){
        $v = $l.variants.$base
        if(-not $v){ continue }
        $cat = $l.category
        $fname = ($l.key + '_' + $base + '.safetensors')
        $dest = Join-Path $Root ("loras\$base\$cat\$fname")
        if((Test-Path $dest) -and ((Get-Item $dest).Length -gt 100000)){ Add-Content $log ("SKIP "+$fname); continue }
        $u = Get-SignedUrl $v.url $Proxy $CookieJar
        if(-not $u){ Add-Content $log ("SIGNFAIL "+$fname); continue }
        $tmpF = $dest + '.dl'
        Remove-Item $tmpF -Force -ErrorAction SilentlyContinue
        if($u -match 'b2\.civitai\.com'){
            & curl.exe -sL --max-time 600 --speed-time 45 --speed-limit 30000 -x $Proxy -o $tmpF "$u" 2>&1 | Out-Null
        } else {
            & curl.exe -sL --max-time 600 --speed-time 45 --speed-limit 30000 -o $tmpF "$u" 2>&1 | Out-Null
        }
        if((Test-Path $tmpF) -and ((Get-Item $tmpF).Length -gt 100000)){
            Move-Item $tmpF $dest -Force
            Add-Content $log ("OK   {0,-46} {1,6:N1} MB" -f $fname,((Get-Item $dest).Length/1MB))
        } else {
            Remove-Item $tmpF -Force -ErrorAction SilentlyContinue
            Add-Content $log ("FAIL "+$fname)
        }
    }
}
Add-Content $log "=== ALL DONE ==="
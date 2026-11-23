param([string]$Manifest, [string]$Root, [string]$CookieJar, [string]$Proxy)
$ErrorActionPreference='Continue'

function Get-SignedUrl($api, $proxy, $jar){
    $h = & curl.exe -sIL --max-time 35 -x $proxy -b $jar -A 'Mozilla/5.0' $api 2>&1
    $locs = $h | Select-String -Pattern '^location:' | ForEach-Object { ($_.Line -replace '^location:\s*','').Trim() }
    foreach($l in $locs){
        if($l -match 'login|auth\.civitai'){ continue }
        if($l -match 'civitai\.com/file|cloudflarestorage|b2\.civitai|r2\.|amazonaws'){ return $l }
    }
    return $null
}

function Download-One($url, $dest, $proxy, $maxTry=3){
    for($i=1; $i -le $maxTry; $i++){
        $tmp = $dest + ".part"
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        $useProxy = $url -match 'b2\.civitai\.com'
        if($useProxy){
            & curl.exe -sL --max-time 900 -x $proxy -o $tmp "$url" 2>&1 | Out-Null
        } else {
            & curl.exe -sL --max-time 900 -o $tmp "$url" 2>&1 | Out-Null
        }
        if((Test-Path $tmp) -and ((Get-Item $tmp).Length -gt 100000)){
            Move-Item $tmp $dest -Force
            return $true
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

$m = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($base in @('anima','moss','krea2')){
    foreach($cat in @('char','style','ctrl','q','x')){
        New-Item -ItemType Directory -Path "$Root\loras\$base\$cat" -Force | Out-Null
    }
}

$ok=0; $fail=0; $skip=0
$failedList = @()
foreach($l in $m.loras){
    foreach($base in @('anima','moss','krea2')){
        $v = $l.variants.$base
        if(-not $v){ continue }
        $cat = $l.category
        $fname = ($l.key + '_' + $base + '.safetensors')
        $dest = "$Root\loras\$base\$cat\$fname"
        if((Test-Path $dest) -and ((Get-Item $dest).Length -gt 100000)){
            $mb=[math]::Round((Get-Item $dest).Length/1MB,1)
            Write-Output ("SKIP  {0,-46} {1,6:N1} MB" -f $fname,$mb); $skip++; continue
        }
        $u = Get-SignedUrl $v.url $Proxy $CookieJar
        if(-not $u){
            Write-Output ("SIGN-FAIL " + $fname); $failedList += $fname; $fail++; continue
        }
        $t0 = Get-Date
        $good = Download-One $u $dest $Proxy 3
        $sec = [math]::Round(((Get-Date)-$t0).TotalSeconds,0)
        if($good){
            $mb = [math]::Round((Get-Item $dest).Length/1MB,1)
            Write-Output ("OK    {0,-46} {1,6:N1} MB  {2,4}s" -f $fname,$mb,$sec)
            $ok++
        } else {
            Write-Output ("FAIL  {0,-46}        {1,4}s" -f $fname,$sec)
            $failedList += $fname; $fail++
        }
    }
}
Write-Output ("`n=== 结果: 成功 $ok / 跳过 $skip / 失败 $fail ===")
if($failedList.Count){ Write-Output ("失败列表: " + ($failedList -join ', ')) }

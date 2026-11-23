param(
    [string]$Manifest = "F:\ComfyUI_Frontend\data\style_slider_manifest.json",
    [string]$Root = "F:\ComfyUI_Models\loras",
    [string]$CookieJar = "$env:TEMP\civ_cookies.txt",
    [string]$Proxy = "http://127.0.0.1:7897"
)
$ErrorActionPreference = 'Continue'

function Get-SignedUrl($api, $proxy, $jar) {
    $h = & curl.exe -sIL --max-time 35 -x $proxy -b $jar -A 'Mozilla/5.0' $api 2>&1
    $locs = $h | Select-String -Pattern '^location:' | ForEach-Object { ($_.Line -replace '^location:\s*', '').Trim() }
    foreach ($l in $locs) {
        if ($l -match 'login|auth\.civitai') { continue }
        if ($l -match 'civitai\.com/file|cloudflarestorage|b2\.civitai|amazonaws') { return $l }
    }
    return $null
}

function SafeName($s) {
    $x = $s -replace '[\\/:*?"<>|]', '_'
    $x = $x -replace '\s+', '_'
    if ($x.Length -gt 70) { $x = $x.Substring(0, 70) }
    return $x
}

$m = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$log = Join-Path $Root 'style-slider-download.log'
Add-Content $log "=== START $(Get-Date -Format 'HH:mm:ss') ==="

$ok = 0; $skip = 0; $fail = 0
$failList = @()

foreach ($group in @('style', 'slider')) {
    $dirBase = if ($group -eq 'style') { '' } else { '_sliders\' }
    foreach ($item in $m.$group) {
        foreach ($base in @('anima', 'moss', 'krea2')) {
            $v = $item.versions.$base
            if (-not $v) { continue }
            $cat = if ($group -eq 'style') { 'style' } else { '' }
            if ($group -eq 'style') {
                $dir = Join-Path $Root "$base\style"
            } else {
                $dir = Join-Path $Root "_sliders\$base"
            }
            New-Item -ItemType Directory -Path $dir -Force | Out-Null

            $slug = SafeName $item.name
            $fname = "$slug`_$base.safetensors"
            $dest = Join-Path $dir $fname

            if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 100000)) {
                Add-Content $log "SKIP  $fname"
                $skip++
                continue
            }

            $u = Get-SignedUrl $v.url $Proxy $CookieJar
            if (-not $u) {
                Add-Content $log "SIGNFAIL $fname"
                $failList += $fname
                $fail++
                continue
            }
            $tmpF = $dest + '.dl'
            Remove-Item $tmpF -Force -ErrorAction SilentlyContinue
            if ($u -match 'b2\.civitai\.com') {
                & curl.exe -sL --max-time 900 --speed-time 60 --speed-limit 20000 -x $Proxy -o $tmpF "$u" 2>&1 | Out-Null
            } else {
                & curl.exe -sL --max-time 900 --speed-time 60 --speed-limit 20000 -o $tmpF "$u" 2>&1 | Out-Null
            }
            if ((Test-Path $tmpF) -and ((Get-Item $tmpF).Length -gt 100000)) {
                Move-Item $tmpF $dest -Force
                $mb = [math]::Round((Get-Item $dest).Length / 1MB, 1)
                Add-Content $log ("OK    $fname  $mb MB")
                $ok++
            } else {
                Remove-Item $tmpF -Force -ErrorAction SilentlyContinue
                Add-Content $log "FAIL  $fname"
                $failList += $fname
                $fail++
            }
            Start-Sleep -Milliseconds 200
        }
    }
}
Add-Content $log "=== DONE ok=$ok skip=$skip fail=$fail ==="
if ($failList.Count) { Add-Content $log ("FAILED: " + ($failList -join ', ')) }
Write-Output "ok=$ok skip=$skip fail=$fail"

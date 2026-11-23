param(
    [string]$Manifest = "F:\ComfyUI_Frontend\data\extra_manifest.json",
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
    if ($x.Length -gt 60) { $x = $x.Substring(0, 60) }
    return $x
}

$m = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$log = Join-Path $Root 'extra-download.log'
Add-Content $log "=== START $(Get-Date -Format 'HH:mm:ss') ==="
$ok = 0; $skip = 0; $fail = 0

foreach ($item in $m) {
    $group = $item.group
    foreach ($vk in $item.versions.PSObject.Properties.Name) {
        # 跳过 bakalight v2（作者说失败）
        if ($vk -eq 'anima_v20') { Add-Content $log "SKIP-v2 bakalight (author said failed)"; continue }
        $v = $item.versions.$vk
        $base = $vk -replace '_v\d+$', ''   # anima_v30 -> anima
        if ($base -notin @('anima', 'moss', 'krea2')) { $base = $vk }

        if ($group -eq 'slider') {
            $dir = Join-Path $Root "_sliders\$base"
        } else {
            $dir = Join-Path $Root "$base\style"
        }
        New-Item -ItemType Directory -Path $dir -Force | Out-Null

        $slug = SafeName $item.name
        $suffix = if ($vk -match '(_v\d+)$') { $Matches[1] } else { '' }
        $fname = "$slug$suffix`_$base.safetensors"
        $dest = Join-Path $dir $fname

        if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 100000)) {
            Add-Content $log "SKIP  $fname"; $skip++; continue
        }
        $u = Get-SignedUrl $v.url $Proxy $CookieJar
        if (-not $u) { Add-Content $log "SIGNFAIL $fname"; $fail++; continue }
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
            Add-Content $log "FAIL  $fname"; $fail++
        }
        Start-Sleep -Milliseconds 200
    }
}
Add-Content $log "=== DONE ok=$ok skip=$skip fail=$fail ==="
Write-Output "ok=$ok skip=$skip fail=$fail"

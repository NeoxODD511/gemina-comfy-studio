"""补下失败的 LoRA（用 Python 避开 PowerShell 中文编码问题）"""
import json, urllib.request, os, sys, io, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
JAR = os.path.join(os.environ.get("TEMP", "."), "civ_cookies.txt")
ROOT = r"F:\ComfyUI_Models\loras"
BASE_KEY = {"Anima": "anima", "MOSS Image": "moss", "Krea 2": "krea2"}

opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))

# 需要重下的：模型 ID -> (目标 base, 目标子目录)
RETRY = [
    (2629905, ["anima", "moss", "krea2"], "style"),   # 米山舞
    (789313, ["krea2"], "style"),                      # 80s Fantasy Movie
    (2526312, ["moss"], "ctrl"),                       # Darkness Slider moss
]


def load_jar():
    txt = ""
    if os.path.isfile(JAR):
        with open(JAR, encoding="utf-8") as f:
            txt = f.read()
    return txt


def get_signed(api_url):
    """用 curl 取签名 URL（curl 处理重定向更稳）"""
    import subprocess, tempfile
    hdr = os.path.join(tempfile.gettempdir(), "hdr_retry.txt")
    cmd = ["curl.exe", "-sIL", "--max-time", "35", "-x", PROXY,
           "-b", JAR, "-A", "Mozilla/5.0", api_url]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=40).stdout.decode("utf-8", "replace")
    except Exception:
        return None
    for line in out.splitlines():
        if line.lower().startswith("location:"):
            u = line.split(":", 1)[1].strip()
            if "login" in u or "auth.civitai" in u:
                continue
            if any(k in u for k in ("civitai.com/file", "cloudflarestorage", "b2.civitai", "amazonaws")):
                return u
    return None


def download(url, dest):
    import subprocess
    use_proxy = "b2.civitai.com" in url
    cmd = ["curl.exe", "-sL", "--max-time", "900", "--speed-time", "60", "--speed-limit", "20000", "-o", dest]
    if use_proxy:
        cmd += ["-x", PROXY]
    cmd.append(url)
    try:
        subprocess.run(cmd, capture_output=True, timeout=950)
    except Exception:
        return False
    return os.path.isfile(dest) and os.path.getsize(dest) > 100000


def main():
    ok = fail = skip = 0
    for mid, bases, cat in RETRY:
        req = urllib.request.Request(f"https://civitai.com/api/v1/models/{mid}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        m = json.loads(opener.open(req, timeout=40).read().decode("utf-8"))
        name = m.get("name")
        # 每个 base 取最新版本
        picked = {}
        for v in m.get("modelVersions") or []:
            bm = v.get("baseModel")
            if bm not in BASE_KEY:
                continue
            b = BASE_KEY[bm]
            if b in picked:
                continue
            f = None
            for f0 in v.get("files") or []:
                if f0.get("primary"):
                    f = f0
                    break
            if not f:
                continue
            picked[b] = f.get("downloadUrl")
        for b in bases:
            url = picked.get(b)
            if not url:
                print(f"  [{mid}] {b}: 无版本")
                continue
            # 目录
            if cat == "ctrl":
                d = os.path.join(ROOT, "_sliders", b)
            else:
                d = os.path.join(ROOT, b, cat)
            os.makedirs(d, exist_ok=True)
            # 文件名用 id 避免中文问题
            fname = f"lora_{mid}_{b}.safetensors"
            dest = os.path.join(d, fname)
            if os.path.isfile(dest) and os.path.getsize(dest) > 100000:
                print(f"  SKIP {fname}")
                skip += 1
                continue
            signed = get_signed(url)
            if not signed:
                print(f"  SIGNFAIL {fname}")
                fail += 1
                continue
            tmp = dest + ".dl"
            if download(signed, tmp):
                os.replace(tmp, dest)
                mb = round(os.path.getsize(dest) / 1024 / 1024, 1)
                print(f"  OK   {fname}  {mb} MB")
                ok += 1
            else:
                if os.path.isfile(tmp):
                    os.remove(tmp)
                print(f"  FAIL {fname}")
                fail += 1
        time.sleep(0.5)
    print(f"\n结果: ok={ok} skip={skip} fail={fail}")


if __name__ == "__main__":
    main()

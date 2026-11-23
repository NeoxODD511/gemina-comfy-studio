"""自动重下并完整性校验 9 个残缺的 .safetensors LoRA 文件"""
import json, os, struct, subprocess, sys, io, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
JAR = os.path.join(os.environ.get("TEMP", "."), "civ_cookies.txt")

TARGETS = [
    # 优先补齐 Anima 3 个
    (r"F:\ComfyUI_Models\loras\anima\style\The_Look_anima.safetensors", "extra_manifest.json", "The Look", "anima"),
    (r"F:\ComfyUI_Models\loras\anima\q\aesthetic_quality_anima.safetensors", "download_manifest.json", "aesthetic_quality", "anima"),
    (r"F:\ComfyUI_Models\loras\anima\style\niji_sweet_spot_anima.safetensors", "download_manifest.json", "niji_sweet_spot", "anima"),
    # 再补齐 MOSS 2 个 & Krea 2 4 个
    (r"F:\ComfyUI_Models\loras\moss\style\Aesthetic_Quality_Modifiers_-_Masterpiece_moss.safetensors", "style_slider_manifest.json", "Aesthetic Quality Modifiers - Masterpiece", "moss"),
    (r"F:\ComfyUI_Models\loras\moss\x\turbo_moss_moss.safetensors", "download_manifest.json", "turbo_moss", "moss"),
    (r"F:\ComfyUI_Models\loras\krea2\q\aesthetic_quality_krea2.safetensors", "download_manifest.json", "aesthetic_quality", "krea2"),
    (r"F:\ComfyUI_Models\loras\krea2\style\Aesthetic_Quality_Modifiers_-_Masterpiece_krea2.safetensors", "style_slider_manifest.json", "Aesthetic Quality Modifiers - Masterpiece", "krea2"),
    (r"F:\ComfyUI_Models\loras\krea2\style\niji_sweet_spot_krea2.safetensors", "download_manifest.json", "niji_sweet_spot", "krea2"),
    (r"F:\ComfyUI_Models\loras\krea2\style\The_Look_krea2.safetensors", "extra_manifest.json", "The Look", "krea2"),
]


def check_safetensors(path):
    if not os.path.isfile(path):
        return "not found"
    sz = os.path.getsize(path)
    if sz < 10000:
        return f"too small ({sz}B)"
    try:
        with open(path, "rb") as f:
            hdr_len = struct.unpack("<Q", f.read(8))[0]
            if hdr_len > sz - 8 or hdr_len > 100_000_000:
                return f"bad header len {hdr_len}"
            hdr = json.loads(f.read(hdr_len).decode("utf-8"))
        max_end = 0
        for k, v in hdr.items():
            if k == "__metadata__":
                continue
            offs = v.get("data_offsets")
            if offs and len(offs) == 2 and offs[1] > max_end:
                max_end = offs[1]
        expected = 8 + hdr_len + max_end
        if sz < expected:
            return f"truncated ({sz}/{expected})"
        return None
    except Exception as e:
        return str(e)


def find_url(mf, key, base):
    with open(rf"F:\ComfyUI_Frontend\data\{mf}", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, list):
        items = d
    elif "loras" in d:
        items = d["loras"]
    elif "style" in d:
        items = (d.get("style") or []) + (d.get("slider") or [])
    else:
        items = []
    for it in items:
        if it.get("key") == key or it.get("name") == key or it.get("title") == key:
            vers = it.get("versions") or it.get("variants") or it.get("files") or {}
            if isinstance(vers, dict) and base in vers:
                v = vers[base]
                return v.get("url") or v.get("download_url")
            if isinstance(vers, list):
                for vv in vers:
                    if str(vv.get("base", "")).lower() == base:
                        return vv.get("url") or vv.get("download_url")
    return None


def get_signed(api_url):
    cmd = ["curl.exe", "-sIL", "--max-time", "35", "-x", PROXY, "-A", "Mozilla/5.0"]
    if os.path.isfile(JAR):
        cmd += ["-b", JAR]
    cmd.append(api_url)
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=45).stdout.decode("utf-8", "replace")
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


def download_file(url, dest):
    use_proxy = "b2.civitai.com" in url
    for attempt in range(1, 4):
        cmd = [
            "curl.exe", "-sL", "-C", "-", "--retry", "3",
            "--max-time", "900", "--speed-time", "45", "--speed-limit", "10000",
            "-o", dest
        ]
        if use_proxy:
            cmd += ["-x", PROXY]
        cmd.append(url)
        try:
            subprocess.run(cmd, capture_output=True, timeout=920)
        except Exception:
            pass
        err = check_safetensors(dest)
        if err is None:
            return True, None
        print(f"    attempt {attempt} incomplete: {err}", flush=True)
        time.sleep(2)
    return False, check_safetensors(dest)


def main():
    ok = fail = skip = 0
    for dest, mf, key, base in TARGETS:
        fname = os.path.basename(dest)
        if check_safetensors(dest) is None:
            print(f"[SKIP] {fname} already intact", flush=True)
            skip += 1
            continue
        url = find_url(mf, key, base)
        if not url:
            print(f"[MISS_URL] {fname}", flush=True)
            fail += 1
            continue
        print(f"[DOWN] {fname} ...", flush=True)
        signed = get_signed(url)
        if not signed:
            print(f"[SIGNFAIL] {fname} ({url})", flush=True)
            fail += 1
            continue
        tmp = dest + ".fixdl"
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        good, err = download_file(signed, tmp)
        if good:
            os.replace(tmp, dest)
            mb = round(os.path.getsize(dest) / 1024 / 1024, 1)
            print(f"[OK]   {fname} ({mb} MB, verified intact!)", flush=True)
            ok += 1
        else:
            print(f"[FAIL] {fname}: {err}", flush=True)
            fail += 1
    print(f"\nDONE: ok={ok}, skip={skip}, fail={fail}", flush=True)


if __name__ == "__main__":
    main()

"""下载三底模的姿势控制模型"""
import json, urllib.request, os, sys, io, subprocess, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
JAR = os.path.join(os.environ.get("TEMP", "."), "civ_cookies.txt")
MODELS = r"F:\ComfyUI\app\comfyui-master\models"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))

# (api_url, 目标子目录, 目标文件名, 说明)
TARGETS = [
    # Anima LLLite
    ("https://civitai.com/api/download/models/3149841?fileId=3030473", "controlnet", "ab1_lineart.safetensors", "Anima LLLite AB1 LINEART"),
    ("https://civitai.com/api/download/models/3149826?fileId=3030424", "controlnet", "ab1_canny.safetensors", "Anima LLLite AB1 CANNY"),
    ("https://civitai.com/api/download/models/2924692?fileId=2805095", "controlnet", "lineart_realistic.safetensors", "Anima LLLite AP3 LINEART"),
    ("https://civitai.com/api/download/models/2924690?fileId=2805092", "controlnet", "canny.safetensors", "Anima LLLite AP3 CANNY"),
    # Anima Control Pose
    ("https://civitai.com/api/download/models/3070469?fileId=2949287", "controlnet", "anima_pose_preview2.safetensors", "Anima Control Pose preview2"),
    # Krea 2 Depth Control LoRA
    ("https://civitai.com/api/download/models/3097135?fileId=2976752", "loras", "krea2_depth-control-lora.safetensors", "Krea2 Depth ControlNet LoRA"),
    # MOSS Color & Depth (model patch)
    ("https://civitai.com/api/download/models/3416153?fileId=3309150", "model_patches", "moss-color-depth-control.safetensors", "MOSS Color & Depth Controlnet"),
]


def get_signed(api):
    cmd = ["curl.exe", "-sIL", "--max-time", "40", "-x", PROXY, "-b", JAR, "-A", "Mozilla/5.0", api]
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


def download(url, dest):
    use_proxy = "b2.civitai.com" in url
    cmd = ["curl.exe", "-sL", "--max-time", "1200", "--speed-time", "90", "--speed-limit", "15000", "-o", dest]
    if use_proxy:
        cmd += ["-x", PROXY]
    cmd.append(url)
    try:
        subprocess.run(cmd, capture_output=True, timeout=1250)
    except Exception:
        return False
    return os.path.isfile(dest) and os.path.getsize(dest) > 50000


def main():
    ok = skip = fail = 0
    for api, sub, fname, label in TARGETS:
        d = os.path.join(MODELS, sub)
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, fname)
        if os.path.isfile(dest) and os.path.getsize(dest) > 50000:
            print(f"SKIP  {label}  ({fname})")
            skip += 1
            continue
        signed = get_signed(api)
        if not signed:
            print(f"SIGNFAIL {label}")
            fail += 1
            continue
        tmp = dest + ".dl"
        if download(signed, tmp):
            os.replace(tmp, dest)
            mb = round(os.path.getsize(dest) / 1024 / 1024, 1)
            print(f"OK    {label}  -> {sub}/{fname}  {mb} MB")
            ok += 1
        else:
            if os.path.isfile(tmp):
                os.remove(tmp)
            print(f"FAIL  {label}")
            fail += 1
        time.sleep(0.3)
    print(f"\n结果: ok={ok} skip={skip} fail={fail}")


if __name__ == "__main__":
    main()

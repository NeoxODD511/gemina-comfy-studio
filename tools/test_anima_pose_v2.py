"""Anima LLLite 姿势控制测试 v2 —— 姿势图先转线稿再喂 LLLite"""
import json, os, sys, io, time, urllib.request, urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"

PROMPT = {
    "1": {"class_type": "PoseGallery", "inputs": {"pose_id": "full_sexy_P001_front", "language": "zh"}},
    "2": {"class_type": "AnimeLineArtPreprocessor", "inputs": {"image": ["1", 0], "resolution": 1024}},
    "3": {"class_type": "ImageScale", "inputs": {
        "image": ["2", 0], "upscale_method": "lanczos", "width": 832, "height": 1216, "crop": "center"}},
    "4": {"class_type": "GetImageSize", "inputs": {"image": ["3", 0]}},
    "5": {"class_type": "UNETLoader", "inputs": {"unet_name": "anima\\anima-base-v1.0.safetensors", "weight_dtype": "default"}},
    "6": {"class_type": "CLIPLoader", "inputs": {"clip_name": "anima\\qwen_3_06b_base.safetensors", "type": "stable_diffusion", "device": "default"}},
    "7": {"class_type": "VAELoader", "inputs": {"vae_name": "anima\\qwen_image_vae.safetensors"}},
    "8": {"class_type": "ModelPatchLoader", "inputs": {"name": "ab1_lineart.safetensors"}},
    "9": {"class_type": "AnimaLLLiteApply", "inputs": {
        "model": ["5", 0], "model_patch": ["8", 0], "image": ["3", 0],
        "strength": 1.0, "start_percent": 0.0, "end_percent": 0.9}},
    "10": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "1girl, solo, full body, standing, masterpiece, best quality, anime coloring, detailed face, beautiful eyes, school uniform, looking at viewer, soft lighting",
        "clip": ["6", 0]}},
    "11": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "lowres, bad anatomy, bad hands, text, error, extra digits, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, lineart, monochrome, sketch, grid, halftone",
        "clip": ["6", 0]}},
    "12": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    "13": {"class_type": "KSampler", "inputs": {
        "seed": 20261122, "steps": 20, "cfg": 4.0, "sampler_name": "er_sde", "scheduler": "simple",
        "denoise": 1.0, "model": ["9", 0], "positive": ["10", 0], "negative": ["11", 0], "latent_image": ["12", 0]}},
    "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["7", 0]}},
    "15": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Anima_Pose_v2", "images": ["14", 0]}},
    "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Anima_Pose_v2_lineart", "images": ["3", 0]}},
}


def post(path, data):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def get(path, timeout=30):
    return json.loads(urllib.request.urlopen(COMFY + path, timeout=timeout).read().decode())


def main():
    print("=== 提交 ===")
    try:
        r = post("/prompt", {"prompt": PROMPT, "client_id": "anima_v2"})
    except urllib.error.HTTPError as e:
        print("HTTP", e.code)
        print(e.read().decode()[:2000])
        return 1
    pid = r.get("prompt_id")
    print("prompt_id:", pid)
    if r.get("node_errors"):
        print("节点错误:", json.dumps(r["node_errors"], ensure_ascii=False)[:1500])
        return 1

    print("=== 等待（最多 20 分钟）===")
    for i in range(200):
        time.sleep(6)
        try:
            h = get(f"/history/{pid}")
        except Exception:
            continue
        if pid in h:
            st = h[pid].get("status", {})
            print("状态:", st.get("status_str"), "completed=", st.get("completed"))
            for nid, out in (h[pid].get("outputs") or {}).items():
                for img in out.get("images", []):
                    print(f"  输出 [{nid}]: {img.get('filename')} {img.get('subfolder','')}")
            if st.get("status_str") == "error":
                for m in st.get("messages", []):
                    if m[0] == "execution_error":
                        print("错误节点:", m[1].get("node_type"))
                        print("错误信息:", m[1].get("exception_message", "")[:600])
            return 0 if st.get("completed") else 1
        if i % 20 == 0 and i:
            print(f"  [{i*6}s] 继续等待...")
    print("超时")
    return 1


if __name__ == "__main__":
    sys.exit(main())

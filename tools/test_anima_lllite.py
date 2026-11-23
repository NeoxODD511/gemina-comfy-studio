"""跑一张 Anima LLLite 姿势控制测试图"""
import json, os, sys, io, time, urllib.request

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"

# 直接用 API 格式构造（比转换 UI 格式更可控）
PROMPT = {
    "1": {"class_type": "PoseGallery", "inputs": {"pose_id": "full_sexy_P001_front", "language": "zh"}},
    "2": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 1}},
    "3": {"class_type": "GetImageSize", "inputs": {"image": ["2", 0]}},
    "4": {"class_type": "UNETLoader", "inputs": {"unet_name": "anima\\anima-base-v1.0.safetensors", "weight_dtype": "default"}},
    "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": "anima\\qwen_3_06b_base.safetensors", "type": "stable_diffusion", "device": "default"}},
    "6": {"class_type": "VAELoader", "inputs": {"vae_name": "anima\\qwen_image_vae.safetensors"}},
    "7": {"class_type": "ModelPatchLoader", "inputs": {"name": "anima_pose_preview2.safetensors"}},
    "8": {"class_type": "AnimaLLLiteApply", "inputs": {
        "model": ["4", 0], "model_patch": ["7", 0], "image": ["2", 0],
        "strength": 1.0, "start_percent": 0.0, "end_percent": 0.9}},
    "9": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "1girl, solo, masterpiece, best quality, anime coloring, detailed face, beautiful eyes, school uniform, looking at viewer, soft lighting",
        "clip": ["5", 0]}},
    "10": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, lineart, monochrome, sketch",
        "clip": ["5", 0]}},
    "11": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    "12": {"class_type": "KSampler", "inputs": {
        "seed": 20261122, "steps": 20, "cfg": 4.0, "sampler_name": "er_sde", "scheduler": "simple",
        "denoise": 1.0, "model": ["8", 0], "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["11", 0]}},
    "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["6", 0]}},
    "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Anima_Pose_test2", "images": ["13", 0]}},
}


def post(path, data):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def get(path, timeout=30):
    return json.loads(urllib.request.urlopen(COMFY + path, timeout=timeout).read().decode())


def main():
    # 先确认 PoseGallery 能拿到有效 pose
    print("=== 提交任务 ===")
    try:
        r = post("/prompt", {"prompt": PROMPT, "client_id": "anima_test"})
    except urllib.error.HTTPError as e:
        print("提交失败:", e.code)
        print(e.read().decode()[:2000])
        return 1
    pid = r.get("prompt_id")
    print("prompt_id:", pid)
    if r.get("node_errors"):
        print("节点错误:", json.dumps(r["node_errors"], ensure_ascii=False)[:1500])

    # 轮询
    print("=== 等待生成 ===")
    for i in range(120):
        time.sleep(3)
        try:
            h = get(f"/history/{pid}")
        except Exception:
            continue
        if pid in h:
            entry = h[pid]
            status = entry.get("status", {})
            print("状态:", status.get("status_str"), "completed=", status.get("completed"))
            outputs = entry.get("outputs", {})
            for nid, out in outputs.items():
                for img in out.get("images", []):
                    print(f"  输出: {img.get('filename')}  type={img.get('type')}  subfolder={img.get('subfolder')}")
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                print("错误详情:", json.dumps(msgs, ensure_ascii=False)[:1500])
            return 0 if status.get("completed") else 1
        if i % 10 == 0:
            q = get("/queue")
            running = len(q.get("queue_running", []))
            print(f"  [{i*3}s] running={running}")
    print("超时")
    return 1


if __name__ == "__main__":
    sys.exit(main())

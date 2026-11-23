"""批量查询 C 站模型的全部底模版本 + 触发词，生成下载清单"""
import json, urllib.request, os, sys, io, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
BASE_MODELS = ["Anima", "MOSS Image", "Krea 2"]
BASE_KEY = {"Anima": "anima", "MOSS Image": "moss", "Krea 2": "krea2"}

STYLE_IDS = [599757, 929497, 1132089, 1155749, 789313, 1349631, 22800, 2564225,
             1380736, 311073, 863136, 2533943, 1738546, 1357076, 878199, 2762978,
             2284180, 878386, 681120, 3005005]
SLIDER_IDS = [2513759, 2732158, 2535632, 2546450, 738727, 2521578, 2533131,
              2568691, 3008688, 2827092, 3042936, 2972655, 3053108]

opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))


def fetch_model(mid):
    url = f"https://civitai.com/api/v1/models/{mid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = opener.open(req, timeout=40).read()
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        return {"_error": str(e)}


def pick_versions(model):
    """按底模挑最新版本，返回 {base_key: {url, ver, trigger, name}}"""
    out = {}
    for v in model.get("modelVersions") or []:
        bm = v.get("baseModel")
        if bm not in BASE_MODELS:
            continue
        key = BASE_KEY[bm]
        if key in out:
            continue  # 已取到更新的（API 按新到旧排）
        # 主文件
        f = None
        for f0 in v.get("files") or []:
            if f0.get("primary"):
                f = f0
                break
        if not f:
            for f0 in v.get("files") or []:
                if f0.get("type") == "Model":
                    f = f0
                    break
        if not f:
            continue
        words = v.get("trainedWords") or []
        out[key] = {
            "ver": v.get("name"),
            "version_id": v.get("id"),
            "url": f.get("downloadUrl"),
            "filename": f.get("name"),
            "size_kb": f.get("sizeKB"),
            "trigger": ", ".join(words) if words else "",
        }
    return out


def main():
    result = {"style": [], "slider": []}
    for group, ids in (("style", STYLE_IDS), ("slider", SLIDER_IDS)):
        for mid in ids:
            m = fetch_model(mid)
            if "_error" in m:
                print(f"  [{mid}] 查询失败: {m['_error'][:60]}")
                continue
            name = m.get("name")
            vs = pick_versions(m)
            if not vs:
                print(f"  [{mid}] {name[:40]} -> 无三底模版本")
                continue
            result[group].append({"id": mid, "name": name, "versions": vs})
            print(f"  [{mid}] {name[:44]:46s} -> {', '.join(vs.keys())}")
            time.sleep(0.3)

    out = r"F:\ComfyUI_Frontend\data\style_slider_manifest.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\nwritten:", out)
    print(f"画风 {len(result['style'])} 个，滑块 {len(result['slider'])} 个")


if __name__ == "__main__":
    main()

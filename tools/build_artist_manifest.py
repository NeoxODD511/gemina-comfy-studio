"""第三批：用户清单里筛选出的三底模可用模型"""
import json, urllib.request, sys, io, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))
BASE_KEY = {"Anima": "anima", "MOSS Image": "moss", "Krea 2": "krea2"}

TARGETS = {
    213206: "D-ART @18dart5",
    178169: "Afrobull",
    1200733: "Iwao178",
    29215: "BArtstyle 蔚蓝档案",
    128568: "Cyberpunk Anime Style",
    912942: "Retro Sci-fi 90's anime",
    1586542: "Anime art",
}


def fetch(mid):
    req = urllib.request.Request(f"https://civitai.com/api/v1/models/{mid}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(opener.open(req, timeout=40).read().decode("utf-8"))


def main():
    out = []
    for mid, label in TARGETS.items():
        try:
            m = fetch(mid)
        except Exception as e:
            print(f"[{mid}] 失败: {e}")
            continue
        name = m.get("name")
        versions = {}
        for v in m.get("modelVersions") or []:
            bm = v.get("baseModel")
            if bm not in BASE_KEY:
                continue
            key = BASE_KEY[bm]
            if key in versions:
                continue
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
            versions[key] = {
                "ver": v.get("name"),
                "url": f.get("downloadUrl"),
                "filename": f.get("name"),
                "size_mb": round((f.get("sizeKB") or 0) / 1024, 1),
                "trigger": ", ".join(words) if words else "",
            }
        if versions:
            out.append({"id": mid, "name": name, "label": label, "versions": versions})
            print(f"[{mid}] {label:26s} {name[:34]:36s} -> {', '.join(versions.keys())}")
        else:
            print(f"[{mid}] {label:26s} 无三底模版本")
        time.sleep(0.3)

    path = r"F:\ComfyUI_Frontend\data\artist_manifest.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nwritten:", path, f"({len(out)} 个模型)")


if __name__ == "__main__":
    main()

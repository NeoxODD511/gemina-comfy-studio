"""补充下载清单：The Look / 米山舞 / 少把盐 / Darkness Slider / bakalight"""
import json, urllib.request, sys, io, os, time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = "http://127.0.0.1:7897"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))
BASE_KEY = {"Anima": "anima", "MOSS Image": "moss", "Krea 2": "krea2"}

# id -> (分组, 说明)
TARGETS = {
    1882546: ("style", "The Look - 自然表情"),
    2629905: ("style", "米山舞 Yoneyama Mai"),
    2638358: ("style", "少把盐"),
    2526312: ("slider", "Darkness Slider"),
    2644401: ("style", "bakalight 光影"),
}


def fetch(mid):
    req = urllib.request.Request(f"https://civitai.com/api/v1/models/{mid}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(opener.open(req, timeout=40).read().decode("utf-8"))


def main():
    out = []
    for mid, (group, note) in TARGETS.items():
        m = fetch(mid)
        name = m.get("name")
        versions = {}
        for v in m.get("modelVersions") or []:
            bm = v.get("baseModel")
            if bm not in BASE_KEY:
                continue
            key = BASE_KEY[bm]
            # 每个底模取最新版本；bakalight 额外保留 v1
            if key in versions and not (mid == 2644401 and v.get("name", "").startswith("v1")):
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
            suffix = ""
            if mid == 2644401:
                suffix = "_" + v.get("name", "").replace(".", "").replace(" ", "")
            versions[key + suffix] = {
                "ver": v.get("name"),
                "url": f.get("downloadUrl"),
                "filename": f.get("name"),
                "size_mb": round((f.get("sizeKB") or 0) / 1024, 1),
                "trigger": ", ".join(words) if words else "",
            }
        out.append({"id": mid, "name": name, "group": group, "note": note, "versions": versions})
        print(f"[{mid}] {name[:44]:46s} -> {', '.join(versions.keys())}")
        time.sleep(0.3)

    path = r"F:\ComfyUI_Frontend\data\extra_manifest.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nwritten:", path)


if __name__ == "__main__":
    main()

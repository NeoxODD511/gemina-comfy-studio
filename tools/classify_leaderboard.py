"""C站 LoRA 排行榜分类：只保留二次元向，按 画风/画师/姿势/构图/光影 归类
修正：分类主要依据模型名，desc 仅作辅助；画风优先级最高
"""
import json, re, os, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = os.path.join(os.environ.get("TEMP", "."), "all_lora.json")
OUT = r"F:\ComfyUI_Frontend\data\leaderboard.json"

REALISTIC = [
    r"ultrareal", r"famegrid", r"photo", r"photograph", r"candid", r"iphone", r"lightbox",
    r"purelens", r"cinematic", r"film\b", r"realism", r"realistic", r"skin texture",
    r"hyperreal", r"fpv", r"polaroid", r"analog", r"dslr", r"3d skin",
]

# 顺序 = 优先级。画风放最前，因为画风 LoRA 名字里常带 anime/style/画师名
RULES = [
    ("画风/画师", [
        r"style", r"画风", r"画师", r"artist", r"artstyle", r"niji", r"flat.?color",
        r"dark.?art", r"ghibli", r"cyberpunk", r"赛博", r"watercolor", r"水彩", r"oil.?paint",
        r"cel.?shad", r"赛璐璐", r"pencil", r"彩铅", r"sketch", r"线稿", r"lineart",
        r"retro", r"复古", r"pixel", r"像素", r"anime", r"illustration", r"插画",
        r"manga", r"漫画", r"aesthetic", r"palette", r"pastel", r"粉彩", r"vibrant",
        r"meion", r"krekkov", r"takorin", r"disney", r"bss", r"movie", r"noir",
        r"melancholy", r"aesthetic", r"soft.?touch", r"harem", r"xanime",
    ]),
    ("光影", [
        r"light", r"光影", r"shadow", r"glow", r"rim.?light", r"backlight", r"volumetric",
        r"lighting", r"illuminat", r"sunlight", r"neon", r"luminous", r"chiaroscuro",
        r"darkness", r"brightness", r"contrast", r"saturat", r"色温", r"tone", r"hue",
        r"atmosphere", r"氛围", r"god.?ray",
    ]),
    ("构图", [
        r"composition", r"构图", r"angle", r"视角", r"framing", r"perspective", r"tilt",
        r"camera", r"镜头", r"closeup", r"close.?up", r"wide.?shot", r"zoom", r"panorama",
        r"depth.?of.?field", r"bokeh", r"layout", r"view", r"shot\b", r"framing",
    ]),
    ("姿势", [
        r"pose", r"姿势", r"slider", r"thigh", r"hip", r"waist", r"body.?weight", r"breast",
        r"leg", r"hand", r"kneel", r"sitting", r"standing", r"lying", r"action", r"gesture",
        r"体态", r"身材", r"lips", r"height", r"muscle", r"belly",
    ]),
]

CHECK_ONLY_NAME = True   # 只按模型名判断，避免 desc 干扰


def is_realistic(name, desc, tags):
    s = (name + " " + desc + " " + tags).lower()
    for p in REALISTIC:
        if re.search(p, s):
            return True
    return False


def classify(name, desc, tags):
    target = name.lower() if CHECK_ONLY_NAME else (name + " " + desc + " " + tags).lower()
    for cat, pats in RULES:
        for p in pats:
            if re.search(p, target):
                return cat
    return "其他"


def main():
    with open(SRC, encoding="utf-8") as f:
        rows = json.load(f)

    merged = {}
    for r in rows:
        mid = r["id"]
        if mid not in merged:
            merged[mid] = {
                "id": mid, "name": r["name"], "bases": set(),
                "downloads": r.get("downloads") or 0,
                "likes": r.get("likes") or 0,
                "nsfw": r.get("nsfw"), "tags": r.get("tags") or "",
                "desc": (r.get("desc") or "")[:160],
            }
        merged[mid]["bases"].add(r.get("base") or "unknown")

    out = []
    for m in merged.values():
        if is_realistic(m["name"], m["desc"], m["tags"]):
            continue
        m["bases"] = sorted(m["bases"])
        m["category"] = classify(m["name"], m["desc"], m["tags"])
        out.append(m)

    order = {"画风/画师": 0, "光影": 1, "构图": 2, "姿势": 3, "其他": 4}
    out.sort(key=lambda x: (order.get(x["category"], 9), -x["downloads"]))

    stats = {}
    for o in out:
        stats[o["category"]] = stats.get(o["category"], 0) + 1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"total": len(out), "stats": stats, "items": out}, f, ensure_ascii=False, indent=2)

    print(json.dumps({"total": len(out), "stats": stats}, ensure_ascii=False, indent=2))
    for cat in ["画风/画师", "光影", "构图", "姿势", "其他"]:
        items = [o for o in out if o["category"] == cat]
        if not items:
            continue
        print(f"\n=== {cat} ({len(items)}) ===")
        for o in items[:15]:
            print(f"  {o['name'][:50]:52s} {'/'.join(o['bases'])[:26]:28s} dl={o['downloads']:,}")


if __name__ == "__main__":
    main()

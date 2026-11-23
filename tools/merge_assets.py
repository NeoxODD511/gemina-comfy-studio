"""
合并所有词库到前端 assets
数据源：
  1. workbench_tags_cn.json   18250 标签（7 类）
  2. wardrobe_characters.json 2390 角色 + 284 作品
  3. wardrobe_character_outfits.json 2316 角色的多套服装
  4. wardrobe_scenes.json     271 场景（4 分组）
  5. pose-gallery pose-zh.json 1439 姿势（带缩略图）
"""
import json, os, sys, io, re

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

STAGE = r"F:\ComfyUI_Frontend\data\staging"
OUT = r"F:\ComfyUI_Frontend\data\assets"
POSE_INDEX = r"F:\ComfyUI\app\comfyui-master\custom_nodes\comfyui-pose-gallery\library\data\pose-zh.json"
os.makedirs(OUT, exist_ok=True)


def load(path):
    p = os.path.join(STAGE, path) if not os.path.isabs(path) else path
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def nw(s):
    if s is None:
        return ""
    if isinstance(s, list):
        return ", ".join(nw(x) for x in s if x)
    return re.sub(r"\s+", " ", str(s).strip())


# ---------- 1. 姿势 ----------
def build_poses():
    out, seen = [], set()

    # 来源A：pose-gallery 1439 张（带缩略图，优先级最高）
    pg = load(POSE_INDEX)
    if isinstance(pg, list):
        for it in pg:
            pid = it.get("id")
            if not pid:
                continue
            seen.add(pid.lower())
            name = it.get("姿势名称") or pid
            cat = it.get("分类") or ""
            sysname = it.get("体系") or ""
            angle = it.get("角度") or ""
            out.append({
                "id": pid,
                "name": name,
                "zh": name,
                "cat": cat,
                "system": sysname,
                "angle": angle,
                "thumb": it.get("缩略图") or "",
                "img": it.get("原图") or "",
                "tags": "",
                "level": 0,
                "src": "pose-gallery",
            })

    # 来源B：workbench 动作类
    wb = load("workbench_tags_cn.json")
    if wb and isinstance(wb.get("tags"), list):
        for t in wb["tags"]:
            if t.get("cat") != "动作":
                continue
            en = nw(t.get("en"))
            if not en or en.lower() in seen:
                continue
            seen.add(en.lower())
            out.append({
                "id": en, "name": nw(t.get("zh")) or en, "zh": nw(t.get("zh")) or en,
                "cat": nw(t.get("sub")) or "动作", "system": "workbench", "angle": "",
                "thumb": "", "img": "", "tags": en, "level": 0, "src": "workbench",
            })
    return out


# ---------- 2. 服装 ----------
def build_outfits():
    out, seen = [], set()

    # 来源A：workbench 服装类（3799）
    wb = load("workbench_tags_cn.json")
    if wb and isinstance(wb.get("tags"), list):
        for t in wb["tags"]:
            if t.get("cat") != "服装":
                continue
            en = nw(t.get("en"))
            if not en or en.lower() in seen:
                continue
            seen.add(en.lower())
            out.append({
                "id": en, "name": nw(t.get("zh")) or en, "zh": nw(t.get("zh")) or en,
                "tags": en, "level": 0, "src": "workbench",
                "group": nw(t.get("sub")) or "服装",
            })

    # 来源B：wardrobe 角色服装（2316 角色 × 多套）
    co = load("wardrobe_character_outfits.json")
    if co and isinstance(co.get("outfits"), dict):
        for char_key, entry in co["outfits"].items():
            if not isinstance(entry, dict):
                continue
            for idx, o in enumerate(entry.get("list") or []):
                if not isinstance(o, dict):
                    continue
                tagstr = nw(o.get("tags"))
                if not tagstr:
                    continue
                oid = f"{char_key}::{o.get('id') or idx}"
                if oid.lower() in seen:
                    continue
                seen.add(oid.lower())
                out.append({
                    "id": oid,
                    "name": nw(o.get("zh")) or (o.get("id") or f"服装{idx+1}"),
                    "zh": nw(o.get("zh")) or "",
                    "tags": tagstr,
                    "level": int(o.get("level") or 0),
                    "src": "wardrobe",
                    "group": char_key,
                })
    return out


# ---------- 3. 角色 ----------
def build_characters():
    out, seen = [], set()

    # 来源A：wardrobe 2390 角色（带作品、发型、瞳色、缩略图）
    wc = load("wardrobe_characters.json")
    if wc and isinstance(wc.get("characters"), list):
        for c in wc["characters"]:
            if not isinstance(c, dict):
                continue
            tag = nw(c.get("tag") or c.get("name"))
            if not tag or tag.lower() in seen:
                continue
            seen.add(tag.lower())
            out.append({
                "id": tag,
                "name": nw(c.get("zh")) or nw(c.get("name")) or tag,
                "zh": nw(c.get("zh")) or "",
                "en": nw(c.get("name")) or tag,
                "work": nw(c.get("work")) or "其他",
                "trigger": nw(c.get("trigger")) or tag,
                "pop": c.get("pop") or 0,
                "hair": nw(c.get("hair")),
                "eyes": nw(c.get("eyes")),
                "tags": nw(c.get("tags")),
                "thumb": c.get("thumb") or "",
                "level": 0,
                "src": "wardrobe",
            })

    # 来源B：workbench 角色类（2923）
    wb = load("workbench_tags_cn.json")
    if wb and isinstance(wb.get("tags"), list):
        for t in wb["tags"]:
            if t.get("cat") != "角色":
                continue
            en = nw(t.get("en"))
            if not en or en.lower() in seen:
                continue
            seen.add(en.lower())
            out.append({
                "id": en, "name": nw(t.get("zh")) or en, "zh": nw(t.get("zh")) or "",
                "en": en, "work": nw(t.get("sub")) or "其他", "trigger": en,
                "pop": 0, "hair": "", "eyes": "", "tags": en, "thumb": "",
                "level": 0, "src": "workbench",
            })
    return out


# ---------- 4. 场景 ----------
def build_scenes():
    out, seen = [], set()

    # 来源A：wardrobe 271 场景（带结构化 tags）
    sc = load("wardrobe_scenes.json")
    if sc and isinstance(sc.get("scenes"), list):
        for s in sc["scenes"]:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or ""
            if not sid or sid.lower() in seen:
                continue
            seen.add(sid.lower())
            tags = s.get("tags") or {}
            tagstr = ", ".join(nw(v) for v in tags.values() if v) if isinstance(tags, dict) else nw(tags)
            out.append({
                "id": sid,
                "name": nw(s.get("zh")) or sid,
                "zh": nw(s.get("zh")) or "",
                "desc": nw(s.get("desc")),
                "group": s.get("group") or "其他",
                "tags": tagstr,
                "extra": nw(s.get("extra")),
                "level": int(s.get("level") or 0),
                "src": "wardrobe",
            })

    # 来源B：workbench 场景类（1448）
    wb = load("workbench_tags_cn.json")
    if wb and isinstance(wb.get("tags"), list):
        for t in wb["tags"]:
            if t.get("cat") != "场景":
                continue
            en = nw(t.get("en"))
            if not en or en.lower() in seen:
                continue
            seen.add(en.lower())
            out.append({
                "id": en, "name": nw(t.get("zh")) or en, "zh": nw(t.get("zh")) or "",
                "desc": "", "group": nw(t.get("sub")) or "场景",
                "tags": en, "extra": "", "level": 0, "src": "workbench",
            })
    return out


# ---------- 5. 其他类 ----------
def build_cat(cat):
    out, seen = [], set()
    wb = load("workbench_tags_cn.json")
    if wb and isinstance(wb.get("tags"), list):
        for t in wb["tags"]:
            if t.get("cat") != cat:
                continue
            en = nw(t.get("en"))
            if not en or en.lower() in seen:
                continue
            seen.add(en.lower())
            out.append({
                "id": en, "name": nw(t.get("zh")) or en, "zh": nw(t.get("zh")) or "",
                "tags": en, "group": nw(t.get("sub")) or cat, "level": 0,
                "src": "workbench",
            })
    return out


def main():
    poses = build_poses()
    outfits = build_outfits()
    chars = build_characters()
    scenes = build_scenes()
    styles = build_cat("自定义")
    props = build_cat("道具")
    appearance = build_cat("外形")

    def dump(name, data):
        p = os.path.join(OUT, name)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"{name:22s} {len(data):6d} 条  {os.path.getsize(p)/1024/1024:.1f} MB")

    dump("poses.json", poses)
    dump("outfits.json", outfits)
    dump("characters.json", chars)
    dump("scenes.json", scenes)
    dump("styles.json", styles)
    dump("props.json", props)
    dump("appearance.json", appearance)

    # 作品分组（给前端做折叠菜单）
    works = {}
    for c in chars:
        w = c["work"]
        works.setdefault(w, 0)
        works[w] += 1
    with io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "counts": {
                "poses": len(poses), "outfits": len(outfits), "characters": len(chars),
                "scenes": len(scenes), "styles": len(styles), "props": len(props),
                "appearance": len(appearance),
            },
            "works": dict(sorted(works.items(), key=lambda kv: -kv[1])),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n作品分组: {len(works)} 个")
    top = sorted(works.items(), key=lambda kv: -kv[1])[:10]
    for w, n in top:
        print(f"  {w}: {n}")


if __name__ == "__main__":
    main()

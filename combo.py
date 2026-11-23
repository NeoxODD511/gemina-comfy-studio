"""一键搭配：随机组合 场景 × 角色 × 服装 × 姿势 × 画风 → 完整 prompt"""
import json, os, random, sys, io, re

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ASSET = r"F:\ComfyUI_Frontend\data\assets"
STAGE = r"F:\ComfyUI_Frontend\data\staging"

QUALITY = "masterpiece, best quality, very aesthetic, absurdres, highres"
NEGATIVE = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, "
            "fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, "
            "signature, watermark, username, blurry, artist name, bad proportions, "
            "deformed, disfigured, extra limbs, malformed limbs, mutated hands, "
            "poorly drawn face, poorly drawn hands, mutation, ugly, extra fingers")

# level=0 时排除的显式成人词（workbench 服装库没有分级，只能靠关键词拦）
NSFW_WORDS = [
    "panties", "lingerie", "underwear", "thong", "g-string", "gstring",
    "nude", "naked", "nipple", "areola", "topless", "bottomless",
    "see-through", "transparent clothes", "no bra", "no panties",
    "cameltoe", "cleavage", "underboob", "sideboob", "downblouse",
    "bondage", "bdsm", "shibari", "crotch", "pubic",
    "sex", "penis", "vagina", "cum", "masturbation", "orgasm",
    "bra only", "bra", "garter belt", "stockings only",
]


def is_safe(text, max_level):
    """level=0 时过滤显式成人词；level>=1 放宽"""
    if max_level >= 1:
        return True
    low = str(text or "").lower()
    return not any(w in low for w in NSFW_WORDS)


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def load_assets():
    d = {}
    for name in ("poses", "outfits", "characters", "scenes", "styles"):
        p = os.path.join(ASSET, name + ".json")
        d[name] = load(p) if os.path.isfile(p) else []
    return d


def load_raw_scenes():
    """读原始 scenes（保留 scene_nl / count_lock / tags 结构）"""
    p = os.path.join(STAGE, "wardrobe_scenes.json")
    if not os.path.isfile(p):
        return []
    j = load(p)
    return j.get("scenes") or []


def load_raw_outfits():
    p = os.path.join(STAGE, "wardrobe_character_outfits.json")
    if not os.path.isfile(p):
        return {}
    j = load(p)
    return j.get("outfits") or {}


def pick(lst, exclude=None):
    if not lst:
        return None
    if exclude and len(lst) > 1:
        cand = [x for x in lst if x.get("id") != exclude]
        if cand:
            lst = cand
    return random.choice(lst)


def list_combo_options(max_level=4):
    """返回指定等级下可供用户自主挑选的场景与画风列表"""
    A = load_assets()
    raw_scenes = load_raw_scenes()
    scenes = [
        {
            "id": s.get("id"),
            "zh": s.get("zh") or s.get("id"),
            "theme": s.get("theme") or "",
            "level": int(s.get("level") or 0),
            "count_lock": s.get("count_lock") or "",
        }
        for s in raw_scenes
        if int(s.get("level") or 0) <= max_level
    ]
    styles = [
        {"id": st.get("id") or st.get("name"), "name": st.get("name") or st.get("zh") or st.get("id")}
        for st in (A.get("styles") or [])
    ]
    return {"scenes": scenes, "styles": styles}


def make_combo(max_level=0, work="", use_pose=True, use_scene=True, seed=None, locked=None, disabled=None):
    if seed is not None:
        random.seed(seed)
    locked = locked if isinstance(locked, dict) else {}
    disabled = set(disabled or [])
    A = load_assets()
    raw_scenes = load_raw_scenes()
    raw_outfits = load_raw_outfits()

    # 1. 场景（支持用户锁定/指定 ID 或禁用）
    scene = None
    if "scene" not in disabled:
        if "scene" in locked and locked["scene"]:
            lv_s = locked["scene"]
            if isinstance(lv_s, dict) and lv_s.get("tags") is not None:
                scene = lv_s
            else:
                sid = lv_s.get("id") if isinstance(lv_s, dict) else str(lv_s)
                scene = next((s for s in raw_scenes if str(s.get("id")) == str(sid)), None)
        elif use_scene and raw_scenes:
            cand = [s for s in raw_scenes if int(s.get("level") or 0) <= max_level]
            scene = pick(cand)

    # 2. 角色（优先信息完整的 wardrobe 角色，兼容中英文作品名过滤）
    chars = A["characters"]
    norm_fn = None
    try:
        import server as _srv
        norm_fn = getattr(_srv, "_norm_work_cn", None)
    except Exception:
        pass
    if work:
        wl = work.casefold()
        chars = [c for c in chars
                 if str(c.get("work", "")).casefold() == wl
                 or (norm_fn and str(norm_fn(c.get("work", ""))).casefold() == wl)]
    rich_chars = [c for c in chars if c.get("src") == "wardrobe" and (c.get("hair") or c.get("eyes") or c.get("tags"))]
    if rich_chars:
        chars = rich_chars

    cl = str((scene or {}).get("count_lock") or "").strip()
    cl_low = cl.lower()
    is_two_girls = ("2girls" in cl_low) or ("yuri" in cl_low)
    is_multi = is_two_girls or ("1boy" in cl_low and "1girl" in cl_low) or ("multiple" in cl_low) or ("2boys" in cl_low)

    if is_two_girls or ("1girl" in cl_low):
        female_pool = [c for c in chars if "1boy" not in str(c.get("tags") or "").lower()]
        if female_pool:
            chars = female_pool

    def _resolve_char(val):
        if isinstance(val, dict) and (val.get("trigger") or val.get("id")):
            return val
        cid = str(val or "")
        return next((c for c in A["characters"] if str(c.get("id")) == cid), None)

    char = None
    if "character" not in disabled:
        if "character" in locked and locked["character"]:
            char = _resolve_char(locked["character"]) or pick(chars)
        else:
            char = pick(chars)

    char2 = None
    if "character2" not in disabled:
        if "character2" in locked and locked["character2"]:
            char2 = _resolve_char(locked["character2"])
        elif is_two_girls:
            char2 = pick(chars, exclude=(char or {}).get("id"))

    # 3. 服装（支持用户锁定/自选或禁用）
    outfit = None
    if "outfit" not in disabled:
        if "outfit" in locked and locked["outfit"]:
            lo = locked["outfit"]
            if isinstance(lo, dict) and (lo.get("tags") or lo.get("name")):
                outfit = lo
            else:
                oid = str(lo)
                outfit = next((o for o in A["outfits"] if str(o.get("id")) == oid), None)
        else:
            if char:
                ck = char.get("id") or ""
                entry = raw_outfits.get(ck)
                if entry and isinstance(entry, dict):
                    lst = [o for o in (entry.get("list") or [])
                           if isinstance(o, dict) and int(o.get("level") or 0) <= max_level]
                    if lst:
                        o = pick(lst)
                        if o:
                            outfit = {
                                "id": f"{ck}::{o.get('id')}",
                                "name": o.get("zh") or o.get("id"),
                                "tags": ", ".join(o.get("tags") or []),
                                "level": o.get("level", 0),
                                "src": "character",
                            }
            if not outfit:
                gen = [o for o in A["outfits"]
                       if "::" not in str(o.get("id", ""))
                       and o.get("tags")
                       and is_safe(str(o.get("name", "")) + " " + str(o.get("tags", "")), max_level)]
                o = pick(gen)
                if o:
                    outfit = {
                        "id": o.get("id"),
                        "name": o.get("name") or o.get("id"),
                        "tags": o.get("tags"),
                        "level": o.get("level", 0),
                        "src": "generic",
                    }

    # 4. 姿势（支持用户锁定/自选或禁用）
    pose = None
    if "pose" not in disabled:
        if "pose" in locked and locked["pose"]:
            lp = locked["pose"]
            if isinstance(lp, dict) and (lp.get("id") or lp.get("name")):
                pose = lp
            else:
                pid = str(lp)
                pose = next((p for p in A["poses"] if str(p.get("id")) == pid), None)
        elif use_pose:
            poses = A["poses"]
            cand = [p for p in poses if p.get("thumb")]
            pose = pick(cand) or pick(poses)

    # 5. 画风（支持用户锁定/自选或禁用）
    style_hint = None
    styles = A["styles"]
    if "style_hint" not in disabled:
        if "style_hint" in locked and locked["style_hint"]:
            ls = locked["style_hint"]
            if isinstance(ls, dict) and (ls.get("name") or ls.get("id")):
                style_hint = ls
            else:
                sid = str(ls)
                style_hint = next((st for st in styles if str(st.get("id")) == sid or str(st.get("name")) == sid), {"id": sid, "name": sid})
        elif styles:
            style_hint = pick(styles)

    # ---- 组装 prompt ----
    parts = []
    # 人数/性别锁：多人场景优先尊重 scene.count_lock（绝不硬写 solo！）
    if is_multi and cl:
        parts.append(cl)
    else:
        gender = None
        if char:
            ctags = str(char.get("tags") or "").lower()
            if "1boy" in ctags or "1boy," in ctags:
                gender = "1boy, solo"
            elif "1girl" in ctags:
                gender = "1girl, solo"
            elif "male" in ctags and "female" not in ctags:
                gender = "1boy, solo"
        if gender:
            parts.append(gender)
        elif cl and "1boy" not in cl_low:
            parts.append("solo")
        else:
            parts.append("solo")

    # 质量词
    parts.append(QUALITY)

    # 角色特征
    def _append_char_traits(ch):
        if not ch:
            return
        parts.append(ch.get("trigger") or ch.get("id"))
        if ch.get("hair"):
            parts.append(f"{ch['hair']} hair")
        if ch.get("eyes"):
            parts.append(f"{ch['eyes']} eyes")
        ctags_list = [s.strip() for s in str(ch.get("tags") or "").split(",") if s.strip()]
        trait_kws = ("ears", "tail", "halo", "wings", "horns", "horn", "fang", "ahoge")
        for tg in ctags_list:
            if any(k in tg.lower() for k in trait_kws):
                parts.append(tg)

    _append_char_traits(char)
    if char2:
        _append_char_traits(char2)

    # 服装
    if outfit and outfit.get("tags"):
        parts.append(outfit["tags"])

    # 场景结构化标签
    if scene:
        t = scene.get("tags") or {}
        order = ("shot_size", "viewpoint", "pose_base", "action", "place",
                 "weather", "light_fx", "texture_fx", "eye_gaze", "emotion",
                 "n_state", "n_exposure")
        for k in order:
            v = t.get(k)
            if v:
                parts.append(v)
        if scene.get("extra"):
            parts.append(scene["extra"])

    # 姿势标签（场景没给 pose_base 时才补进 prompt；否则姿势只作参考图）
    pose_conflict = bool(scene and (scene.get("tags") or {}).get("pose_base"))
    if pose and not pose_conflict:
        if pose.get("tags"):
            parts.append(pose["tags"])

    # 英文整句（Anima 支持整句，可选启用）
    scene_nl = (scene or {}).get("scene_nl", "") if scene else ""

    # 去重（保序）
    def _dedup_join(seq):
        seen_s = set()
        out = []
        for p in seq:
            for seg in [s.strip() for s in str(p).split(",") if s.strip()]:
                k = seg.casefold()
                if k not in seen_s:
                    seen_s.add(k)
                    out.append(seg)
        return ", ".join(out)

    prompt = _dedup_join(parts)

    # 双人分区域模式专用：全局提示词不含两位角色的个人特征（个人特征由左右独立框承载，防止主框+分区叠加出第3人）
    global_prompt = prompt
    if char and char2:
        g_parts = []
        if is_multi and cl:
            g_parts.append(cl)
        else:
            g_parts.append("2girls")
        g_parts.append(QUALITY)
        if outfit and outfit.get("tags"):
            g_parts.append(outfit["tags"])
        if scene:
            t = scene.get("tags") or {}
            for k in ("shot_size", "viewpoint", "pose_base", "action", "place",
                      "weather", "light_fx", "texture_fx", "eye_gaze", "emotion",
                      "n_state", "n_exposure"):
                if t.get(k):
                    g_parts.append(t[k])
            if scene.get("extra"):
                g_parts.append(scene["extra"])
        if pose and not pose_conflict and pose.get("tags"):
            g_parts.append(pose["tags"])
        global_prompt = _dedup_join(g_parts)

    return {
        "scene": scene,
        "character": char,
        "character2": char2,
        "outfit": outfit,
        "pose": pose,
        "pose_conflict": pose_conflict,
        "style_hint": style_hint,
        "prompt": prompt,
        "global_prompt": global_prompt,
        "negative": NEGATIVE,
        "level": int(scene.get("level") or 0) if scene else 0,
        "scene_nl": scene_nl,
    }


if __name__ == "__main__":
    print("=== 测试 3 套搭配（level<=0）===")
    for i in range(3):
        c = make_combo(max_level=0, seed=1000 + i)
        print(f"\n--- 第 {i+1} 套 (level={c['level']}) ---")
        print("场景:", (c["scene"] or {}).get("zh"), "|", (c["scene"] or {}).get("theme"))
        print("角色:", (c["character"] or {}).get("name"), "|", (c["character"] or {}).get("work"))
        print("服装:", (c["outfit"] or {}).get("name"))
        print("姿势:", (c["pose"] or {}).get("name"))
        print("prompt:", c["prompt"][:300])

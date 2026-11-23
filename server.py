"""
ComfyUI 前端服务（独立网页，零第三方依赖）
- 端口 8189
- 功能：模型/LoRA 选择、5 类 LoRA 管理、姿势/衣服/角色选择、prompt 组装、提交生成、GitHub 搜索
- 只调用 ComfyUI 的 /prompt /history /view /object_info API，不改其源码
"""
import json, os, sys, time, mimetypes, threading, urllib.parse, urllib.request, re, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
PORT = int(os.environ.get("FRONTEND_PORT", "8189"))
LORA_DIR = os.environ.get("LORA_DIR", r"F:\ComfyUI_Models\loras")
MODEL_DIR = os.environ.get("MODEL_DIR", r"F:\ComfyUI_Models\anima\diffusion_models")
COMFY_UI_DIR = os.environ.get("COMFY_UI_DIR", r"F:\ComfyUI\app\comfyui-master")
ASSET_DIR = os.path.join(DATA, "assets")          # 姿势/衣服/角色 词库
os.makedirs(ASSET_DIR, exist_ok=True)
DESKTOP_OUT_DIR = os.environ.get("DESKTOP_OUT_DIR", r"C:\Users\Administrator\Desktop\CpmfyUI出图")
os.makedirs(DESKTOP_OUT_DIR, exist_ok=True)
_SAVED_DESKTOP_IMAGES = set()

sys.path.insert(0, ROOT)
import lora_index
import combo


# ---------------- 工具 ----------------
def comfy_get(path, timeout=10):
    url = COMFY.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def comfy_post(path, payload, timeout=30):
    url = COMFY.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode("utf-8").strip()
        return json.loads(txt) if txt else {"ok": True}


def json_resp(handler, obj, status=200):
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def text_resp(handler, text, ctype="text/plain; charset=utf-8", status=200):
    raw = text.encode("utf-8") if isinstance(text, str) else text
    handler.send_response(status)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


# ---------------- 词库 ----------------
DEFAULT_POSES = [
    {"id": "standing", "name": "站立", "tags": "standing, full body, looking at viewer"},
    {"id": "sitting", "name": "坐姿", "tags": "sitting, on chair, looking at viewer"},
    {"id": "lying", "name": "躺姿", "tags": "lying, on back, looking at viewer"},
    {"id": "kneeling", "name": "跪姿", "tags": "kneeling, looking at viewer"},
    {"id": "walking", "name": "行走", "tags": "walking, motion, from side"},
    {"id": "running", "name": "奔跑", "tags": "running, dynamic pose, motion blur"},
    {"id": "jumping", "name": "跳跃", "tags": "jumping, mid-air, dynamic pose"},
    {"id": "leaning", "name": "倚靠", "tags": "leaning against wall, casual"},
    {"id": "crouching", "name": "蹲姿", "tags": "crouching, looking at viewer"},
    {"id": "arms_crossed", "name": "抱臂", "tags": "crossed arms, confident, standing"},
    {"id": "hand_on_hip", "name": "叉腰", "tags": "hand on hip, standing, confident"},
    {"id": "looking_back", "name": "回眸", "tags": "looking back, from behind, turning head"},
    {"id": "close_up", "name": "特写", "tags": "close-up, portrait, face focus"},
    {"id": "upper_body", "name": "上半身", "tags": "upper body, portrait"},
    {"id": "full_body", "name": "全身", "tags": "full body, standing"},
]

DEFAULT_OUTFITS = [
    {"id": "school_uniform", "name": "校服", "tags": "school uniform, serafuku, pleated skirt"},
    {"id": "maid", "name": "女仆装", "tags": "maid outfit, apron, frilled headdress"},
    {"id": "kimono", "name": "和服", "tags": "kimono, obi, traditional japanese clothes"},
    {"id": "hanfu", "name": "汉服", "tags": "hanfu, chinese clothes, long sleeves"},
    {"id": "suit", "name": "西装", "tags": "business suit, necktie, formal"},
    {"id": "casual", "name": "休闲", "tags": "casual wear, t-shirt, jeans"},
    {"id": "hoodie", "name": "卫衣", "tags": "hoodie, casual, loose clothes"},
    {"id": "dress", "name": "连衣裙", "tags": "dress, sleeveless dress"},
    {"id": "swimsuit", "name": "泳装", "tags": "swimsuit, one-piece swimsuit"},
    {"id": "armor", "name": "铠甲", "tags": "armor, breastplate, fantasy armor"},
    {"id": "coat", "name": "大衣", "tags": "long coat, trench coat"},
    {"id": "gothic", "name": "哥特", "tags": "gothic lolita, frills, dark clothes"},
    {"id": "sportswear", "name": "运动装", "tags": "sportswear, track jacket, shorts"},
    {"id": "nurse", "name": "护士服", "tags": "nurse uniform, white dress"},
    {"id": "santa", "name": "圣诞装", "tags": "santa costume, red dress"},
    {"id": "none", "name": "不指定", "tags": ""},
]


ASSET_CATS = {
    "poses": "poses.json",
    "outfits": "outfits.json",
    "characters": "characters.json",
    "scenes": "scenes.json",
    "styles": "styles.json",
    "props": "props.json",
    "appearance": "appearance.json",
}

_ASSET_CACHE = {}

# 姿势敏感分类/体系（用于独立分区）
POSE_SENSITIVE_CATS = {
    "性感・大胆系", "挤胸・强调事业线系", "正常位（传教士）", "后入位",
    "骑乘位", "背向坐位", "立位贴身", "坐位贴身", "面对面坐位",
    "贴身", "贴脸系",
}
POSE_SENSITIVE_SYSTEMS = {"双人缠绵"}   # 性感系里多是正常站姿，不整体标记



WORK_CN_MAP = {
    "kantai collection": "舰队Collection",
    "goddess of victory: nikke": "胜利女神：NIKKE",
    "touhou": "东方Project",
    "hololive": "Hololive",
    "blue archive": "蔚蓝档案",
    "idolmaster": "偶像大师",
    "fate": "Fate / FGO",
    "fate/grand order": "Fate / FGO",
    "fate (series)": "Fate / FGO",
    "umamusume": "赛马娘",
    "赛马娘": "赛马娘",
    "honkai: star rail": "崩坏：星穹铁道",
    "崩坏星穹铁道": "崩坏：星穹铁道",
    "wuthering waves": "鸣潮",
    "arknights": "明日方舟",
    "明日方舟": "明日方舟",
    "genshin impact": "原神",
    "原神": "原神",
    "zenless zone zero": "绝区零",
    "azur lane": "碧蓝航线",
    "precure": "光之美少女",
    "girls und panzer": "少女与战车",
    "love live!": "Love Live!",
    "fire emblem": "火焰纹章",
    "kemono friends": "兽娘动物园",
    "nijisanji": "彩虹社",
    "girls' frontline": "少女前线",
    "persona 5: the phantom x": "女神异闻录",
    "persona": "女神异闻录",
    "vocaloid": "VOCALOID / V家",
    "final fantasy": "最终幻想",
    "danganronpa (series)": "弹丸论破",
    "bishoujo senshi sailor moon": "美少女战士",
    "granblue fantasy": "碧蓝幻想",
    "bang dream!": "BanG Dream!",
    "bang dream": "BanG Dream!",
    "mahou shoujo madoka magica": "魔法少女小圆",
    "honkai (series)": "崩坏系列",
    "world witches series": "强袭魔女",
    "monogatari (series)": "物语系列",
    "league of legends": "英雄联盟",
    "lyrical nanoha": "魔法少女奈叶",
    "toaru majutsu no index": "魔法禁书目录",
    "chainsaw man": "电锯人",
    "电锯人": "电锯人",
    "gochuumon wa usagi desu ka?": "请问您今天要来点兔子吗？",
    "xenoblade": "异度神剑",
    "gundam": "机动战士高达",
    "eva": "新世纪福音战士 EVA",
    "neon genesis evangelion": "新世纪福音战士 EVA",
    "k-on!": "轻音少女",
    "street fighter": "街头霸王",
    "princess connect!": "公主连结",
    "splatoon": "斯普拉遁",
    "guilty gear": "罪恶装备",
    "umineko no naku koro ni": "海猫鸣泣之时",
    "senki zesshou symphogear": "战姬绝唱",
    "yuru yuri": "摇曳百合",
    "suzumiya haruhi no yuuutsu": "凉宫春日的忧郁",
    "kill la kill": "斩服少女",
    "pokemon": "宝可梦",
    "re:zero": "Re:从零开始的异世界生活",
    "sword art online": "刀剑神域",
    "spy x family": "间谍过家家",
    "bocchi the rock!": "孤独摇滚！",
    "frieren": "葬送的芙莉莲",
    "sousou no frieren": "葬送的芙莉莲",
    "overwatch": "守望先锋",
    "nier (series)": "尼尔系列",
    "nier:automata": "尼尔：机械纪元",
    "punishing: gray raven": "战双帕弥什",
    "reverse:1999": "重返未来：1999",
    "path to nowhere": "无期迷途",
    "mahjong soul": "雀魂",
    "snowbreak: containment zone": "尘白禁区",
    "limbus company": "边狱巴士",
    "project sekai": "世界计划",
    "vocaloid / v家": "VOCALOID / V家",
}


def _norm_work_cn(w):
    raw = str(w or "").strip()
    if not raw:
        return "其他"
    return WORK_CN_MAP.get(raw.casefold(), raw)


def _char_info_map():
    chars = _load_cat("characters")
    return {
        str(c.get("id", "")): {
            "name": c.get("name") or c.get("zh") or c.get("id") or "",
            "work": c.get("work") or "",
            "pop": int(c.get("pop") or 0),
        }
        for c in chars
    }


def _load_cat(cat):
    """读取某一类词库（带内存缓存）"""
    if cat in _ASSET_CACHE:
        return _ASSET_CACHE[cat]
    fname = ASSET_CATS.get(cat)
    data = []
    if fname:
        p = os.path.join(ASSET_DIR, fname)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    data = loaded
            except Exception:
                data = []
    # 内置常用项：
    #   - 与外部词库同 id 的跳过（避免重复）
    #   - 不重复的排到最后（纯标签、无图）
    if cat == "poses":
        existing = {str(x.get("id", "")).lower() for x in data}
        extras = [dict(x, builtin=True, no_thumb=True) for x in DEFAULT_POSES
                  if str(x.get("id", "")).lower() not in existing]
        data = data + extras
        # 标记敏感姿势
        for it in data:
            c = str(it.get("cat", ""))
            sysn = str(it.get("system", ""))
            it["sensitive"] = (c in POSE_SENSITIVE_CATS) or (sysn in POSE_SENSITIVE_SYSTEMS)
    elif cat == "outfits":
        existing = {str(x.get("id", "")).lower() for x in data}
        extras = [dict(x, builtin=True) for x in DEFAULT_OUTFITS
                  if str(x.get("id", "")).lower() not in existing]
        data = extras + data
        # 去重：相同 tags 的只留第一个（保留有 group 分类的）
        seen_tags = set()
        dedup = []
        for it in data:
            t = str(it.get("tags", "")).strip().lower()
            if not t:
                dedup.append(it)
                continue
            if t in seen_tags:
                continue
            seen_tags.add(t)
            dedup.append(it)
        data = dedup
        # 标记敏感分组（Lv0 时可过滤）+ 角色专属服装关联中文角色名与所属作品
        cmap = _char_info_map()
        for it in data:
            g = str(it.get("group", ""))
            it["sensitive"] = g in ("情趣", "内衣", "泳装")
            if it.get("src") == "wardrobe":
                info = cmap.get(g) or {}
                it["char_name"] = info.get("name") or g.replace("_", " ")
                it["char_work"] = info.get("work") or ""
                it["char_pop"] = info.get("pop") or 0
    elif cat == "characters":
        # 规范作品中文名并保留原始 work_raw，按人气降序
        for it in data:
            raw_w = str(it.get("work") or "").strip()
            it["work_raw"] = raw_w
            it["work"] = _norm_work_cn(raw_w)
        data = sorted(data, key=lambda x: -(x.get("pop") or 0))
    _ASSET_CACHE[cat] = data
    return data


def load_asset_library():
    """全量加载（兼容旧调用）"""
    return {cat: _load_cat(cat) for cat in ASSET_CATS}


def query_assets(cat=None, q=None, group=None, offset=0, limit=0, collapsed=False, safe=False, part="all"):
    """分页/搜索/分组查询；collapsed=True 时把多视角姿势聚合为一组"""
    if cat and cat in ASSET_CATS:
        items = _load_cat(cat)
        if q:
            ql = q.lower()
            items = [x for x in items if ql in (
                str(x.get("id", "")) + " " + str(x.get("name", "")) + " "
                + str(x.get("char_name", "")) + " " + str(x.get("char_work", "")) + " "
                + str(x.get("tags", "")) + " " + str(x.get("trigger", "")) + " "
                + str(x.get("work", "")) + " " + str(x.get("work_raw", "")) + " "
                + str(x.get("group", "")) + " "
                + str(x.get("cat", "")) + " " + str(x.get("system", ""))
            ).lower()]
        if group:
            gl = group.casefold()
            items = [x for x in items
                     if str(x.get("group", "")).casefold() == gl
                     or str(x.get("work", "")).casefold() == gl
                     or str(x.get("work_raw", "")).casefold() == gl
                     or str(x.get("system", "")).casefold() == gl
                     or str(x.get("cat", "")).casefold() == gl
                     or str(x.get("src", "")).casefold() == gl]
            if cat == "outfits" and gl == "wardrobe":
                items = sorted(items, key=lambda x: -(x.get("char_pop") or 0))
        # 敏感内容（服装的情趣/内衣/泳聚类）：可单独取
        if part in ("normal", "sensitive") and cat in ("outfits", "poses"):
            want = (part == "sensitive")
            items = [x for x in items if bool(x.get("sensitive")) == want]
        elif safe and cat in ("outfits", "poses"):
            normal = [x for x in items if not x.get("sensitive")]
            sensitive = [x for x in items if x.get("sensitive")]
            items = normal + sensitive
        # 姿势多视角聚合
        if collapsed and cat == "poses":
            import re as _re
            groups = {}
            order = []
            for it in items:
                pid = str(it.get("id", ""))
                gid = _re.sub(r"_(front|high|low|side|diag)$", "", pid)
                if gid not in groups:
                    groups[gid] = {
                        "id": gid,
                        "name": it.get("name") or gid,
                        "cat": it.get("cat", ""),
                        "system": it.get("system", ""),
                        "src": it.get("src", ""),
                        "angles": [],
                    }
                    order.append(gid)
                groups[gid]["angles"].append({
                    "id": pid,
                    "angle": it.get("angle", ""),
                    "thumb": it.get("thumb", ""),
                    "img": it.get("img", ""),
                })
            items = [groups[g] for g in order]
        total = len(items)
        if limit and limit > 0:
            page = items[offset:offset + limit]
        elif offset:
            page = items[offset:]
        else:
            page = items
        return {"cat": cat, "total": total, "offset": offset,
                "collapsed": collapsed, "items": page}

    # 无 cat：返回各类统计 + 分组信息
    stats = {}
    for c in ASSET_CATS:
        stats[c] = len(_load_cat(c))
    # 角色作品分组（合并大小写重复）
    works = {}
    canon = {}
    for ch in _load_cat("characters"):
        w = (ch.get("work") or "其他").strip()
        key = w.casefold()
        if key not in canon:
            canon[key] = w
        else:
            # 保留出现次数多的写法优先，这里简单取更长的（通常更规范）
            if len(w) > len(canon[key]):
                canon[key] = w
        works[key] = works.get(key, 0) + 1
    works_sorted = {}
    for key, n in sorted(works.items(), key=lambda kv: -kv[1]):
        works_sorted[canon[key]] = n
    # 姿势体系分组
    pose_sys = {}
    for pz in _load_cat("poses"):
        s = pz.get("system") or "其他"
        pose_sys[s] = pose_sys.get(s, 0) + 1
    return {
        "stats": stats,
        "works": works_sorted,
        "pose_systems": pose_sys,
        "cats": list(ASSET_CATS.keys()),
    }


# ---------------- 生成 ----------------
# 质量词：后端追加，前端不显示也不提交
DEFAULT_POSITIVE = ("masterpiece, absurdres, very aesthetic, best quality, highres, "
                    "newest, score_9, score_8, ultra detailed")
DEFAULT_NEGATIVE = ("worst quality, low quality, lowres, score_1, score_2, score_3, "
                    "bad anatomy, watermark, artist name")


def _append_tags(base, extra):
    """在已有提示词后追加标签；去重但不覆盖用户已写内容"""
    base = (base or "").strip()
    have = {s.strip().casefold() for s in base.split(",") if s.strip()}
    add = [s.strip() for s in extra.split(",")
           if s.strip() and s.strip().casefold() not in have]
    if not add:
        return base
    return (base + ", " + ", ".join(add)) if base else ", ".join(add)


def build_prompt_payload(req):
    """
    req: {
      model: "anima\\xxx.safetensors",
      positive, negative,
      width, height, steps, cfg, sampler, scheduler, seed,
      loras: [{file, weight}, ...],
      clip_name, vae_name
    }
    """
    model = req.get("model")
    clip_name = req.get("clip_name", "anima\\qwen_3_06b_base.safetensors")
    vae_name = req.get("vae_name", "anima\\qwen_image_vae.safetensors")
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model,
              "weight_dtype": req.get("weight_dtype", "fp8_e4m3fn")}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": clip_name, "type": "stable_diffusion", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae_name}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {
            "width": int(req.get("width", 832)), "height": int(req.get("height", 1216)), "batch_size": 1}},
    }
    # LoRA 链
    loras = req.get("loras") or []
    model_ref = ["1", 0]
    clip_ref = ["2", 0]
    nid = 10
    for i, l in enumerate(loras):
        f = l.get("file")
        w = float(l.get("weight", 0.7))
        if not f:
            continue
        node = str(nid)
        g[node] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": f, "strength_model": w, "strength_clip": w,
                "model": model_ref, "clip": clip_ref,
            },
        }
        model_ref = [node, 0]
        clip_ref = [node, 1]
        nid += 1

    positive = _append_tags(req.get("positive", ""), DEFAULT_POSITIVE)
    negative = _append_tags(req.get("negative", ""), DEFAULT_NEGATIVE)
    # 纯女性场景自动防串台护盾（当正面未出现男性或 futa 相关词时，在负面自动压制）
    _pos_low = positive.lower()
    if not any(k in _pos_low for k in ("1boy", "boys", "male", "hetero", "futanari", "futa", "penis", "dildo", "trap")):
        negative = _append_tags(negative, "futanari, penis")
    base_model_ref = model_ref

    # 姿势图 LLLite 线稿控图（支持单人 & 双人姿势图）
    pose_ctrl = req.get("pose_ctrl") or {}
    if isinstance(pose_ctrl, dict) and pose_ctrl.get("enabled") and pose_ctrl.get("pose_id"):
        w_px = int(req.get("width", 832))
        h_px = int(req.get("height", 1216))
        p_str = float(pose_ctrl.get("strength", 0.85))
        p_end = float(pose_ctrl.get("end_percent", 0.85))
        g["60"] = {"class_type": "PoseGallery", "inputs": {"pose_id": str(pose_ctrl["pose_id"]), "language": "zh"}}
        g["61"] = {"class_type": "AnimeLineArtPreprocessor", "inputs": {"image": ["60", 0], "resolution": 1024}}
        g["62"] = {"class_type": "ImageScale", "inputs": {
            "image": ["61", 0], "upscale_method": "lanczos", "width": w_px, "height": h_px, "crop": "center"}}
        g["63"] = {"class_type": "ModelPatchLoader", "inputs": {"name": "ab1_lineart.safetensors"}}
        g["64"] = {"class_type": "AnimaLLLiteApply", "inputs": {
            "model": model_ref, "model_patch": ["63", 0], "image": ["62", 0],
            "strength": p_str, "start_percent": 0.0, "end_percent": p_end}}
        model_ref = ["64", 0]
        negative = _append_tags(negative, "lineart, monochrome, sketch, grid, halftone")

    g["20"] = {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": clip_ref}}
    g["21"] = {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": clip_ref}}
    pos_ref = ["20", 0]

    # 双人分区域独立提示词隔离（ConditioningSetAreaPercentage + ConditioningCombine，防止光环/发色串台）
    dual = req.get("dual_char") or {}
    if isinstance(dual, dict) and dual.get("enabled"):
        c1 = str(dual.get("char1") or "").strip()
        c2 = str(dual.get("char2") or "").strip()
        if c1 or c2:
            # 光环防串台护盾：一方有 halo 而另一方没有时，自动为另一方补 no halo
            has_h1 = "halo" in c1.lower() and "no halo" not in c1.lower()
            has_h2 = "halo" in c2.lower() and "no halo" not in c2.lower()
            if has_h1 and not has_h2 and c2:
                c2 = _append_tags(c2, "no halo")
            elif has_h2 and not has_h1 and c1:
                c1 = _append_tags(c1, "no halo")
            layout = dual.get("layout", "lr")
            d_str = float(dual.get("strength", 0.85))
            # 防 3 人护盾：双人分区时自动在负面词压制第 3 人
            if "3girls" not in positive.lower() and "multiple girls" not in positive.lower():
                negative = _append_tags(negative, "3girls, extra person, crowd")
                g["21"] = {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": clip_ref}}
            # Anima 内部采用 5D Cosmos Latent (B, C, T=1, H, W)，必须用 ConditioningSetAreaPercentageVideo (带 temporal/z)
            if layout == "tb":
                a1 = {"x": 0.0, "y": 0.0, "z": 0.0, "width": 1.0, "height": 0.52, "temporal": 1.0, "strength": d_str}
                a2 = {"x": 0.0, "y": 0.48, "z": 0.0, "width": 1.0, "height": 0.52, "temporal": 1.0, "strength": d_str}
            else:
                a1 = {"x": 0.0, "y": 0.0, "z": 0.0, "width": 0.52, "height": 1.0, "temporal": 1.0, "strength": d_str}
                a2 = {"x": 0.48, "y": 0.0, "z": 0.0, "width": 0.52, "height": 1.0, "temporal": 1.0, "strength": d_str}
            if c1:
                g["70"] = {"class_type": "CLIPTextEncode", "inputs": {"text": c1, "clip": clip_ref}}
                g["71"] = {"class_type": "ConditioningSetAreaPercentageVideo", "inputs": {"conditioning": ["70", 0], **a1}}
                g["74"] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": pos_ref, "conditioning_2": ["71", 0]}}
                pos_ref = ["74", 0]
            if c2:
                g["72"] = {"class_type": "CLIPTextEncode", "inputs": {"text": c2, "clip": clip_ref}}
                g["73"] = {"class_type": "ConditioningSetAreaPercentageVideo", "inputs": {"conditioning": ["72", 0], **a2}}
                g["75"] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": pos_ref, "conditioning_2": ["73", 0]}}
                pos_ref = ["75", 0]

    seed_val = int(req.get("seed", 0)) or int(time.time() * 1000) % 2147483647
    g["30"] = {"class_type": "KSampler", "inputs": {
        "seed": seed_val,
        "steps": int(req.get("steps", 28)),
        "cfg": float(req.get("cfg", 4.0)),
        "sampler_name": req.get("sampler", "euler"),
        "scheduler": req.get("scheduler", "simple"),
        "denoise": 1.0,
        "model": model_ref,
        "positive": pos_ref,
        "negative": ["21", 0],
        "latent_image": ["4", 0],
    }}
    latent_out = ["30", 0]
    hires = req.get("hires") or {}
    if isinstance(hires, dict) and hires.get("enabled"):
        scale = float(hires.get("scale", 1.5))
        if scale and abs(scale - 1.0) > 1e-3:
            g["35"] = {"class_type": "LatentUpscaleBy", "inputs": {
                "samples": latent_out,
                "upscale_method": hires.get("method", "nearest-exact"),
                "scale_by": scale,
            }}
            latent_out = ["35", 0]
        g["36"] = {"class_type": "KSampler", "inputs": {
            "seed": seed_val,
            "steps": int(hires.get("steps", 15)),
            "cfg": float(hires.get("cfg", 7.0)),
            "sampler_name": req.get("sampler", "euler"),
            "scheduler": req.get("scheduler", "simple"),
            "denoise": float(hires.get("denoise", 0.7)),
            "model": model_ref,
            "positive": pos_ref,
            "negative": ["21", 0],
            "latent_image": latent_out,
        }}
        latent_out = ["36", 0]
    g["40"] = {"class_type": "VAEDecode", "inputs": {"samples": latent_out, "vae": ["3", 0]}}
    img_out = ["40", 0]

    # 自动修脸（ComfyUI-Impact-Pack FaceDetailer + face_yolov8m.pt，全身/双人防糊脸神器）
    fd = req.get("face_detailer") or {}
    if isinstance(fd, dict) and fd.get("enabled"):
        g["80"] = {
            "class_type": "UltralyticsDetectorProvider",
            "inputs": {"model_name": fd.get("model_name", "bbox/face_yolov8m.pt")},
        }
        g["81"] = {
            "class_type": "FaceDetailer",
            "inputs": {
                "image": img_out,
                "model": base_model_ref,
                "clip": clip_ref,
                "vae": ["3", 0],
                "guide_size": 512,
                "guide_size_for": True,
                "max_size": 1024,
                "seed": seed_val,
                "steps": int(fd.get("steps", 14)),
                "cfg": float(req.get("cfg", 4.0)),
                "sampler_name": req.get("sampler", "euler"),
                "scheduler": req.get("scheduler", "simple"),
                "positive": ["20", 0],
                "negative": ["21", 0],
                "denoise": float(fd.get("denoise", 0.4)),
                "feather": 5,
                "noise_mask": True,
                "force_inpaint": True,
                "bbox_threshold": 0.5,
                "bbox_dilation": 10,
                "bbox_crop_factor": 3.0,
                "sam_detection_hint": "center-1",
                "sam_dilation": 0,
                "sam_threshold": 0.93,
                "sam_bbox_expansion": 0,
                "sam_mask_hint_threshold": 0.7,
                "sam_mask_hint_use_negative": "False",
                "drop_size": 10,
                "bbox_detector": ["80", 0],
                "wildcard": "",
                "cycle": 1,
            },
        }
        img_out = ["81", 0]

    g["50"] = {"class_type": "SaveImage", "inputs": {
        "filename_prefix": req.get("prefix", "frontend"), "images": img_out}}
    return g


def load_workflow_presets():
    p = os.path.join(ROOT, "workflows", "presets.json")
    if not os.path.isfile(p):
        return {"items": []}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"items": [], "error": str(e)}


def _mirror_history_images(history_dict):
    """出图完成时自动复制一份高清原图到桌面 CpmfyUI出图 目录"""
    if not isinstance(history_dict, dict):
        return
    try:
        os.makedirs(DESKTOP_OUT_DIR, exist_ok=True)
        for entry in history_dict.values():
            if not isinstance(entry, dict):
                continue
            outputs = entry.get("outputs") or {}
            for node_out in outputs.values():
                for im in (node_out.get("images") or []):
                    fn = im.get("filename")
                    if not fn:
                        continue
                    sub = im.get("subfolder") or ""
                    tp = im.get("type") or "output"
                    key = (fn, sub, tp)
                    if key in _SAVED_DESKTOP_IMAGES:
                        continue
                    dst = os.path.join(DESKTOP_OUT_DIR, os.path.basename(fn))
                    if os.path.isfile(dst):
                        _SAVED_DESKTOP_IMAGES.add(key)
                        continue
                    qs = urllib.parse.urlencode({"filename": fn, "subfolder": sub, "type": tp})
                    url = COMFY.rstrip("/") + "/view?" + qs
                    with urllib.request.urlopen(url, timeout=15) as r:
                        raw = r.read()
                    with open(dst, "wb") as f:
                        f.write(raw)
                    _SAVED_DESKTOP_IMAGES.add(key)
    except Exception:
        pass


# ---------------- 路由 ----------------
class Handler(__import__("http.server", fromlist=["BaseHTTPRequestHandler"]).BaseHTTPRequestHandler):
    server_version = "ComfyFrontend/1.0"

    def log_message(self, fmt, *args):
        pass

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path = p.path
        qs = urllib.parse.parse_qs(p.query or "")

        if path == "/" or path == "/index.html":
            return self._serve_file(os.path.join(WEB, "index.html"), "text/html; charset=utf-8")

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            safe = os.path.normpath(os.path.join(WEB, rel))
            if not safe.startswith(WEB):
                return json_resp(self, {"error": "forbidden"}, 403)
            mt, _ = mimetypes.guess_type(safe)
            return self._serve_file(safe, mt or "application/octet-stream")

        if path == "/api/status":
            try:
                st = comfy_get("/system_stats", timeout=5)
                return json_resp(self, {"comfy": "online", "stats": st})
            except Exception as e:
                return json_resp(self, {"comfy": "offline", "error": str(e)})

        if path == "/api/workflows":
            return json_resp(self, load_workflow_presets())

        if path == "/api/models":
            try:
                oi = comfy_get("/object_info/UNETLoader")
                names = oi["UNETLoader"]["input"]["required"]["unet_name"][0]
                return json_resp(self, {"items": names})
            except Exception as e:
                return json_resp(self, {"items": [], "error": str(e)})

        if path == "/api/loras":
            try:
                oi = comfy_get("/object_info/LoraLoader")
                names = oi["LoraLoader"]["input"]["required"]["lora_name"][0]
            except Exception:
                names = []
            idx_path = os.path.join(DATA, "lora-index.json")
            idx = {}
            if os.path.isfile(idx_path):
                try:
                    with open(idx_path, encoding="utf-8") as f:
                        idx = json.load(f)
                except Exception:
                    idx = {}
            # 索引里 file 用正斜杠，ComfyUI 用反斜杠
            by_file = {it["file"].replace("/", "\\"): it for it in idx.get("items", [])}
            by_base = {}
            for it in idx.get("items", []):
                key = it["file"].replace("/", "\\")
                by_base.setdefault(key.lower(), it)
                by_base.setdefault(os.path.basename(key).lower(), it)
            items = []
            for n in names:
                key = n.replace("/", "\\")
                meta = by_file.get(key) or by_base.get(key.lower()) or by_base.get(os.path.basename(key).lower()) or {}
                parts = key.split("\\")
                # 从路径推断 base
                if parts[0] == "_realistic":
                    base = parts[1] if len(parts) > 1 else "unknown"
                    isolated = True
                else:
                    base = parts[0] if parts else "unknown"
                    isolated = bool(meta.get("isolated", False))
                catdir = parts[-2] if len(parts) >= 2 else ""
                category = meta.get("category") or (catdir if catdir in lora_index.CATEGORIES else "x")
                items.append({
                    "file": n,
                    "name": meta.get("name") or os.path.basename(key),
                    "cn": meta.get("cn") or "",
                    "desc": meta.get("desc") or "",
                    "warn": meta.get("warn") or "",
                    "weight_hint": meta.get("weight_hint") or "",
                    "base": base,
                    "category": category,
                    "isolated": isolated,
                    "weight": meta.get("weight", 0.5),
                    "trigger": meta.get("trigger", ""),
                    "note": meta.get("note", ""),
                    "size_mb": meta.get("size_mb"),
                })
            return json_resp(self, {
                "items": items,
                "categories": lora_index.CATEGORIES,
                "bases": lora_index.BASES,
                "isolated_root": lora_index.ISOLATED_ROOT,
            })

        if path == "/api/combo/options":
            try:
                max_level = int((qs.get("level") or ["4"])[0])
                return json_resp(self, combo.list_combo_options(max_level=max_level))
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/combo":
            try:
                max_level = int((qs.get("level") or ["0"])[0])
                work = (qs.get("work") or [""])[0]
                seed_raw = (qs.get("seed") or [""])[0]
                seed = int(seed_raw) if seed_raw else None
                use_pose = (qs.get("pose") or ["1"])[0] != "0"
                use_scene = (qs.get("scene") or ["1"])[0] != "0"
                r = combo.make_combo(max_level=max_level, work=work,
                                     use_pose=use_pose, use_scene=use_scene, seed=seed)
                return json_resp(self, r)
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/assets":
            try:
                cat = (qs.get("cat") or [None])[0]
                q = (qs.get("q") or [None])[0]
                group = (qs.get("group") or [None])[0]
                offset = int((qs.get("offset") or ["0"])[0])
                limit = int((qs.get("limit") or ["0"])[0])
                collapsed = (qs.get("collapsed") or ["0"])[0] == "1"
                safe = (qs.get("safe") or ["0"])[0] == "1"
                part = (qs.get("part") or ["all"])[0]
            except Exception:
                cat = q = group = None
                offset = limit = 0
                collapsed = False
                safe = False
                part = "all"
            if cat or q or group:
                return json_resp(self, query_assets(cat=cat, q=q, group=group,
                                                    offset=offset, limit=limit,
                                                    collapsed=collapsed, safe=safe, part=part))
            return json_resp(self, query_assets())

        if path == "/api/history":
            pid = (qs.get("id") or [""])[0]
            try:
                h = comfy_get("/history/" + pid, timeout=10)
                _mirror_history_images(h)
                return json_resp(self, h)
            except Exception as e:
                return json_resp(self, {"error": str(e)})

        if path == "/api/queue":
            try:
                q = comfy_get("/queue", timeout=5)
                if isinstance(q, dict):
                    q["progress"] = dict(_PROGRESS)
                return json_resp(self, q)
            except Exception as e:
                return json_resp(self, {"error": str(e)})

        # ---- pose-gallery 图片静态服务 ----
        if path.startswith("/pose-thumb/") or path.startswith("/pose-img/"):
            sub = "thumbs" if path.startswith("/pose-thumb/") else "img"
            fname = os.path.basename(path.split("/", 2)[-1])
            base_dir = os.path.join(
                COMFY_UI_DIR, "custom_nodes", "comfyui-pose-gallery", "library", sub)
            full = os.path.join(base_dir, fname)
            if not os.path.isfile(full):
                return json_resp(self, {"error": "not found", "file": fname}, 404)
            ext = os.path.splitext(fname)[1].lower()
            ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".webp": "image/webp"}.get(ext, "application/octet-stream")
            try:
                with open(full, "rb") as fp:
                    data = fp.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                return json_resp(self, {"error": str(e)}, 500)

        if path == "/api/image":
            fn = (qs.get("filename") or [""])[0]
            sub = (qs.get("subfolder") or [""])[0]
            typ = (qs.get("type") or ["output"])[0]
            try:
                url = COMFY.rstrip("/") + "/view?" + urllib.parse.urlencode(
                    {"filename": fn, "subfolder": sub, "type": typ})
                with urllib.request.urlopen(url, timeout=20) as r:
                    data = r.read()
                return text_resp(self, data, "image/png")
            except Exception as e:
                return json_resp(self, {"error": str(e)}, 404)

        if path == "/api/reindex":
            try:
                idx = lora_index.build(LORA_DIR, os.path.join(DATA, "lora-index.json"))
                return json_resp(self, {"ok": True, "count": idx["count"], "stats": idx["stats"]})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/github":
            q = (qs.get("q") or [""])[0]
            return json_resp(self, github_search(q))

        return json_resp(self, {"error": "not found"}, 404)

    def _serve_file(self, path, ctype):
        if not os.path.isfile(path):
            return json_resp(self, {"error": "not found", "path": path}, 404)
        with open(path, "rb") as f:
            data = f.read()
        return text_resp(self, data, ctype)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        path = p.path
        try:
            body = self._read_json()
        except Exception as e:
            return json_resp(self, {"error": "bad json: " + str(e)}, 400)

        if path == "/api/generate":
            try:
                g = build_prompt_payload(body)
                r = comfy_post("/prompt", {"prompt": g, "client_id": "comfy-frontend"})
                return json_resp(self, {"ok": True, "prompt_id": r.get("prompt_id"), "number": r.get("number")})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/combo":
            try:
                r = combo.make_combo(
                    max_level=int(body.get("level", 0)),
                    work=str(body.get("work") or ""),
                    use_pose=bool(body.get("use_pose", True)),
                    use_scene=bool(body.get("use_scene", True)),
                    seed=body.get("seed"),
                    locked=body.get("locked") or {},
                    disabled=body.get("disabled") or [],
                )
                return json_resp(self, r)
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/interrupt":
            try:
                comfy_post("/interrupt", {})
                return json_resp(self, {"ok": True})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/free":
            try:
                comfy_post("/free", {"unload_models": True, "free_memory": True})
                return json_resp(self, {"ok": True})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/queue/clear":
            try:
                payload = {"delete": body["delete"]} if body.get("delete") else {"clear": True}
                comfy_post("/queue", payload)
                return json_resp(self, {"ok": True})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/tagger":
            try:
                res = run_wd14_tagger(body)
                return json_resp(self, res)
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        if path == "/api/assets":
            # 保存自定义词库
            try:
                for key, fname in (("poses", "poses.json"), ("outfits", "outfits.json"), ("characters", "characters.json")):
                    if key in body:
                        with open(os.path.join(ASSET_DIR, fname), "w", encoding="utf-8") as f:
                            json.dump(body[key], f, ensure_ascii=False, indent=2)
                return json_resp(self, {"ok": True})
            except Exception as e:
                return json_resp(self, {"ok": False, "error": str(e)}, 500)

        return json_resp(self, {"error": "not found"}, 404)


_WD14_CACHE = {"sess": None, "tags": None, "input_name": None, "size": 448}
WD14_MODEL_DIR = r"F:\ComfyUI\ComfyUI\custom_nodes\ComfyUI-WD14-Tagger\models"
WD14_ONNX = os.path.join(WD14_MODEL_DIR, "wd-swinv2-tagger-v3.onnx")
WD14_CSV = os.path.join(WD14_MODEL_DIR, "wd-swinv2-tagger-v3.csv")


def _ensure_wd14():
    if _WD14_CACHE["sess"] is not None:
        return
    if not os.path.isfile(WD14_ONNX) or os.path.getsize(WD14_ONNX) < 400_000_000:
        raise RuntimeError("WD14 反推模型仍在下载中或未完整就绪，请稍候片刻再试")
    if not os.path.isfile(WD14_CSV):
        raise RuntimeError("缺少 WD14 标签表 wd-swinv2-tagger-v3.csv")
    import csv, onnxruntime as ort
    tags = []
    with open(WD14_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tags.append((row["name"], int(row["category"])))
    sess = ort.InferenceSession(WD14_ONNX, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    _WD14_CACHE["sess"] = sess
    _WD14_CACHE["tags"] = tags
    _WD14_CACHE["input_name"] = inp.name
    _WD14_CACHE["size"] = int(inp.shape[1]) if len(inp.shape) >= 2 and isinstance(inp.shape[1], int) else 448


def run_wd14_tagger(body):
    import base64, io as _io
    import numpy as np
    from PIL import Image

    _ensure_wd14()
    img_b64 = body.get("image") or ""
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]
    if not img_b64:
        return {"ok": False, "error": "未收到图片数据"}
    raw = base64.b64decode(img_b64)
    im = Image.open(_io.BytesIO(raw))
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")

    sz = _WD14_CACHE["size"]
    w, h = im.size
    m = max(w, h)
    canvas = Image.new("RGB", (m, m), (255, 255, 255))
    canvas.paste(im, ((m - w) // 2, (m - h) // 2))
    canvas = canvas.resize((sz, sz), Image.BICUBIC)

    arr = np.asarray(canvas, dtype=np.float32)[:, :, ::-1]  # RGB -> BGR
    arr = np.expand_dims(arr, axis=0)
    probs = _WD14_CACHE["sess"].run(None, {_WD14_CACHE["input_name"]: arr})[0][0]

    th = float(body.get("threshold", 0.35))
    cth = float(body.get("char_threshold", 0.75))
    general, chars = [], []
    for (name, cat), p in zip(_WD14_CACHE["tags"], probs):
        score = float(p)
        clean = name if len(name) <= 3 else name.replace("_", " ")
        if cat == 0 and score >= th:
            general.append({"tag": clean, "score": round(score, 3)})
        elif cat == 4 and score >= cth:
            chars.append({"tag": clean, "score": round(score, 3)})
    general.sort(key=lambda x: -x["score"])
    chars.sort(key=lambda x: -x["score"])
    return {"ok": True, "general": general, "characters": chars}


def github_search(q):
    """轻量 GitHub 搜索（search/repositories），无需 token"""
    if not q:
        return {"items": [], "note": "empty query"}
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": 20})
    req = urllib.request.Request(url, headers={
        "User-Agent": "comfy-frontend/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        items = [{
            "full_name": it["full_name"],
            "html_url": it["html_url"],
            "description": it.get("description"),
            "stars": it.get("stargazers_count"),
            "updated": it.get("updated_at"),
            "topics": it.get("topics", []),
        } for it in data.get("items", [])]
        return {"items": items, "total": data.get("total_count", 0)}
    except Exception as e:
        return {"items": [], "error": str(e)}


def main():
    from http.server import ThreadingHTTPServer
    # 启动时重建一次索引
    try:
        lora_index.build(LORA_DIR, os.path.join(DATA, "lora-index.json"))
    except Exception as e:
        print("index build failed:", e)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"ComfyUI Frontend -> http://127.0.0.1:{PORT}")
    print(f"ComfyUI backend -> {COMFY}")
    srv.serve_forever()


_PROGRESS = {"running": False, "node": "", "stage": "", "value": 0, "max": 0, "pct": 0}


def _ws_progress_loop():
    """纯标准库后台线程：直连 ComfyUI WS 实时采集步数与百分比，供前端轮询零跨域读取"""
    import socket, struct
    while True:
        try:
            u = urllib.parse.urlparse(COMFY)
            host = u.hostname or "127.0.0.1"
            port = u.port or 8188
            s = socket.create_connection((host, port), timeout=10)
            s.settimeout(60)
            req = (
                "GET /ws?clientId=comfy-frontend HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            s.sendall(req.encode())
            buf = b""
            while b"\r\n\r\n" not in buf:
                chunk = s.recv(1024)
                if not chunk:
                    raise EOFError("ws handshake closed")
                buf += chunk
            # 处理粘包（握手后紧跟的帧字节）
            extra = buf.split(b"\r\n\r\n", 1)[1]

            def recv_exact(n):
                nonlocal extra
                while len(extra) < n:
                    chunk = s.recv(max(4096, n - len(extra)))
                    if not chunk:
                        raise EOFError("ws closed")
                    extra += chunk
                out, extra = extra[:n], extra[n:]
                return out

            while True:
                h = recv_exact(2)
                opcode = h[0] & 0x0F
                masked = (h[1] & 0x80) != 0
                length = h[1] & 0x7F
                if length == 126:
                    length = struct.unpack("!H", recv_exact(2))[0]
                elif length == 127:
                    length = struct.unpack("!Q", recv_exact(8))[0]
                mask = recv_exact(4) if masked else b""
                payload = recv_exact(length)
                if masked:
                    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                if opcode == 8:
                    break
                if opcode == 9:  # ping -> pong
                    s.sendall(b"\x8a\x00")
                    continue
                if opcode != 1:
                    continue
                try:
                    msg = json.loads(payload.decode("utf-8", "replace"))
                except Exception:
                    continue
                t = msg.get("type")
                d = msg.get("data") or {}
                if t == "execution_start":
                    _PROGRESS.update({"running": True, "stage": "加载模型", "value": 0, "max": 0, "pct": 0})
                elif t == "executed":
                    out = d.get("output") or {}
                    if out.get("images"):
                        _mirror_history_images({"_ws": {"outputs": {"_node": out}}})
                elif t == "executing":
                    nid = d.get("node")
                    if nid is None:
                        _PROGRESS.update({"running": False, "node": "", "stage": "完成", "pct": 100})
                        pid = d.get("prompt_id")
                        if pid:
                            try:
                                _mirror_history_images(comfy_get("/history/" + str(pid), timeout=10))
                            except Exception:
                                pass
                    else:
                        sn = str(nid)
                        st = _PROGRESS.get("stage") or "运行中"
                        if sn == "30": st = "初绘采样"
                        elif sn == "36": st = "二段精绘"
                        elif sn == "40": st = "VAE 解码"; _PROGRESS["pct"] = 96
                        elif sn == "50": st = "保存图像"; _PROGRESS["pct"] = 99
                        elif sn in ("60", "61", "62", "63", "64"): st = "姿势控图预处理"
                        elif sn in ("1", "2", "3") or (sn.isdigit() and 10 <= int(sn) < 20): st = "加载模型/LoRA"
                        _PROGRESS.update({"running": True, "node": sn, "stage": st})
                elif t == "progress":
                    v = int(d.get("value") or 0)
                    m = max(1, int(d.get("max") or 1))
                    _PROGRESS.update({"running": True, "value": v, "max": m, "pct": round(v * 100 / m)})
                elif t == "progress_state" and isinstance(d.get("nodes"), dict):
                    for nd in d["nodes"].values():
                        if isinstance(nd, dict) and nd.get("state") == "running" and (nd.get("max") or 0) > 0:
                            v, m = int(nd.get("value") or 0), int(nd.get("max") or 1)
                            _PROGRESS.update({"running": True, "value": v, "max": m, "pct": round(v * 100 / m)})
                            break
                elif t == "execution_error":
                    _PROGRESS.update({"running": False, "stage": "出错", "pct": 0})
        except Exception:
            time.sleep(2)


if __name__ == "__main__":
    threading.Thread(target=_ws_progress_loop, daemon=True).start()
    main()

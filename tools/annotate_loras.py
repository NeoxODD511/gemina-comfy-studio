"""给 LoRA 索引补中文说明 + 清理重复"""
import json, os, sys, io, hashlib, collections

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"F:\ComfyUI_Models\loras"
INDEX = r"F:\ComfyUI_Frontend\data\lora-index.json"

# ---- 中文说明库：按文件名小写关键词匹配 ----
# 格式：(关键词列表, 中文名, 作用说明, 推荐权重, 注意事项)
NOTES = [
    # ===== 画风/画师 =====
    (["velvet's_mythic", "velvets_mythic"],
     "Velvet 奇幻风", "奇幻华丽画风，线条浓重、氛围史诗感，适合幻想/战斗场景", "0.6-0.8",
     "C站画风榜第一（25万下载）；三底模通吃，触发词各底模不同"),
    (["aesthetic_quality_modifiers"],
     "审美质量增强", "booru 画质词训练，整体提升完成度与美感", "0.4-0.6",
     "榜二（19万下载）；几乎必挂，但权重过高会弱化画风特征"),
    (["flat_color"],
     "平涂赛璐璐", "无描边平涂，动画赛璐璐质感", "0.5-0.7",
     "适合做番剧截图风；会抑制细节，别和细节强化类同高权"),
    (["hyperdetailed_colored_pencil"],
     "彩铅精细插画", "彩铅颗粒质感，细节密集，Niji 系插画风", "0.4-0.7",
     "颗粒感强，低分辨率下容易糊"),
    (["80s_fantasy_movie"],
     "80年代奇幻电影", "复古柔光 + 胶片色，80s 奇幻片质感", "0.5-0.8",
     "带 ArsMovieStill 触发词；偏写实光影，二次元感会降低"),
    (["70s_horror_movie"],
     "70年代恐怖片", "暗调颗粒、古早恐怖片质感", "0.5-0.8",
     "氛围压抑，适合黑深残；只有 MOSS/Krea2 版"),
    (["60s_psychedelic_movie"],
     "60年代迷幻电影", "高饱和、色彩扭曲的迷幻片质感", "0.5-0.8",
     "色彩会非常跳，慎与鲜艳画风叠加"),
    (["dark_ghibli"],
     "吉卜力暗黑童话", "吉卜力水彩背景 + 赛璐璐角色，暗黑童话氛围", "0.5-0.8",
     "背景水彩感强，适合奇幻/童话题材"),
    (["granblue_fantasy"],
     "碧蓝幻想风", "游戏插画风，厚涂 + 精致光影，角色华丽", "0.5-0.8",
     "MOSS 版无触发词，靠权重生效"),
    (["gpt-image-2_anima", "style___gpt-image-2", "style_>_gpt-image-2"],
     "GPT-Image-2 风格", "GPT-Image-2 风格迁移，干净锐利、高完成度插画", "0.4-0.7",
     "会明显提升「AI 感」但很干净；适合做商插风格"),
    (["dark_art_style"],
     "暗黑艺术风", "高对比、低沉色调，黑深残/哥特题材", "0.6-0.8",
     "触发词 dark_art_style；会压暗画面，注意补光"),
    (["krekkov"],
     "Krekkov 画师风", "Krekkov 画师风格", "0.5-0.8",
     "无触发词，靠权重生效"),
    (["铭音", "meion"],
     "铭音 meion 风格", "国产画师风，色彩通透、二次元感强", "0.5-0.8",
     "Anima 版触发词 @meionANIMAstyle"),
    (["少把盐"],
     "少把盐画师风", "国产画师风，作者持续迭代到 v2.5", "0.5-0.8",
     "Anima/MOSS 双版；无触发词"),
    (["90's_anime_melancholy", "90s_anime_melancholy"],
     "90年代动画·忧郁", "复古赛璐璐 + 低饱和，90s 动画的忧郁氛围", "0.5-0.8",
     "触发词 90s_melancholy, retro"),
    (["90s_anime_aesthetic"],
     "90年代动画·美学", "复古噪点 + 暖调，90s 动画美学", "0.5-0.8",
     "触发词 90s_anime_aesthetic, 1990s (style), retro"),
    (["蔚蓝档案", "blue_archive"],
     "蔚蓝档案风格", "400+ 张 BA 官图训练，碧蓝档案游戏立绘风", "0.5-0.8",
     "明亮通透；无触发词，可加 blue archive 强化"),
    (["takorin"],
     "Takorin 画师风", "Takorin 画师风格", "0.5-0.8",
     "仅 Anima/MOSS 版"),
    (["disneylike"],
     "迪士尼风", "迪士尼式圆润卡通，五官柔化", "0.5-0.8",
     "Krea2 版触发词 Digital illustration of"),
    (["bakalight_v10"],
     "bakalight 光影 v1（偏暗）", "有层次感的偏暗电影光影风格（v1 版）", "0.5-0.8",
     "仅 Anima 版"),
    (["bakalight_v30"],
     "bakalight 光影 v3（偏亮）", "有层次感的偏亮通透光影风格（v3 版）", "0.5-0.8",
     "仅 Anima 版"),
    (["bakalight"],
     "bakalight 光影", "有层次感的光影风格", "0.5-0.8",
     "仅 Anima 版"),
    (["the_look"],
     "The Look 自然表情", "解决 AI「死鱼眼」，让眼神和微表情自然生动", "0.5-0.8",
     "触发词 LookDaal；这是表情类不是画风，和画风 LoRA 不冲突"),
    (["a1kx_sty"],
     "A1kx 画风", "A1kx 画师风格", "0.5-0.7", "本地原有"),
    (["chen-bin", "chen_bin"],
     "陈斌画风", "chen-bin 画师风格", "0.5-0.7", "本地原有"),
    (["gulugulu"],
     "gulugulu 画风", "gulugulu 画师风格（v1 epoch26）", "0.5-0.7", "本地原有"),
    (["khstyle"],
     "KH 画风", "khstyle 画师风格（v1 epoch26）", "0.5-0.7", "本地原有"),
    (["lora_2629905"],
     "米山舞风格", "米山舞画风：动感构图、强透视、鲜明色块", "0.5-0.8",
     "三底模各有版本；适合动感插画，不适合静态立绘"),
    (["semi-realistic"],
     "半写实风格", "二次元与写实之间，皮肤质感真实", "0.4-0.6",
     "【写实隔离区】会破坏纯二次元感"),

    # ===== 画质/细节 =====
    (["add_micro_details"],
     "微细节增强", "补充微小细节（发丝、纹理、褶皱），细节底座", "0.3-0.5",
     "权重超过 0.6 会出噪点纹理"),
    (["context_detailer"],
     "上下文细节补充", "在已有内容基础上补细节，不改变构图", "0.3-0.5",
     "适合高清化阶段挂载"),
    (["highres-aesthetic-boost", "highres_aesthetic"],
     "高分辨率审美增强", "提升高清阶段的审美与锐度", "0.3-0.5",
     "高分辨率修复时用，低分辨率意义不大"),
    (["3d_skin", "3d skin"],
     "3D 皮肤质感", "增强皮肤真实质感，偏 3D 渲染", "0.2-0.4",
     "【写实隔离区】会让二次元变「3D 塑料感」"),

    # ===== 控制/滑块 =====
    (["body_weight", "body_weight_slider"],
     "体重滑杆", "负值变瘦 / 正值变胖，体型基础控制", "0.3-0.6",
     "滑块类一次只开一个，多个体型滑杆会互相干扰"),
    (["hips_slider", "hips"],
     "臀部滑杆", "臀部宽窄控制", "0.3-0.6", "滑块类，慎与其他体型滑杆同挂"),
    (["thighs_slider", "thighs"],
     "大腿滑杆", "大腿粗细控制", "0.3-0.6", "滑块类"),
    (["darkness_slider", "darkness"],
     "明暗滑杆", "画面整体明暗控制", "0.3-0.5",
     "只能调强度不能指定光位；精确光影靠自然语言"),

    # ===== 加速 =====
    (["turbo_anima"],
     "Anima 加速", "Turbo 加速，把步数压到 8-12 步", "0.6-1.0",
     "必挂。不挂 Turbo 出图成本高 3 倍"),
    (["turbo_moss"],
     "MOSS 加速", "MOSS Image 的 4 步 Turbo LoRA", "0.6-1.0",
     "必挂。配 MOSS 底模用 8-12 步"),

    # ===== 实验 =====
    (["gpt-image-2_anima-base1"],
     "像素风实验", "GPT-Image-2 蒸馏到 Anima 的像素风实验品", "0.4-0.6",
     "实验性，效果不稳定，验证后可归入画风类"),
]


def match_note(fname):
    low = fname.lower()
    for kws, cn, desc, w, warn in NOTES:
        for kw in kws:
            if kw in low:
                return {"cn": cn, "desc": desc, "weight_hint": w, "warn": warn}
    return None


def sha256_of(path, chunk=8 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    idx = json.load(open(INDEX, encoding="utf-8"))
    items = idx.get("items") or []

    # 1. 补中文说明
    hit = miss = 0
    for it in items:
        n = match_note(it.get("name", ""))
        if n:
            it["cn"] = n["cn"]
            it["desc"] = n["desc"]
            it["weight_hint"] = n["weight_hint"]
            it["warn"] = n["warn"]
            hit += 1
        else:
            miss += 1
    print(f"中文说明: 命中 {hit} / 未命中 {miss}")

    # 2. 检测重复（同底模+同大小+同哈希）
    by_key = collections.defaultdict(list)
    for it in items:
        p = os.path.join(ROOT, it["file"].replace("/", os.sep))
        if not os.path.isfile(p):
            continue
        by_key[(it.get("base"), os.path.getsize(p))].append((it, p))

    dup_groups = []
    for key, group in by_key.items():
        if len(group) < 2:
            continue
        hashed = [(it, p, sha256_of(p)) for it, p in group]
        by_hash = collections.defaultdict(list)
        for it, p, h in hashed:
            by_hash[h].append((it, p))
        for h, same in by_hash.items():
            if len(same) > 1:
                dup_groups.append(same)

    print(f"\n重复组: {len(dup_groups)}")
    removed = []
    for same in dup_groups:
        # 保留文件名更规范的那个（更短/无 lora_ 前缀）
        same_sorted = sorted(same, key=lambda x: (len(x[0]["name"]), x[0]["name"]))
        keep = same_sorted[0]
        print(f"  保留: {keep[0]['name']}")
        for it, p in same_sorted[1:]:
            print(f"    删除: {it['name']}  ({os.path.getsize(p)/1024/1024:.1f} MB)")
            try:
                os.remove(p)
                removed.append(it["file"])
            except Exception as e:
                print(f"    删除失败: {e}")

    # 3. 从索引里移除已删的
    if removed:
        rset = set(removed)
        items = [it for it in items if it["file"] not in rset]

    idx["items"] = items
    idx["count"] = len(items)
    json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n清理后总数: {len(items)}（删除 {len(removed)} 个）")


if __name__ == "__main__":
    main()

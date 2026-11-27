"""
LoRA 索引（v2）—— 按底模隔离 + 5 类分类 + 写实隔离区

目录约定：
  F:\\ComfyUI_Models\\loras\\
    anima\\{char,style,ctrl,q,x}\\*.safetensors
    moss\\{...}
    krea2\\{...}
    _realistic\\{anima,moss,krea2}\\{...}      <- 写实隔离区，默认不参与二次元出图

核心原则：
- 三底模的 LoRA 各自独立训练，绝不混用；索引里 base 字段强制标注
- 同名不同哈希全部保留，不覆盖不删除
- _realistic 下的内容标记 isolated=True，前端默认隐藏
"""
import os, json, re, hashlib, time

BASES = ["anima", "moss", "krea2"]
ISOLATED_ROOT = "_realistic"
SLIDER_ROOT = "_sliders"

CATEGORIES = {
    "char":  {"label": "角色 Character", "prefix": "char_",  "weight": [0.6, 0.9], "default_weight": 0.75},
    "style": {"label": "画风 Style",     "prefix": "style_", "weight": [0.4, 0.8], "default_weight": 0.60},
    "ctrl":  {"label": "控制 Control",   "prefix": "ctrl_",  "weight": [0.3, 0.6], "default_weight": 0.45},
    "q":     {"label": "画质 Quality",   "prefix": "q_",     "weight": [0.2, 0.5], "default_weight": 0.35},
    "x":     {"label": "功能 Utility",   "prefix": "x_",     "weight": [0.2, 0.6], "default_weight": 0.40},
}

# 目录名 -> 分类（新结构靠目录定分类，最可靠；兼容 char 与 character 两种命名）
DIR_CATEGORY = {"char": "char", "character": "char", "style": "style", "ctrl": "ctrl", "q": "q", "x": "x"}

# 文件名关键词回退（目录不在标准结构时）
INFER_RULES = [
    ("ctrl", [r"pose", r"slider", r"view", r"camera", r"angle", r"hand", r"line_?art", r"sketch",
              r"composition", r"depth", r"openpose", r"dwpose", r"control", r"layout", r"tilt",
              r"weight", r"thigh", r"hip", r"darkness", r"brightness", r"contrast"]),
    ("q",    [r"detail", r"quality", r"highres", r"aesthetic", r"skin", r"sharp", r"light",
              r"real", r"texture", r"enhance", r"upscale", r"boost", r"detailer", r"3d"]),
    ("style",[r"style", r"_sty", r"arts", r"watercolor", r"oil", r"cel", r"flat", r"pencil",
              r"cyberpunk", r"ghibli", r"retro", r"dark_art", r"niji", r"chen", r"gulugulu",
              r"khstyle", r"a1kx", r"blue_archive", r"realistic"]),
    ("char", [r"character", r"girl", r"boy", r"waifu", r"person", r"outfit"]),
    ("x",    [r"turbo", r"test", r"tmp", r"remov", r"watermark", r"logo", r"text", r"experiment", r"gpt"]),
]


def is_realistic(name):
    """判断是否写实类（用于隔离区兜底判断）"""
    low = name.lower()
    return bool(re.search(r"real|photo|film|candid|iphone|photography|lightbox|lens|flesh|skin.?tex", low))


# ================= 中文说明库 =================
# (关键词列表, 中文名, 作用说明, 推荐权重, 注意事项)
CN_NOTES = [
    # ---- 画风/画师 ----
    (["velvet's_mythic", "velvets_mythic"], "Velvet 奇幻风",
     "奇幻华丽画风，线条浓重、氛围史诗感，适合幻想/战斗场景", "0.6-0.8",
     "C站画风榜第一（25万下载）；触发词各底模不同"),
    (["aesthetic_quality_modifiers", "aesthetic_quality"], "审美质量增强",
     "booru 画质词训练，整体提升完成度与美感", "0.4-0.6",
     "榜二（19万下载）；几乎必挂，权重过高会弱化画风特征"),
    (["flat_color"], "平涂赛璐璐",
     "无描边平涂，动画赛璐璐质感", "0.5-0.7",
     "适合番剧截图风；会抑制细节"),
    (["hyperdetailed_colored_pencil"], "彩铅精细插画",
     "彩铅颗粒质感，细节密集，Niji 系插画风", "0.4-0.7",
     "颗粒感强，低分辨率下容易糊"),
    (["niji_sweet_spot", "niji"], "日系甜点画风",
     "柔和粉彩，少女感强，C站人气画风", "0.4-0.8",
     "三底模各有版本，触发词相同"),
    (["80s_fantasy_movie"], "80年代奇幻电影",
     "复古柔光 + 胶片色，80s 奇幻片质感", "0.5-0.8",
     "带 ArsMovieStill 触发词；偏写实光影"),
    (["70s_horror_movie"], "70年代恐怖片",
     "暗调颗粒、古早恐怖片质感", "0.5-0.8",
     "氛围压抑，适合黑深残；仅 MOSS/Krea2 版"),
    (["60s_psychedelic_movie"], "60年代迷幻电影",
     "高饱和、色彩扭曲的迷幻片质感", "0.5-0.8",
     "色彩会非常跳，慎与鲜艳画风叠加"),
    (["dark_ghibli"], "吉卜力暗黑童话",
     "吉卜力水彩背景 + 赛璐璐角色，暗黑童话氛围", "0.5-0.8",
     "背景水彩感强，适合奇幻/童话题材"),
    (["granblue_fantasy"], "碧蓝幻想风",
     "游戏插画风，厚涂 + 精致光影，角色华丽", "0.5-0.8",
     "MOSS 版无触发词，靠权重生效"),
    (["style___gpt-image-2", "style_>_gpt-image-2", "gpt-image-2"], "GPT-Image-2 风格",
     "GPT-Image-2 风格迁移，干净锐利、高完成度插画", "0.4-0.7",
     "会明显提升「AI 感」但很干净；适合商插风格"),
    (["dark_art_style"], "暗黑艺术风",
     "高对比、低沉色调，黑深残/哥特题材", "0.6-0.8",
     "触发词 dark_art_style；会压暗画面，注意补光"),
    (["krekkov"], "Krekkov 画师风", "Krekkov 画师风格", "0.5-0.8", "无触发词，靠权重生效"),
    (["铭音", "meion"], "铭音 meion 风格",
     "国产画师风，色彩通透、二次元感强", "0.5-0.8",
     "Anima 版触发词 @meionANIMAstyle"),
    (["少把盐"], "少把盐画师风",
     "国产画师风，作者持续迭代到 v2.5", "0.5-0.8", "Anima/MOSS 双版；无触发词"),
    (["90's_anime_melancholy", "90s_anime_melancholy"], "90年代动画·忧郁",
     "复古赛璐璐 + 低饱和，90s 动画的忧郁氛围", "0.5-0.8",
     "触发词 90s_melancholy, retro"),
    (["90s_anime_aesthetic"], "90年代动画·美学",
     "复古噪点 + 暖调，90s 动画美学", "0.5-0.8",
     "触发词 90s_anime_aesthetic, 1990s (style), retro"),
    (["蔚蓝档案", "blue_archive"], "蔚蓝档案风格",
     "400+ 张 BA 官图训练，碧蓝档案游戏立绘风", "0.5-0.8",
     "明亮通透；无触发词"),
    (["takorin"], "Takorin 画师风", "Takorin 画师风格", "0.5-0.8", "仅 Anima/MOSS 版"),
    (["disneylike"], "迪士尼风",
     "迪士尼式圆润卡通，五官柔化", "0.5-0.8", "Krea2 版触发词 Digital illustration of"),
    (["bakalight"], "bakalight 光影",
     "有层次感的光影风格，v1 偏暗、v3 偏亮", "0.5-0.8",
     "仅 Anima 版；作者说 v2 训练失败，建议 v1 或 v3"),
    (["the_look"], "The Look 自然表情",
     "解决 AI「死鱼眼」，让眼神和微表情自然生动", "0.5-0.8",
     "触发词 LookDaal；表情类，与画风 LoRA 不冲突"),
    (["a1kx_sty"], "A1kx 画风", "A1kx 画师风格", "0.5-0.7", "本地原有"),
    (["chen-bin", "chen_bin"], "陈斌画风", "chen-bin 画师风格", "0.5-0.7", "本地原有"),
    (["gulugulu"], "gulugulu 画风", "gulugulu 画师风格（v1 epoch26）", "0.5-0.7", "本地原有"),
    (["khstyle"], "KH 画风", "khstyle 画师风格（v1 epoch26）", "0.5-0.7", "本地原有"),
    (["lora_2629905"], "米山舞风格",
     "米山舞画风：动感构图、强透视、鲜明色块", "0.5-0.8",
     "三底模各有版本；适合动感插画，不适合静态立绘"),
    (["semi-realistic"], "半写实风格", "二次元与写实之间，皮肤质感真实", "0.4-0.6",
     "【写实隔离区】会破坏纯二次元感"),
    (["in_real_update"], "写实化", "把二次元往写实方向推", "0.3-0.5",
     "【写实隔离区】纯二次元项目不要挂"),

    # ---- 画质/细节 ----
    (["add_micro_details"], "微细节增强",
     "补充微小细节（发丝、纹理、褶皱），细节底座", "0.3-0.5", "权重超过 0.6 会出噪点纹理"),
    (["context_detailer"], "上下文细节补充",
     "在已有内容基础上补细节，不改变构图", "0.3-0.5", "适合高清化阶段挂载"),
    (["highres-aesthetic-boost", "highres_aesthetic"], "高分辨率审美增强",
     "提升高清阶段的审美与锐度", "0.3-0.5", "高分辨率修复时用"),
    (["3d_skin", "3d skin"], "3D 皮肤质感",
     "增强皮肤真实质感，偏 3D 渲染", "0.2-0.4", "【写实隔离区】会让二次元变塑料感"),

    # ---- 控制/滑块 ----
    (["body_weight", "body_weight_slider"], "体重滑杆",
     "负值变瘦 / 正值变胖，体型基础控制", "0.3-0.6", "滑块一次只开一个，多个会互相干扰"),
    (["hips_slider", "hips"], "臀部滑杆", "臀部宽窄控制", "0.3-0.6", "滑块类，慎与其他体型滑杆同挂"),
    (["thighs_slider", "thighs"], "大腿滑杆", "大腿粗细控制", "0.3-0.6", "滑块类"),
    (["darkness_slider", "darkness"], "明暗滑杆",
     "画面整体明暗控制", "0.3-0.5", "只能调强度；精确光影靠自然语言"),
    (["lips_size_slider", "lips_size"], "嘴唇厚度滑杆",
     "调节嘴唇厚薄", "0.3-0.5", "滑块类，幅度小，建议 0.3-0.5"),
    (["long_legs_slider", "long_legs"], "腿长比例滑杆",
     "拉长腿部比例，改善身材比例", "0.3-0.6", "过高会比例失调"),
    (["super_hip-waist", "super_hip_waist", "hip-waist"], "腰臀比强化",
     "强化腰细臀宽的对比", "0.3-0.6", "与 Hips/Thighs 滑杆同挂会叠加过度"),
    (["waist_slider", "waist"], "腰围滑杆", "腰部粗细控制", "0.3-0.6", "滑块类"),
    (["moss_age_slider", "age_slider"], "年龄滑杆",
     "年龄控制（萝莉 ↔ 熟女）", "0.3-0.6", "仅 MOSS 版；Lv0 场景建议调低"),
    (["line_weight_slider", "line_weight"], "线条粗细滑杆",
     "控制画面线条粗细，适合线稿风/漫画风", "0.3-0.6", "配 LLLite 线稿控制时会互相影响"),
    (["quality_enhance_textslider", "textslider"], "质量增强文本滑杆",
     "MOSS 用的质量增强滑杆（LECO 训练）", "0.2-0.6",
     "MOSS 专属；作者建议 0~1 之间测试"),

    # ---- 加速 ----
    (["turbo_anima"], "Anima 加速", "Turbo 加速，把步数压到 8-12 步", "0.6-1.0",
     "必挂。不挂 Turbo 出图成本高 3 倍"),
    (["turbo_moss"], "MOSS 加速", "MOSS Image 的 4 步 Turbo LoRA", "0.6-1.0",
     "必挂。配 MOSS 底模用 8-12 步"),

    # ---- 实验 ----
    (["gpt-image-2_anima-base1"], "像素风实验",
     "GPT-Image-2 蒸馏到 Anima 的像素风实验品", "0.4-0.6", "实验性，效果不稳定"),

    # ---- 五大名家画风 & 蓝色星原画风 ----
    (["蓝色星原_官方美术画风"], "蓝色星原·官方美术风",
     "蛮啾《蓝色星原：旅谣》角色立绘与命座卡面风格", "0.7-0.9", "适配 Anima 底模；搭蓝原角色显著增效", ""),
    (["米奇王_michiking_魅魔学生会part4"], "米奇王·魅魔学生会4画风",
     "みちきんぐ同人志细腻油润肉感与丝袜光泽", "0.8-1.0", "适配 Anima-Base1.0 或 Malebolgia_Fraud 底模", "Malebolgia, Anmitsuyomogitei"),
    (["雷火剑_raikaken直属画风"], "雷火剑·直属画风 v1",
     "雷火剣经典眼型、油亮高光与动态张力", "0.8-1.0", "适配 Anima 通用底模；免触发词", ""),
    (["t-rexstudio动画风_冠军版"], "雷火剑·T-Rex厂牌冠军版",
     "T-Rex 里番动画截图质感与高光肌肤", "0.85-0.95", "适配 Anima 通用底模", "T-RexAnimaStyle, anime coloring, anime screencap, shiny skin"),
    (["t-rex动画多架构版", "t-rex动画风_【适配krea2"], "雷火剑·T-Rex动画风",
     "Studio T-Rex 番剧动画上色质感", "0.8-1.0", "对应目录底模使用", "TRexStudio"),
    (["kegareboshi污星"], "雷火剑×佐藤空气·污星风",
     "名作《ケガレボシ》专属动画画风", "0.6-0.9", "适配 Anima 通用底模", "trexx_kage"),
    (["佐藤空气_satoukuuki冠军综合版", "佐藤空气_satoukuuki精炼版", "佐藤空气_satoukuuki_【适配"], "佐藤空气·综合画风",
     "左藤空気标志性丰满肉感与实用向笔触", "0.8-1.0", "对应目录底模使用；免触发词", ""),
    (["佐藤空气_vr5魅魔本画风v2"], "佐藤空气·VR5魅魔本V2",
     "Vanishing Reality 5 同人志浓厚油润画风", "0.9-1.0", "最配 Malebolgia_Fraud 特调 Anima 底模", "malebolgia"),
    (["朝凪_asanagi冠军版_v2"], "朝凪·Asanagi冠军版 v2",
     "Fatalpulse 凌厉粗线条与极具张力的神态", "0.8-1.0", "适配 Anima 通用底模", "4s4n4g1sknsfw"),
    (["朝凪_asanagi免触发词版"], "朝凪·Asanagi免触发词版",
     "朝凪画风直出，无需额外触发词", "0.8-1.0", "适配 Anima 通用底模", ""),
    (["朝凪_asanagi_p版"], "朝凪·Asanagi P版",
     "朝凪画师串微调版", "0.8-1.0", "适配 Anima 通用底模", "@asanagi"),
    (["山药锅锅"], "山药锅锅(药锅锅)画风",
     "少前/云图御用画师，通透丝袜与细腻肌肤质感", "0.8-1.0", "推荐 er_sde + beta, CFG 4-5", "@syjt"),

    # ---- 蓝色星原 / 原神 / 少前2 角色 ----
    (["蓝色星原_星临者_starborn"], "蓝色星原·女星临者 v2",
     "女主角星临者（支持默认礼装、自定义换色与内置女仆装）", "0.75-0.95", "适配 Anima 底模", "xiaoxingchen"),
    (["源千代_minamotochiyo_v2"], "蓝色星原·源千代(公测原皮)",
     "黑长直红瞳太刀少女，藏青水手服轻甲黑丝", "0.8-0.95", "适配 Anima 底模", "k_minamoto_chiyo, black_hair, very_long_hair, blunt_bangs, red_eyes, red_inner_hair"),
    (["源千代_绯色潜行"], "蓝色星原·源千代(绯色潜行)",
     "高马尾露肩黑金紧身衣与腿甲高跟靴皮肤", "0.8-0.95", "适配 Anima 底模", "k_chiyo_skin, black_hair, very_long_hair, high_ponytail, blunt_bangs, sidelocks, red_eyes"),
    (["蓝色星原_枫糖"], "蓝色星原·枫糖(Maple)",
     "金发蓝瞳双丸子头猫娘接待员，白丝短裤", "0.8-0.95", "适配 Anima 底模", "fengtang, blonde hair, blue eyes, cat ears, cat tail, double bun"),
    (["蓝色星原_涂山小玉"], "蓝色星原·涂山小玉",
     "青华乡狐仙少女，低双马尾国风白丝礼装", "0.8-0.95", "适配 Anima 底模", "tushanxiaoyu, low twintails, very long hair"),
    (["蓝色星原_米砂"], "蓝色星原·米砂(Misha)",
     "绿瞳尖耳木精灵（支持白裙原皮与黑丝宿舍皮）", "0.8-0.95", "适配 Anima 底模", "misha, green eyes, pointy ears"),
    (["蓝色星原_夏尔"], "蓝色星原·夏尔(Shalle)",
     "蓝发尖耳角饰精灵，露肩蓝裙配黑丝高跟", "0.8-0.95", "适配 Anima 底模", "xiaer, blue hair, blue eyes, pointy ears, horns"),
    (["蓝色星原_红宝石"], "蓝色星原·红宝石(Ruby)",
     "灰发紫瞳魔女帽，红衣百褶裙吊带黑丝", "0.8-0.95", "适配 Anima 底模", "hongbaoshi, grey hair, purple eyes, witch hat"),
    (["蓝色星原_法兰塔"], "蓝色星原·法兰塔(Falanta)",
     "翼人族御姐首领，白翼面纹露肩礼裙", "0.8-0.95", "适配 Anima 底模", "falanta, facial mark, white wings, large breasts"),
    (["蓝色星原_艾妮丝"], "蓝色星原·艾妮丝(Anais)",
     "浅棕发紫花瞳羊角魔导御姐", "0.8-0.95", "适配 Anima 底模", "ainisi, light brown hair, purple eyes, sheep horns, flower-shaped pupils, large breasts"),
    (["蓝色星原_莉莉"], "蓝色星原·莉莉(Lily)",
     "金发绿瞳持盾枪骑士，黑丝长靴绝对领域", "0.8-0.95", "适配 Anima 底模", "liliq, blonde hair, green eyes, braid"),
    (["蓝色星原_露米"], "蓝色星原·露米(Lumi)",
     "金发薄荷绿渐变半透明紫蝶翼同行妖精", "0.8-1.0", "适配 Anima 底模", "lumi, fairy, blonde hair, gradient hair, mint green hair, pointed ears, butterfly wings, translucent wings"),
    (["蓝色星原_永远"], "蓝色星原·永远(YongYuan)",
     "无垢海浅蓝超长发紫瞳神秘少女", "0.8-0.95", "适配 Anima 底模", "k_yongyuan, light_blue_hair, very_long_hair, purple_eyes"),
    (["若娜瓦_ronova_v2_【适配anima标准"], "原神·死之执政若娜瓦 v2",
     "铂金长发金花瞳、红角头纱与红黑眼死神羽翼", "0.85-1.0", "适配标准 2B Anima；负面建议加 3d, cel shading", "ronovagenshin, wings, red wings, veil, black dress"),
    (["若娜瓦_ronova_【适配anima-29b"], "原神·若娜瓦(29B原生版)",
     "专为 40 层 Anima-2.9B 重映射版本", "0.5-0.7", "专配 NovaAnimeAMV70_29B / mature29B 底模", "ronovagenshin, wings, red wings, veil, black dress"),
    (["若娜瓦_ronova_【适配krea2"], "原神·若娜瓦(Krea2版)",
     "死之执政若娜瓦 Krea2 专版，支持英文自然语言", "0.9-1.0", "专配 Krea2 底模", "ronovagenshin"),
    (["若娜瓦_ronova_【适配moss"], "原神·若娜瓦(MOSS版)",
     "死之执政若娜瓦 MOSS 专版", "0.8-1.0", "专配 MOSS 底模", "Ronova, very long hair, white hair, yellow eyes, black dress"),
    (["少前2_破坏者_destroyer"], "少前2·破坏者(双造型)",
     "内置机械腿战衣(battle suit)与垂绒黑巧黑丝兔女郎(bunny suit)", "0.8-1.0", "通过 battle suit / bunny suit 切换原皮与兔女郎皮", "destroyer, grey hair, black hair, streaked hair, twintails, yellow eyes"),
]


def match_cn(fname):
    low = fname.lower()
    for item in CN_NOTES:
        kws, cn, desc, w, warn = item[:5]
        for kw in kws:
            if kw in low:
                res = {"cn": cn, "desc": desc, "weight_hint": w, "warn": warn}
                if len(item) >= 6:
                    res["trigger"] = item[5]
                    res["explicit_trigger"] = True
                return res
    return {}


def infer_category(name):
    low = name.lower()
    for cat, pats in INFER_RULES:
        for p in pats:
            if re.search(p, low):
                return cat
    return "x"


def sha256_of(path, chunk=8 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def infer_trigger(name):
    base = re.sub(r"\.(safetensors|pt|ckpt)$", "", name, flags=re.I)
    base = re.sub(r"[_\-]+", " ", base)
    base = re.sub(r"\b(v\d+(\.\d+)?|\d{5,}|anima|sdxl|illustrious|pony|noobai|epoch\d*|base\d*)\b",
                  "", base, flags=re.I)
    return base.strip()


def scan(lora_root, with_hash=False):
    """扫描整个 loras 根目录，返回记录列表"""
    records = []
    if not os.path.isdir(lora_root):
        return records

    for entry in os.listdir(lora_root):
        top = os.path.join(lora_root, entry)
        if not os.path.isdir(top):
            continue
        isolated = (entry == ISOLATED_ROOT)
        for root, dirs, files in os.walk(top):
            for fn in files:
                if not fn.lower().endswith((".safetensors", ".pt", ".ckpt")):
                    continue
                full = os.path.join(root, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, lora_root).replace("\\", "/")
                parts = rel.split("/")
                # 解析 base 与 category
                if isolated:
                    # _realistic/anima/style/x.safetensors
                    base = parts[1] if len(parts) > 2 else "unknown"
                    catdir = parts[2] if len(parts) > 3 else (parts[2] if len(parts) > 2 else "")
                    cat = DIR_CATEGORY.get(catdir, infer_category(fn))
                elif entry == SLIDER_ROOT:
                    # _sliders/anima/x.safetensors -> 一律 ctrl
                    base = parts[1] if len(parts) > 1 else "unknown"
                    cat = "ctrl"
                else:
                    # anima/style/x.safetensors
                    base = parts[0] if parts else "unknown"
                    catdir = parts[1] if len(parts) > 2 else ""
                    cat = DIR_CATEGORY.get(catdir, infer_category(fn))
                if base not in BASES and base != "unknown":
                    base = "unknown"
                rec = {
                    "file": rel,
                    "name": fn,
                    "base": base,
                    "category": cat,
                    "isolated": isolated or is_realistic(fn),
                    "size": st.st_size,
                    "size_mb": round(st.st_size / 1024 / 1024, 1),
                    "mtime": int(st.st_mtime),
                    "trigger": infer_trigger(fn),
                    "weight": CATEGORIES[cat]["default_weight"],
                    "note": "",
                }
                rec.update(match_cn(fn))
                if with_hash:
                    rec["sha256"] = sha256_of(full)
                records.append(rec)

    # 同名检测
    by_name = {}
    for r in records:
        by_name.setdefault(r["name"].lower(), []).append(r)
    for name, group in by_name.items():
        if len(group) > 1:
            hashes = {g.get("sha256") for g in group}
            for g in group:
                if with_hash and len(hashes) > 1:
                    g["note"] = "同名多版本(不同哈希)，全部保留"
                elif with_hash:
                    g["note"] = "完全重复(同哈希)"
                else:
                    g["note"] = "同名多版本(不同底模或版本)"
                g["duplicate_name"] = True
    return records


def build(lora_root, out_path, with_hash=False):
    recs = scan(lora_root, with_hash=with_hash)
    stats = {}
    for r in recs:
        key = ("_realistic" if r["isolated"] else r["base"])
        stats.setdefault(key, {})
        stats[key].setdefault(r["category"], 0)
        stats[key][r["category"]] += 1

    idx = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lora_root": lora_root,
        "bases": BASES,
        "isolated_root": ISOLATED_ROOT,
        "categories": CATEGORIES,
        "count": len(recs),
        "stats": stats,
        "items": recs,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    return idx


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    lora_root = r"F:\ComfyUI_Models\loras"
    idx = build(lora_root, os.path.join(root, "data", "lora-index.json"), with_hash=False)
    print(json.dumps({"count": idx["count"], "stats": idx["stats"]}, ensure_ascii=False, indent=2))

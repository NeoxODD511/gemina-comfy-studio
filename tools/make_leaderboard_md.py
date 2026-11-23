"""生成 C 站二次元 LoRA 精选清单（四类）"""
import json, os, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LB = r"F:\ComfyUI_Frontend\data\leaderboard.json"
OUT = r"F:\ComfyUI_Frontend\data\C站二次元LoRA精选.md"

# 人工精选：id -> (作用说明)
PURPOSE = {
    # ---- 画风/画师 ----
    599757: "奇幻华丽风，六底模通吃；线条浓重、氛围史诗感，适合幻想/战斗场景",
    929497: "画质审美增强，booru 画质词训练；三底模通用，长期榜一",
    1132089: "平涂无描边风格，赛璐璐动画质感",
    1155749: "彩铅精细插画风，Niji 系质感，细节颗粒感强",
    912942: "90年代复古科幻动画风，霓虹/胶片颗粒",
    1380736: "暗黑艺术风，高对比低沉色调，适合黑深残/哥特题材",
    22800: "碧蓝幻想游戏画风，厚涂+精致光影",
    2554999: "日系甜点画风，柔和粉彩，少女感强",
    2564225: "GPT-Image-2 风格迁移，干净锐利的高完成度插画",
    2533943: "铭音画师风，国产二次元，色彩通透",
    2638358: "少把盐画师风，Anima/Moss 双版",
    2629905: "米山舞画师风，动感构图+强烈透视",
    2724509: "番剧截图质感，动画截图风，适合做二创截图",
    599757: "Velvet 奇幻风",
}
# 补充：用名称关键词匹配
NAME_HINTS = [
    ("80s Fantasy Movie", "80年代奇幻电影质感，复古柔光+胶片色"),
    ("70s Horror Movie", "70年代恐怖片质感，暗调颗粒感"),
    ("60s Psychedelic Movie", "60年代迷幻电影，高饱和扭曲色彩"),
    ("Dark Ghibli Fairytales", "吉卜力暗黑童话，水彩背景+赛璐璐角色"),
    ("Granblue fantasy style", "碧蓝幻想游戏画风"),
    ("Krekkov Style", "Krekkov 画师风"),
    ("Takorin Style", "Takorin 画师风"),
    ("DisneyLike style", "迪士尼式圆润卡通"),
    ("90's anime melancholy", "90年代动画忧郁氛围，复古赛璐璐+低饱和"),
    ("90s anime aesthetic", "90年代动画美学，复古噪点+暖调"),
    ("Retro Neo Noir", "复古黑色电影风，强烈明暗对比"),
    ("Alt-Girl/E-Girl", "另类女孩/电子女孩造型风格"),
    ("地雷系", "地雷系亚文化造型，黑粉配色+日系亚逼风"),
    ("油画湿润厚涂", "油画湿润厚涂，笔触明显+厚重质感"),
    # 姿势
    ("Body weight slider", "体重滑杆（负值瘦/正值胖），体型控制基础"),
    ("Breast Slider", "胸部尺寸滑杆"),
    ("Thighs slider", "大腿粗细滑杆"),
    ("Hips slider", "臀部宽窄滑杆"),
    ("Waist Slider", "腰围粗细滑杆"),
    ("super hip-waist", "腰臀比强化滑杆"),
    ("Lips size slider", "嘴唇厚度滑杆"),
    ("Long legs slider", "腿长比例滑杆"),
    ("BottomHeavySlider", "下重体型滑杆（下半身丰满）"),
    ("MOSS Age Slider", "年龄滑杆（萝莉↔熟女）"),
    ("Line Weight Slider", "线条粗细控制，适合线稿风"),
    # 构图
    ("True First-Person POV", "第一人称人眼视角，代入感极强"),
    ("Fixed Perspective View", "固定透视视角，抑制模型乱构图"),
    ("构图自控", "构图自控，指定画面元素位置"),
    ("Bodycam View", "随身摄像头视角，vlog 质感"),
    ("Door Peephole View", "猫眼视角，鱼眼畸变+窥视感"),
    ("Livestream", "直播截图构图，手机/桌面视角"),
    # 光影
    ("Darkness Slider", "画面明暗滑杆"),
    ("Moss lighting slider", "光照强度/方向滑杆"),
    ("Opulent Darkness", "奢华暗调光影，高对比+暗部细节"),
    ("Better Light & Shadow", "光影质量增强，改善明暗过渡"),
]

LABEL = {
    599757: "Velvet's Mythic Fantasy Styles",
    929497: "Aesthetic Quality Modifiers",
    1132089: "Flat Color",
    1155749: "Hyperdetailed Colored Pencil",
    912942: "Retro Sci-fi 90's anime",
    1380736: "Dark Art Style",
    22800: "Granblue fantasy style",
    2554999: "Niji Sweet Spot",
    2564225: "Style > gpt-image-2",
    2533943: "铭音 meion style",
    2638358: "少把盐",
    2629905: "米山舞 Yoneyama Mai",
    2724509: "Better Anime Screencap",
}


def purpose_of(name, desc):
    for k, v in PURPOSE.items():
        if isinstance(k, int):
            continue
    for kw, txt in NAME_HINTS:
        if kw.lower() in name.lower():
            return txt
    # 从 desc 截取
    d = (desc or "").strip()
    if d:
        return d[:80]
    return "—"


def main():
    lb = json.load(open(LB, encoding="utf-8"))
    items = lb["items"]

    # 手动补充分类修正
    FIX_CAT = {
        "地雷系/jirai kei": "画风/画师",
        "Moss/Anima-油画湿润厚涂二次元（nai5其三）": "画风/画师",
        "The Look": "画风/画师",
        "少把盐 Anima//Moss Base/Moss Heal": "画风/画师",
        "Alt-Girl/E-Girl": "画风/画师",
    }
    for it in items:
        for k, v in FIX_CAT.items():
            if k in it["name"]:
                it["category"] = v

    lines = ["# C站二次元 LoRA 精选（仅 Anima / MOSS Image / Krea 2）", ""]
    lines.append("> 数据源：Civitai 官方 API，types=LORA，period=Month，按下载量排序")
    lines.append("> 已排除全部写实类（UltraReal、Famegrid、Phone Photography、PureLens 等）")
    lines.append("")

    order = ["画风/画师", "姿势", "构图", "光影"]
    for cat in order:
        sub = [i for i in items if i["category"] == cat]
        sub.sort(key=lambda x: -x["downloads"])
        if cat == "画风/画师":
            sub = sub[:20]
        elif cat == "姿势":
            sub = sub[:13]
        lines.append(f"## {cat}（{len(sub)} 个）")
        lines.append("")
        lines.append("| 名称 | 支持底模 | 下载 | 作用 |")
        lines.append("|---|---|---|---|")
        for it in sub:
            nm = it["name"].replace("|", "\\|")[:60]
            bases = "/".join(it["bases"])
            dl = f"{it['downloads']:,}"
            pp = purpose_of(it["name"], it.get("desc", "")).replace("|", "\\|")
            lines.append(f"| {nm} | {bases} | {dl} | {pp} |")
        lines.append("")

    lines.append("## 统计")
    lines.append("")
    lines.append(f"- 筛选后总数：{lb['total']} 个（已排除写实）")
    for k, v in lb["stats"].items():
        lines.append(f"- {k}：{v}")
    lines.append("")
    lines.append("## 重要观察")
    lines.append("")
    lines.append("- **画风/画师是绝对主流**（90/181），C站二次元 LoRA 生态几乎都在卷画风")
    lines.append("- **姿势类 13 个里全是体型滑块**（体重/胸/腿/腰/臀/身高），真正的「动作姿势」LoRA 极少")
    lines.append("- **构图只有 6 个**，且集中在 POV/视角类，通用构图控制几乎没有")
    lines.append("- **光影只有 4 个**，是二次元 LoRA 生态最薄弱的一环")
    lines.append("")
    lines.append("> 结论：姿势/构图/光影的缺口，靠 LoRA 补不齐，必须靠 ControlNet/深度图方案（见 pose-gallery）")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("written:", OUT)
    print("分类统计:", json.dumps(lb["stats"], ensure_ascii=False))


if __name__ == "__main__":
    main()

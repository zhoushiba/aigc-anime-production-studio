"""行业常量：题材、镜头语言、画风预设、故事结构模板、质检清单。

这些常量同时被「提示词构建器」「种子数据」「前端下拉框」使用，
集中在一处可以避免前后端枚举漂移。
"""

from __future__ import annotations

# ---------------- 剧集 ----------------
GENRES = ("热血", "日常", "悬疑", "治愈", "科幻", "搞笑", "奇幻")

PLATFORMS = {
    "vertical_short": "竖屏短视频",
    "horizontal_series": "横屏番剧",
}

PLATFORM_RESOLUTION = {
    "vertical_short": "1080x1920",
    "horizontal_series": "1920x1080",
}

SERIES_STATUS_LABELS = {
    "draft": "策划中",
    "in_production": "制作中",
    "review": "审核中",
    "completed": "已完成",
    "archived": "已归档",
}

EPISODE_STATUS_LABELS = {
    "draft": "草稿",
    "scripting": "编剧",
    "storyboard": "分镜",
    "generating": "生成素材",
    "editing": "剪辑合成",
    "review": "审核",
    "delivered": "已交付",
}

# ---------------- 镜头语言 ----------------
SHOT_SIZES = ("远景", "全景", "中景", "近景", "特写")

SHOT_SIZE_PROMPT = {
    "远景": "extreme wide shot, establishing shot, tiny figures in vast environment",
    "全景": "full shot, full body in frame, environment visible",
    "中景": "medium shot, waist-up framing, background slightly blurred",
    "近景": "close-up shot, chest-up framing, detailed expression",
    "特写": "extreme close-up, eyes and facial detail, shallow depth of field",
}

CAMERA_ANGLE_PROMPT = {
    "平视": "eye-level camera angle, natural perspective",
    "俯视": "high angle shot looking down, subject appears vulnerable",
    "仰视": "low angle shot looking up, subject appears powerful",
    "斜视": "dutch angle, tilted horizon, uneasy mood",
    "主观": "POV shot, first person perspective",
}

CAMERA_MOVES = ("固定", "推", "拉", "摇", "移", "跟", "升降")

CAMERA_MOVE_PROMPT = {
    "固定": "static camera, locked-off frame",
    "推": "slow dolly in, push-in, increasing intimacy",
    "拉": "dolly out, pull-back reveal",
    "摇": "pan across the scene",
    "移": "lateral tracking move",
    "跟": "follow shot, camera tracks the character",
    "升降": "crane up, rising camera",
}

TRANSITIONS = {
    "cut": "硬切",
    "dissolve": "叠化",
    "wipe": "划像",
    "fade": "淡入淡出",
}

LIGHTING_PROMPT = {
    "日": "bright daylight, soft rim light, warm highlights",
    "黄昏": "golden hour, long shadows, orange backlight",
    "夜": "night scene, cool moonlight, practical neon accents",
    "雨": "rainy atmosphere, wet reflections, misty diffusion",
    "室内": "interior lighting, soft window light, cozy ambience",
}

QUALITY_WORDS = (
    "masterpiece, best quality, ultra detailed, cinematic composition, "
    "dramatic lighting, film grain, 4k, sharp focus"
)

DEFAULT_NEGATIVE = (
    "lowres, worst quality, blurry, jpeg artifacts, watermark, signature, text, "
    "bad anatomy, extra fingers, missing fingers, deformed, disfigured, "
    "extra limbs, mutated hands, long neck, cross-eyed"
)

# ---------------- 画风模板（内置 12 套） ----------------
STYLE_PRESETS: list[dict] = [
    {
        "name": "日系赛璐璐",
        "style_key": "cel_shading",
        "content": "Japanese anime cel shading, clean crisp lineart, flat color blocks, two-tone shadows",
        "negative_prompt": "3d render, photorealistic, messy lines",
        "description": "电视动画标配画风，线条干净、色块平涂，适合量产分镜",
        "tags": "TV动画,量产,高性价比",
    },
    {
        "name": "厚涂剧场版",
        "style_key": "impasto",
        "content": "thick impasto digital painting, painterly brush strokes, rich volume, cinematic key light",
        "negative_prompt": "flat colors, cel shading, lineart",
        "description": "剧场版质感，体积感强，适合关键镜头与海报",
        "tags": "剧场版,海报,高质感",
    },
    {
        "name": "国风水墨",
        "style_key": "chinese_ink",
        "content": "Chinese ink wash painting, xuan paper texture, elegant negative space, subtle pigment bleed",
        "negative_prompt": "western cartoon, neon, heavy saturation",
        "description": "水墨留白，适合东方奇幻与古风题材",
        "tags": "国风,古风,艺术向",
    },
    {
        "name": "赛博霓虹",
        "style_key": "cyberpunk",
        "content": "cyberpunk neon city, holographic signage, rain-slick reflective streets, volumetric haze",
        "negative_prompt": "pastoral, sunny countryside, low contrast",
        "description": "高对比霓虹光影，适合科幻与都市悬疑",
        "tags": "科幻,赛博,夜景",
    },
    {
        "name": "清新水彩",
        "style_key": "watercolor",
        "content": "soft watercolor illustration, bleeding pigments, visible paper grain, gentle gradients",
        "negative_prompt": "hard edges, heavy black ink, 3d shading",
        "description": "柔和通透，适合治愈日常与回忆段落",
        "tags": "治愈,日常,回忆",
    },
    {
        "name": "3D 渲染",
        "style_key": "pixar_3d",
        "content": "3D render, stylized Pixar-like character, subsurface scattering, octane render, ambient occlusion",
        "negative_prompt": "2d flat, sketch, rough lineart",
        "description": "三维卡通风，适合合家欢与预告片",
        "tags": "3D,合家欢,预告",
    },
    {
        "name": "吉卜力风",
        "style_key": "ghibli",
        "content": "Studio Ghibli style, lush hand-painted backgrounds, warm nostalgic light, soft clouds",
        "negative_prompt": "cyberpunk, harsh neon, dystopian",
        "description": "手绘自然背景，情绪温暖，适合治愈系番剧",
        "tags": "治愈,自然,怀旧",
    },
    {
        "name": "蒸汽波复古",
        "style_key": "vaporwave",
        "content": "vaporwave aesthetic, pastel gradient grid, retro 80s chrome, glitch accents",
        "negative_prompt": "medieval, naturalistic, muted colors",
        "description": "复古电子风，适合 MV 与实验短片",
        "tags": "MV,实验,复古",
    },
    {
        "name": "黑白漫画",
        "style_key": "manga",
        "content": "black and white manga panel, screentone shading, high contrast ink, dramatic speed lines",
        "negative_prompt": "full color, painterly, soft gradients",
        "description": "网点纸质感，适合战斗与心理描写",
        "tags": "漫画,战斗,心理",
    },
    {
        "name": "新海诚光色",
        "style_key": "shinkai",
        "content": "Makoto Shinkai style, hyper-detailed sky, lens flare, saturated dusk gradients, emotional lighting",
        "negative_prompt": "flat lighting, low detail sky, muddy colors",
        "description": "极致天空与光晕，适合青春情感戏",
        "tags": "青春,情感,天空",
    },
    {
        "name": "像素游戏",
        "style_key": "pixel_art",
        "content": "pixel art, 16-bit palette, crisp pixel edges, retro game sprite composition",
        "negative_prompt": "smooth gradients, 3d render, photorealistic",
        "description": "复古像素，适合短片彩蛋与游戏联动",
        "tags": "像素,复古,彩蛋",
    },
    {
        "name": "美式卡通",
        "style_key": "cartoon",
        "content": "American cartoon, bold clean outlines, exaggerated expressions, saturated primaries",
        "negative_prompt": "anime, subtle shading, muted palette",
        "description": "夸张表情与粗线条，适合搞笑向短视频",
        "tags": "搞笑,短视频,夸张",
    },
]

STYLE_BY_KEY = {item["style_key"]: item for item in STYLE_PRESETS}

# ---------------- 故事结构模板 ----------------
STRUCTURE_TEMPLATES: dict[str, dict] = {
    "three_act": {
        "name": "三幕式",
        "description": "建置 → 对抗 → 解决。商业动画短片最稳的结构，冲突递进清晰。",
        "acts": [
            {"act": 1, "title": "第一幕 · 建置", "hint": "交代世界、主角与日常，10% 处埋下情感钩子（约 25% 篇幅）"},
            {"act": 2, "title": "第二幕 · 对抗", "hint": "主角遭遇阻碍，冲突升级两次，中点发生反转（约 50% 篇幅）"},
            {"act": 3, "title": "第三幕 · 解决", "hint": "高潮对决 + 情绪落点，回扣开场的钩子（约 25% 篇幅）"},
        ],
    },
    "qi_cheng_zhuan_he": {
        "name": "起承转合",
        "description": "东方叙事的四段式，短篇幅里节奏更紧，适合 60-120 秒竖屏短片。",
        "acts": [
            {"act": 1, "title": "起", "hint": "一个具体的生活切片，快速建立人物关系（15 秒内）"},
            {"act": 2, "title": "承", "hint": "日常被一件小事扰动，细节堆叠情绪"},
            {"act": 3, "title": "转", "hint": "意外反转或误会揭开，情绪峰值"},
            {"act": 4, "title": "合", "hint": "回到日常但有变化，用一个物件/动作收尾"},
        ],
    },
    "hero_journey": {
        "name": "英雄之旅（简化）",
        "description": "召唤 → 试炼 → 回归，适合热血成长向番剧单集。",
        "acts": [
            {"act": 1, "title": "平凡世界与召唤", "hint": "主角的缺口被点明，收到一个无法拒绝的邀请"},
            {"act": 2, "title": "跨越门槛", "hint": "第一次踏出舒适区，遇到导师与伙伴"},
            {"act": 3, "title": "试炼与深渊", "hint": "最大挫败，主角失去某个依靠"},
            {"act": 4, "title": "顿悟与回归", "hint": "用开场埋下的物件完成成长闭环"},
        ],
    },
}

# ---------------- 质检清单 ----------------
QUALITY_ITEMS: list[dict] = [
    {"key": "character_consistency", "label": "角色一致性（发型/瞳色/服装跨镜头统一）", "category": "画面"},
    {"key": "color_uniform", "label": "色彩统一（同一场次色调不跳）", "category": "画面"},
    {"key": "storyboard_complete", "label": "分镜齐全（场次与镜头无缺失、无跳切）", "category": "叙事"},
    {"key": "duration_ok", "label": "时长达标（成片总时长与目标误差 ±10% 内）", "category": "节奏"},
    {"key": "subtitle_proofread", "label": "字幕无错字、时间轴对齐台词", "category": "字幕"},
    {"key": "resolution_bitrate", "label": "分辨率与码率满足平台要求", "category": "技术"},
    {"key": "platform_comp", "label": "平台合规（竖屏安全区、封面比例、无版权风险）", "category": "交付"},
    {"key": "audio_mix", "label": "音效与 BGM 混音平衡，无爆音", "category": "声音"},
]

# ---------------- 生成参数枚举 ----------------
GENERATION_KINDS = {
    "text2image": "文生图",
    "img2video": "图生视频",
}

TASK_STATUS_LABELS = {
    "queued": "排队中",
    "running": "生成中",
    "succeeded": "成功",
    "failed": "失败",
    "timeout": "超时",
    "canceled": "已取消",
}

ASSET_STATUS_LABELS = {
    "candidate": "候选",
    "selected": "入选",
    "rejected": "淘汰",
    "archived": "归档",
}

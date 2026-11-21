"""提示词构建器。

核心公式（对应 JD 的「AIGC 工具应用」能力）：

    主体 + 动作 + 镜头语言 + 画风 + 光影 + 画质词 + 负向词

镜头语言由景别 / 机位 / 运镜三部分拼装；角色与场景卡提供一致性前缀
（外形 prompt、LoRA、seed），保证同一角色跨镜头不跑形。
"""

from __future__ import annotations

from typing import Any

from app.constants import (
    CAMERA_ANGLE_PROMPT,
    CAMERA_MOVE_PROMPT,
    DEFAULT_NEGATIVE,
    QUALITY_WORDS,
    SHOT_SIZE_PROMPT,
    STYLE_PRESETS,
)

# 景别 → 英文/中文混合提示词（若 constants 中缺失则用这里的兜底）
_SHOT_FALLBACK = {
    "远景": "wide establishing shot, tiny subject in vast scenery",
    "全景": "full shot, full body in frame",
    "中景": "medium shot, waist up",
    "近景": "close-up shot, head and shoulders",
    "特写": "extreme close-up, detailed eyes",
}
_ANGLE_FALLBACK = {
    "平视": "eye-level angle",
    "俯视": "high angle looking down",
    "仰视": "low angle looking up",
    "斜视": "dutch angle",
    "主观": "POV shot",
}
_MOVE_FALLBACK = {
    "固定": "static camera",
    "推": "dolly in, push in",
    "拉": "dolly out, pull back",
    "摇": "pan camera",
    "移": "trucking shot",
    "跟": "tracking shot",
    "升降": "crane shot, vertical move",
}
_LIGHTING_FALLBACK = {
    "黄昏逆光": "golden hour backlight, rim light",
    "夜晚霓虹": "neon night lighting, cyan and magenta",
    "清晨柔光": "soft morning light, low contrast",
    "室内暖光": "warm indoor practical light",
    "阴天散射": "overcast diffuse light",
    "月光": "moonlight, cool blue tone",
    "火光": "firelight, warm flicker",
    "影棚布光": "studio three-point lighting",
}
_QUALITY_FALLBACK = "masterpiece, best quality, ultra detailed, sharp focus, cinematic composition, 8k"

# 二次优化：问题码 → 追加修正词（英文，直接进 prompt）
REVISION_FIXES: dict[str, str] = {
    "hand_broken": "perfect detailed hands, five fingers, anatomically correct",
    "face_broken": "detailed symmetric face, clean facial features, consistent character face",
    "composition_off": "balanced composition, rule of thirds, subject centered",
    "color_inconsistent": "color grade consistent with previous shots, unified palette",
    "extra_limbs": "exactly two arms and two legs, correct anatomy",
    "blurry": "sharp focus, high resolution, crisp line art",
    "text_artifact": "no text, no watermark, no letters in image",
    "style_drift": "consistent anime style, same line weight, matching character design",
}

REVISION_LABELS: dict[str, str] = {
    "hand_broken": "手部结构错误",
    "face_broken": "脸部崩坏",
    "composition_off": "构图偏移",
    "color_inconsistent": "色调不一致",
    "extra_limbs": "多余肢体",
    "blurry": "模糊 / 分辨率不足",
    "text_artifact": "出现文字水印",
    "style_drift": "画风漂移",
}


def _pick(mapping: Any, key: str, fallback: dict[str, str], default: str = "") -> str:
    """兼容 constants 里 dict / list 两种存储形态。"""
    if isinstance(mapping, dict):
        value = mapping.get(key)
        if isinstance(value, dict):
            return str(value.get("prompt") or value.get("en") or value.get("label") or default)
        if isinstance(value, str):
            return value
    if isinstance(mapping, list):
        for item in mapping:
            if isinstance(item, dict) and (item.get("key") == key or item.get("name") == key):
                return str(item.get("prompt") or item.get("en") or item.get("label") or default)
    return fallback.get(key, default)


def _normalize_style(item: dict[str, Any]) -> dict[str, Any]:
    """把 constants.STYLE_PRESETS 的字段（style_key/content/negative_prompt）统一成 key/prompt/negative。"""
    normalized = dict(item)
    normalized["key"] = str(item.get("key") or item.get("style_key") or item.get("name") or "")
    normalized["name"] = str(item.get("name") or normalized["key"])
    normalized["prompt"] = str(item.get("prompt") or item.get("content") or "")
    normalized["negative"] = str(item.get("negative") or item.get("negative_prompt") or "")
    normalized["tags"] = str(item.get("tags") or "")
    return normalized


def style_preset(style: str) -> dict[str, Any]:
    """取画风预设（含 prompt / negative / palette 等）。"""
    raw = STYLE_PRESETS
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                items.append({"key": key, **value})
            else:
                items.append({"key": key, "name": key, "prompt": str(value)})
    elif isinstance(raw, list):
        items = [_normalize_style(item) for item in raw if isinstance(item, dict)]

    for item in items:
        aliases = {str(item.get("key", "")), str(item.get("name", "")), str(item.get("label", "")), str(item.get("style", ""))}
        if style in aliases:
            return item
    return {
        "key": style,
        "name": style,
        "prompt": f"{style} anime style",
        "negative": "",
        "palette": "",
    }


def style_choices() -> list[dict[str, str]]:
    """给前端下拉框用的画风列表。"""
    raw = STYLE_PRESETS
    if isinstance(raw, dict):
        return [
            {"key": key, "name": (value.get("name") if isinstance(value, dict) else str(value)) or key}
            for key, value in raw.items()
        ]
    if isinstance(raw, list):
        choices = []
        for item in raw:
            if isinstance(item, dict):
                normalized = _normalize_style(item)
                choices.append({"key": normalized["key"], "name": normalized["name"], "tags": normalized["tags"]})
        return choices
    return []


def build_prompt(
    *,
    subject: str = "",
    action: str = "",
    shot_size: str = "中景",
    camera_angle: str = "平视",
    camera_move: str = "固定",
    style: str = "日系赛璐璐",
    lighting: str = "",
    quality: str = "",
    negative: str = "",
    consistency_prefix: str = "",
    consistency_tokens: list[str] | None = None,
) -> dict[str, Any]:
    """按公式拼装正向 / 负向提示词，并回传拆解明细供前端展示。"""
    preset = style_preset(style)
    style_prompt = str(preset.get("prompt") or f"{style} anime style")
    style_negative = str(preset.get("negative") or "")

    parts = {
        "subject": subject.strip(),
        "action": action.strip(),
        "shot": ", ".join(
            [
                _pick(SHOT_SIZE_PROMPT, shot_size, _SHOT_FALLBACK),
                _pick(CAMERA_ANGLE_PROMPT, camera_angle, _ANGLE_FALLBACK),
                _pick(CAMERA_MOVE_PROMPT, camera_move, _MOVE_FALLBACK),
            ]
        ),
        "style": style_prompt,
        "lighting": _pick(_LIGHTING_FALLBACK, lighting, _LIGHTING_FALLBACK) if lighting else "",
        "quality": quality.strip() or QUALITY_WORDS.get("default", _QUALITY_FALLBACK)
        if isinstance(QUALITY_WORDS, dict)
        else (quality.strip() or _QUALITY_FALLBACK),
        "consistency": ", ".join([token for token in ([consistency_prefix] + (consistency_tokens or [])) if token]),
    }
    ordered = [parts[key] for key in ("subject", "action", "shot", "style", "lighting", "quality", "consistency")]
    prompt = ", ".join([chunk for chunk in ordered if chunk])

    negatives = [chunk for chunk in (negative.strip(), style_negative, DEFAULT_NEGATIVE) if chunk]
    return {
        "prompt": prompt,
        "negative_prompt": ", ".join(negatives),
        "parts": parts,
        "style": {"key": preset.get("key", style), "name": preset.get("name", style)},
    }


def build_from_shot(
    shot: Any,
    *,
    style: str,
    character: Any | None = None,
    scene_card: Any | None = None,
    consistency: bool = True,
) -> dict[str, Any]:
    """从分镜行生成提示词：自动带上角色/场景一致性信息。"""
    prefixes: list[str] = []
    tokens: list[str] = []
    if scene_card is not None:
        if scene_card.prompt_prefix:
            prefixes.append(str(scene_card.prompt_prefix))
        if scene_card.prompt:
            prefixes.append(str(scene_card.prompt))
        if consistency and scene_card.seed:
            tokens.append(f"scene seed {scene_card.seed}")
    if character is not None:
        if character.prompt_prefix:
            prefixes.append(str(character.prompt_prefix))
        if character.appearance_prompt:
            prefixes.append(str(character.appearance_prompt))
        if consistency:
            if character.lora_name:
                tokens.append(f"lora:{character.lora_name}:{character.lora_weight}")
            if character.seed:
                tokens.append(f"character seed {character.seed}")

    subject = str(getattr(shot, "description", "") or "")
    if not subject:
        subject = ", ".join([p for p in (getattr(shot, "characters", ""), getattr(shot, "dialogue", "")) if p])
    return build_prompt(
        subject=subject,
        action=str(getattr(shot, "description", "") or ""),
        shot_size=str(getattr(shot, "shot_size", "中景")),
        camera_angle=str(getattr(shot, "camera_angle", "平视")),
        camera_move=str(getattr(shot, "camera_move", "固定")),
        style=style,
        negative=str(getattr(shot, "negative_prompt", "") or ""),
        consistency_prefix=", ".join(prefixes),
        consistency_tokens=tokens,
    )


def fix_prompt(base_prompt: str, issues: list[str]) -> str:
    """二次优化：把问题码翻译成修正词追加到原 prompt 后面。"""
    fixes = [REVISION_FIXES[code] for code in issues if code in REVISION_FIXES]
    if not fixes:
        return base_prompt
    return f"{base_prompt}, {', '.join(fixes)}"


def issue_choices() -> list[dict[str, str]]:
    return [{"key": key, "label": label} for key, label in REVISION_LABELS.items()]

"""离线占位图渲染。

MockProvider 用它按 (seed, prompt) 确定性地画出「动漫风」场景占位图：
渐变天空 + 光斑 + 速度线 + 山脊剪影 + 分镜信息文字块，再生成缩略图。
同一 seed + 同一 prompt 永远得到同一张图，方便复现与对比。
"""

from __future__ import annotations

import colorsys
import hashlib
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def load_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, min(1.0, max(0.0, s)), min(1.0, max(0.0, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def palette_from_seed(seed: int) -> dict[str, tuple[int, int, int]]:
    """由 seed 推导一套稳定的配色。"""
    hue = ((seed * 2654435761) % 1000) / 1000.0
    return {
        "sky_top": _rgb(hue, 0.55, 0.28),
        "sky_bottom": _rgb(hue + 0.08, 0.45, 0.85),
        "glow": _rgb(hue + 0.10, 0.35, 1.0),
        "accent": _rgb(hue + 0.55, 0.70, 0.95),
        "ink": _rgb(hue + 0.02, 0.60, 0.12),
        "ridge": _rgb(hue + 0.02, 0.70, 0.22),
    }


def _wrap(text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 4) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text.replace("\r", ""):
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        try:
            width = font.getlength(current + char)
        except AttributeError:  # 极老版本 Pillow
            width = len(current + char) * 8
        if width > max_width and current:
            lines.append(current)
            current = char
        else:
            current += char
    if current:
        lines.append(current)
    return lines[:max_lines]


def render_placeholder(
    *,
    seed: int,
    size: tuple[int, int],
    prompt: str,
    shot_label: str = "",
    style_label: str = "",
    kind: str = "text2image",
    provider: str = "mock",
) -> Image.Image:
    """按 seed 确定性渲染一张占位图。"""
    width, height = max(64, int(size[0])), max(64, int(size[1]))
    rng = random.Random(seed)
    colors = palette_from_seed(seed)
    image = Image.new("RGB", (width, height), colors["sky_top"])
    draw = ImageDraw.Draw(image)

    # 1) 竖向渐变天空
    for y in range(height):
        draw.line([(0, y), (width, y)], fill=_lerp(colors["sky_top"], colors["sky_bottom"], y / (height - 1)))

    # 2) 光斑（高斯模糊后叠加，模拟景深）
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(10):
        radius = rng.randint(width // 14, max(width // 14 + 1, width // 2))
        cx = rng.randint(-width // 3, width)
        cy = rng.randint(-height // 4, height // 2)
        odraw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*colors["glow"], rng.randint(24, 70)),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(2, width // 110)))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")

    # 3) 斜向速度线（动感）
    for _ in range(22):
        x = rng.randint(-width, width + width // 3)
        thickness = rng.randint(1, max(2, width // 260))
        draw.line([(x, height), (x + height // 3, 0)], fill=(255, 255, 255, rng.randint(14, 44)), width=thickness)

    # 4) 地平线与山脊剪影
    horizon = int(height * (0.62 + rng.random() * 0.1))
    ridge_points = [(0, height), (0, horizon)]
    step = max(24, width // 12)
    y = horizon
    for x in range(0, width + step, step):
        y = horizon - rng.randint(0, max(4, height // 14))
        ridge_points.append((x, y))
    ridge_points.extend([(width, horizon), (width, height)])
    draw.polygon(ridge_points, fill=(*colors["ridge"], 255))
    draw.line(ridge_points[1:-2], fill=(*colors["accent"], 120), width=max(2, width // 400))

    # 5) 主体剪影（一个人物轮廓，让画面更像分镜）
    cx = int(width * (0.35 + rng.random() * 0.3))
    base = int(height * 0.86)
    body_h = int(height * (0.22 + rng.random() * 0.08))
    head_r = max(6, int(body_h * 0.18))
    draw.ellipse([cx - head_r, base - body_h - head_r * 2, cx + head_r, base - body_h], fill=(*colors["ink"], 235))
    draw.polygon(
        [(cx - head_r * 2, base), (cx + head_r * 2, base), (cx + head_r, base - body_h), (cx - head_r, base - body_h)],
        fill=(*colors["ink"], 235),
    )

    # 6) 暗角
    vignette = Image.new("L", (width, height), 0)
    vdraw = ImageDraw.Draw(vignette)
    pad = int(min(width, height) * 0.12)
    vdraw.ellipse([-pad, -pad, width + pad, height + pad], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(int(min(width, height) * 0.08)))
    black = Image.new("RGB", (width, height), (0, 0, 0))
    image = Image.composite(image, black, vignette.point(lambda v: 120 + int(v * 0.53)))

    # 7) 信息文字块
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(max(14, width // 26))
    body_font = load_font(max(11, width // 44))
    tag_font = load_font(max(10, width // 56))
    band_top = int(height * 0.70)
    draw.rectangle([0, band_top, width, height], fill=(8, 10, 24, 150))

    label = " / ".join([part for part in (style_label, shot_label) if part]) or "分镜预览"
    draw.text((int(width * 0.05), band_top + int(height * 0.018)), label, font=title_font, fill=(255, 255, 255, 235))

    text_lines = _wrap(prompt or "（空提示词）", body_font, int(width * 0.90), max_lines=3)
    line_y = band_top + int(height * 0.018) + int(height * 0.045)
    for line in text_lines:
        draw.text((int(width * 0.05), line_y), line, font=body_font, fill=(226, 232, 240, 220))
        line_y += int(height * 0.032)

    footer = f"{provider.upper()} · {kind.upper()} · seed {seed}"
    draw.text((int(width * 0.05), height - int(height * 0.055)), footer, font=tag_font, fill=(160, 174, 192, 220))
    watermark = "AI 生成占位图"
    draw.text(
        (width - int(width * 0.05) - int(tag_font.getlength(watermark)), height - int(height * 0.055)),
        watermark,
        font=tag_font,
        fill=(160, 174, 192, 220),
    )
    return image


def save_asset_image(
    image: Image.Image,
    *,
    directory: Path,
    thumbs_dir: Path,
    stem: str,
    thumb_width: int = 320,
) -> dict[str, object]:
    """落盘主图 + 缩略图，返回相对路径与尺寸信息。"""
    directory.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:8]
    filename = f"{stem}-{digest}.png"
    main_path = directory / filename
    image.save(main_path, format="PNG", optimize=True)

    ratio = thumb_width / max(1, image.width)
    thumb = image.resize((thumb_width, max(1, int(image.height * ratio))), Image.LANCZOS)
    thumb_path = thumbs_dir / f"{stem}-{digest}.jpg"
    thumb.save(thumb_path, format="JPEG", quality=82)

    return {
        "filename": filename,
        "path": main_path,
        "thumb_path": thumb_path,
        "width": image.width,
        "height": image.height,
        "file_size": main_path.stat().st_size,
    }

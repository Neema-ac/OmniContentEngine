"""
Renders an actual downloadable PNG thumbnail from a blueprint the model produced,
instead of only describing what a thumbnail should look like.
"""

import base64
import io

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

_font_cache = {}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, size)
            _font_cache[size] = font
            return font
        except Exception:
            continue
    font = ImageFont.load_default(size=size) if hasattr(ImageFont, "load_default") else ImageFont.load_default()
    _font_cache[size] = font
    return font


def _hex_to_rgb(hex_color: str, fallback=(30, 30, 30)):
    try:
        h = (hex_color or "").strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            return fallback
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _gradient_background(width: int, height: int, primary_rgb, secondary_rgb, angle: int = 35) -> Image.Image:
    """Diagonal gradient using PIL's built-in linear_gradient (fast, no numpy needed)."""
    base = Image.linear_gradient("L").rotate(angle, expand=True, resample=Image.BICUBIC)
    base = base.resize((width * 2, height * 2))
    left = (base.width - width) // 2
    top = (base.height - height) // 2
    base = base.crop((left, top, left + width, top + height))
    colorized = ImageOps.colorize(base, black=secondary_rgb, white=primary_rgb)
    return colorized.convert("RGB")


def _add_vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    """Darkens the edges slightly so foreground text/subject pops more."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([-w * 0.3, -h * 0.3, w * 1.3, h * 1.3], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.18)))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    vignette = Image.composite(img, dark, mask)
    return Image.blend(img, vignette, strength)


def _add_grain(img: Image.Image, opacity: int = 14) -> Image.Image:
    """Light film-grain texture so flat gradients read as designed, not generated."""
    w, h = img.size
    noise = Image.effect_noise((w, h), 22).convert("L")
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, noise_rgb, opacity / 255)


def _fit_headline_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_height: int,
                        candidate_sizes=(88, 78, 68, 58, 50, 44)):
    """Picks the largest font size where the wrapped headline fits both max_width and max_height."""
    best = None
    for size in candidate_sizes:
        font = _load_font(size)
        lines = _wrap_text(draw, text, font, max_width)
        line_height = size + 6
        if len(lines) <= 2 and line_height * len(lines) <= max_height:
            return font, lines
        best = (font, lines[:2])
    return best


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_thumbnail_image(
    overlay_text: str,
    sub_text: str = "",
    primary_hex: str = "#E11D48",
    secondary_hex: str = "#111827",
    width: int = 1280,
    height: int = 720,
) -> bytes:
    primary_rgb = _hex_to_rgb(primary_hex, (225, 29, 72))
    secondary_rgb = _hex_to_rgb(secondary_hex, (17, 24, 39))

    img = _gradient_background(width, height, primary_rgb, secondary_rgb)
    img = _add_vignette(img)
    img = _add_grain(img)
    draw = ImageDraw.Draw(img, "RGBA")

    # Legibility panel behind the text
    panel_height = int(height * 0.34)
    draw.rectangle([0, height - panel_height, width, height], fill=(0, 0, 0, 155))

    headline = (overlay_text or "VIRAL HOOK").upper()
    margin = 48
    top_pad, bottom_pad = 22, 18
    sub_font = _load_font(32)
    sub_block_height = (sub_font.size + 14) if sub_text else 0
    max_text_width = width - 2 * margin
    max_headline_height = panel_height - top_pad - bottom_pad - sub_block_height
    headline_font, lines = _fit_headline_font(draw, headline, max_text_width, max_headline_height)

    y = height - panel_height + top_pad
    for line in lines:
        draw.text((margin, y), line, font=headline_font, fill=(255, 255, 255, 255),
                   stroke_width=5, stroke_fill=(0, 0, 0, 255))
        y += headline_font.size + 6

    if sub_text:
        draw.text((margin, y + 10), sub_text, font=sub_font, fill=(225, 225, 225, 255))

    # Thin frame for a cleaner, more finished edge
    border_color = tuple(min(255, c + 40) for c in primary_rgb) + (200,)
    draw.rectangle([0, 0, width - 1, height - 1], outline=border_color, width=6)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_thumbnail_data_uri(**kwargs) -> str:
    png_bytes = generate_thumbnail_image(**kwargs)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"
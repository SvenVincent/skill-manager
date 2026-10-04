#!/usr/bin/env python3
"""生成安装包界面素材：

- src-tauri/icons/dmg-background.png   macOS DMG 拖拽安装背景（窗口 660x400pt 的 2x 图）
- src-tauri/icons/nsis-header.bmp      Windows NSIS 安装器顶栏位图（150x57）
- src-tauri/icons/nsis-sidebar.bmp     Windows NSIS 欢迎页侧边位图（164x314）

配色取自应用图标源图（app-icon.png）四角采样，重新生成图标后如需同步安装界面可再跑：
    python3 scripts/generate-installer-art.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src-tauri" / "icons"
APP_ICON = ICONS / "app-icon.png"

# 与源图四角一致的渐变色（TL/TR/BL/BR）
TL = (0x20, 0x42, 0xF3)
TR = (0x24, 0xA8, 0xE4)  # 源图右上角偏青，略压暗保证标题可读
BL = (0x8D, 0x2B, 0xFD)
BR = (0x17, 0x4B, 0xEF)
CYAN = (0x6F, 0xE9, 0xFF)

CJK_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"  # index 0=W3, 1=W6
LATIN_FONT = "/System/Library/Fonts/SFNS.ttf"


def font(path: str, size: int, index: int = 0, bold: bool = False) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(path, size, index=index)
    if bold:
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def gradient(size: tuple[int, int], tl, tr, bl, br) -> Image.Image:
    """四角双线性渐变：顶行/底行先做横向插值，再逐行纵向混合。"""
    w, h = size
    top_row = Image.new("RGB", (w, 1))
    bottom_row = Image.new("RGB", (w, 1))
    tp, bp = top_row.load(), bottom_row.load()
    for x in range(w):
        t = x / (w - 1)
        tp[x, 0] = tuple(round(a + (b - a) * t) for a, b in zip(tl, tr))
        bp[x, 0] = tuple(round(a + (b - a) * t) for a, b in zip(bl, br))
    out = Image.new("RGB", (w, h))
    for y in range(h):
        out.paste(Image.blend(top_row, bottom_row, y / (h - 1)), (0, y))
    return out


def add_alpha(img: Image.Image) -> Image.Image:
    return img.convert("RGBA")


def rounded(img: Image.Image, radius: int) -> Image.Image:
    """给不透明图加圆角，返回 RGBA。"""
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def radial_glow(size: tuple[int, int], color, peak_alpha: int) -> Image.Image:
    """中心亮斑。"""
    w, h = size
    small = 64
    g = Image.new("L", (small, small), 0)
    gp = g.load()
    for y in range(small):
        for x in range(small):
            d = ((x - small / 2) ** 2 + (y - small / 2) ** 2) ** 0.5 / (small / 2)
            gp[x, y] = max(0, round(peak_alpha * (1 - min(d, 1) ** 2)))
    g = g.resize((w, h), Image.BILINEAR)
    out = Image.new("RGBA", (w, h), color + (0,))
    out.putalpha(g)
    return out


def text_center(draw: ImageDraw.ImageDraw, xy_y: int, text: str, f: ImageFont.FreeTypeFont,
                fill, width: int, letter_spacing: int = 0) -> None:
    if letter_spacing:
        widths = [draw.textlength(ch, font=f) + letter_spacing for ch in text]
        total = sum(widths) - letter_spacing
        x = (width - total) / 2
        for ch, w_ch in zip(text, widths):
            draw.text((x, xy_y), ch, font=f, fill=fill)
            x += w_ch
    else:
        tw = draw.textlength(text, font=f)
        draw.text(((width - tw) / 2, xy_y), text, font=f, fill=fill)


# ---------------------------------------------------------------- DMG 背景
def dmg_background() -> Image.Image:
    W, H = 1320, 800  # 660x400pt @2x
    img = add_alpha(gradient((W, H), TL, TR, BL, BR))

    # 轨道环：呼应图标里的轨道线条
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((60, 90, W - 60, 90 + 560), outline=CYAN + (46,), width=5)
    rd.ellipse((170, 40, W - 170, 40 + 700), outline=(255, 255, 255, 26), width=4)
    img.alpha_composite(ring)

    # 顶/底部轻微压暗，保证文字可读
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(0, 240):
        a = round(70 * (1 - y / 240))
        sd.line([(0, y), (W, y)], fill=(10, 10, 40, a))
    for y in range(H - 240, H):
        a = round(80 * (1 - (H - y) / 240))
        sd.line([(0, y), (W, y)], fill=(10, 10, 40, a))
    img.alpha_composite(shade)

    # 两个图标落位的柔光，让拖拽目标更醒目
    # appPosition/applicationFolderPosition 默认 (180,170)/(480,170) pt → x2
    for cx, cy in ((488, 468), (1088, 468)):
        img.alpha_composite(radial_glow((520, 520), (255, 255, 255), 40),
                            (cx - 260, cy - 260))

    d = ImageDraw.Draw(img)

    # 标题 + 副标题
    title_f = font(LATIN_FONT, 84, bold=True)
    sub_f = font(CJK_FONT, 36, index=1)
    text_center(d, 96, "SkillManager", title_f, (255, 255, 255, 255), W, letter_spacing=6)
    text_center(d, 212, "AI Agent Skill 跨平台管理器", sub_f, (255, 255, 255, 215), W)

    # 拖拽箭头：应用图标槽 → Applications 槽
    y = 468
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle((646, y - 8, 880, y + 8), radius=8, fill=CYAN + (255,))
    gd.polygon([(876, y - 26), (932, y), (876, y + 26)], fill=CYAN + (255,))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((646, y - 8, 880, y + 8), radius=8, fill=CYAN + (255,))
    d.polygon([(876, y - 26), (932, y), (876, y + 26)], fill=CYAN + (255,))

    # 底部说明
    tip_f = font(CJK_FONT, 40, index=1)
    text_center(d, 682, "将 SkillManager 拖入「应用程序」文件夹完成安装", tip_f,
                (255, 255, 255, 240), W)

    return img.convert("RGB")


# ------------------------------------------------------------ NSIS 位图
def art_square(size: int, crop: tuple[int, int, int, int] | None = None) -> Image.Image:
    """从图标源图取方形素材并加圆角。"""
    src = Image.open(APP_ICON).convert("RGB")
    if crop:
        src = src.crop(crop)
    return rounded(src.resize((size, size), Image.LANCZOS), radius=round(size * 0.22))


def nsis_header() -> Image.Image:
    W, H = 150, 57
    img = add_alpha(gradient((W, H), TL, TR, BL, BR))
    img.alpha_composite(art_square(H - 8, crop=(382, 300, 642, 560)), (4, 4))
    d = ImageDraw.Draw(img)
    f = font(LATIN_FONT, 13, bold=True)
    d.text((58, (H - 16) / 2), "SkillManager", font=f, fill=(255, 255, 255, 255))
    return img.convert("RGB")


def nsis_sidebar() -> Image.Image:
    W, H = 164, 314
    img = add_alpha(gradient((W, H), TL, BL, TL, BR))  # 上下渐变
    img.alpha_composite(radial_glow((300, 300), (255, 255, 255), 46), (W // 2 - 150, -60))
    art = art_square(124)
    img.alpha_composite(art, ((W - 124) // 2, 34))
    d = ImageDraw.Draw(img)
    f1 = font(LATIN_FONT, 17, bold=True)
    f2 = font(CJK_FONT, 11)
    text_center(d, 182, "SkillManager", f1, (255, 255, 255, 255), W)
    text_center(d, 208, "AI Agent Skill 管理器", f2, (255, 255, 255, 210), W)
    return img.convert("RGB")


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    dmg_background().save(ICONS / "dmg-background.png", optimize=True)
    nsis_header().save(ICONS / "nsis-header.bmp")
    nsis_sidebar().save(ICONS / "nsis-sidebar.bmp")
    print("written:", *(p.name for p in sorted(ICONS.glob("*")) if p.name.startswith(("dmg", "nsis"))))


if __name__ == "__main__":
    main()

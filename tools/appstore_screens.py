"""App Store screenshots: a pastel dawn palette, one short headline + emoji badge in dark ink, and a big
phone bleeding off the bottom. The build slide shows Day 1 next to Day 30.
Usage: python tools/appstore_screens.py [slide names...]   (raw 1320x2868 captures in SRC)"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys

SRC = "/private/tmp/claude-501/-Users-jamesangrellera-RIZER/0b8b9016-7c85-49c1-b471-4f73b6285a01/scratchpad/store/"
OUT = "/Users/jamesangrellera/RIZER/docs/appstore/"
W, H = 1320, 2868
INK = (38, 40, 70)

def font(size, weight):
    f = ImageFont.truetype("/System/Library/Fonts/SFNSRounded.ttf", size)
    try: f.set_variation_by_axes([weight])
    except Exception: pass
    return f

EMOJI = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 160)

# Pastel dawn palette: every slide the same lightness, hues walking around the colour wheel.
SKY, PEACH, BUTTER, MINT, LILAC, APRICOT, SAGE, ROSE, PERI = (
    ((178, 212, 246), (222, 237, 252)),
    ((250, 200, 170), (253, 230, 212)),
    ((247, 224, 158), (252, 241, 205)),
    ((176, 226, 198), (220, 243, 228)),
    ((206, 192, 242), (232, 225, 250)),
    ((250, 212, 160), (253, 235, 208)),
    ((196, 218, 192), (228, 239, 224)),
    ((246, 192, 204), (251, 225, 230)),
    ((180, 188, 236), (219, 223, 248)),
)

shots = [  # (raw capture(s), emoji, headline, palette)
    ("home_morning", "☀️", "Meet your\nwake-up buddy", SKY),
    ("mission", "🎯", "Beat a mission to\nturn off the alarm", PEACH),
    ("farm", "🌾", "Crops only grow\nwhen you rise", BUTTER),
    ("reward", "💰", "Every morning\npays off", ROSE),
    (("day1", "day30"), "🏗️", "Watch your\nisland grow", MINT),
    ("streak", "🔥", "Gamified\naccountability", LILAC),
    ("sick", "🤒", "Sleep in?\nYour buddy feels it", SAGE),
    ("inside", "🏡", "Decorate a\ncozy home", APRICOT),
    ("night", "🌙", "Bedtime,\ntogether", PERI),
]

def background(c1, c2):
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W / 2 - 560, -420, W / 2 + 560, 640], fill=(255, 255, 255, 90))
    return Image.alpha_composite(bg.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(120)))

def emoji_badge(ch, size):
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=EMOJI, embedded_color=True)
    bbox = im.getbbox()
    im = im.crop(bbox) if bbox else im
    im.thumbnail((size, size), Image.LANCZOS)
    return im

def erase_island(img):
    """Paints the Dynamic Island out of a raw capture by blending the sky on either side of it."""
    px = img.load()
    x0, x1 = 420, 900
    for yy in range(10, 175):
        a, b = px[x0, yy], px[x1, yy]
        for xx in range(x0, x1):
            t = (xx - x0) / (x1 - x0)
            px[xx, yy] = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    return img

def phone(bg, name, x, top, sw, no_island=False):
    sh = int(sw * H / W)
    raw = Image.open(SRC + name + ".png").convert("RGB")
    if no_island:
        raw = erase_island(raw)
    shot = raw.resize((sw, sh), Image.LANCZOS)
    r, bz = int(sw * 0.11), max(8, int(sw * 0.015))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x - bz, top + 30, x + sw + bz, top + sh + 30], r + bz, fill=(60, 50, 90, 80))
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(44)))
    ImageDraw.Draw(bg).rounded_rectangle([x - bz, top - bz, x + sw + bz, top + sh + bz], r + bz, fill=(24, 24, 30))
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw, sh], r, fill=255)
    bg.paste(shot, (x, top), mask)
    return bg

def pill(bg, text, cx, y):
    f = font(46, 700)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = d.textlength(text, font=f)
    d.rounded_rectangle([cx - w / 2 - 30, y, cx + w / 2 + 30, y + 76], 38, fill=(255, 255, 255, 210))
    d.text((cx - w / 2, y + 12), text, font=f, fill=INK + (255,))
    return Image.alpha_composite(bg, layer)

def hero(bg, top):
    """The buddy sitting on the phone's top edge, with a speech bubble."""
    m = Image.open(OUT + "mochi_hero.png").convert("RGBA")
    m = m.crop(m.getbbox())
    mw = 440
    m = m.resize((mw, int(m.height * mw / m.width)), Image.LANCZOS)
    x, y = W // 2 - mw // 2, top + 70 - m.height
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([x + 50, y + m.height - 50, x + mw - 50, y + m.height + 20], fill=(20, 20, 40, 120))
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(22)))
    bg.alpha_composite(m, (x, y))
    f = font(58, 760)
    text = "Rise and shine!"
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = d.textlength(text, font=f)
    bx, by = W - (w + 72) - 36, y - 40
    d.rounded_rectangle([bx, by, bx + w + 72, by + 112], 56, fill=(255, 255, 255, 250))
    d.polygon([(bx + 40, by + 100), (bx + 100, by + 104), (bx - 10, by + 170)], fill=(255, 255, 255, 250))
    d.text((bx + 36, by + 22), text, font=f, fill=INK + (255,))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([bx, by + 12, bx + w + 72, by + 124], 56, fill=(40, 30, 70, 60))
    bg = Image.alpha_composite(bg, sh.filter(ImageFilter.GaussianBlur(18)))
    return Image.alpha_composite(bg, layer)

only = sys.argv[1:]
for i, (name, emoji, title, (c1, c2)) in enumerate(shots, 1):
    label = name if isinstance(name, str) else "build"
    if only and label not in only: continue
    bg = background(c1, c2)

    # Badge disc and headline on their own layers so alpha blends properly.
    soft = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, di = ImageDraw.Draw(soft), ImageDraw.Draw(ink)
    disc, cx = 210, W // 2
    ds.ellipse([cx - disc / 2, 120, cx + disc / 2, 120 + disc], fill=(255, 255, 255, 150))
    tf, track = font(114, 820), 2
    y = 120 + disc + 44
    for line in title.split("\n"):
        w = sum(di.textlength(c, font=tf) for c in line) + track * (len(line) - 1)
        x = (W - w) / 2
        for c in line:
            di.text((x, y), c, font=tf, fill=INK + (255,))
            x += di.textlength(c, font=tf) + track
        y += 136
    bg = Image.alpha_composite(bg, soft)
    e = emoji_badge(emoji, 128)
    bg.alpha_composite(e, (cx - e.width // 2, 120 + (disc - e.height) // 2))
    bg = Image.alpha_composite(bg, ink)

    top = y + 70 + (400 if label == "home_morning" else 0)
    if isinstance(name, str):
        bg = phone(bg, name, (W - 1080) // 2, top, 1080, no_island=label == "home_morning")
    else:
        # Day 1 over Day 30: wide cards cropped to the island so the difference reads at a glance.
        cw, gap = 1120, 44
        for k, (raw, tag) in enumerate(zip(name, ("Day 1", "Day 30"))):
            crop = Image.open(SRC + raw + ".png").convert("RGB").crop((0, 660, W, 1760))
            ch = int(crop.height * cw / crop.width)
            crop = crop.resize((cw, ch), Image.LANCZOS)
            x, yy = (W - cw) // 2, top + k * (ch + gap)
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle([x, yy + 24, x + cw, yy + ch + 24], 64, fill=(60, 50, 90, 70))
            bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(36)))
            mask = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw, ch], 64, fill=255)
            bg.paste(crop, (x, yy), mask)
            bg = pill(bg, tag, x + 150, yy + 36)

    if label == "home_morning":
        bg = hero(bg, top)

    bg.convert("RGB").save(OUT + f"{i:02d}_{label}.png")
    print(OUT + f"{i:02d}_{label}.png")

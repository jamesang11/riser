# Riser app icon: a flat sun rising over the horizon in a dawn sky (variant "A").
# Usage: python3 tools/icon_sun.py out.png A   (needs Pillow; variants B/C/D are the other explorations)
from PIL import Image, ImageDraw, ImageFilter
import math, sys
S = 4096            # supersampled canvas, downsampled to 1024
OUT = sys.argv[1]

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def vgrad(stops, size=S):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]; p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                k = (t - p0) / (p1 - p0) if p1 > p0 else 0
                d.line([(0, y), (size, y)], fill=lerp(hexc(c0), hexc(c1), k)); break
    return img

def radial_sun(r, inner, outer):
    """A disc with a soft top-to-bottom tint."""
    disc = vgrad([(0, inner), (1, outer)], size=2 * r)
    m = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    return disc, m

def glow(img, cx, cy, r, color, alpha):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    g = g.filter(ImageFilter.GaussianBlur(r * 0.35))
    img.alpha_composite(g)

def dawn_bg():
    return vgrad([(0, "#2C3E91"), (0.42, "#7C6BCB"), (0.72, "#F29A8E"), (1, "#FFC98A")]).convert("RGBA")

def sun_over_horizon(img, horizon, r, cx=S // 2, sun=("#FFE27A", "#FF9A3D"), ground=("#FF9C6B", "#F07A55")):
    cy = horizon
    glow(img, cx, cy, int(r * 1.55), hexc("#FFD27A"), 120)
    disc, m = radial_sun(r, *sun)
    img.paste(disc, (cx - r, cy - r), m)
    # ground below the horizon
    band = vgrad([(0, ground[0]), (1, ground[1])], size=S).crop((0, 0, S, S - horizon)).convert("RGBA")
    img.paste(band, (0, horizon))
    return cx, cy

def leaves(img, x, y, scale=1.0, color="#5DBB63", stem="#4AA65A"):
    """A short stem from (x, y) with two pointed leaves opening upward in a V."""
    d = ImageDraw.Draw(img)
    stem_h, stem_w = int(210 * scale), int(46 * scale)
    top = y - stem_h
    d.rounded_rectangle([x - stem_w // 2, top, x + stem_w // 2, y + 40], radius=stem_w // 2, fill=hexc(stem))
    L, W = 360 * scale, 170 * scale
    for side in (-1, 1):
        ang = math.radians(-90 + side * 48)           # up and outward
        pts = []
        for i in range(41):
            t = i / 40
            pts.append((L * t, (W / 2) * math.sin(math.pi * t)))
        for i in range(40, -1, -1):
            t = i / 40
            pts.append((L * t, -(W / 2) * math.sin(math.pi * t)))
        rot = [(x + px * math.cos(ang) - py * math.sin(ang), top + 10 + px * math.sin(ang) + py * math.cos(ang)) for px, py in pts]
        d.polygon(rot, fill=hexc(color))

variant = sys.argv[2]
if variant == "A":
    img = dawn_bg(); sun_over_horizon(img, int(S * 0.70), int(S * 0.30))
elif variant == "B":
    img = dawn_bg(); cx, cy = sun_over_horizon(img, int(S * 0.74), int(S * 0.29))
    leaves(img, cx, cy - int(S * 0.29) + 40, scale=2.2)
elif variant == "C":
    img = dawn_bg(); cx, cy = sun_over_horizon(img, int(S * 0.74), int(S * 0.31))
    d = ImageDraw.Draw(img)
    ink = hexc("#7A3418"); w = 95
    for ex in (cx - 360, cx + 360):
        ey = cy - 420
        d.arc([ex - 220, ey - 220, ex + 220, ey + 220], start=25, end=155, fill=ink, width=w)   # closed, sleepy eyes
    for bx in (cx - 560, cx + 560):
        d.ellipse([bx - 150, cy - 230, bx + 150, cy - 110], fill=hexc("#FF8A6B"))
elif variant == "D":
    img = vgrad([(0, "#FFC247"), (1, "#FF7A3D")]).convert("RGBA")
    d = ImageDraw.Draw(img)
    cx, cy, r = S // 2, int(S * 0.64), int(S * 0.21)
    white = (255, 250, 238)
    for k in range(7):                          # rays fanning over the top half
        a = math.radians(180 + 15 + k * 25)
        r0, r1 = r + 190, r + 560
        p0 = (cx + math.cos(a) * r0, cy + math.sin(a) * r0); p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
        d.line([p0, p1], fill=white, width=190)
        for p in (p0, p1): d.ellipse([p[0] - 95, p[1] - 95, p[0] + 95, p[1] + 95], fill=white)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=white)
    d.rectangle([0, cy, S, S], fill=hexc("#FF7A3D"))                # horizon cuts the sun in half
    img.alpha_composite(vgrad([(0, "#FF8F45"), (1, "#F2632F")]).crop((0, cy, S, S)).convert("RGBA"), (0, cy))
img.convert("RGB").resize((1024, 1024), Image.LANCZOS).save(OUT)

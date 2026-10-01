"""Seed-bud hot-air balloon the sprout rides in."""
import math
from mathutils import Vector, Matrix
import common as C

RIM_Z = 0.17        # basket rim height
SEAT_Z = 0.10       # cushion top (SeatPoint)


def envelope(name="Envelope"):
    green = C.mat("BalloonGreen", "6CC265", rough=0.75)
    cream = C.mat("BalloonCream", "F7EBCF", rough=0.8)
    prof = [(0.0, 0.585), (0.1, 0.6), (0.15, 0.645), (0.27, 0.76), (0.4, 0.91), (0.475, 1.06), (0.5, 1.18),
            (0.48, 1.3), (0.4, 1.43), (0.27, 1.52), (0.12, 1.585), (0.0, 1.605)]
    seg = 64
    mask = lambda z: min(1, max(0, (z - 0.62) / 0.3)) * min(1, max(0, (1.6 - z) / 0.25))
    env = C.lathe(name, prof, seg=seg, mat=green, rfun=lambda t, z: 1 + 0.05 * abs(math.sin(4 * t)) ** 0.7 * mask(z), sharp=70)
    # cream stripes on the panel seams (8 narrow stripes)
    def stripe(c, n):
        a = math.atan2(c.y, c.x) % (2 * math.pi)
        k = (a / (2 * math.pi / 8)) % 1.0
        return (k < 0.065 or k > 0.935) and 0.64 < c.z < 1.57
    C.paint_faces(env, cream, stripe)
    C.shade(env, 180)
    return env


def build_balloon():
    root = C.empty("Balloon")
    wick = C.mat("Wicker", "C99A5B", rough=0.9)
    wickd = C.mat("WickerDark", "96683A", rough=0.9)
    rope = C.mat("Rope", "D9BE8C", rough=0.9)
    parts = []
    # woven basket: hollow, gentle flare, woven bands + vertical weave ripple
    prof = [(0.0, 0.0), (0.19, 0.0), (0.205, 0.02), (0.215, 0.09), (0.225, RIM_Z - 0.01),
            (0.2, RIM_Z - 0.005), (0.19, 0.08), (0.18, 0.05), (0.0, 0.05)]
    bask = C.lathe("basket", prof, seg=32, mat=wick, rfun=lambda t, z: 1 + (0.02 * math.cos(16 * t) if 0.015 < z < RIM_Z - 0.02 else 0), sharp=60)
    C.paint_faces(bask, wickd, lambda c, n: abs(((c.z - 0.02) / 0.05) % 1 - 0.5) < 0.12 and n.z > -0.5 and abs(n.z) < 0.6 and (c.x ** 2 + c.y ** 2) > 0.2 ** 2)
    parts.append(bask)
    parts.append(C.torus("rim", (0, 0, RIM_Z), R=0.215, r=0.022, mat=wickd, seg=32, mseg=8))
    parts.append(C.torus("rimb", (0, 0, 0.012), R=0.197, r=0.016, mat=wickd, seg=32, mseg=6))
    # seat cushion
    parts.append(C.cyl("cushion", (0, 0, 0.05), r=0.17, h=SEAT_Z - 0.05, mat=C.mat("Blossom", rough=0.9), seg=24, base=True, bevel=0.02, bseg=2))
    # ropes: basket rim -> envelope throat
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p0 = Vector((0.205 * math.cos(a), 0.205 * math.sin(a), RIM_Z + 0.01))
        p1 = Vector((0.12 * math.cos(a), 0.12 * math.sin(a), 0.63))
        parts.append(C.tube("rope", [p0, (p0 + p1) / 2 + Vector((0.01 * math.cos(a), 0.01 * math.sin(a), 0)), p1], r=0.009, mat=rope, seg=5, res=3))
        parts.append(C.sphere("knot", p0 + Vector((0, 0, 0.005)), r=0.018, mat=rope, seg=8, rings=5))
    # burner
    parts.append(C.cyl("burner", (0, 0, 0.555), r=0.06, r2=0.05, h=0.07, mat=C.mat("Iron", rough=0.6), seg=12, base=True, bevel=0.01, bseg=1))
    parts.append(C.sphere("flame", (0, 0, 0.64), r=1, scale=(0.035, 0.035, 0.05), mat=C.mat("GlowBurner", "FFB347", rough=0.9, emit="FF9A3C", strength=1.0), seg=10, rings=6))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        parts.append(C.tube("strut", [(0.055 * math.cos(a), 0.055 * math.sin(a), 0.585), (0.115 * math.cos(a), 0.115 * math.sin(a), 0.63)], r=0.006,
                            mat=C.mat("Iron"), seg=4, res=1))
    b = C.join(parts, "Basket")
    C.set_origin(b, (0, 0, 0))
    C.set_parent(b, root)
    # envelope with skirt and a sprouting top
    env = envelope()
    skirt = C.lathe("skirt", [(0.1, 0.57), (0.135, 0.575), (0.16, 0.625), (0.15, 0.65), (0.1, 0.64)], seg=32, mat=C.mat("BalloonCream"),
                    rfun=lambda t, z: 1 + 0.06 * math.cos(16 * t) * (z < 0.6), sharp=60)
    top = [C.tube("tipstem", [(0, 0, 1.59), (0.0, 0.0, 1.66), (0.03, 0, 1.7)], r=0.016, radii=[1.2, 1.0, 0.7], mat=C.mat("Stem", rough=0.75), seg=6, res=3)]
    for sx in (-1, 1):
        lf = C.leaf("tl", length=0.2, width=0.075, thick=0.014, curl=0.07, mat=C.mat("Leaf", rough=0.7), fold=0.35)
        C.paint_faces(lf, C.mat("LeafLight", rough=0.7), lambda c, n: n.z > 0.55 and c.x > 0.03)
        lf.data.transform(C.xform(rot=(0, -22, 0)))
        if sx < 0:
            lf.data.transform(C.xform(rot=(0, 0, 180)))
        lf.data.transform(C.xform(rot=(0, 0, 20)))
        lf.location = (0, 0, 1.6)
        C.bake_transform(lf)
        top.append(lf)
    e = C.join([env, skirt] + top, "Envelope")
    C.set_origin(e, (0, 0, 0.6))
    C.set_parent(e, root)
    C.empty("SeatPoint", (0, 0, SEAT_Z), parent=root)
    return root

"""Farm Island: the sprout's workplace (smaller sky-island with plots, barn, pump...)."""
import math, random
import bpy
from mathutils import Vector, Matrix
import common as C
import a_island as I

K = 0.75               # scale vs the home island (R ~6 -> ~4.5)
SPIN = 150             # rotate the outline so it differs from the home island

PITCH = 1.2
PLOT = 0.95
SOIL_TOP = 0.09
PLOTS = [(-PITCH, -1.35), (0.0, -1.35), (PITCH, -1.35), (-PITCH, -0.15), (0.0, -0.15), (PITCH, -0.15)]
BARN = (0.35, 2.15)
DOCK = (-2.05, -2.75)
WORK = (2.05, -0.75)
PUMP = (-2.35, 0.9)
HAY = (2.45, 1.05)
SIGN = (1.75, -2.45)

KEEP_OUT = [(x, y, 0.62) for x, y in PLOTS] + [(BARN[0], BARN[1], 1.45), (DOCK[0], DOCK[1], 0.8), (WORK[0], WORK[1], 0.4),
                                                (PUMP[0], PUMP[1], 0.55), (HAY[0], HAY[1], 0.5), (SIGN[0], SIGN[1], 0.35)]


def rim_r(t):
    """Outline radius of the farm island at world angle t."""
    return I.R(t - math.radians(SPIN)) * K


def free(x, y, m=0.1):
    return all(math.hypot(x - a, y - b) > r + m for a, b, r in KEEP_OUT)


def underside(rnd):
    parts = []
    for (t, u, s) in [(-1.2, 0.36, 0.8), (-2.2, 0.5, 0.65), (-0.3, 0.58, 0.7), (0.9, 0.3, 0.85), (2.4, 0.42, 0.75),
                      (3.6, 0.3, 0.7), (-1.75, 0.7, 0.55), (0.3, 0.75, 0.5), (4.6, 0.62, 0.55)]:
        r = I.under_r(t, u)
        rk = I.rock("rk", rnd, s, mats=("Rock", "RockDark"), flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.data.transform(C.xform(rot=(rnd.uniform(-30, 30), rnd.uniform(-30, 30), 0), scale=(1, 1, 1.3)))
        rk.location = Vector((math.cos(t) * r * 0.97, math.sin(t) * r * 0.97, I.under_z(t, u))) + I.TIP_OFF * u * u
        C.bake_transform(rk)
        parts.append(rk)
    for (dx, dy, dz, s) in [(0.3, 0.1, -5.5, 0.55), (-0.25, 0.25, -5.2, 0.5)]:
        rk = I.rock("rt", rnd, s, mats=("RockDark", "RockDark"), flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.location = (dx + I.TIP_OFF.x, dy + I.TIP_OFF.y, dz)
        C.bake_transform(rk)
        parts.append(rk)
    for t, L in [(-1.35, 1.9), (-0.75, 1.5), (0.45, 2.0), (2.9, 1.6), (-2.9, 1.7)]:
        parts.append(I.hanging_root(rnd, t, L))
    for t, L in [(-1.62, 1.7), (-0.45, 1.3), (-2.55, 1.9)]:
        parts.append(I.hanging_vine(rnd, t, L))
    return parts


def plot_bed(x, y, rnd):
    soil = C.mat("FarmSoil", "5E3B26", rough=0.95)
    soill = C.mat("FarmSoilLight", "7A4E31", rough=0.95)
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts = [C.box("soil", (x, y, 0), (PLOT - 0.06, PLOT - 0.06, SOIL_TOP - 0.02), mat=soil, bevel=0.03, bseg=2, base=True)]
    for k in range(3):                              # furrow ridges
        yy = y - 0.3 + k * 0.3
        rg = C.cyl("ridge", (x, yy, SOIL_TOP - 0.035), r=0.085, h=PLOT - 0.14, rot=(0, 90, 0), mat=soill, seg=10, smooth=True)
        rg.data.transform(Matrix.Diagonal((1, 1, 0.45, 1)))
        C.jitter(rg, 0.006, 12, rnd.randint(0, 99))
        parts.append(rg)
    hb = PLOT / 2
    for (bx, by, sx, sy) in [(0, -hb, PLOT + 0.08, 0.08), (0, hb, PLOT + 0.08, 0.08), (-hb, 0, 0.08, PLOT - 0.08), (hb, 0, 0.08, PLOT - 0.08)]:
        parts.append(C.box("brd", (x + bx, y + by, 0), (sx, sy, 0.12), mat=wood if (sx > 0.5) else woodd, bevel=0.022, bseg=1, base=True))
    for cx in (-hb, hb):
        for cy in (-hb, hb):
            parts.append(C.box("cp", (x + cx, y + cy, 0), (0.11, 0.11, 0.15), mat=woodd, bevel=0.025, bseg=1, base=True))
    return parts


def barn(x, y):
    red = C.mat("BarnRed", "D9574A", rough=0.85)
    trim = C.mat("BarnTrim", "F6EEDC", rough=0.85)
    roof = C.mat("BarnRoof", "7A4F3A", rough=0.85)
    W, D, Hw = 1.7, 1.3, 1.05
    parts = [C.box("fnd", (x, y, 0), (W + 0.12, D + 0.12, 0.12), mat=C.mat("Rock", rough=0.9), bevel=0.04, bseg=2, base=True)]
    # gambrel gable walls extruded along Y
    prof = [(-W / 2, 0.1), (W / 2, 0.1), (W / 2, Hw), (W / 2 - 0.22, Hw + 0.5), (0, Hw + 0.78), (-W / 2 + 0.22, Hw + 0.5), (-W / 2, Hw)]
    wall = C.prism("wall", prof, -D / 2, D / 2, red, bevel=0.03)
    wall.location = (x, y, 0)
    C.bake_transform(wall)
    parts.append(wall)
    # gambrel roof: 4 slabs
    segs = [((-W / 2 - 0.12, Hw - 0.05), (-W / 2 + 0.22, Hw + 0.5)), ((-W / 2 + 0.22, Hw + 0.5), (0, Hw + 0.78)),
            ((0, Hw + 0.78), (W / 2 - 0.22, Hw + 0.5)), ((W / 2 - 0.22, Hw + 0.5), (W / 2 + 0.12, Hw - 0.05))]
    for (a, b) in segs:
        a, b = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        d = b - a
        L = d.length + 0.06
        nrm = Vector((-d.z, 0, d.x)).normalized()
        if nrm.z < 0:
            nrm = -nrm
        c = (a + b) / 2 + nrm * 0.06
        sl = C.box("rf", (0, 0, 0), (L, D + 0.3, 0.1), mat=roof, bevel=0.035, bseg=2)
        sl.data.transform(C.xform(rot=(0, -math.degrees(math.atan2(d.z, d.x)), 0)))
        sl.location = (x + c.x, y, c.z)
        C.bake_transform(sl)
        parts.append(sl)
    # big front door with X brace + trim, hayloft window
    fy = y - D / 2 - 0.02
    parts.append(C.box("dtrim", (x, fy, 0.1), (0.82, 0.05, 0.86), mat=trim, bevel=0.02, bseg=1, base=True))
    parts.append(C.box("door", (x, fy - 0.01, 0.14), (0.7, 0.05, 0.76), mat=red, bevel=0.015, bseg=1, base=True))
    for s in (-1, 1):
        br = C.box("x", (0, 0, 0), (0.98, 0.03, 0.07), mat=trim, bevel=0.01, bseg=1)
        br.data.transform(C.xform(rot=(0, s * 47, 0)))
        br.location = (x, fy - 0.04, 0.52)
        C.bake_transform(br)
        parts.append(br)
    parts.append(C.box("hl", (x, fy, Hw + 0.28), (0.44, 0.05, 0.36), mat=trim, bevel=0.015, bseg=1))
    parts.append(C.box("hlw", (x, fy - 0.015, Hw + 0.28), (0.32, 0.05, 0.24), mat=C.mat("GlowWindow", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0), bevel=0.0, smooth=False))
    for sx in (-1, 1):
        parts.append(C.box("cor", (x + sx * W / 2, fy + D / 2, 0.1), (0.08, D + 0.06, 0.07), mat=trim, bevel=0.015, bseg=1))
        parts.append(C.box("corv", (x + sx * W / 2, fy, 0.1), (0.08, 0.08, Hw - 0.08), mat=trim, bevel=0.015, bseg=1, base=True))
    # side window
    parts.append(C.box("sw", (x + W / 2 + 0.01, y, 0.65), (0.05, 0.4, 0.34), mat=trim, bevel=0.012, bseg=1))
    parts.append(C.box("swg", (x + W / 2 + 0.025, y, 0.65), (0.05, 0.3, 0.24), mat=C.mat("GlowWindow"), bevel=0.0, smooth=False))
    # weathervane
    parts.append(C.cyl("vp", (x, y, Hw + 0.85), r=0.018, h=0.3, mat=C.mat("Iron", rough=0.6), seg=6, base=True))
    parts.append(C.prism("rooster", [(0, 0), (0.18, 0.02), (0.12, 0.1), (0.02, 0.12)], -0.01, 0.01, C.mat("Iron"), smooth=False))
    parts[-1].location = (x - 0.08, y, Hw + 1.1)
    C.bake_transform(parts[-1])
    return parts


def fence(rnd, a0, a1, rr):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts = []
    n = int(abs(a1 - a0) * rr / 0.55)
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        r = rim_r(a) - rr
        p = Vector((r * math.cos(a), r * math.sin(a), 0))
        pts.append(p)
        parts.append(C.box("fp", p, (0.09, 0.09, 0.5), mat=woodd, bevel=0.02, bseg=1, base=True))
        parts.append(C.cyl("fcap", p + Vector((0, 0, 0.5)), r=0.05, r2=0.0, h=0.06, mat=woodd, seg=4, base=True, smooth=False))
    for z in (0.2, 0.38):
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a
            rl = C.box("rail", (0, 0, 0), (d.length + 0.06, 0.05, 0.06), mat=wood, bevel=0.015, bseg=1)
            rl.data.transform(C.xform(rot=(0, 0, math.degrees(math.atan2(d.y, d.x)))))
            rl.location = (a + b) / 2 + Vector((0, 0, z))
            C.bake_transform(rl)
            parts.append(rl)
    return parts


def pump(x, y):
    iron = C.mat("PumpTeal", "4FA3A5", rough=0.6)
    parts = [C.box("pbase", (x, y, 0), (0.42, 0.42, 0.08), mat=C.mat("Rock", rough=0.9), bevel=0.03, bseg=2, base=True),
             C.cyl("pbody", (x, y, 0.08), r=0.08, r2=0.07, h=0.6, mat=iron, seg=12, base=True, bevel=0.015, bseg=1),
             C.cyl("pcap", (x, y, 0.68), r=0.1, h=0.05, mat=iron, seg=12, base=True, bevel=0.015, bseg=1),
             C.sphere("pknob", (x, y, 0.76), r=0.035, mat=iron, seg=10, rings=6),
             C.tube("spout", [(x, y - 0.06, 0.55), (x, y - 0.2, 0.55), (x, y - 0.24, 0.48)], r=0.028, mat=iron, seg=8, res=3),
             C.tube("handle", [(x + 0.06, y, 0.66), (x + 0.2, y, 0.74), (x + 0.36, y, 0.72)], r=0.018, mat=C.mat("Iron", rough=0.6), seg=6, res=3)]
    bucket = C.lathe("bucket", [(0, 0), (0.1, 0), (0.12, 0.2), (0.105, 0.19), (0.09, 0.02), (0, 0.02)], seg=16, mat=C.mat("Wood", rough=0.8))
    bucket.location = (x, y - 0.3, 0)
    C.bake_transform(bucket)
    parts += [bucket, C.torus("bb", (x, y - 0.3, 0.14), R=0.115, r=0.01, mat=C.mat("Iron"), seg=16, mseg=4),
              C.cyl("water", (x, y - 0.3, 0.16), r=0.1, h=0.01, mat=C.mat("Water", "6EC8E6", rough=0.15, spec=0.6), seg=16)]
    return parts


def hay(x, y):
    hm = C.mat("Hay", "E8C766", rough=0.95)
    hd = C.mat("HayDark", "CFA944", rough=0.95)
    b = C.box("bale", (x, y, 0), (0.7, 0.45, 0.4), mat=hm, bevel=0.08, bseg=3, base=True)
    C.jitter(b, 0.012, 14, 3)
    parts = [b]
    for dx in (-0.18, 0.18):
        parts.append(C.box("twine", (x + dx, y, 0.2), (0.03, 0.47, 0.42), mat=hd, bevel=0.012, bseg=1))
    b2 = C.box("bale2", (0, 0, 0), (0.62, 0.42, 0.34), mat=hm, bevel=0.07, bseg=3, base=True)
    b2.data.transform(C.xform(rot=(0, 0, 25)))
    b2.location = (x + 0.1, y + 0.05, 0.4)
    parts.append(b2)
    rnd = random.Random(2)
    for i in range(10):
        a = rnd.uniform(0, 6.28)
        p = Vector((x + 0.45 * math.cos(a), y + 0.35 * math.sin(a), 0.005))
        parts.append(C.tube("straw", [p, p + Vector((0.08 * math.cos(a + 1), 0.08 * math.sin(a + 1), 0.0))], r=0.008, mat=hd, seg=4, res=1))
    return parts


def sign(x, y):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    return [C.box("sp1", (x - 0.25, y, 0), (0.07, 0.07, 0.62), mat=woodd, bevel=0.015, bseg=1, base=True),
            C.box("sp2", (x + 0.25, y, 0), (0.07, 0.07, 0.62), mat=woodd, bevel=0.015, bseg=1, base=True),
            C.box("board", (x, y - 0.03, 0.5), (0.72, 0.05, 0.3), mat=C.mat("WoodLight", rough=0.8), bevel=0.03, bseg=2)]


def dock(x, y):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts = []
    top = 0.14
    for k in range(5):
        parts.append(C.box("pl", (x - 0.4 + k * 0.2, y, top - 0.03), (0.18, 1.0, 0.06), mat=wood if k % 2 else C.mat("WoodLight"), bevel=0.015, bseg=1))
    for cx in (-0.42, 0.42):
        for cy in (-0.42, 0.42):
            parts.append(C.cyl("dp", (x + cx, y + cy, -0.3), r=0.05, h=0.6, mat=woodd, seg=8, base=True, bevel=0.012, bseg=1))
    for cx in (-0.42, 0.42):
        parts.append(C.box("beam", (x + cx, y, top - 0.08), (0.06, 1.0, 0.05), mat=woodd, bevel=0.012, bseg=1))
    parts.append(C.torus("ring", (x + 0.42, y - 0.45, top + 0.02), R=0.05, r=0.01, rot=(90, 0, 0), mat=C.mat("Iron", rough=0.6), seg=10, mseg=4))
    return parts, top


def build_farm_island():
    rnd = random.Random(31)
    root = C.empty("FarmIsland")
    body = I.build_body()
    under = C.join(underside(rnd))
    C.set_origin(under, (0, 0, 0))
    for o in (body, under):
        o.data.transform(C.xform(rot=(0, 0, SPIN), scale=(K, K, K)))
    body.name = body.data.name = "FarmBody"
    C.update()

    parts = [under]
    for (x, y) in PLOTS:
        parts += plot_bed(x, y, rnd)
    parts += barn(*BARN)
    parts += fence(rnd, math.radians(105), math.radians(215), 0.4)
    parts += pump(*PUMP)
    parts += hay(*HAY)
    parts += sign(*SIGN)
    dk, dtop = dock(*DOCK)
    parts += dk
    # path of stepping stones from the dock to the plots
    for k, (px, py) in enumerate([(-1.6, -2.25), (-1.2, -2.15), (-0.75, -2.1), (-0.3, -2.12), (0.15, -2.1), (0.6, -2.15)]):
        st = C.cyl("stone", (px, py, 0), r=0.17, h=0.035, mat=C.mat("Pebble", rough=0.9), seg=10, base=True, bevel=0.012, bseg=1)
        st.data.transform(Matrix.Diagonal((1, 0.8, 1, 1)))
        parts.append(st)
    # decor: tufts, flowers, pebbles on free grass
    placed = []
    def spots(n, sep, rmin=0.0):
        out = []
        tries = 0
        while len(out) < n and tries < 4000:
            tries += 1
            t = rnd.uniform(0, 2 * math.pi)
            rr = math.sqrt(rnd.uniform(0, 1)) * (rim_r(t) - 0.35)
            x, y = rr * math.cos(t), rr * math.sin(t)
            if rr < rmin or not free(x, y) or any(math.hypot(x - a, y - b) < sep for a, b in placed):
                continue
            if -2.4 < y < -1.95 and -1.9 < x < 0.9:      # keep the stepping-stone path clear
                continue
            placed.append((x, y)); out.append((x, y))
        return out
    for (x, y) in spots(26, 0.45):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        tf = I.grass_tuft("tuft", rnd, s=rnd.uniform(0.9, 1.3))
        tf.location = (x, y, z)
        C.bake_transform(tf)
        parts.append(tf)
    cols = ["White", "FlowerYellow", "Blossom", "Purple"]
    for i, (cx, cy) in enumerate(spots(9, 0.6)):
        for k in range(3):
            x, y = cx + rnd.uniform(-0.2, 0.2), cy + rnd.uniform(-0.2, 0.2)
            z, n = I.surface_z(body, x, y)
            if z is None:
                continue
            fl = I.tiny_flower(rnd, cols[i % 4])
            fl.data.transform(C.xform(scale=(1.4, 1.4, 1.4), rot=(0, 0, rnd.uniform(0, 360))))
            fl.location = (x, y, z + 0.008)
            C.bake_transform(fl)
            parts.append(fl)
    for (x, y) in spots(8, 0.5):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        rk = I.rock("st", rnd, rnd.uniform(0.07, 0.14), sub=1)
        rk.location = (x, y, z + 0.01)
        C.bake_transform(rk)
        parts.append(rk)
    decor = C.join(parts, "FarmDecor")
    C.set_origin(decor, (0, 0, 0))
    C.set_parent(body, root)
    C.set_parent(decor, root)

    for i, (x, y) in enumerate(PLOTS):
        C.empty("Plot%d" % (i + 1), (x, y, SOIL_TOP), parent=root)
    C.empty("BalloonDock", (DOCK[0], DOCK[1], dtop), parent=root)
    C.empty("WorkSpot", (WORK[0], WORK[1], 0.0), parent=root)
    for name, pos, size, seed in [("FloatRock1", (-5.6, 1.2, -1.6), 0.8, 13), ("FloatRock2", (5.2, -2.4, -2.3), 0.62, 17)]:
        fr = I.float_rock(name, size, seed)
        fr.location = pos
        C.update()
        mn, mx = C.world_bbox([fr])
        C.set_origin(fr, (mn + mx) / 2)
        C.set_parent(fr, root)
    return root

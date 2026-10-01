"""Buildings: cottage, tent, windmill."""
import math, random
from mathutils import Vector, Matrix
import common as C


def glow_window_mat():
    return C.mat("GlowWindow", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0)


def window(w=0.4, h=0.44, flowers=True, shutters=False, seed=0):
    """Framed window facing -Y, centered at origin. Returns joined object."""
    rnd = random.Random(seed)
    glass = glow_window_mat()
    fr = C.mat("WoodDark", rough=0.8)
    wood = C.mat("Wood", rough=0.8)
    t = 0.07
    parts = [C.box("g", (0, 0.015, 0), (w, 0.03, h), mat=glass, bevel=0.0, smooth=False)]
    parts += [C.box("f", (0, -0.02, h / 2 + t / 2 - 0.01), (w + 2 * t - 0.02, 0.08, t), mat=fr, bevel=0.022, bseg=1),
              C.box("f", (0, -0.02, -h / 2 - t / 2 + 0.01), (w + 2 * t - 0.02, 0.08, t), mat=fr, bevel=0.022, bseg=1),
              C.box("f", (-w / 2 - t / 2 + 0.01, -0.02, 0), (t, 0.08, h), mat=fr, bevel=0.022, bseg=1),
              C.box("f", (w / 2 + t / 2 - 0.01, -0.02, 0), (t, 0.08, h), mat=fr, bevel=0.022, bseg=1),
              C.box("m", (0, -0.005, 0), (0.035, 0.04, h), mat=fr, bevel=0.01, bseg=1),
              C.box("m", (0, -0.005, 0), (w, 0.04, 0.035), mat=fr, bevel=0.01, bseg=1),
              C.box("sill", (0, -0.06, -h / 2 - t + 0.005), (w + 2 * t + 0.08, 0.16, 0.05), mat=fr, bevel=0.02, bseg=1)]
    if shutters:
        tm = C.mat("RoofTeal", rough=0.8)
        for s in (-1, 1):
            sh = C.box("sh", (s * (w / 2 + t + 0.13), -0.03, 0), (0.22, 0.04, h + 0.1), mat=tm, bevel=0.018, bseg=2)
            parts.append(sh)
            parts.append(C.box("shb", (s * (w / 2 + t + 0.13), -0.055, 0), (0.16, 0.02, 0.04), mat=C.mat("RoofTealDark", rough=0.8), bevel=0.008, bseg=1))
    if flowers:
        bz = -h / 2 - t - 0.1
        parts.append(C.box("fb", (0, -0.1, bz), (w + 0.16, 0.17, 0.15), mat=wood, bevel=0.025, bseg=2))
        parts.append(C.sphere("leaves", (0, -0.1, bz + 0.08), r=1, scale=((w + 0.1) / 2, 0.08, 0.07), mat=C.mat("LeafDark", rough=0.85), seg=16, rings=6))
        cols = ["Blossom", "FlowerYellow", "BlossomDeep", "White", "Coral"]
        n = 5
        for i in range(n):
            x = -w / 2 + (i + 0.5) * w / n + rnd.uniform(-0.02, 0.02)
            parts.append(C.sphere("fl", (x, -0.13 + rnd.uniform(-0.03, 0.03), bz + 0.13 + rnd.uniform(0, 0.03)), r=0.045,
                                  mat=C.mat(cols[(i + seed) % len(cols)], rough=0.8), seg=7, rings=4))
    w_ = C.join(parts, "win")
    C.set_origin(w_, (0, 0, 0))
    return w_


# ============================================================================ COTTAGE
def build_cottage():
    root = C.empty("Cottage")
    W, D = 2.0, 1.7
    zf, zw, zr = 0.22, 1.62, 2.66
    cream = C.mat("Cream", rough=0.88)
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    rock = C.mat("Rock", rough=0.9)
    rockd = C.mat("RockDark", rough=0.9)
    roof = C.mat("RoofRed", rough=0.8)
    roofd = C.mat("RoofRedDark", rough=0.8)
    glass = glow_window_mat()
    rnd = random.Random(4)
    body = []

    body.append(C.box("fnd", (0, 0, 0), (W + 0.18, D + 0.18, zf + 0.02), mat=rock, bevel=0.06, bseg=2, base=True))
    # foundation stones
    for i in range(9):
        x = -W / 2 + 0.1 + i * (W - 0.2) / 8
        body.append(C.box("fs", (x + rnd.uniform(-0.03, 0.03), -D / 2 - 0.09, 0.11), (0.2, 0.05, 0.13 + rnd.uniform(-0.02, 0.02)),
                          mat=rockd if i % 3 == 0 else rock, bevel=0.03, bseg=1))
    body.append(C.prism("wall", [(-W / 2, zf), (W / 2, zf), (W / 2, zw), (0, zr), (-W / 2, zw)], -D / 2, D / 2, cream, bevel=0.035))
    for sx in (-1, 1):
        for sy in (-1, 1):
            body.append(C.box("post", (sx * W / 2, sy * D / 2, zf), (0.13, 0.13, zw - zf), mat=woodd, bevel=0.03, bseg=2, base=True))
    for sy in (-1, 1):
        body.append(C.box("beam", (0, sy * (D / 2 + 0.015), zw), (W + 0.12, 0.1, 0.11), mat=woodd, bevel=0.03, bseg=2))

    # door + frame + knob
    dw, dh = 0.56, 0.98
    body.append(C.prism("doorframe", C.arch_pts(dw + 0.16, dh + 0.08, 12, zf), -D / 2 - 0.035, -D / 2 + 0.02, woodd, bevel=0.025, bseg=1))
    body.append(C.prism("door", C.arch_pts(dw, dh, 12, zf), -D / 2 - 0.055, -D / 2 - 0.02, wood, bevel=0.015, bseg=1))
    for x in (-0.1, 0.1):
        body.append(C.box("plank", (x, -D / 2 - 0.058, zf + 0.44), (0.022, 0.012, 0.8), mat=woodd, bevel=0.005, bseg=1))
    body.append(C.sphere("knob", (0.17, -D / 2 - 0.085, zf + 0.47), r=0.038, mat=C.mat("Brass", rough=0.45), seg=10, rings=6))
    body.append(C.box("hinge", (-0.2, -D / 2 - 0.06, zf + 0.75), (0.16, 0.012, 0.04), mat=C.mat("Iron", rough=0.6), bevel=0.006, bseg=1))
    body.append(C.box("hinge", (-0.2, -D / 2 - 0.06, zf + 0.22), (0.16, 0.012, 0.04), mat=C.mat("Iron", rough=0.6), bevel=0.006, bseg=1))
    # steps
    body.append(C.box("step1", (0, -D / 2 - 0.2, 0), (0.86, 0.34, 0.2), mat=rock, bevel=0.05, bseg=2, base=True))
    body.append(C.box("step2", (0, -D / 2 - 0.47, 0), (1.0, 0.3, 0.1), mat=C.mat("Pebble", rough=0.9), bevel=0.04, bseg=2, base=True))
    # bushes flanking the steps
    for sx in (-1, 1):
        b = C.sphere("bush", (sx * 0.7, -D / 2 - 0.2, 0.16), r=1, scale=(0.24, 0.2, 0.2), mat=C.mat("Leaf", rough=0.85), seg=12, rings=7)
        C.jitter(b, 0.015, 8, 3)
        body.append(b)
        body.append(C.sphere("bf", (sx * 0.7 + 0.05, -D / 2 - 0.36, 0.26), r=0.04, mat=C.mat("Blossom" if sx < 0 else "FlowerYellow"), seg=7, rings=4))
        body.append(C.sphere("bf", (sx * 0.7 - 0.09, -D / 2 - 0.32, 0.2), r=0.035, mat=C.mat("White"), seg=7, rings=4))

    # windows
    for sx in (-1, 1):
        wdw = window(0.4, 0.44, flowers=True, seed=2 + sx)
        C.place(wdw, 0, (sx * 0.64, -D / 2 - 0.02, 1.0))
        body.append(wdw)
    for sx in (-1, 1):
        wdw = window(0.42, 0.46, flowers=False, shutters=True, seed=5)
        C.place(wdw, 90 if sx > 0 else -90, (sx * (W / 2 + 0.02), 0.05, 1.02))
        body.append(wdw)
    # round attic window
    ra = 0.17
    body.append(C.cyl("ag", (0, -D / 2 + 0.005, 2.04), r=ra, h=0.04, rot=(90, 0, 0), mat=glass, seg=20, smooth=False))
    body.append(C.torus("af", (0, -D / 2 - 0.02, 2.04), R=ra + 0.02, r=0.045, rot=(90, 0, 0), mat=woodd, seg=16, mseg=6))
    body.append(C.box("am", (0, -D / 2 - 0.01, 2.04), (2 * ra, 0.03, 0.03), mat=woodd, bevel=0.008, bseg=1))
    body.append(C.box("am", (0, -D / 2 - 0.01, 2.04), (0.03, 0.03, 2 * ra), mat=woodd, bevel=0.008, bseg=1))
    walls = C.join(body, "CottageBody")
    C.set_parent(walls, root)

    # roof: stepped shingle strips
    rp = []
    half = W / 2
    L0 = math.hypot(half, zr - zw)
    d = Vector((half / L0, 0, -(zr - zw) / L0))
    n = Vector((-(d.z), 0, d.x))                # outward normal for +X side
    over = 0.34
    Ltot = L0 + over
    rows = 4
    Ls = Ltot / rows
    th = 0.13
    ang = math.degrees(math.atan2(zr - zw, half))
    for sx in (-1, 1):
        dd = Vector((d.x * sx, 0, d.z))
        nn = Vector((n.x * sx, 0, n.z))
        for i in range(rows):
            off = 0.018 * (rows - 1 - i)
            s = (i + 0.5) * Ls - 0.04
            ctr = Vector((0, 0, zr)) + nn * (th / 2 + 0.01 + off) + dd * s
            strip = C.box("rs", (0, 0, 0), (Ls + 0.1, D + 0.5 - 0.0 * i, th), mat=roof if i % 2 == 0 else roofd, bevel=0.045, bseg=2)
            strip.data.transform(C.xform(rot=(0, sx * ang, 0)))
            strip.location = ctr
            C.bake_transform(strip)
            rp.append(strip)
    ridge = C.cyl("ridge", (0, 0, zr + th + 0.05), r=0.11, h=D + 0.56, rot=(90, 0, 0), mat=roofd, seg=12, bevel=0.03, bseg=1)
    rp.append(ridge)
    for sy in (-1, 1):
        rp.append(C.sphere("rk", (0, sy * (D / 2 + 0.29), zr + th + 0.05), r=0.12, mat=roofd, seg=10, rings=6))

    # chimney
    cx, cy = 0.52, 0.36
    ch_top = 3.1
    rp.append(C.box("chim", (cx, cy, 1.5), (0.38, 0.38, ch_top - 1.5), mat=rock, bevel=0.04, bseg=2, base=True))
    rp.append(C.box("cap", (cx, cy, ch_top - 0.02), (0.5, 0.5, 0.12), mat=rockd, bevel=0.04, bseg=2))
    rp.append(C.box("band", (cx, cy, ch_top - 0.24), (0.42, 0.42, 0.06), mat=rockd, bevel=0.02, bseg=2))
    for i in range(10):
        face = rnd.choice([(-1, 0), (0, -1), (1, 0)])
        z = rnd.uniform(2.1, ch_top - 0.35)
        u = rnd.uniform(-0.12, 0.12)
        px = cx + (face[0] * 0.195 if face[0] else u)
        py = cy + (face[1] * 0.195 if face[1] else u)
        sz = (0.03 if face[0] else 0.13, 0.03 if face[1] else 0.13, 0.08)
        rp.append(C.box("cs", (px, py, z), sz, mat=rockd if i % 2 else C.mat("Pebble"), bevel=0.014, bseg=1))
    roofo = C.join(rp, "Roof")
    C.set_parent(roofo, root)

    C.empty("SmokePoint", (cx, cy, ch_top + 0.08), parent=root)
    C.empty("DoorPoint", (0, -D / 2 - 0.75, 0), parent=root)
    return root


# ============================================================================ TENT
def build_tent():
    import bmesh
    root = C.empty("Tent")
    orange = C.mat("TentOrange", rough=0.85)
    creamc = C.mat("TentCream", rough=0.85)
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    inter = C.mat("Interior", rough=0.95)
    rope = C.mat("Rope", "D9BE8C", rough=0.9)
    HW, HD, HZ = 0.82, 0.86, 1.36          # half width, half depth, ridge height
    stripes = 7
    parts = []
    # canvas panels with a gentle sag, 7 vertical stripes each side
    for sx in (-1, 1):
        bm = bmesh.new()
        ns, ny = 10, stripes * 3
        grid = []
        for i in range(ns + 1):
            s = i / ns
            row = []
            for j in range(ny + 1):
                y = -HD - 0.05 + (2 * HD + 0.1) * j / ny
                x = sx * (HW + 0.06) * s
                z = HZ * (1 - s) + 0.01
                sag = 0.05 * math.sin(math.pi * s) * (0.6 + 0.4 * math.sin(math.pi * j / ny))
                x -= sx * sag * 0.75
                z -= sag * 0.6
                # flare at the hem
                if i == ns:
                    x += sx * 0.03
                row.append(bm.verts.new((x, y, z)))
            grid.append(row)
        for i in range(ns):
            for j in range(ny):
                f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
                f.material_index = (j // 3) % 2
        panel = C.mk("panel", bm, [orange, creamc])
        so = panel.modifiers.new("Sol", 'SOLIDIFY')
        so.thickness = 0.045
        so.offset = 1 if sx > 0 else -1
        C.apply_mods(panel)
        C.add_bevel(panel, 0.012, 1, limit=True, angle=60)
        C.apply_mods(panel)
        C.shade(panel, 50)
        parts.append(panel)
    # back wall + dark interior
    parts.append(C.prism("back", [(-HW, 0.0), (HW, 0.0), (0, HZ)], HD - 0.02, HD + 0.02, creamc, bevel=0.01))
    parts.append(C.prism("inback", [(-HW + 0.1, 0.0), (HW - 0.1, 0.0), (0, HZ - 0.12)], HD - 0.06, HD - 0.03, inter, smooth=False))
    parts.append(C.box("floor", (0, 0.05, 0.005), (2 * HW - 0.15, 2 * HD - 0.1, 0.01), mat=inter, bevel=0.0, smooth=False))
    # front flaps tied back (crescent shapes)
    for sx in (-1, 1):
        pts = []
        n = 10
        for i in range(n + 1):                     # outer edge along the tent side, bottom->top
            s = i / n
            pts.append((sx * HW * (1 - s), HZ * s))
        for i in range(n - 1, -1, -1):             # inner curved edge top->bottom
            s = i / n
            k = 0.62 * math.sin(math.pi * (s * 0.85 + 0.15)) ** 0.8
            pts.append((sx * HW * (1 - s) * (1 - k), HZ * s))
        pts = [(x, z) for (x, z) in pts]
        if sx < 0:
            pts = list(reversed(pts))
        fl = C.prism("flap", pts, -HD - 0.07, -HD - 0.03, orange, smooth=True, sharp=60)
        parts.append(fl)
        # tie
        parts.append(C.torus("tie", (sx * 0.36, -HD - 0.075, 0.55), R=0.07, r=0.018, rot=(90, 0, 0), mat=rope, seg=12, mseg=6))
    # front hem trim (cream band along front edges)
    for sx in (-1, 1):
        parts.append(C.tube("trim", [(0, -HD - 0.06, HZ + 0.02), (sx * HW * 0.5, -HD - 0.06, HZ * 0.5), (sx * (HW + 0.04), -HD - 0.06, 0.02)],
                            r=0.028, mat=creamc, seg=6, res=2))
    # poles, ridge pole, pennant
    for sy in (-1, 1):
        parts.append(C.cyl("pole", (0, sy * (HD + 0.06), 0), r=0.04, h=HZ + 0.26, mat=wood, seg=10, base=True, bevel=0.012))
        parts.append(C.sphere("knob", (0, sy * (HD + 0.06), HZ + 0.28), r=0.06, mat=woodd, seg=10, rings=6))
    parts.append(C.cyl("ridgepole", (0, 0, HZ + 0.04), r=0.035, h=2 * HD + 0.2, rot=(90, 0, 0), mat=woodd, seg=10, bevel=0.01))
    flag = C.prism("flag", [(0.0, 0.0), (0.34, -0.07), (0.0, -0.16)], -0.012, 0.012, C.mat("RoofRed", rough=0.8), bevel=0.006, sharp=60)
    for v in flag.data.vertices:               # little wave
        v.co.y += 0.04 * math.sin(v.co.x * 12)
    flag.location = (0.03, -HD - 0.06, HZ + 0.24)
    parts.append(flag)
    # guy ropes + pegs
    for sy in (1,):
        top = Vector((0, sy * (HD + 0.06), HZ + 0.18))
        peg = Vector((0, sy * (HD + 0.62), 0.04))
        mid = (top + peg) / 2 - Vector((0, 0, 0.04))
        parts.append(C.tube("rope", [top, mid, peg], r=0.011, mat=rope, seg=4, res=4))
        parts.append(C.cyl("peg", (0, sy * (HD + 0.64), -0.02), r=0.03, r2=0.018, h=0.12, mat=woodd, seg=6, base=True))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.cyl("peg", (sx * (HW + 0.14), sy * (HD - 0.1), -0.02), r=0.026, r2=0.016, h=0.1, mat=woodd, seg=6, base=True))
    tent = C.join(parts, "TentBody")
    C.set_parent(tent, root)

    # rug with cream border + fringe
    rug = [C.box("rugb", (0, -HD - 0.42, 0), (1.0, 0.6, 0.03), mat=creamc, bevel=0.012, bseg=2, base=True),
           C.box("rugi", (0, -HD - 0.42, 0.012), (0.82, 0.44, 0.03), mat=C.mat("Rug", rough=0.9), bevel=0.01, bseg=2, base=True),
           ]
    for sx in (-1, 1):
        for i in range(6):
            rug.append(C.box("fr", (sx * 0.52, -HD - 0.42 - 0.25 + i * 0.1, 0.004), (0.06, 0.03, 0.012), mat=creamc, bevel=0.0, smooth=False))
    rugo = C.join(rug, "Rug")
    C.set_origin(rugo, (0, 0, 0))
    C.set_parent(rugo, root)
    C.empty("DoorPoint", (0, -HD - 0.3, 0), parent=root)
    return root


# ============================================================================ WINDMILL
def build_windmill():
    root = C.empty("Windmill")
    rock = C.mat("Rock", rough=0.9)
    rockd = C.mat("RockDark", rough=0.9)
    cream = C.mat("Cream", rough=0.88)
    teal = C.mat("RoofTeal", rough=0.8)
    teald = C.mat("RoofTealDark", rough=0.8)
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    creamc = C.mat("TentCream", rough=0.85)
    parts = []
    # stone base: stacked courses (octagonal)
    prof = []
    z = 0.0
    r = 0.8
    courses = 4
    ch = 0.24
    for i in range(courses):
        rr = r - i * 0.03
        prof += [(rr - 0.03, z), (rr, z + 0.04), (rr, z + ch - 0.04), (rr - 0.03, z + ch)]
        z += ch
    prof = [(0, 0)] + prof + [(0, z)]
    base = C.lathe("base", prof, seg=8, mat=rock, rot=(0, 0, 22.5), sharp=30)
    parts.append(base)
    zb = z
    # tapered wooden tower
    tower = C.lathe("tower", [(0, zb - 0.02), (0.68, zb - 0.02), (0.6, 1.7), (0.52, 2.22), (0, 2.22)], seg=8, mat=cream, rot=(0, 0, 22.5), sharp=30)
    parts.append(tower)
    parts.append(C.lathe("trim1", [(0, zb - 0.05), (0.74, zb - 0.05), (0.76, zb + 0.02), (0.72, zb + 0.07), (0, zb + 0.07)], seg=8, mat=woodd, rot=(0, 0, 22.5), sharp=30))
    parts.append(C.lathe("trim2", [(0, 2.16), (0.58, 2.16), (0.6, 2.22), (0.57, 2.27), (0, 2.27)], seg=8, mat=woodd, rot=(0, 0, 22.5), sharp=30))
    # vertical corner battens on the tower
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        p0 = Vector((0.68 * math.cos(a), 0.68 * math.sin(a), zb))
        p1 = Vector((0.52 * math.cos(a), 0.52 * math.sin(a), 2.2))
        parts.append(C.tube("batten", [p0, p1], r=0.028, mat=woodd, seg=4, res=1, caps=True, sharp=40))
    # cap roof (rounded cone) + finial
    cap = C.lathe("cap", [(0, 2.25), (0.66, 2.25), (0.7, 2.33), (0.62, 2.48), (0.42, 2.72), (0.2, 2.9), (0.06, 2.98), (0, 3.0)], seg=20, mat=teal, sharp=70)
    parts.append(cap)
    parts.append(C.lathe("capband", [(0, 2.24), (0.69, 2.24), (0.72, 2.3), (0.69, 2.36), (0, 2.36)], seg=20, mat=teald, sharp=70))
    parts.append(C.sphere("fin", (0, 0, 3.04), r=0.07, mat=C.mat("Brass", rough=0.45), seg=10, rings=6))
    # door (front, -Y) on the stone base
    fy = -0.8 * math.cos(math.radians(22.5)) + 0.01
    parts.append(C.prism("dframe", C.arch_pts(0.5, 0.8, 10, 0.02), fy - 0.03, fy + 0.05, woodd, bevel=0.02))
    parts.append(C.prism("door", C.arch_pts(0.38, 0.72, 10, 0.02), fy - 0.05, fy - 0.01, wood, bevel=0.012))
    parts.append(C.sphere("knob", (0.1, fy - 0.07, 0.38), r=0.03, mat=C.mat("Brass", rough=0.45), seg=8, rings=5))
    parts.append(C.box("st", (0, fy - 0.2, 0), (0.62, 0.28, 0.08), mat=C.mat("Pebble"), bevel=0.03, base=True))
    # window on tower front
    ty = -0.585 * math.cos(math.radians(22.5))
    wdw = window(0.26, 0.3, flowers=False, seed=1)
    wdw.data.transform(C.xform(rot=(-4, 0, 0)))
    C.place(wdw, 0, (0, ty - 0.01, 1.55))
    parts.append(wdw)
    # hub shaft
    hub = Vector((0, -0.86, 2.4))
    parts.append(C.cyl("shaft", (0, -0.62, 2.4), r=0.075, h=0.36, rot=(90, 0, 0), mat=woodd, seg=12, bevel=0.015))
    body = C.join(parts, "WindmillBody")
    C.set_parent(body, root)

    # blades: 4 lattice sails in the XZ plane (perpendicular to Y), origin at hub
    bl = [C.sphere("hubcap", (0, -0.06, 0), r=0.12, scale=(1, 0.8, 1), mat=C.mat("Brass", rough=0.45), seg=14, rings=8),
          C.cyl("hubdisc", (0, 0.02, 0), r=0.15, h=0.08, rot=(90, 0, 0), mat=woodd, seg=14, bevel=0.02)]
    L = 1.02
    for k in range(4):
        a = 90 * k + 45
        arm = [C.box("arm", (L / 2, 0, 0), (L, 0.05, 0.06), mat=wood, bevel=0.015, bseg=2)]
        sail_len, sail_w = 0.74, 0.28
        sx0 = 0.24
        arm.append(C.box("sail", (sx0 + sail_len / 2, 0.02, sail_w / 2 + 0.03), (sail_len, 0.022, sail_w), mat=creamc, bevel=0.01, bseg=1))
        for j in range(4):
            x = sx0 + j * sail_len / 3
            arm.append(C.box("slat", (x, -0.015, sail_w / 2 + 0.03), (0.03, 0.03, sail_w + 0.04), mat=woodd, bevel=0.008, bseg=1))
        arm.append(C.box("rail", (sx0 + sail_len / 2, -0.015, sail_w + 0.045), (sail_len + 0.03, 0.03, 0.03), mat=woodd, bevel=0.008, bseg=1))
        a_obj = C.join(arm)
        C.set_origin(a_obj, (0, 0, 0))
        a_obj.data.transform(C.xform(rot=(0, -a, 0)))
        bl.append(a_obj)
    blades = C.join(bl, "Blades")
    C.set_origin(blades, (0, 0, 0))
    blades.location = hub
    C.set_parent(blades, root)
    return root

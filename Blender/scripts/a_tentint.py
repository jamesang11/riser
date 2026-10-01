"""Cutaway interior of the sprout's camp tent (root `TentInterior`), framed like bedroom.usdz."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import common as C

HALF = 2.0
RIDGE_X, RIDGE_Z = 0.2, 2.6
LEFT_X = -2.0                 # left slope meets the ground here
MAT = Vector((-0.55, 0.45, 0))
MAT_TOP = 0.16
SPROUT_LOCAL = Vector((0, -0.2, MAT_TOP))
SPROUT_SCALE = 2.1
RECLINE = -0.62


def canvas_mats():
    return [C.mat("TentOrange", rough=0.85), C.mat("TentCream", rough=0.85)]


def slope_panel(x_top, z_top, x_bot, z_bot, y0, y1, stripe=0.4, sag=0.07, name="slope"):
    bm = bmesh.new()
    ns, ny = 12, int((y1 - y0) / stripe) * 4
    grid = []
    for i in range(ns + 1):
        s = i / ns
        row = []
        for j in range(ny + 1):
            y = y0 + (y1 - y0) * j / ny
            x = x_top + (x_bot - x_top) * s
            z = z_top + (z_bot - z_top) * s
            sg = sag * math.sin(math.pi * s) * (0.7 + 0.3 * math.sin(math.pi * j / ny))
            # sag toward the inside of the tent (away from the canvas normal)
            x += sg * 0.75 * (1 if x_bot < x_top else -1)
            z -= sg * 0.6
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(ns):
        for j in range(ny):
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            f.material_index = (j // 4) % 2
    o = C.mk(name, bm, canvas_mats())
    so = o.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.06; so.offset = 1
    C.apply_mods(o)
    C.add_bevel(o, 0.015, 1, limit=True, angle=60)
    C.apply_mods(o)
    C.shade(o, 50)
    return o


def back_wall(y, stripe=0.4):
    """A-frame back canvas (vertical stripes), thickness along +Y."""
    bm = bmesh.new()
    xl, xr = LEFT_X, RIDGE_X + (RIDGE_X - LEFT_X)
    def h(x):
        return RIDGE_Z * (1 - abs(x - RIDGE_X) / (RIDGE_X - LEFT_X))
    xs = sorted(set([xl + k * stripe for k in range(int((xr - xl) / stripe) + 1)] + [RIDGE_X, xr]))
    faces = []
    for k, (a, b) in enumerate(zip(xs[:-1], xs[1:])):
        vs = [bm.verts.new((a, y, 0)), bm.verts.new((b, y, 0))]
        if h(b) > 1e-4:
            vs.append(bm.verts.new((b, y, h(b))))
        if h(a) > 1e-4:
            vs.append(bm.verts.new((a, y, h(a))))
        f = bm.faces.new(vs)
        f.material_index = int(round((a - xl) / stripe)) % 2
    o = C.mk("backwall", bm, canvas_mats())
    so = o.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.06; so.offset = -1
    C.apply_mods(o)
    C.shade(o, 40)
    return o


def ground(rnd):
    grass = C.mat("Grass", rough=0.9)
    parts = [C.box("ground", (0.1, 0, -0.2), (2 * HALF + 0.9, 2 * HALF + 0.6, 0.2), mat=grass, bevel=0.08, bseg=3, base=True),
             C.box("dirt", (0.1, 0, -0.44), (2 * HALF + 0.8, 2 * HALF + 0.5, 0.26), mat=C.mat("Dirt", rough=0.9), bevel=0.06, bseg=2, base=True)]
    # woven groundsheet: checker weave strips
    cols = [C.mat("WeaveA", "D9B98A", rough=0.95), C.mat("WeaveB", "C99F6E", rough=0.95)]
    bm = bmesh.new()
    n = 14
    x0, x1, y0, y1 = -1.85, 2.0, -1.8, 1.9
    V = [[bm.verts.new((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * j / n, 0.012)) for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n):
        for j in range(n):
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            f.material_index = (i + j) % 2
    sheet = C.mk("sheet", bm, cols)
    so = sheet.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.02
    C.apply_mods(sheet)
    parts.append(sheet)
    border = C.mat("WeaveBorder", "A8754A", rough=0.9)
    for (cx, cy, sx, sy) in [((x0 + x1) / 2, y0, x1 - x0 + 0.08, 0.08), ((x0 + x1) / 2, y1, x1 - x0 + 0.08, 0.08), (x0, (y0 + y1) / 2, 0.08, y1 - y0), (x1, (y0 + y1) / 2, 0.08, y1 - y0)]:
        parts.append(C.box("border", (cx, cy, 0), (sx, sy, 0.035), mat=border, bevel=0.01, bseg=1, base=True))
    import a_island as I
    for i in range(18):
        t = rnd.uniform(0, 2 * math.pi)
        x = 0.1 + math.cos(t) * rnd.uniform(2.1, 2.45)
        y = math.sin(t) * rnd.uniform(2.05, 2.35)
        if y > 1.9 and x < 2.0:
            continue
        tf = I.grass_tuft("tuft", rnd, s=rnd.uniform(0.9, 1.3))
        tf.location = (x, y, 0.02)
        C.bake_transform(tf)
        parts.append(tf)
    return parts


def blanket(top, x0, x1, y0, y1):
    cols = [C.mat("QuiltPink", "F7B7C9", rough=0.95), C.mat("QuiltBlue", "A8D0F0", rough=0.95), C.mat("QuiltMint", "A8E0C8", rough=0.95),
            C.mat("QuiltButter", "FFE9A8", rough=0.95), C.mat("QuiltLilac", "D0B8F0", rough=0.95)]
    back = C.mat("QuiltBack", "F6EEDC", rough=0.95)
    nx, ny = 14, 9
    bm = bmesh.new()
    V = []
    w = (x1 - x0) / 2
    for i in range(nx + 1):
        row = []
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            dx = abs(x - (x0 + x1) / 2)
            z = top + 0.015 + 0.012 * math.sin(x * 9 + y * 4)
            if dx > w - 0.1:
                z -= min(top - 0.02, (dx - (w - 0.1)) * 2.5)
            row.append(bm.verts.new((x, y, z)))
        V.append(row)
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            c = f.calc_center_median()
            f.material_index = int(math.floor(c.x / 0.18) * 2 + math.floor(c.y / 0.18) * 3) % 5
    q = C.mk("blanket", bm, cols)
    so = q.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.03; so.offset = 1
    C.apply_mods(q)
    fold = C.box("fold", ((x0 + x1) / 2, y1 - 0.06, top + 0.05), (x1 - x0 - 0.12, 0.14, 0.035), mat=back, bevel=0.015, bseg=2)
    roll = C.cyl("roll", ((x0 + x1) / 2, y1 + 0.005, top + 0.045), r=0.03, h=x1 - x0 - 0.12, rot=(0, 90, 0), mat=back, seg=8)
    return [q, fold, roll]


def bedroll():
    cx, cy = MAT.x, MAT.y
    teal = C.mat("Bedroll", "7DBFB3", rough=0.9)
    tealD = C.mat("BedrollDark", "5FA396", rough=0.9)
    parts = [C.box("mat", (cx, cy, 0.0), (1.25, 2.1, MAT_TOP), mat=teal, bevel=0.06, bseg=3, base=True)]
    for k in range(5):                                   # quilted channels
        parts.append(C.box("seam", (cx, cy - 0.84 + k * 0.42, MAT_TOP - 0.005), (1.24, 0.03, 0.012), mat=tealD, bevel=0.0, smooth=False))
    # rolled end at the head, plump pillow in front of it
    parts.append(C.cyl("roll", (cx, cy + 1.02, 0.2), r=0.2, h=1.24, rot=(0, 90, 0), mat=tealD, seg=16, bevel=0.03, bseg=2))
    parts.append(C.torus("strap", (cx - 0.4, cy + 1.02, 0.2), R=0.205, r=0.018, rot=(0, 90, 0), mat=C.mat("WoodDark"), seg=16, mseg=5))
    parts.append(C.torus("strap", (cx + 0.4, cy + 1.02, 0.2), R=0.205, r=0.018, rot=(0, 90, 0), mat=C.mat("WoodDark"), seg=16, mseg=5))
    pil = C.box("pillow", (0, 0, 0), (0.9, 0.42, 0.26), mat=C.mat("Pillow", "FFFFFF", rough=0.9), bevel=0.11, bseg=4, base=True)
    pil.data.transform(C.xform(rot=(-25, 0, 0)))
    pil.location = (cx, cy + 0.68, MAT_TOP - 0.03)
    parts.append(pil)
    parts += blanket(MAT_TOP, cx - 0.66, cx + 0.66, cy - 1.07, cy - 0.12)
    return parts


def lantern(x, y, zc):
    iron = C.mat("Iron", rough=0.6)
    glow = C.mat("GlowLamp", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0)
    parts = [C.tube("cord", [(x, y, RIDGE_Z - 0.03), (x, y, zc + 0.24)], r=0.008, mat=C.mat("Rope", "D9BE8C", rough=0.9), seg=4, res=1),
             C.torus("hook", (x, y, zc + 0.24), R=0.03, r=0.007, rot=(90, 0, 0), mat=iron, seg=10, mseg=4),
             C.lathe("cap", [(0, zc + 0.12), (0.1, zc + 0.12), (0.06, zc + 0.19), (0, zc + 0.21)], seg=12, mat=iron),
             C.lathe("glass", [(0, zc - 0.1), (0.075, zc - 0.1), (0.085, zc), (0.075, zc + 0.12), (0, zc + 0.12)], seg=12, mat=glow),
             C.cyl("base", (x, y, zc - 0.12), r=0.09, h=0.04, mat=iron, seg=12)]
    for o in parts[2:4]:
        o.location = (x, y, 0)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        parts.append(C.tube("bar", [(x + 0.085 * math.cos(a), y + 0.085 * math.sin(a), zc - 0.1), (x + 0.085 * math.cos(a), y + 0.085 * math.sin(a), zc + 0.12)],
                            r=0.008, mat=iron, seg=4, res=1))
    return parts


def crate(x, y):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    S = 0.46
    parts = []
    for k in range(3):
        z = 0.02 + k * 0.15
        for (cx, cy, sx, sy) in [(x, y - S / 2, S, 0.03), (x, y + S / 2, S, 0.03), (x - S / 2, y, 0.03, S), (x + S / 2, y, 0.03, S)]:
            parts.append(C.box("slat", (cx, cy, z), (sx, sy, 0.12), mat=wood, bevel=0.01, bseg=1, base=True))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.box("post", (x + sx * S / 2, y + sy * S / 2, 0), (0.06, 0.06, S), mat=woodd, bevel=0.012, bseg=1, base=True))
    parts.append(C.box("lid", (x, y, S), (S + 0.04, S + 0.04, 0.04), mat=wood, bevel=0.012, bseg=1, base=True))
    top = S + 0.04
    mug = C.lathe("mug", [(0, top), (0.05, top), (0.055, top + 0.1), (0.047, top + 0.1), (0.044, top + 0.015), (0, top + 0.015)], seg=14, mat=C.mat("MugTeal", "5DB3B5", rough=0.5))
    mug.location = (x - 0.1, y - 0.08, 0)
    parts += [mug, C.torus("handle", (x - 0.1 + 0.06, y - 0.08, top + 0.05), R=0.028, r=0.008, rot=(90, 0, 0), mat=C.mat("MugTeal"), seg=10, mseg=4),
              C.cyl("cocoa", (x - 0.1, y - 0.08, top + 0.085), r=0.046, h=0.004, mat=C.mat("Cocoa", "8B5A3C", rough=0.4), seg=12)]
    parts += [C.cyl("holder", (x + 0.1, y + 0.06, top), r=0.06, h=0.02, mat=C.mat("Brass", rough=0.45), seg=12, base=True),
              C.cyl("candle", (x + 0.1, y + 0.06, top + 0.02), r=0.03, h=0.12, mat=C.mat("Candle", "FFF3D6", rough=0.7), seg=10, base=True),
              C.lathe("flame", [(0, top + 0.145), (0.014, top + 0.16), (0, top + 0.2)], seg=8, mat=C.mat("GlowCandle", "FFC04D", rough=0.9, emit="FFB347", strength=1.0))]
    parts[-1].location = (x + 0.1, y + 0.06, 0)
    return parts


def backpack(x, y):
    body = C.mat("Backpack", "E0674F", rough=0.8)
    flap = C.mat("BackpackFlap", "F2B45A", rough=0.8)
    strap = C.mat("WoodDark", rough=0.8)
    parts = [C.box("bp", (x, y, 0), (0.42, 0.26, 0.5), mat=body, bevel=0.1, bseg=3, base=True),
             C.box("flap", (x, y - 0.02, 0.34), (0.44, 0.3, 0.2), mat=flap, bevel=0.08, bseg=3, base=True),
             C.box("pocket", (x, y - 0.14, 0.08), (0.28, 0.06, 0.18), mat=flap, bevel=0.04, bseg=2, base=True),
             C.box("buckle", (x, y - 0.18, 0.4), (0.05, 0.02, 0.06), mat=C.mat("Brass", rough=0.45), bevel=0.008, bseg=1),
             C.torus("loop", (x, y, 0.56), R=0.06, r=0.014, rot=(90, 0, 0), mat=strap, seg=12, mseg=5)]
    parts.append(C.cyl("rollmat", (x, y, 0.6), r=0.07, h=0.46, rot=(0, 90, 0), mat=C.mat("Bedroll", "7DBFB3", rough=0.9), seg=12))
    for o in parts:
        o.data.transform(Matrix.Translation(o.location - Vector((x, y, 0))))
        o.location = (0, 0, 0)
        o.data.transform(C.xform(rot=(0, 0, -30)))
        o.data.transform(Matrix.Translation((x, y, 0)))
    return parts


def books(x, y):
    cols = ["4FA3A5", "F59BB6", "FFD65A", "B79BE8"]
    parts = []
    z = 0.03
    for k, c in enumerate(cols):
        h = 0.05 + 0.01 * (k % 2)
        parts.append(C.box("bk", (x + 0.01 * k, y, z), (0.26 - 0.02 * k, 0.19 - 0.01 * k, h), mat=C.mat("Book" + c, c, rough=0.8), bevel=0.008, bseg=1, base=True,
                           rot=(0, 0, 10 * (k % 2) - 5)))
        z += h
    return parts


def bunting():
    cols = ["F59BB6", "FFD65A", "7BC96F", "6EC8E6", "B79BE8"]
    parts = []
    y0, y1 = -1.9, 1.85
    pts = []
    for i in range(9):
        t = i / 8
        y = y0 + (y1 - y0) * t
        pts.append(Vector((RIDGE_X - 0.35, y, RIDGE_Z - 0.55 - 0.12 * math.sin(math.pi * (t * 2 % 1)))))
    parts.append(C.tube("string", pts, r=0.006, mat=C.mat("Rope", "D9BE8C", rough=0.9), seg=4, res=4))
    for k in range(16):
        t = (k + 0.5) / 16
        y = y0 + (y1 - y0) * t
        z = RIDGE_Z - 0.55 - 0.12 * math.sin(math.pi * (t * 2 % 1))
        fl = C.prism("flag", [(-0.07, 0.0), (0.07, 0.0), (0.0, -0.16)], -0.004, 0.004, C.mat("Flag" + cols[k % 5], cols[k % 5], rough=0.8), smooth=False)
        fl.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
        fl.location = (RIDGE_X - 0.35, y, z)
        C.bake_transform(fl)
        parts.append(fl)
    # hang the bunting ends from the canvas
    return parts


def potted_sprout(x, y):
    pot = C.lathe("pot", [(0, 0), (0.07, 0), (0.09, 0.12), (0.095, 0.13), (0, 0.13)], seg=14, mat=C.mat("Terracotta", "D9804F", rough=0.85))
    pot.location = (x, y, 0)
    parts = [pot, C.cyl("psoil", (x, y, 0.12), r=0.085, h=0.015, mat=C.mat("Soil", rough=0.95), seg=12)]
    parts.append(C.tube("st", [(x, y, 0.12), (x, y, 0.2), (x + 0.01, y, 0.25)], r=0.008, mat=C.mat("Stem"), seg=5, res=2))
    for s in (-1, 1):
        lf = C.leaf("l", length=0.08, width=0.035, thick=0.006, curl=0.03, mat=C.mat("Leaf", rough=0.8), seg=8, rings=5)
        lf.data.transform(C.xform(rot=(0, -25, 0 if s > 0 else 180)))
        lf.location = (x, y, 0.235)
        C.bake_transform(lf)
        parts.append(lf)
    return parts


def build_tent_interior():
    rnd = random.Random(14)
    root = C.empty("TentInterior")
    parts = ground(rnd)
    parts.append(slope_panel(RIDGE_X, RIDGE_Z, LEFT_X, 0.0, -HALF, HALF))
    # stub of the cut-away right slope near the ridge (shows canvas thickness)
    parts.append(slope_panel(RIDGE_X, RIDGE_Z, RIDGE_X + 0.16, RIDGE_Z - 0.19, -HALF, HALF, sag=0.0, name="stub"))
    parts.append(back_wall(HALF))
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts.append(C.cyl("ridge", (RIDGE_X, 0, RIDGE_Z - 0.02), r=0.05, h=2 * HALF + 0.4, rot=(90, 0, 0), mat=woodd, seg=10, bevel=0.012, bseg=1))
    for y in (-HALF - 0.05, HALF - 0.1):
        parts.append(C.cyl("pole", (RIDGE_X, y, 0), r=0.045, h=RIDGE_Z + 0.2, mat=wood, seg=10, base=True, bevel=0.015, bseg=1))
        parts.append(C.sphere("knob", (RIDGE_X, y, RIDGE_Z + 0.24), r=0.08, mat=woodd, seg=10, rings=6))
    # ropes + pegs at the canvas foot
    for y in (-1.6, 0.0, 1.6):
        parts.append(C.cyl("peg", (LEFT_X - 0.12, y, -0.02), r=0.03, r2=0.018, h=0.12, mat=woodd, seg=6, base=True))
    parts += bedroll()
    lx, ly, lz = RIDGE_X - 0.02, 0.55, 1.75
    parts += lantern(lx, ly, lz)
    parts += crate(0.55, 1.3)
    # (backpack + book stack removed to free the placement slots)
    parts += bunting()
    parts += potted_sprout(0.45, 0.72)
    body = C.join(parts, "TentInteriorMesh")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    C.empty("SproutOrigin", MAT + SPROUT_LOCAL, parent=root)
    C.empty("LampLight", (lx, ly, lz), parent=root)
    C.empty("RoomCenter", (-0.25, 0.4, 1.0), parent=root)
    # player placement slots (items face Blender -Y = SceneKit +Z at identity)
    C.slot("SlotFloor1", (1.45, 1.4, 0.0), root)                      # back-right, against the back canvas
    C.slot("SlotFloor2", (1.3, -0.35, 0.0), root, rz=30)              # right side, turned toward the camera
    C.slot("SlotFloor3", (-0.6, -1.45, 0.0), root, rz=15)             # in front of the bedroll foot
    C.slot("SlotWall1", (0.45, HALF - 0.07, 1.45), root)              # back canvas above the crate
    # on the sloped left canvas: face into the tent, tilted with the slope
    L = math.hypot(RIDGE_X - LEFT_X, RIDGE_Z)
    nrm = Vector((RIDGE_Z / L, 0, -(RIDGE_X - LEFT_X) / L))      # inward canvas normal
    p = Vector((LEFT_X + (RIDGE_X - LEFT_X) * 1.4 / RIDGE_Z, -0.6, 1.4)) + nrm * 0.1
    C.slot("SlotWall2", tuple(p), root, rz=90, ry_after=math.degrees(math.atan2(-nrm.z, nrm.x)))
    return root

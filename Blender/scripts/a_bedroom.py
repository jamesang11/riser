"""Cozy cutaway bedroom diorama (root `Bedroom`) for sick days."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import common as C
import a_sickbed as SB

HALF = 2.25             # floor half-size (4.5 m)
WALL_H = 2.8
WT = 0.15               # wall thickness
BED = Vector((-0.55, 1.2, 0))            # bed centre (headboard toward +Y / back wall)
SPROUT_LOCAL = Vector((0, -0.12, SB.MAT_TOP))
SPROUT_SCALE = 2.1
RECLINE = -0.62         # radians about X (app applies the same)


def moved(objs, off):
    for o in objs:
        o.data.transform(Matrix.Translation(Vector(off) + o.location))
        o.location = (0, 0, 0)
    return objs


def flat_blanket():
    cols = [C.mat("QuiltPink", "F7B7C9", rough=0.95), C.mat("QuiltBlue", "A8D0F0", rough=0.95), C.mat("QuiltMint", "A8E0C8", rough=0.95),
            C.mat("QuiltButter", "FFE9A8", rough=0.95), C.mat("QuiltLilac", "D0B8F0", rough=0.95)]
    back = C.mat("QuiltBack", "F6EEDC", rough=0.95)
    x0, x1, y0, y1 = -0.74, 0.74, -1.0, -0.05
    nx, ny = 16, 10
    bm = bmesh.new()
    V = []
    for i in range(nx + 1):
        row = []
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            z = SB.MAT_TOP + 0.015
            if abs(x) > 0.64:
                z -= min(0.2, (abs(x) - 0.64) * 2.6)
            if y < -0.92:
                z -= min(0.2, (-0.92 - y) * 3.0)
            z += 0.012 * math.sin(x * 9 + y * 4)
            row.append(bm.verts.new((x, y, z)))
        V.append(row)
    patch = 0.185
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            c = f.calc_center_median()
            f.material_index = int(math.floor(c.x / patch) * 2 + math.floor(c.y / patch) * 3) % len(cols)
    q = C.mk("blanket", bm, cols)
    so = q.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.03; so.offset = 1
    C.apply_mods(q)
    fold = C.box("fold", (0, y1 - 0.06, SB.MAT_TOP + 0.05), (1.3, 0.14, 0.035), mat=back, bevel=0.015, bseg=2)
    roll = C.cyl("roll", (0, y1 + 0.005, SB.MAT_TOP + 0.045), r=0.03, h=1.3, rot=(0, 90, 0), mat=back, seg=8)
    return [q, fold, roll]


def walls(rnd):
    cream = C.mat("Wallpaper", "F6E9D2", rough=0.9)
    stripe = C.mat("WallpaperStripe", "F2E2C7", rough=0.9)
    lower = C.mat("Wainscot", "BFD8B8", rough=0.85)
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    parts = [C.box("backwall", (0, HALF + WT / 2, 0), (2 * HALF + 2 * WT, WT, WALL_H), mat=cream, bevel=0.02, bseg=1, base=True),
             C.box("leftwall", (-HALF - WT / 2, 0, 0), (WT, 2 * HALF + WT, WALL_H), mat=cream, bevel=0.02, bseg=1, base=True)]
    # lower sage wainscot + chair rail + skirting + top trim
    parts.append(C.box("wb", (0, HALF - 0.01, 0), (2 * HALF, 0.03, 0.9), mat=lower, bevel=0.0, smooth=False, base=True))
    parts.append(C.box("wl", (-HALF + 0.01, 0, 0), (0.03, 2 * HALF, 0.9), mat=lower, bevel=0.0, smooth=False, base=True))
    for (z, h, d, top) in [(0.0, 0.16, 0.05, False), (0.88, 0.05, 0.05, False), (WALL_H - 0.02, 0.09, WT + 0.1, True)]:
        yb = HALF + WT / 2 if top else HALF - d / 2
        xl = -HALF - WT / 2 if top else -HALF + d / 2
        m = wood if z > 0.5 else woodd
        parts.append(C.box("tb", (0, yb, z), (2 * HALF + 0.3, d, h), mat=m, bevel=0.012, bseg=1, base=True))
        parts.append(C.box("tl", (xl, 0, z), (d, 2 * HALF + 0.3, h), mat=m, bevel=0.012, bseg=1, base=True))
    # subtle wallpaper stripes (upper part)
    for k in range(13):
        x = -HALF + 0.18 + k * 0.35
        parts.append(C.box("sb", (x, HALF - 0.005, 0.93), (0.1, 0.01, WALL_H - 1.0), mat=stripe, bevel=0.0, smooth=False, base=True))
        y = -HALF + 0.18 + k * 0.35
        parts.append(C.box("sl", (-HALF + 0.005, y, 0.93), (0.01, 0.1, WALL_H - 1.0), mat=stripe, bevel=0.0, smooth=False, base=True))
    # cutaway wall caps (wood edge on the open ends)
    parts.append(C.box("capb", (HALF + WT / 2, HALF + WT / 2, 0), (WT + 0.04, WT + 0.04, WALL_H + 0.06), mat=wood, bevel=0.015, bseg=1, base=True))
    parts.append(C.box("capl", (-HALF - WT / 2, -HALF - WT / 2, 0), (WT + 0.04, WT + 0.04, WALL_H + 0.06), mat=wood, bevel=0.015, bseg=1, base=True))
    parts.append(C.box("corner", (-HALF - WT / 2, HALF + WT / 2, 0), (WT + 0.04, WT + 0.04, WALL_H + 0.06), mat=wood, bevel=0.015, bseg=1, base=True))
    return parts


def floor(rnd):
    tones = [C.mat("FloorA", "C9905A", rough=0.8), C.mat("FloorB", "B98350", rough=0.8), C.mat("FloorC", "D49D66", rough=0.8)]
    parts = []
    w = 0.3
    n = int(2 * HALF / w)
    for i in range(n):
        y = -HALF + w / 2 + i * w
        cut = rnd.uniform(-1.4, 1.4)
        for (xa, xb) in [(-HALF, cut), (cut, HALF)]:
            parts.append(C.box("plank", ((xa + xb) / 2, y, -0.12), (xb - xa - 0.01, w - 0.012, 0.12), mat=tones[(i + (xa > -HALF)) % 3], bevel=0.008, bseg=1, base=True))
    parts.append(C.box("base", (0, 0, -0.35), (2 * HALF + 0.3, 2 * HALF + 0.3, 0.24), mat=C.mat("WoodDark", rough=0.8), bevel=0.03, bseg=1, base=True))
    return parts


def window():
    wood = C.mat("Wood", rough=0.8)
    glass = C.mat("GlowWindow", "CFE8F5", rough=0.3, emit="FFD58A", strength=0.5)
    cx, cz, r = 1.05, 1.75, 0.45
    y = HALF - 0.02
    parts = [C.cyl("glass", (cx, y, cz), r=r, h=0.02, rot=(90, 0, 0), mat=glass, seg=28, smooth=False),
             C.torus("frame", (cx, y - 0.03, cz), R=r + 0.03, r=0.055, rot=(90, 0, 0), mat=wood, seg=28, mseg=8),
             C.box("mv", (cx, y - 0.025, cz), (0.045, 0.04, 2 * r), mat=wood, bevel=0.01, bseg=1),
             C.box("mh", (cx, y - 0.025, cz), (2 * r, 0.04, 0.045), mat=wood, bevel=0.01, bseg=1),
             C.box("sill", (cx, y - 0.08, cz - r - 0.07), (0.8, 0.16, 0.05), mat=wood, bevel=0.015, bseg=2),
             C.cyl("rod", (cx, y - 0.1, cz + r + 0.14), r=0.018, h=1.35, rot=(0, 90, 0), mat=C.mat("WoodDark"), seg=8)]
    for s in (-1, 1):
        parts.append(C.sphere("rodend", (cx + s * 0.68, y - 0.1, cz + r + 0.14), r=0.035, mat=C.mat("WoodDark"), seg=8, rings=5))
        # gathered curtain: a wavy panel pinched at the tie
        bm = bmesh.new()
        rows = []
        for i in range(9):
            t = i / 8
            z = cz + r + 0.14 - t * 1.15
            pinch = 1 - 0.55 * math.exp(-((t - 0.58) / 0.14) ** 2)
            width = 0.28 * pinch * (1 + 0.35 * t)
            row = []
            for j in range(7):
                u = j / 6
                xx = cx + s * (0.66 - width * u)
                yy = y - 0.1 - 0.035 * math.sin(u * math.pi * 3) * pinch
                row.append(bm.verts.new((xx, yy, z)))
            rows.append(row)
        for i in range(8):
            for j in range(6):
                bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
        cur = C.mk("curtain", bm, [C.mat("Curtain", "F7B7C9", rough=0.95)])
        so = cur.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.02
        C.apply_mods(cur)
        C.shade(cur, 60)
        parts.append(cur)
        parts.append(C.torus("tie", (cx + s * 0.6, y - 0.1, cz + r + 0.14 - 0.58 * 1.15), R=0.07, r=0.015, rot=(0, 90, 0), scale=(1, 1.4, 0.7), mat=C.mat("QuiltButter", "FFE9A8"), seg=12, mseg=5))
    return parts


def nightstand(x, y):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts = [C.box("ns", (x, y, 0), (0.52, 0.44, 0.56), mat=wood, bevel=0.03, bseg=2, base=True),
             C.box("nstop", (x, y, 0.56), (0.58, 0.5, 0.05), mat=woodd, bevel=0.02, bseg=2, base=True),
             C.box("drawer", (x, y - 0.225, 0.36), (0.42, 0.02, 0.15), mat=C.mat("WoodLight", rough=0.8), bevel=0.01, bseg=1),
             C.sphere("knob", (x, y - 0.245, 0.36), r=0.025, mat=C.mat("Brass", rough=0.45), seg=8, rings=5)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.cyl("leg", (x + sx * 0.21, y + sy * 0.17, -0.0), r=0.025, r2=0.02, h=0.06, mat=woodd, seg=6))
    base = C.lathe("lampbase", [(0, 0.61), (0.09, 0.61), (0.11, 0.66), (0.08, 0.75), (0.03, 0.8), (0.02, 0.9), (0, 0.9)], seg=16, mat=C.mat("LampCeramic", "5DB3B5", rough=0.4))
    base.location = (x - 0.05, y + 0.03, 0)
    shade = C.lathe("shade", [(0.1, 0.88), (0.18, 0.88), (0.12, 1.08), (0.06, 1.08)], seg=18, mat=C.mat("GlowLamp", "FFF1C8", rough=0.8, emit="FFD58A", strength=1.0), caps=False, sharp=80)
    so = shade.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.012
    C.apply_mods(shade)
    shade.location = (x - 0.05, y + 0.03, 0)
    parts += [base, shade]
    # little book + glasses on the nightstand
    parts.append(C.box("book", (x + 0.14, y - 0.05, 0.61), (0.16, 0.22, 0.04), mat=C.mat("BookRed", "E0674F", rough=0.8), bevel=0.008, bseg=1, base=True, rot=(0, 0, 12)))
    return parts, Vector((x - 0.05, y + 0.03, 0.98))


def rug():
    cols = [C.mat("RugPink", "F4A9B8", rough=0.95), C.mat("RugCream", "F6EEDC", rough=0.95), C.mat("RugSage", "A9CFA4", rough=0.95), C.mat("RugMustard", "EFC869", rough=0.95)]
    parts = [C.cyl("rugc", (0, 0, 0.0), r=0.12, h=0.035, mat=cols[0], seg=16, base=True, bevel=0.015, bseg=1)]
    for k in range(1, 9):
        parts.append(C.torus("braid", (0, 0, 0.018), R=0.12 + k * 0.105, r=0.055, scale=(1, 1, 0.34), mat=cols[k % 4], seg=40, mseg=6))
    for o in parts:
        o.data.transform(Matrix.Diagonal((1.0, 0.78, 1, 1)))
    return moved(parts, (0.15, -0.55, 0))


def bookshelf(x, y):
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    W, D, H = 1.0, 0.34, 1.35
    parts = [C.box("bsL", (x, y - W / 2, 0), (D, 0.05, H), mat=wood, bevel=0.012, bseg=1, base=True),
             C.box("bsR", (x, y + W / 2, 0), (D, 0.05, H), mat=wood, bevel=0.012, bseg=1, base=True),
             C.box("bsB", (x - D / 2 + 0.01, y, 0), (0.02, W, H), mat=woodd, bevel=0.0, smooth=False, base=True)]
    rnd = random.Random(8)
    bcols = ["E0674F", "4FA3A5", "F2B45A", "B79BE8", "7BC96F", "F59BB6", "34497A"]
    for k, z in enumerate((0.0, 0.44, 0.88, H - 0.04)):
        parts.append(C.box("shelf", (x, y, z), (D, W, 0.04), mat=wood, bevel=0.01, bseg=1, base=True))
        if z > H - 0.1:
            continue
        yy = y - W / 2 + 0.06
        while yy < y + W / 2 - 0.12:
            bw = rnd.uniform(0.04, 0.07)
            bh = rnd.uniform(0.24, 0.34)
            col = rnd.choice(bcols)
            tilt = 0 if rnd.random() > 0.15 else 12
            parts.append(C.box("bk", (x + 0.02, yy + bw / 2, z + 0.04), (0.24, bw, bh), mat=C.mat("Book" + col, col, rough=0.8), bevel=0.006, bseg=1, base=True, rot=(tilt, 0, 0)))
            yy += bw + 0.008
            if rnd.random() < 0.12:
                yy += 0.12
    # trinkets on top: a tiny potted succulent and a globe-ish ball
    pot = C.lathe("tpot", [(0, H), (0.06, H), (0.07, H + 0.09), (0, H + 0.09)], seg=12, mat=C.mat("Terracotta", "D9804F", rough=0.85))
    pot.location = (x, y - 0.25, 0)
    parts.append(pot)
    parts.append(C.sphere("succ", (x, y - 0.25, H + 0.12), r=1, scale=(0.07, 0.07, 0.05), mat=C.mat("Leaf", rough=0.8), seg=10, rings=6))
    parts.append(C.sphere("ball", (x, y + 0.22, H + 0.09), r=0.08, mat=C.mat("RoofTeal", rough=0.6), seg=12, rings=8))
    return parts


def plant(x, y):
    parts = [C.lathe("pot", [(0, 0), (0.17, 0), (0.22, 0.34), (0.24, 0.36), (0.24, 0.4), (0.0, 0.4)], seg=18, mat=C.mat("Terracotta", "D9804F", rough=0.85))]
    parts[0].location = (x, y, 0)
    parts.append(C.cyl("psoil", (x, y, 0.37), r=0.21, h=0.02, mat=C.mat("Soil", rough=0.95), seg=16))
    rnd = random.Random(5)
    for k in range(8):
        a = k * 45 + rnd.uniform(-15, 15)
        L = rnd.uniform(0.45, 0.7)
        st = C.tube("pst", [(x, y, 0.38), (x + 0.1 * math.cos(math.radians(a)), y + 0.1 * math.sin(math.radians(a)), 0.38 + L * 0.7)], r=0.012, mat=C.mat("Stem"), seg=4, res=1)
        lf = C.leaf("pl", length=0.34, width=0.14, thick=0.02, curl=-0.06, mat=C.mat("Leaf" if k % 2 else "LeafDark", rough=0.8), seg=8, rings=5, fold=0.3)
        lf.data.transform(C.xform(rot=(0, -10 + rnd.uniform(-20, 20), a)))
        lf.location = (x + 0.1 * math.cos(math.radians(a)), y + 0.1 * math.sin(math.radians(a)), 0.38 + L * 0.7)
        C.bake_transform(lf)
        parts += [st, lf]
    return parts


def picture(center, normal_axis, w, h, kind):
    """Framed picture on a wall. normal_axis 'y' = back wall (faces -Y), 'x' = left wall (faces +X)."""
    wood = C.mat("WoodDark", rough=0.8)
    parts = []
    fr = C.box("frame", (0, 0, 0), (w + 0.08, 0.04, h + 0.08), mat=wood, bevel=0.012, bseg=1)
    bg = C.box("art", (0, -0.022, 0), (w, 0.01, h), mat=C.mat("ArtSky", "A8D8F0" if kind == 0 else "FCE3C8", rough=0.9), bevel=0.0, smooth=False)
    parts += [fr, bg]
    if kind == 0:     # little landscape: hill + sun
        parts.append(C.sphere("hill", (0, -0.028, -h / 2), r=1, scale=(w * 0.6, 0.004, h * 0.45), mat=C.mat("Grass", rough=0.9), seg=16, rings=6))
        parts.append(C.cyl("sun", (w * 0.22, -0.03, h * 0.2), r=h * 0.12, h=0.004, rot=(90, 0, 0), mat=C.mat("FlowerYellow"), seg=14))
    else:             # sprout portrait-ish: a cream blob with a stem
        parts.append(C.sphere("blob", (0, -0.028, -h * 0.12), r=1, scale=(w * 0.3, 0.004, h * 0.26), mat=C.mat("SproutBodyArt", "F3F6E4", rough=0.9), seg=16, rings=6))
        parts.append(C.box("st", (0, -0.03, h * 0.2), (0.012, 0.004, h * 0.14), mat=C.mat("Stem"), bevel=0.0, smooth=False))
        for s in (-1, 1):
            parts.append(C.sphere("eye", (s * w * 0.09, -0.032, -h * 0.13), r=1, scale=(0.012, 0.003, 0.018), mat=C.mat("SproutEye"), seg=8, rings=4))
    o = C.join(parts)
    C.set_origin(o, (0, 0, 0))
    if normal_axis == 'x':
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
    o.location = center
    C.bake_transform(o)
    return o


def calendar(x, z):
    parts = [C.box("cal", (x, HALF - 0.012, z), (0.26, 0.012, 0.32), mat=C.mat("Paper", "FFFFFF", rough=0.9), bevel=0.004, bseg=1),
             C.box("calh", (x, HALF - 0.02, z + 0.12), (0.26, 0.012, 0.08), mat=C.mat("RoofRed", rough=0.8), bevel=0.004, bseg=1),
             C.cyl("pin", (x, HALF - 0.03, z + 0.17), r=0.012, h=0.02, rot=(90, 0, 0), mat=C.mat("Brass", rough=0.45), seg=8)]
    for i in range(4):
        for j in range(5):
            m = C.mat("CalRed", "F28B8B", rough=0.9) if (i, j) == (2, 3) else C.mat("CalGrid", "D8D2C4", rough=0.9)
            parts.append(C.box("cell", (x - 0.1 + j * 0.05, HALF - 0.02, z + 0.04 - i * 0.05), (0.035, 0.006, 0.035), mat=m, bevel=0.0, smooth=False))
    return parts


def slippers(x, y):
    parts = []
    for s in (-1, 1):
        sl = C.sphere("slip", (x + s * 0.09, y, 0.035), r=1, scale=(0.06, 0.13, 0.04), rot=(0, 0, s * 8), mat=C.mat("Slipper", "F7B7C9", rough=0.95), seg=12, rings=6)
        for v in sl.data.vertices:
            if v.co.z < 0.0:
                v.co.z *= 0.3
        parts.append(sl)
        parts.append(C.sphere("pom", (x + s * 0.09, y - 0.09, 0.07), r=0.028, mat=C.mat("QuiltBack"), seg=8, rings=5))
    return parts


def build_bedroom():
    rnd = random.Random(12)
    root = C.empty("Bedroom")
    parts = floor(rnd) + walls(rnd)
    bed = moved(SB.bed_frame() + SB.stool() + flat_blanket(), BED)
    parts += bed
    ns, lamp_pt = nightstand(BED.x - 1.05, HALF - 0.4)
    parts += ns
    parts += window()
    parts += rug()
    # (bookshelf + potted plant removed to free the player placement slots)
    parts.append(picture((-HALF + 0.02, -0.95, 2.05), 'x', 0.42, 0.32, 0))
    parts.append(picture((-HALF + 0.02, 1.05, 2.05), 'x', 0.28, 0.36, 1))
    parts.append(picture((BED.x - 0.05, HALF - 0.02, 2.1), 'y', 0.5, 0.36, 0))
    parts += calendar(0.22, 1.5)
    parts += slippers(BED.x + 0.95, BED.y - 1.25)
    body = C.join(parts, "BedroomMesh")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    C.empty("SproutOrigin", BED + SPROUT_LOCAL, parent=root)
    C.empty("LampLight", lamp_pt, parent=root)
    C.empty("RoomCenter", (-0.2, 0.55, 1.0), parent=root)
    # player placement slots (items face Blender -Y = SceneKit +Z at identity)
    C.slot("SlotFloor1", (1.65, 1.7, 0.0), root)                      # back-right, under the window
    C.slot("SlotFloor2", (-1.72, -1.3, 0.0), root, rz=90)             # against the left wall, front
    C.slot("SlotFloor3", (-1.75, 0.95, 0.0), root, rz=90)             # against the left wall, beside the bed
    C.slot("SlotWall1", (-HALF + 0.01, -0.1, 1.4), root, rz=90)       # left wall
    C.slot("SlotWall2", (-1.75, HALF - 0.01, 1.55), root)             # back wall above the nightstand
    return root

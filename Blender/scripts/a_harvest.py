"""Harvest festival decor: pumpkin patch, scarecrow, autumn maple."""
import math, random
from mathutils import Vector, Matrix
import common as C
import a_nature
from a_hats import maple_leaf


def pumpkin(name, r, col, rnd, squash=0.72):
    m = C.mat(col[0], col[1], rough=0.75)
    prof = []
    n = 10
    for i in range(n + 1):
        phi = math.pi * i / n
        prof.append((r * math.sin(phi) if 0 < i < n else 0.0, r * squash * (1 - math.cos(phi))))
    prof[0] = (0.0, r * squash * 0.12)          # dimpled bottom
    prof[-1] = (0.0, r * squash * 1.82)         # dimpled top
    o = C.lathe(name, prof, seg=40, mat=m, rfun=lambda t, z: 1 - 0.085 * abs(math.sin(4 * t)) ** 1.4)
    C.shade(o, 180)
    st = C.tube(name + "st", [(0, 0, r * squash * 1.75), (0.01, 0, r * squash * 2.1), (0.05 * r / 0.2, 0, r * squash * 2.25)],
                r=0.028 * r / 0.2 + 0.01, radii=[1.3, 1.0, 0.8], mat=C.mat("WoodDark", rough=0.85), seg=6, res=3)
    p = C.join([o, st], name)
    return p


def round_leaf(name, size):
    o = C.lathe(name, [(0, 0.0), (size, 0.012), (size * 0.9, 0.02), (0, 0.03)], seg=16, mat=C.mat("LeafDark", rough=0.85),
                rfun=lambda t, z: 0.8 + 0.2 * abs(math.cos(2.5 * t)), sharp=80)
    for v in o.data.vertices:
        v.co.z += 0.6 * (v.co.x ** 2 + v.co.y ** 2) / size   # cupped
    return o


def build_pumpkins():
    rnd = random.Random(21)
    root = C.empty("Pumpkins")
    parts = []
    specs = [((0.05, 0.05), 0.3, ("PumpkinOrange", "F28C3A"), 0.7), ((-0.42, -0.2), 0.2, ("PumpkinDeep", "E3702C"), 0.75),
             ((0.45, -0.25), 0.16, ("PumpkinPale", "F3DCA8"), 0.72), ((-0.25, 0.35), 0.13, ("PumpkinGold", "F6B24A"), 0.8)]
    for (x, y), r, col, sq in specs:
        p = pumpkin("pk", r, col, rnd, sq)
        p.data.transform(C.xform(rot=(rnd.uniform(-5, 5), rnd.uniform(-5, 5), rnd.uniform(0, 360))))
        p.location = (x, y, -0.01)
        parts.append(p)
    vine = C.mat("Stem", rough=0.8)
    for pts in [[(0.05, 0.05, 0.02), (-0.2, -0.1, 0.02), (-0.42, -0.2, 0.02)], [(0.05, 0.05, 0.02), (0.3, -0.05, 0.02), (0.45, -0.25, 0.02)],
                [(0.05, 0.05, 0.02), (-0.1, 0.25, 0.02), (-0.25, 0.35, 0.02)], [(0.45, -0.25, 0.02), (0.6, -0.05, 0.02), (0.55, 0.15, 0.03)]]:
        parts.append(C.tube("vine", pts, r=0.014, mat=vine, seg=5, res=5))
    for (x, y, s) in [(-0.2, -0.05, 0.13), (0.28, 0.02, 0.12), (-0.05, 0.3, 0.11), (0.6, 0.02, 0.1), (-0.55, 0.05, 0.12), (0.2, -0.45, 0.1), (-0.15, -0.42, 0.09)]:
        lf = round_leaf("lf", s)
        lf.data.transform(C.xform(rot=(rnd.uniform(-15, 15), rnd.uniform(-15, 15), rnd.uniform(0, 360))))
        lf.location = (x, y, 0.005)
        parts.append(lf)
    # curly tendrils
    for (x, y) in [(-0.3, 0.1), (0.35, -0.4)]:
        pts = [(x + 0.04 * math.cos(a) * (1 - a / 12), y + 0.04 * math.sin(a) * (1 - a / 12), 0.02 + a * 0.004) for a in [i * 0.8 for i in range(12)]]
        parts.append(C.tube("tend", pts, r=0.005, mat=vine, seg=4, res=2))
    # little wooden sign
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    parts.append(C.box("post", (0.42, 0.32, 0), (0.05, 0.05, 0.55), mat=woodd, bevel=0.012, bseg=2, base=True))
    parts.append(C.box("board", (0.42, 0.29, 0.5), (0.34, 0.04, 0.2), mat=wood, bevel=0.02, bseg=2, rot=(0, 0, -8)))
    icon = C.cyl("icon", (0.42, 0.265, 0.5), r=0.055, h=0.012, rot=(90, 0, 0), mat=C.mat("PumpkinOrange"), seg=16)
    parts.append(icon)
    parts.append(C.box("icst", (0.42, 0.262, 0.565), (0.012, 0.012, 0.03), mat=C.mat("Stem"), bevel=0.0, smooth=False))
    for dx in (-0.12, 0.12):
        parts.append(C.box("nail", (0.42 + dx, 0.266, 0.56), (0.014, 0.01, 0.014), mat=C.mat("Iron", rough=0.6), bevel=0.0, smooth=False))
    body = C.join(parts, "PumpkinPatch")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    return root


def build_scarecrow():
    rnd = random.Random(4)
    root = C.empty("Scarecrow")
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    straw = C.mat("HatStraw", "EACB84", rough=0.9)
    strawd = C.mat("StrawDark", "D4AE5E", rough=0.9)
    shirt = C.mat("ShirtBlue", "6F9BD1", rough=0.85)
    patch1 = C.mat("PatchOrange", "F2A15A", rough=0.85)
    patch2 = C.mat("PatchYellow", "FFD65A", rough=0.85)
    sack = C.mat("Burlap", "E3C894", rough=0.95)
    dark = C.mat("SproutEye", rough=0.3)
    parts = [C.cyl("pole", (0, 0.03, 0), r=0.045, h=1.25, mat=woodd, seg=10, base=True, bevel=0.01, bseg=1),
             C.cyl("bar", (0, 0.03, 1.08), r=0.035, h=1.1, rot=(0, 90, 0), mat=woodd, seg=10, bevel=0.01, bseg=1)]
    # shirt torso (soft rounded), sleeves along the bar
    torso = C.box("torso", (0, 0, 0.62), (0.4, 0.24, 0.52), mat=shirt, bevel=0.1, bseg=4, base=True)
    for v in torso.data.vertices:        # slight taper at the waist
        k = (v.co.z - 0.62) / 0.52
        v.co.x *= 0.85 + 0.15 * k
    parts.append(torso)
    for sx in (-1, 1):
        parts.append(C.tube("sleeve", [(sx * 0.15, 0.0, 1.06), (sx * 0.34, 0.01, 1.07), (sx * 0.5, 0.02, 1.06)], r=0.075, radii=[1.1, 1.0, 0.95],
                            mat=shirt, seg=10, res=3))
        parts.append(C.torus("cuff", (sx * 0.5, 0.02, 1.06), R=0.07, r=0.014, rot=(0, 90, 0), mat=C.mat("Rope", "D9BE8C", rough=0.9), seg=14, mseg=5))
        for k in range(5):
            a = math.radians(k * 72 + rnd.uniform(-15, 15))
            tip = Vector((sx * (0.64 + rnd.uniform(-0.02, 0.03)), 0.02 + 0.05 * math.cos(a), 1.06 + 0.05 * math.sin(a)))
            parts.append(C.tube("straw", [(sx * 0.52, 0.02, 1.06), tip], r=0.012, radii=[1, 0.3], mat=straw if k % 2 else strawd, seg=4, res=1))
    # patches + buttons + belt rope
    parts.append(C.box("patch", (-0.1, -0.125, 0.8), (0.1, 0.012, 0.09), mat=patch1, bevel=0.01, bseg=1, rot=(0, 12, 0)))
    parts.append(C.box("patch", (0.11, -0.125, 0.95), (0.08, 0.012, 0.08), mat=patch2, bevel=0.01, bseg=1, rot=(0, -10, 0)))
    parts.append(C.box("patch", (0.36, -0.07, 1.06), (0.06, 0.012, 0.06), mat=patch1, bevel=0.008, bseg=1))
    for z in (0.72, 0.86, 1.0):
        parts.append(C.cyl("btn", (0.0, -0.126, z), r=0.018, h=0.012, rot=(90, 0, 0), mat=C.mat("WoodDark"), seg=10))
    parts.append(C.torus("belt", (0, 0, 0.66), R=0.2, r=0.016, scale=(1, 0.65, 1), mat=C.mat("Rope"), seg=24, mseg=5))
    for k in range(9):
        x = -0.16 + k * 0.04
        parts.append(C.tube("hem", [(x, -0.08 + rnd.uniform(-0.02, 0.02), 0.64), (x * 1.2, -0.1, 0.5 + rnd.uniform(-0.03, 0.03))], r=0.014, radii=[1, 0.3],
                            mat=straw if k % 2 else strawd, seg=4, res=1))
    # head: burlap sack, button eyes, stitched smile, rosy cheeks
    hc = Vector((0, 0.0, 1.33))
    head = C.sphere("head", hc, r=0.19, scale=(1, 0.92, 1.0), mat=sack, seg=24, rings=14)
    C.jitter(head, 0.006, 8, 2)
    parts.append(head)
    parts.append(C.torus("neck", (0, 0, 1.17), R=0.07, r=0.02, mat=C.mat("Rope"), seg=16, mseg=5))
    for sx in (-1, 1):
        parts.append(C.cyl("eye", (sx * 0.065, -0.168, 1.37), r=0.03, h=0.014, rot=(80, 0, 0), mat=dark, seg=14))
        parts.append(C.sphere("shine", (sx * 0.065 - 0.009, -0.177, 1.38), r=0.007, mat=C.mat("EyeShine", "FFFFFF", rough=0.25, emit="FFFFFF", strength=0.6), seg=8, rings=4))
        parts.append(C.sphere("cheek", (sx * 0.12, -0.15, 1.29), r=1, scale=(0.03, 0.01, 0.02), rot=(0, 0, sx * 30), mat=C.mat("SproutCheek"), seg=10, rings=5))
    smile = [(math.sin(a) * 0.075, -0.176 + 0.02 * (1 - math.cos(a)), 1.29 - 0.03 * math.cos(a) + 0.015) for a in [i * 0.2 - 0.6 for i in range(7)]]
    parts.append(C.tube("smile", smile, r=0.007, mat=dark, seg=5, res=3))
    for k in range(0):
        x = -0.06 + k * 0.03
        parts.append(C.box("stitch", (x, -0.176, 1.26 + 0.02 * (abs(x) / 0.06) ** 2), (0.004, 0.006, 0.025), mat=dark, bevel=0.0, smooth=False))
    # straw hat
    brim = C.lathe("brim", [(0.13, 0.01), (0.26, 0.0), (0.3, -0.02), (0.29, -0.03), (0.25, -0.012), (0.13, -0.006), (0.13, 0.01)], seg=36, mat=straw,
                   caps=False, sharp=80, rfun=lambda t, z: 1 + 0.015 * math.cos(30 * t))
    crown = C.lathe("crown", [(0.15, 0.0), (0.14, 0.09), (0.11, 0.15), (0, 0.16)], seg=36, mat=straw)
    band = C.torus("band", (0, 0, 0.025), R=0.148, r=0.02, mat=C.mat("RoofRed", rough=0.8), seg=30, mseg=6)
    hat = C.join([brim, crown, band])
    C.set_origin(hat, (0, 0, 0))
    hat.data.transform(C.xform(rot=(-6, 10, 0)))
    hat.location = (0, 0, 1.45)
    C.bake_transform(hat)
    parts.append(hat)
    for k in range(7):
        a = math.radians(-160 + k * 23)
        p0 = Vector((0.17 * math.cos(a), 0.15 * math.sin(a) + 0.02, 1.42))
        parts.append(C.tube("hair", [p0, p0 + Vector((0.07 * math.cos(a), 0.06 * math.sin(a), -0.09))], r=0.012, radii=[1, 0.3],
                            mat=straw if k % 2 else strawd, seg=4, res=1))
    # a pumpkin at its feet
    pk = pumpkin("pk", 0.12, ("PumpkinOrange", "F28C3A"), rnd, 0.72)
    pk.location = (0.22, -0.18, 0)
    parts.append(pk)
    body = C.join(parts, "ScarecrowBody")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    return root


def build_maple():
    rnd = random.Random(9)
    root = C.empty("Maple")
    top = Vector((0.02, 0, 1.12))
    tr = a_nature.trunk([(0, 0, -0.02), (-0.04, 0, 0.4), (0.05, 0.02, 0.8), tuple(top + Vector((0, 0, 0.25)))], 0.14, [1.25, 1.0, 0.85, 0.7], mat="WoodDark")
    C.set_origin(tr, (0, 0, 0))
    C.set_parent(tr, root)
    c = Vector((0, 0, 1.78))
    spheres = [(c, 0.76), (c + Vector((0.6, 0.05, -0.18)), 0.52), (c + Vector((-0.62, -0.05, -0.16)), 0.54),
               (c + Vector((0.05, 0.55, -0.1)), 0.5), (c + Vector((0.0, -0.58, -0.14)), 0.52),
               (c + Vector((0.3, 0.25, 0.42)), 0.5), (c + Vector((-0.32, -0.22, 0.44)), 0.47), (c + Vector((0.38, -0.35, 0.18)), 0.44),
               (c + Vector((-0.42, 0.35, 0.15)), 0.44)]
    can = C.blob("Canopy", [(p, r) for p, r in spheres], mat=C.mat("MapleOrange", "F08A3C", rough=0.85), voxel=0.045, smooth_iter=5, target=2600)
    a_nature.tone_canopy(can, C.mat("MapleGold", "FFBC5A", rough=0.85), None, seed=7, up=0.5)
    C.paint_faces(can, C.mat("MapleRed", "DC5A3C", rough=0.85), lambda cc, n: n.z < -0.35)
    leaves = []
    for p, nrm in a_nature.surface_points(can, 6, rnd, 1.25, 2.3, c):
        lf = maple_leaf("ml", 0.07, "MapleRed", n=30)
        q = Vector((0, -1, 0)).rotation_difference(nrm)
        lf.data.transform(q.to_matrix().to_4x4())
        lf.location = p + nrm * 0.02
        C.bake_transform(lf)
        leaves.append(lf)
    can = C.join([can] + leaves, "Canopy")
    C.set_origin(can, top)
    C.set_parent(can, root)
    fall = []
    cols = ["MapleRed", "MapleOrange", "MapleGold"]
    for i in range(16):
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0.3, 1.25)
        lf = maple_leaf("fl", rnd.uniform(0.05, 0.07), cols[i % 3], n=30)
        lf.data.transform(C.xform(rot=(90 + rnd.uniform(-10, 10), 0, rnd.uniform(0, 360))))
        lf.location = (d * math.cos(a), d * math.sin(a), 0.008)
        C.bake_transform(lf)
        fall.append(lf)
    fo = C.join(fall, "FallenLeaves")
    C.set_origin(fo, (0, 0, 0))
    C.set_parent(fo, root)
    return root

"""Sprout hats, modelled in SPROUT MODEL SPACE (root `Hat` at the sprout origin).

Each builder constructs the sprout temporarily (to fit against the head by ray casting),
builds the hat, then deletes the sprout unless keep_sprout=True (contact-sheet previews).
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import common as C
import a_sprout

HAT_IDS = ["straw", "flowercrown", "beanie", "frog", "wizard", "crown", "headphones", "bow",
           "explorer", "party", "pumpkin", "maple"]

BODY = None


def head_r(z):
    ok, p, n, _ = BODY.ray_cast(Vector((1, 0, z)), Vector((-1, 0, 0)))
    return p.x


def head_pt(x, y):
    ok, p, n, _ = BODY.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)))
    return p, n


def orient(o, up, loc):
    """Rotate mesh data so local +Z -> up, move object to loc."""
    q = Vector((0, 0, 1)).rotation_difference(up.normalized())
    o.data.transform(q.to_matrix().to_4x4())
    o.location = loc
    C.bake_transform(o)
    return o


def tilt_vec(n, dx=0.0, dy=0.0):
    return (n + Vector((dx, dy, 0))).normalized()


def five_petal(name, r, cols, center="FlowerYellow", seg=7):
    parts = []
    for i in range(5):
        a = 2 * math.pi * i / 5
        p = C.sphere(name + "p", (r * 0.9 * math.cos(a), r * 0.9 * math.sin(a), 0), r=1, scale=(r, r * 0.72, r * 0.28),
                     rot=(0, 0, math.degrees(a)), mat=C.mat(cols[i % len(cols)]), seg=seg, rings=5)
        parts.append(p)
    parts.append(C.sphere(name + "c", (0, 0, r * 0.25), r=r * 0.6, scale=(1, 1, 0.7), mat=C.mat(center), seg=seg, rings=5))
    f = C.join(parts)
    C.set_origin(f, (0, 0, 0))
    return f


def maple_leaf(name, size, col, n=60):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        u = t - math.pi / 2
        lobe = 0.38 + 0.62 * abs(math.cos(2.5 * u)) ** 2.2 + 0.07 * abs(math.cos(7.5 * u)) ** 3
        r = size * lobe * (0.7 if math.sin(t) < -0.3 else 1.0)
        pts.append((r * math.cos(t), r * math.sin(t)))
    o = C.prism(name, pts, -0.004, 0.004, C.mat(col, rough=0.8), bevel=0.0, smooth=False)
    # prism is in XZ: pts x->X, z->Z ; stem
    st = C.tube(name + "s", [(0, 0, -size * 0.6), (0, 0, -size * 1.25)], r=0.004, mat=C.mat(col), seg=4, res=1)
    return C.join([o, st], name)


# ---------------------------------------------------------------------------------------- hats
def hat_straw():
    straw = C.mat("HatStraw", "EACB84", rough=0.9)
    ribbon = C.mat("HatRibbon", "F59BB6", rough=0.8)
    z0 = 0.262
    rip = lambda t, z: 1 + 0.012 * math.cos(36 * t)
    brim = C.lathe("brim", [(0.175, 0.012), (0.25, 0.006), (0.3, -0.006), (0.312, -0.018), (0.3, -0.026), (0.25, -0.014), (0.175, -0.006), (0.175, 0.012)],
                   seg=48, mat=straw, rfun=rip, caps=False, sharp=80)
    crown = C.lathe("crown", [(0.195, 0.0), (0.185, 0.06), (0.16, 0.11), (0.115, 0.14), (0.058, 0.15), (0.05, 0.138), (0.105, 0.126),
                              (0.15, 0.1), (0.172, 0.055), (0.18, 0.0)], seg=48, mat=straw, rfun=rip, caps=False, sharp=80)
    band = C.torus("band", (0, 0, 0.03), R=0.19, r=0.022, mat=ribbon, seg=40, mseg=8, scale=(1, 1, 1.2))
    bows = [C.sphere("bw", (0.07 * s, 0.19, 0.035), r=1, scale=(0.045, 0.015, 0.03), rot=(0, 0, s * 20), mat=ribbon, seg=12, rings=6) for s in (-1, 1)]
    tails = [C.sphere("tl", (0.035 * s, 0.2, -0.02), r=1, scale=(0.018, 0.01, 0.05), rot=(0, s * 20, 0), mat=ribbon, seg=10, rings=5) for s in (-1, 1)]
    daisy = five_petal("dz", 0.022, ["White"])
    daisy.data.transform(C.xform(rot=(80, 0, 0)))
    daisy.location = (-0.12, -0.155, 0.06)
    h = C.join([brim, crown, band, daisy] + bows + tails, "HatMesh")
    C.set_origin(h, (0, 0, 0))
    h.data.transform(C.xform(rot=(-9, -7, 0)))
    h.location = (0, 0, z0)
    C.bake_transform(h)
    return h


def ring_crown_objects(z0, items, rnd, kind):
    parts = []
    rx = head_r(z0) - 0.004
    vine = C.torus("vine", (0, 0, z0), R=rx, r=0.012, mat=C.mat("HatVine", "5FAF5A", rough=0.8), seg=36, mseg=6, scale=(1, 0.9, 1))
    parts.append(vine)
    for i in range(items):
        a = 2 * math.pi * i / items + 0.2
        p = Vector((rx * math.cos(a), 0.9 * rx * math.sin(a), z0))
        outward = Vector((math.cos(a), math.sin(a) / 0.9, 0)).normalized()
        up = (outward * 0.8 + Vector((0, 0, 1))).normalized()
        if kind == "flower":
            cols = [["White"], ["Blossom"], ["FlowerYellow"], ["Purple"], ["BlossomLight"]][i % 5]
            f = five_petal("f%d" % i, rnd.uniform(0.024, 0.03), cols, center="FlowerYellow" if cols != ["FlowerYellow"] else "Orange")
            orient(f, up, p + outward * 0.012)
            parts.append(f)
            lf = C.leaf("l", length=0.045, width=0.018, thick=0.005, curl=0.01, mat=C.mat("Leaf"), seg=8, rings=5)
            lf.data.transform(C.xform(rot=(0, 0, math.degrees(a) + 60)))
            lf.location = Vector((rx * math.cos(a + 0.3), 0.9 * rx * math.sin(a + 0.3), z0 + 0.005))
            parts.append(lf)
        else:
            col = ["Apple", "Orange", "FlowerYellow", "Coral"][i % 4]
            lf = maple_leaf("m%d" % i, rnd.uniform(0.055, 0.065), col)
            # leaf faces outward, standing up-and-out
            face = outward
            lf.data.transform(C.xform(rot=(0, 0, 0)))
            m = Matrix.Rotation(math.atan2(face.y, face.x) - math.pi / 2, 4, 'Z') @ Matrix.Rotation(math.radians(-25), 4, 'X')
            lf.data.transform(m)
            lf.location = p + outward * 0.02 + Vector((0, 0, 0.035))
            C.bake_transform(lf)
            parts.append(lf)
    if kind == "maple":
        for a in (0.9, 2.6, 4.4):
            ac = [C.sphere("acorn", (0, 0, 0), r=1, scale=(0.017, 0.017, 0.021), mat=C.mat("Wood"), seg=10, rings=6),
                  C.sphere("acap", (0, 0, 0.012), r=1, scale=(0.02, 0.02, 0.011), mat=C.mat("WoodDark"), seg=10, rings=5)]
            aco = C.join(ac)
            C.set_origin(aco, (0, 0, 0))
            aco.location = (rx * 1.05 * math.cos(a), 0.9 * rx * 1.05 * math.sin(a), z0 + 0.005)
            parts.append(aco)
    return parts


def hat_flowercrown():
    rnd = random.Random(3)
    h = C.join(ring_crown_objects(0.285, 10, rnd, "flower"), "HatMesh")
    C.set_origin(h, (0, 0, 0))
    return h


def hat_maple():
    rnd = random.Random(5)
    h = C.join(ring_crown_objects(0.28, 8, rnd, "maple"), "HatMesh")
    C.set_origin(h, (0, 0, 0))
    return h


def tilted_cap(parts, x, y, dx, dy, sink=0.012):
    h = C.join(parts, "HatMesh")
    C.set_origin(h, (0, 0, 0))
    p, n = head_pt(x, y)
    up = tilt_vec(n, dx, dy)
    return orient(h, up, p - n * sink)


def hat_beanie():
    mustard = C.mat("HatMustard", "E2B342", rough=0.95)
    mustd = C.mat("HatMustardDark", "C99A2E", rough=0.95)
    dome = C.lathe("dome", [(0, 0.17), (0.08, 0.16), (0.14, 0.12), (0.175, 0.06), (0.185, 0.0)], seg=32, mat=mustard,
                   rfun=lambda t, z: 1 + 0.018 * math.cos(20 * t), caps=False)
    cuff = C.lathe("cuff", [(0.172, -0.01), (0.19, -0.005), (0.195, 0.03), (0.185, 0.05), (0.168, 0.045)], seg=32, mat=mustd,
                   rfun=lambda t, z: 1 + 0.03 * max(0, math.cos(20 * t)), caps=False, sharp=80)
    pom = C.sphere("pom", (0, 0, 0.19), r=0.048, mat=C.mat("NightcapCuff", "FFFFFF", rough=0.95), seg=14, rings=9)
    C.jitter(pom, 0.006, 40, 3)
    return tilted_cap([dome, cuff, pom], -0.035, 0.02, -0.28, 0.06, sink=0.075)


def hat_explorer():
    khaki = C.mat("HatKhaki", "D9C48E", rough=0.9)
    band = C.mat("HatKhakiBand", "8B6B45", rough=0.85)
    dome = C.lathe("dome", [(0, 0.13), (0.08, 0.125), (0.14, 0.095), (0.172, 0.05), (0.18, 0.0)], seg=32, mat=khaki, caps=False)
    brim = C.lathe("brim", [(0.17, 0.004), (0.26, -0.025), (0.275, -0.035), (0.26, -0.038), (0.17, -0.012), (0.17, 0.004)], seg=40, mat=khaki,
                   caps=False, sharp=80)
    bnd = C.lathe("band", [(0.176, 0.0), (0.18, 0.035), (0.172, 0.04), (0.168, 0.0)], seg=32, mat=band, caps=False)
    btn = C.sphere("btn", (0, 0, 0.13), r=0.02, scale=(1, 1, 0.5), mat=band, seg=10, rings=5)
    return tilted_cap([dome, brim, bnd, btn], -0.03, 0.03, -0.22, 0.14, sink=0.06)


def hat_pumpkin():
    orange = C.mat("HatPumpkin", "F28C3A", rough=0.8)
    dome = C.lathe("dome", [(0, 0.13), (0.06, 0.128), (0.11, 0.105), (0.145, 0.06), (0.155, 0.01), (0.14, -0.01), (0, -0.01)], seg=48, mat=orange,
                   rfun=lambda t, z: 1 - 0.09 * abs(math.sin(4 * t)) ** 1.5)
    stalk = C.tube("stalk", [(0, 0, 0.12), (0.005, 0, 0.16), (0.025, 0, 0.185)], r=0.015, radii=[1.2, 1, 0.8], mat=C.mat("WoodDark"), seg=6, res=3)
    lf = C.leaf("lf", length=0.07, width=0.03, thick=0.006, curl=0.02, mat=C.mat("Leaf"), seg=8, rings=5)
    lf.data.transform(C.xform(rot=(0, -20, 30)))
    lf.location = (0.005, 0.0, 0.14)
    C.bake_transform(lf)
    tend = C.tube("tend", [(-0.005, 0, 0.13), (-0.04, 0.01, 0.15), (-0.055, -0.01, 0.13), (-0.045, -0.02, 0.12)], r=0.004, mat=C.mat("Stem"), seg=4, res=4)
    return tilted_cap([dome, stalk, lf, tend], -0.07, 0.02, -0.3, 0.06, sink=0.04)


def hat_wizard():
    navy = C.mat("HatNavy", "34497A", rough=0.8)
    gold = C.mat("HatGold", "F2C14E", rough=0.45)
    cone = C.lathe("cone", [(0.14, 0.0), (0.12, 0.05), (0.09, 0.12), (0.06, 0.2), (0.035, 0.27), (0.015, 0.32), (0, 0.34)], seg=28, mat=navy, caps=False)
    for v in cone.data.vertices:
        t = max(0, v.co.z / 0.34)
        v.co.x -= 0.09 * t ** 2.5
        v.co.z -= 0.04 * t ** 3
    brim = C.lathe("brim", [(0.12, 0.008), (0.2, 0.0), (0.22, -0.008), (0.2, -0.014), (0.12, -0.006), (0.12, 0.008)], seg=36, mat=navy, caps=False, sharp=80)
    band = C.lathe("band", [(0.14, 0.0), (0.13, 0.035), (0.127, 0.035), (0.137, 0.0)], seg=28, mat=gold, caps=False)
    stars = []
    for (a, z, s) in [(20, 0.08, 1.0), (140, 0.12, 0.8), (260, 0.07, 0.9), (320, 0.18, 0.7), (80, 0.2, 0.6)]:
        pts = []
        for i in range(10):
            t = math.pi / 2 + i * math.pi / 5
            r = (0.022 if i % 2 == 0 else 0.009) * s
            pts.append((r * math.cos(t), r * math.sin(t)))
        st = C.prism("star", pts, -0.004, 0.004, gold, smooth=False)
        ar = math.radians(a)
        rr = 0.14 - 0.08 * (z / 0.2) + 0.004
        t = z / 0.34
        st.data.transform(Matrix.Rotation(ar + math.pi / 2, 4, 'Z'))
        st.location = (rr * math.cos(ar) - 0.09 * t ** 2.5, rr * math.sin(ar), z)
        C.bake_transform(st)
        stars.append(st)
    tip = C.sphere("tip", (-0.09, 0, 0.3), r=0.02, mat=gold, seg=10, rings=6)
    return tilted_cap([cone, brim, band, tip] + stars, -0.07, 0.02, -0.35, 0.0, sink=0.02)


def hat_party():
    cols = [C.mat("HatPartyPink", "F59BB6", rough=0.8), C.mat("HatPartyYellow", "FFD65A", rough=0.8), C.mat("HatPartyTeal", "4FA3A5", rough=0.8)]
    cone = C.lathe("cone", [(0.085, 0.0)] + [(0.085 * (1 - i / 10), 0.21 * i / 10) for i in range(1, 10)] + [(0, 0.21)], seg=24, mats=cols, caps=True)
    for p in cone.data.polygons:
        c = p.center
        a = math.atan2(c.y, c.x)
        p.material_index = int(((a / (2 * math.pi)) * 3 + c.z * 14) % 3)
    pom = C.sphere("pom", (0, 0, 0.215), r=0.03, mat=C.mat("NightcapCuff", "FFFFFF", rough=0.95), seg=12, rings=8)
    C.jitter(pom, 0.004, 50, 1)
    trim = C.torus("trim", (0, 0, 0.006), R=0.085, r=0.012, mat=cols[1], seg=24, mseg=6)
    return tilted_cap([cone, pom, trim], 0.12, 0.0, 0.25, 0.0, sink=0.015)


def hat_bow():
    pink = C.mat("HatBowPink", "F48FB1", rough=0.7)
    pinkd = C.mat("HatBowPinkDark", "E0739A", rough=0.7)
    loops = []
    for s in (-1, 1):
        lp = C.sphere("loop", (s * 0.058, 0, 0.0), r=1, scale=(0.06, 0.028, 0.045), rot=(0, s * -15, 0), mat=pink, seg=16, rings=8)
        for v in lp.data.vertices:          # pinch toward the knot
            k = max(0.0, 1 - abs(v.co.x - s * 0.058 + s * 0.06) / 0.12)
        loops.append(lp)
        loops.append(C.sphere("tail", (s * 0.025, -0.005, -0.045), r=1, scale=(0.018, 0.012, 0.045), rot=(0, s * 25, 0), mat=pinkd, seg=10, rings=6))
    knot = C.sphere("knot", (0, -0.012, 0.0), r=1, scale=(0.026, 0.024, 0.03), mat=pinkd, seg=12, rings=8)
    h = C.join(loops + [knot], "HatMesh")
    C.set_origin(h, (0, 0, 0))
    h.data.transform(Matrix.Scale(1.3, 4))
    h.data.transform(C.xform(rot=(90, 0, 0)))           # bow stands up, faces the viewer
    p, n = head_pt(0.115, -0.02)
    h.data.transform(C.xform(rot=(0, 0, -20)))
    h.data.transform(C.xform(rot=(0, 35, 0)))
    h.location = p + n * 0.015
    C.bake_transform(h)
    return h


def hat_frog():
    green = C.mat("HatFrog", "7CC66A", rough=0.85)
    greend = C.mat("HatFrogDark", "5FAF5A", rough=0.85)
    shell = C.lathe("shell", [(0.205, 0.0), (0.19, 0.055), (0.155, 0.1), (0.11, 0.13), (0.058, 0.142), (0.05, 0.13), (0.105, 0.118),
                              (0.148, 0.092), (0.178, 0.05), (0.19, 0.0)], seg=40, mat=green, caps=False, sharp=80)
    rim = C.torus("rim", (0, 0, 0.004), R=0.198, r=0.014, mat=greend, seg=40, mseg=6)
    parts = [shell, rim]
    for s in (-1, 1):
        ex, ey, ez = s * 0.09, -0.075, 0.125
        parts.append(C.sphere("eyeball", (ex, ey, ez), r=0.048, mat=green, seg=16, rings=10))
        parts.append(C.sphere("eyewhite", (ex, ey - 0.028, ez + 0.008), r=0.03, scale=(1, 0.6, 1), mat=C.mat("White"), seg=14, rings=8))
        parts.append(C.sphere("pupil", (ex, ey - 0.046, ez + 0.01), r=0.016, scale=(1, 0.5, 1.1), mat=C.mat("SproutEye"), seg=12, rings=6))
        parts.append(C.sphere("glint", (ex - 0.005, ey - 0.053, ez + 0.02), r=0.005, mat=C.mat("EyeShine", "FFFFFF", rough=0.25, emit="FFFFFF", strength=0.6), seg=8, rings=4))
        parts.append(C.sphere("blush", (s * 0.155, -0.12, 0.05), r=1, scale=(0.025, 0.008, 0.014), rot=(0, 0, s * 40), mat=C.mat("SproutCheek"), seg=10, rings=5))
    pts = [(math.sin(a) * 0.16, -math.cos(a) * 0.16 * 0.95 - 0.012, 0.045 - 0.012 * math.cos(a * 3)) for a in [x * 0.12 - 0.36 for x in range(7)]]
    parts.append(C.tube("smile", pts, r=0.006, mat=C.mat("HatFrogMouth", "3F7A3A", rough=0.8), seg=5, res=3))
    h = C.join(parts, "HatMesh")
    C.set_origin(h, (0, 0, 0))
    h.data.transform(C.xform(rot=(-10, 0, 0)))            # front edge lifted clear of the eyes
    h.location = (0, 0.0, 0.228)
    C.bake_transform(h)
    return h


def hat_crown():
    gold = C.mat("HatGold", "F2C14E", rough=0.45)
    z0 = 0.285
    rx = head_r(z0) + 0.004
    band = C.lathe("band", [(rx, 0.0), (rx + 0.01, 0.0), (rx + 0.012, 0.05), (rx + 0.002, 0.05), (rx, 0.0)], seg=40, mat=gold, caps=False, sharp=50)
    parts = [band]
    for i in range(5):
        a = 2 * math.pi * i / 5 - math.pi / 2
        c = Vector(((rx + 0.006) * math.cos(a), (rx + 0.006) * math.sin(a), 0.05))
        pt = C.cyl("pt", c, r=0.03, r2=0.0, h=0.065, mat=gold, seg=8, base=True, smooth=False)
        parts.append(pt)
        parts.append(C.sphere("ball", c + Vector((0, 0, 0.068)), r=0.013, mat=gold, seg=10, rings=6))
        parts.append(C.sphere("gem", ((rx + 0.014) * math.cos(a + 0.63), (rx + 0.014) * math.sin(a + 0.63), 0.026), r=0.013,
                              scale=(1, 1, 1.2), mat=C.mat("HatGemPink" if i % 2 else "HatGemTeal", "F59BB6" if i % 2 else "5FC7C2", rough=0.2), seg=10, rings=6))
    h = C.join(parts, "HatMesh")
    C.set_origin(h, (0, 0, 0))
    h.data.transform(Matrix.Diagonal((1, 0.9, 1, 1)))
    h.data.transform(C.xform(rot=(0, 9, 0)))
    h.location = (0.012, 0, z0 - 0.012)
    C.bake_transform(h)
    return h


def hat_headphones():
    mint = C.mat("HatMint", "8FD6C4", rough=0.6)
    white = C.mat("HatWhite", "F7F4EC", rough=0.6)
    pink = C.mat("HatCushion", "F7A8B8", rough=0.9)
    parts = []
    by = 0.07
    band_pts = [(-0.232, by, 0.23), (-0.215, by, 0.31), (-0.14, by, 0.385), (0.0, by, 0.41), (0.14, by, 0.385), (0.215, by, 0.31), (0.232, by, 0.23)]
    parts.append(C.tube("band", band_pts, r=0.02, mat=white, seg=8, res=4))
    for s in (-1, 1):
        c = Vector((s * 0.245, 0.03, 0.2))
        parts.append(C.cyl("cup", c, r=0.07, h=0.05, rot=(0, 90, 0), mat=mint, seg=20, bevel=0.015, bseg=2))
        parts.append(C.torus("cush", c - Vector((s * 0.028, 0, 0)), R=0.052, r=0.018, rot=(0, 90, 0), mat=pink, seg=20, mseg=6))
        parts.append(C.tube("yoke", [(s * 0.232, by, 0.23), (s * 0.245, 0.05, 0.25)], r=0.012, mat=white, seg=6, res=1))
        parts.append(C.sphere("dot", c + Vector((s * 0.027, 0, 0)), r=1, scale=(0.006, 0.025, 0.025), mat=white, seg=10, rings=5))
    h = C.join(parts, "HatMesh")
    C.set_origin(h, (0, 0, 0))
    return h


BUILDERS = {i: globals()["hat_" + i] for i in HAT_IDS}


def build_hat(hid, keep_sprout=False):
    global BODY
    sp = a_sprout.build_sprout()
    C.update()
    BODY = bpy.data.objects["Body"]
    root = C.empty("Hat")
    h = BUILDERS[hid]()
    C.shade(h, 60)
    C.set_parent(h, root)
    if keep_sprout:
        return root, sp
    for o in [sp] + list(sp.children_recursive):
        bpy.data.objects.remove(o)
    return root


for _h in HAT_IDS:
    globals()["build_hat_" + _h] = (lambda h=_h: build_hat(h))

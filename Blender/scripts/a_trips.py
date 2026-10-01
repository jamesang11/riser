"""Vacation destination dioramas: trip_<id>.usdz (root `Trip`)."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import common as C
import a_island as I
import a_farm as F
import a_props, a_nature, a_balloon

TRIPS = ["meadow", "woods", "beach", "mushroom", "harbor", "caves", "peaks", "moon"]
K = 0.83

THEME = {  # top, rim, tuft, spin
    "meadow": ("7BC96F", "5FAF5A", "8FD67E", 40), "woods": ("6DB85E", "4F9A4F", "7FC46A", 200),
    "beach": ("F2DDB0", "E3C890", "A8C77A", 95), "mushroom": ("5E9E86", "4A8570", "74B39A", 250),
    "harbor": ("9BD98A", "7CC46E", "B0E39E", 320), "caves": ("8C84A8", "6E6690", "A39BC0", 130),
    "peaks": ("F3F7FF", "DCE6F5", "E6EEFA", 170), "moon": ("A9C3C8", "8FA9B3", "C3D8DC", 20),
}


def M(name, hexc, rough=0.8, **kw):
    return C.mat(name, hexc, rough=rough, **kw)


def glow(name, hexc, base=None, strength=1.0):
    return C.mat(name, base or hexc, rough=0.5, emit=hexc, strength=strength)


def rim_r(t, spin):
    return I.R(t - math.radians(spin)) * K


def face_rz(spot, target):
    d = Vector(target) - Vector(spot)
    return math.degrees(math.atan2(d.x, -d.y))


def base_island(theme, rnd):
    top, rim, tuft, spin = THEME[theme]
    I.SEG = 96
    body = I.build_body()
    under = C.join(F.underside(rnd))
    C.set_origin(under, (0, 0, 0))
    for o in (body, under):
        o.data.transform(C.xform(rot=(0, 0, spin), scale=(K, K, K)))
    body.name = body.data.name = "TripBody"
    C.set_color("Grass", top)
    C.set_color("GrassDark", rim)
    C.set_color("GrassTuft", tuft)
    if theme in ("caves", "moon", "peaks"):
        C.set_color("Dirt", {"caves": "6E6286", "moon": "6C7A96", "peaks": "8C8FA8"}[theme])
        C.set_color("DirtDeep", {"caves": "574C70", "moon": "56627E", "peaks": "737690"}[theme])
    C.update()
    return body, under, spin


def scatter(body, rnd, spin, keep, n_tuft=20, flowers=None, n_flower=0, n_rock=8, tuft_scale=1.1):
    parts = []
    placed = []
    def spots(n, sep):
        out = []
        tries = 0
        while len(out) < n and tries < 4000:
            tries += 1
            t = rnd.uniform(0, 2 * math.pi)
            rr = math.sqrt(rnd.uniform(0, 1)) * (rim_r(t, spin) - 0.4)
            x, y = rr * math.cos(t), rr * math.sin(t)
            if any(math.hypot(x - a, y - b) < r for a, b, r in keep):
                continue
            if any(math.hypot(x - a, y - b) < sep for a, b in placed):
                continue
            placed.append((x, y)); out.append((x, y))
        return out
    for (x, y) in spots(n_tuft, 0.45):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        tf = I.grass_tuft("tuft", rnd, s=rnd.uniform(0.9, 1.3) * tuft_scale)
        tf.location = (x, y, z)
        C.bake_transform(tf)
        parts.append(tf)
    if flowers:
        for i, (cx, cy) in enumerate(spots(n_flower, 0.6)):
            for k in range(3):
                x, y = cx + rnd.uniform(-0.2, 0.2), cy + rnd.uniform(-0.2, 0.2)
                z, n = I.surface_z(body, x, y)
                if z is None:
                    continue
                fl = I.tiny_flower(rnd, flowers[i % len(flowers)])
                fl.data.transform(C.xform(scale=(1.4, 1.4, 1.4), rot=(0, 0, rnd.uniform(0, 360))))
                fl.location = (x, y, z + 0.008)
                C.bake_transform(fl)
                parts.append(fl)
    for (x, y) in spots(n_rock, 0.5):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        rk = I.rock("st", rnd, rnd.uniform(0.07, 0.15), sub=1)
        rk.location = (x, y, z + 0.01)
        C.bake_transform(rk)
        parts.append(rk)
    return parts


def mushroom(loc, r, h, cap_hex, rnd, stem_hex="F6EAD2", spots=True, name="mush", seg=None):
    capm = M("Cap" + cap_hex, cap_hex, rough=0.6)
    cream = M("MushCream", stem_hex, rough=0.85)
    seg = seg or (16 if r > 0.3 else 10)
    stem = C.lathe(name + "st", [(0, 0), (r * 0.42, 0), (r * 0.36, h * 0.3), (r * 0.3, h * 0.7), (r * 0.32, h), (0, h)], seg=seg, mat=cream)
    capo = C.lathe(name + "cap", [(0, h * 0.92), (r * 0.9, h * 0.9), (r * 1.02, h * 0.98), (r * 0.95, h * 1.12), (r * 0.7, h * 1.3), (r * 0.3, h * 1.42), (0, h * 1.44)],
                   seg=seg + 8 if seg > 10 else 14, mat=capm)
    parts = [stem, capo]
    if spots and r > 0.2:
        C.update()
        for k in range(7):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0.15, 0.75) * r
            ok, p, n, _ = capo.ray_cast(Vector((d * math.cos(a), d * math.sin(a), h * 3)), Vector((0, 0, -1)))
            if ok:
                sp = C.sphere("spot", p, r=r * rnd.uniform(0.09, 0.14), scale=(1, 1, 0.3), mat=cream, seg=8, rings=4)
                sp.data.transform(Vector((0, 0, 1)).rotation_difference(n).to_matrix().to_4x4())
                parts.append(sp)
    o = C.join(parts, name)
    C.set_origin(o, (0, 0, 0))
    o.location = loc
    C.bake_transform(o)
    return o


def door(x, y, z0=0.0, w=0.5, h=0.85, wood="Wood"):
    return [C.prism("dframe", C.arch_pts(w + 0.14, h + 0.07, 10, z0), y - 0.03, y + 0.03, C.mat("WoodDark", rough=0.8), bevel=0.015, bseg=1),
            C.prism("door", C.arch_pts(w, h, 10, z0), y - 0.05, y - 0.01, C.mat(wood, rough=0.8), bevel=0.01, bseg=1),
            C.sphere("knob", (x + w * 0.3, y - 0.07, z0 + h * 0.45), r=0.025, mat=C.mat("Brass", rough=0.45), seg=8, rings=5)]


def place_x(objs, x):
    for o in objs:
        o.data.transform(Matrix.Translation((x, 0, 0)))
    return objs


def round_window(x, y, z, r=0.16, mat=None):
    mat = mat or glow("GlowWindow", "FFD58A", base="FFE6A8")
    return [C.cyl("win", (x, y - 0.01, z), r=r, h=0.04, rot=(90, 0, 0), mat=mat, seg=18, smooth=False),
            C.torus("winf", (x, y - 0.035, z), R=r + 0.02, r=0.035, rot=(90, 0, 0), mat=C.mat("WoodDark", rough=0.8), seg=18, mseg=6),
            C.box("mv", (x, y - 0.03, z), (0.025, 0.03, 2 * r), mat=C.mat("WoodDark"), bevel=0.0, smooth=False),
            C.box("mh", (x, y - 0.03, z), (2 * r, 0.03, 0.025), mat=C.mat("WoodDark"), bevel=0.0, smooth=False)]


def sign(x, y, col="WoodLight"):
    return [C.box("sp", (x, y, 0), (0.06, 0.06, 0.7), mat=C.mat("WoodDark", rough=0.8), bevel=0.012, bseg=1, base=True),
            C.box("sb", (x, y - 0.04, 0.62), (0.5, 0.05, 0.24), mat=C.mat(col, rough=0.8), bevel=0.025, bseg=2)]


# =============================================================================== MEADOW
def trip_meadow(rnd):
    P, E = [], {}
    # Dandelion B&B: cream cottage with a fluffy dandelion-puff roof
    L = Vector((-0.4, 2.0, 0))
    P.append(C.box("walls", L, (2.0, 1.6, 1.5), mat=C.mat("Cream", rough=0.88), bevel=0.06, bseg=2, base=True))
    P.append(C.box("fnd", L, (2.15, 1.75, 0.18), mat=C.mat("Rock", rough=0.9), bevel=0.05, bseg=2, base=True))
    puff = C.blob("puff", [((L.x, L.y, 1.95), 1.15, (1.1, 1.0, 0.75)), ((L.x - 0.7, L.y, 1.75), 0.7), ((L.x + 0.7, L.y, 1.75), 0.7),
                           ((L.x, L.y - 0.6, 1.8), 0.7), ((L.x, L.y + 0.6, 1.8), 0.7)], mat=M("DandelionPuff", "FBFAF2", rough=1.0), voxel=0.05, smooth_iter=5, target=2200)
    C.jitter(puff, 0.03, 6, 2)
    C.shade(puff, 180)
    P.append(puff)
    seedm = M("DandelionSeed", "FFFFFF", rough=1.0)
    for k in range(9):
        a = rnd.uniform(0, 6.28); e = rnd.uniform(0.3, 1.2)
        base = Vector((L.x, L.y, 1.9)) + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * 1.05
        tip = base + Vector((math.cos(a), math.sin(a), 0.6)).normalized() * 0.3
        P.append(C.tube("seed", [base, tip], r=0.008, mat=seedm, seg=4, res=1))
        P.append(C.sphere("seedpuff", tip, r=0.07, mat=seedm, seg=8, rings=5))
    P.append(C.cyl("stemtop", (L.x + 0.1, L.y, 2.6), r=0.07, h=0.35, mat=C.mat("Stem"), seg=8, base=True))
    fy = L.y - 0.8
    P += door(L.x, fy, 0.12, 0.55, 0.9)
    P += round_window(L.x - 0.65, fy, 0.95) + round_window(L.x + 0.65, fy, 0.95)
    P += [C.torus("wreath", (L.x, fy - 0.08, 1.18), R=0.1, r=0.03, rot=(90, 0, 0), mat=C.mat("Leaf"), seg=14, mseg=5),
          C.sphere("wf", (L.x, fy - 0.1, 1.08), r=0.035, mat=C.mat("FlowerYellow"), seg=8, rings=5)]
    P += sign(L.x + 1.3, fy - 0.4)
    E["StayPoint"] = ((L.x, fy - 0.6), (L.x, fy - 3))
    # A picnic blanket + basket
    a = Vector((-2.2, -1.0))
    bm = bmesh.new()
    n = 6
    V = [[bm.verts.new((a.x - 0.65 + 1.3 * i / n, a.y - 0.55 + 1.1 * j / n, 0.01)) for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n):
        for j in range(n):
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            f.material_index = (i + j) % 2
    bl = C.mk("blanket", bm, [M("PicnicRed", "E86A5C", rough=0.9), M("PicnicWhite", "FFF6EA", rough=0.9)])
    so = bl.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.015
    C.apply_mods(bl)
    P.append(bl)
    bask = C.lathe("basket", [(0, 0.01), (0.2, 0.01), (0.22, 0.2), (0.2, 0.2), (0, 0.18)], seg=18, mat=M("Wicker", "C99A5B", rough=0.9), rfun=lambda t, z: 1 + 0.03 * math.cos(16 * t))
    bask.data.transform(Matrix.Diagonal((1.3, 0.9, 1, 1)))
    bask.location = (a.x + 0.35, a.y + 0.25, 0.01)
    P.append(bask)
    P.append(C.torus("handle", (a.x + 0.35, a.y + 0.25, 0.2), R=0.18, r=0.015, rot=(90, 0, 0), mat=M("Wicker", "C99A5B"), seg=16, mseg=5, arc=180))
    P.append(C.box("sandwich", (a.x - 0.2, a.y - 0.1, 0.02), (0.16, 0.16, 0.06), mat=M("Bread", "E8C27A"), bevel=0.02, bseg=2, base=True, rot=(0, 0, 20)))
    P.append(C.sphere("apple", (a.x - 0.05, a.y + 0.15, 0.07), r=0.06, mat=M("Apple", "E5533F", rough=0.4), seg=10, rings=7))
    E["ActivityA"] = ((a.x + 0.05, a.y - 0.8), a)
    # B kite on a stake, kite high in the air
    b = Vector((2.3, -0.4))
    P.append(C.cyl("stake", (b.x, b.y, 0), r=0.03, h=0.45, mat=C.mat("WoodDark"), seg=6, base=True))
    kite = Vector((b.x + 0.9, b.y + 1.8, 3.8))
    P.append(C.tube("string", [(b.x, b.y, 0.44), (b.x + 0.5, b.y + 0.9, 2.3), kite], r=0.006, mat=M("KiteString", "F6EEDC"), seg=4, res=5))
    kp = C.prism("kite", [(0, 0.45), (0.3, 0.0), (0, -0.55), (-0.3, 0.0)], -0.015, 0.015, M("KiteRed", "E0674F", rough=0.7), bevel=0.006, bseg=1)
    k2 = C.prism("kite2", [(0, 0.45), (0.3, 0.0), (0, 0.0)], -0.02, 0.018, M("KiteYellow", "FFD65A", rough=0.7), smooth=False)
    k3 = C.prism("kite3", [(0, -0.55), (-0.3, 0.0), (0, 0.0)], -0.02, 0.018, M("KiteYellow", "FFD65A"), smooth=False)
    kk = C.join([kp, k2, k3])
    C.set_origin(kk, (0, 0, 0))
    kk.data.transform(C.xform(rot=(0, 15, 25)))
    kk.location = kite
    C.bake_transform(kk)
    P.append(kk)
    tail = [kite + Vector((0.1 * math.sin(i), 0.05 * i, -0.55 - 0.2 * i)) for i in range(5)]
    P.append(C.tube("tail", tail, r=0.006, mat=M("KiteString", "F6EEDC"), seg=4, res=3))
    for k, q in enumerate(tail[1:]):
        P.append(C.sphere("bow", q, r=1, scale=(0.05, 0.015, 0.03), mat=M(["KiteRed", "KiteBlue"][k % 2], ["E0674F", "6FA8F5"][k % 2]), seg=8, rings=4))
    E["ActivityB"] = ((b.x - 0.35, b.y - 0.3), (b.x + 0.9, b.y + 1.8))
    # C a row of big daisies
    c0 = Vector((0.6, -2.4))
    for k in range(5):
        x = c0.x - 0.8 + k * 0.4
        h = 0.55 + 0.25 * math.sin(k * 1.7) ** 2
        P.append(C.tube("dst", [(x, c0.y, 0), (x + 0.02, c0.y, h * 0.5), (x, c0.y + 0.02, h)], r=0.018, mat=C.mat("Stem"), seg=5, res=2))
        pet = C.lathe("dpet", [(0, 0.0), (0.2, 0.01), (0.0, 0.03)], seg=24, mat=C.mat("White"), rfun=lambda t, z: 0.55 + 0.45 * abs(math.cos(6 * t)) ** 0.5, sharp=80)
        ctr = C.sphere("dctr", (0, 0, 0.02), r=0.06, scale=(1, 1, 0.6), mat=C.mat("FlowerYellow"), seg=10, rings=5)
        hd = C.join([pet, ctr])
        C.set_origin(hd, (0, 0, 0))
        hd.data.transform(C.xform(rot=(60, 0, rnd.uniform(-10, 10))))
        hd.location = (x, c0.y + 0.02, h)
        C.bake_transform(hd)
        P.append(hd)
        P.append(C.leaf("dl", length=0.22, width=0.07, thick=0.012, curl=0.02, mat=C.mat("Leaf"), seg=6, rings=4))
        P[-1].data.transform(C.xform(rot=(0, -30, 180 * (k % 2))))
        P[-1].location = (x, c0.y, 0.15)
        C.bake_transform(P[-1])
    E["ActivityC"] = ((c0.x, c0.y - 0.6), c0)
    # round bushes + dandelion clocks
    for (x, y, s_) in [(-2.9, 1.3, 0.55), (2.6, 1.9, 0.6), (1.4, 2.6, 0.45), (-1.6, -2.9, 0.4)]:
        bush = C.blob("bush", [((x, y, s_ * 0.5), s_), ((x + s_ * 0.6, y, s_ * 0.4), s_ * 0.7), ((x - s_ * 0.5, y + 0.1, s_ * 0.4), s_ * 0.65)],
                      mat=C.mat("Leaf", rough=0.85), voxel=0.05, smooth_iter=4, target=450, flat_bottom=0.0)
        C.paint_faces(bush, C.mat("LeafLight", rough=0.85), lambda c, n: n.z > 0.55)
        P.append(bush)
        for k in range(3):
            P.append(C.sphere("bf", (x + rnd.uniform(-s_, s_) * 0.7, y - s_ * 0.8, s_ * rnd.uniform(0.4, 0.9)), r=0.04, mat=C.mat("Blossom"), seg=6, rings=4))
    for k in range(7):
        t = rnd.uniform(0, 6.28); rr = rnd.uniform(1.5, 3.6)
        x, y = rr * math.cos(t), rr * math.sin(t)
        if any(math.hypot(x - q[0], y - q[1]) < q[2] for q in [(L.x, L.y, 1.8), (a.x, a.y, 1.0), (b.x, b.y, 0.7), (c0.x, c0.y, 1.2)]):
            continue
        h = rnd.uniform(0.35, 0.55)
        P.append(C.tube("dcst", [(x, y, 0), (x + 0.02, y, h)], r=0.01, mat=C.mat("Stem"), seg=4, res=1))
        P.append(C.sphere("dclock", (x + 0.02, y, h + 0.07), r=0.09, mat=M("DandelionPuff", "FBFAF2", rough=1.0), seg=10, rings=6))
    keep = [(L.x, L.y, 1.7), (a.x, a.y, 0.9), (b.x, b.y, 0.6), (c0.x, c0.y, 1.1), (-2.9, 1.3, 0.8), (2.6, 1.9, 0.9), (1.4, 2.6, 0.7), (-1.6, -2.9, 0.6)]
    return P, E, keep, dict(n_tuft=26, flowers=["White", "FlowerYellow", "Blossom", "Purple"], n_flower=14, n_rock=6)


# =============================================================================== WOODS
def trip_woods(rnd):
    P, E = [], {}
    T = Vector((-0.6, 1.9, 0))
    trunk = C.tube("trunk", [(T.x, T.y, -0.05), (T.x + 0.1, T.y, 1.2), (T.x - 0.05, T.y + 0.05, 2.4), (T.x, T.y, 3.0)], r=0.42, radii=[1.3, 1.0, 0.9, 0.8],
                   mat=C.mat("WoodDark", rough=0.85), seg=12, res=4)
    P.append(trunk)
    for k in range(4):
        a = math.radians(k * 90 + 30)
        P.append(C.sphere("root", (T.x + 0.5 * math.cos(a), T.y + 0.5 * math.sin(a), 0.1), r=1, scale=(0.35, 0.15, 0.15), rot=(0, -15, k * 90 + 30), mat=C.mat("WoodDark"), seg=10, rings=6))
    can = C.blob("canopy", [((T.x, T.y, 3.9), 1.3), ((T.x - 1.0, T.y + 0.1, 3.5), 0.9), ((T.x + 1.0, T.y, 3.6), 0.9), ((T.x, T.y + 0.8, 3.6), 0.85),
                            ((T.x + 0.4, T.y - 0.6, 4.3), 0.8)], mat=C.mat("Leaf", rough=0.85), voxel=0.07, smooth_iter=5, target=2200)
    C.paint_faces(can, C.mat("LeafLight", rough=0.85), lambda c, n: n.z > 0.5)
    P.append(can)
    # platform + cabin in the tree
    pz = 2.2
    P.append(C.cyl("platform", (T.x, T.y - 0.2, pz - 0.1), r=1.1, h=0.12, mat=C.mat("Wood", rough=0.8), seg=20, base=True, bevel=0.02, bseg=1))
    for k in range(3):
        a = math.radians(-60 - 30 * k)
        P.append(C.tube("brace", [(T.x + 0.3 * math.cos(a), T.y + 0.3 * math.sin(a), 1.4), (T.x + 0.95 * math.cos(a), T.y - 0.2 + 0.95 * math.sin(a), pz - 0.1)],
                        r=0.04, mat=C.mat("WoodDark"), seg=5, res=1))
    cab = Vector((T.x, T.y - 0.3, pz))
    P.append(C.box("cabin", cab, (1.2, 0.95, 0.9), mat=C.mat("WoodLight", rough=0.8), bevel=0.04, bseg=2, base=True))
    roof = C.prism("croof", [(-0.75, 0.85), (0.75, 0.85), (0, 1.35)], -0.6, 0.6, C.mat("RoofTeal", rough=0.8), bevel=0.03)
    roof.data.transform(Matrix.Translation(cab))
    P.append(roof)
    P += [o for o in door(0, cab.y - 0.47, pz, 0.36, 0.62)]
    for o in P[-3:]:
        o.data.transform(Matrix.Translation((cab.x, 0, 0)))
    P += round_window(cab.x + 0.38, cab.y - 0.47, pz + 0.5, r=0.1)
    for k in range(9):          # railing
        a = math.radians(200 + k * 17.5)
        p0 = Vector((T.x + 1.05 * math.cos(a), T.y - 0.2 + 1.05 * math.sin(a), pz))
        P.append(C.cyl("rail", p0, r=0.025, h=0.35, mat=C.mat("WoodDark"), seg=5, base=True))
    # ladder down the front
    lx, ly = T.x + 0.55, T.y - 1.25
    for s in (-1, 1):
        P.append(C.tube("lrail", [(lx + s * 0.18, ly, 0), (lx + s * 0.18, ly + 0.12, pz)], r=0.03, mat=C.mat("Wood"), seg=5, res=1))
    for k in range(7):
        z = 0.25 + k * 0.3
        P.append(C.cyl("rung", (lx, ly + 0.12 * z / pz, z), r=0.022, h=0.36, rot=(0, 90, 0), mat=C.mat("Wood"), seg=6))
    E["StayPoint"] = ((lx, ly - 0.45), (lx, ly - 3))
    # A campfire with marshmallow sticks
    a = Vector((1.9, -1.4))
    P += C.harvest(a_props.build_campfire(), (a.x, a.y, 0), 20, 1.0)
    for s in (-1, 1):
        base = Vector((a.x + s * 0.55, a.y - 0.45, 0.05))
        tip = Vector((a.x + s * 0.15, a.y - 0.1, 0.45))
        P.append(C.tube("stick", [base, tip], r=0.012, mat=C.mat("WoodDark"), seg=4, res=1))
        P.append(C.cyl("mallow", tip + (tip - base).normalized() * 0.04, r=0.035, h=0.06, rot=(55, 0, s * 40), mat=M("Marshmallow", "FFF6F0", rough=0.9), seg=10))
    E["ActivityA"] = ((a.x - 0.2, a.y - 1.0), a)
    # B mossy log bridge over a stream (stream runs front-left toward the rim)
    water = C.mat("Water", "6EC8E6", rough=0.1, spec=0.7)
    pts = [Vector((-3.6, -0.2)), Vector((-2.6, -0.9)), Vector((-2.0, -1.8)), Vector((-1.6, -3.4))]
    bm = bmesh.new()
    rows = []
    samp = []
    for i in range(12):
        t = i / 11
        q = pts[0] * (1 - t) ** 3 + pts[1] * 3 * t * (1 - t) ** 2 + pts[2] * 3 * t * t * (1 - t) + pts[3] * t ** 3
        samp.append(q)
    for i, q in enumerate(samp):
        d = (samp[min(i + 1, 11)] - samp[max(i - 1, 0)]).normalized()
        nrm = Vector((-d.y, d.x))
        rows.append([bm.verts.new((q.x + nrm.x * o, q.y + nrm.y * o, 0.03)) for o in (-0.38, 0.38)])
    for r0, r1 in zip(rows[:-1], rows[1:]):
        bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
    st = C.mk("stream", bm, [water])
    P.append(st)
    for q in samp[::2]:
        for s in (-1, 1):
            rk = I.rock("bank", rnd, rnd.uniform(0.07, 0.12), sub=1)
            rk.location = (q.x + s * 0.45 * rnd.uniform(0.9, 1.1), q.y + s * 0.1, 0.02)
            C.bake_transform(rk)
            P.append(rk)
    b = samp[6]
    lg = a_props.log("logbridge", 1.5, 0.16, rnd, bark="WoodDark")
    d = (samp[7] - samp[5]).normalized()
    lg.data.transform(C.xform(rot=(0, 0, math.degrees(math.atan2(d.y, d.x)))))
    lg.location = (b.x, b.y, 0.14)
    C.bake_transform(lg)
    P.append(lg)
    P.append(C.blob("moss", [((b.x + d.x * (k - 1) * 0.35, b.y + d.y * (k - 1) * 0.35, 0.27), 0.11) for k in range(3)], mat=M("Moss", "7FC46A", rough=0.95),
                    voxel=0.035, smooth_iter=3, target=400, flat_bottom=0.24))
    E["ActivityB"] = ((b.x + 0.35, b.y - 0.75), (b.x, b.y))
    # C mushroom ring
    c0 = Vector((0.9, -2.7))
    for k in range(8):
        ang = 2 * math.pi * k / 8
        P.append(mushroom((c0.x + 0.55 * math.cos(ang), c0.y + 0.45 * math.sin(ang), 0), rnd.uniform(0.1, 0.15), rnd.uniform(0.14, 0.22),
                          ["E0503F", "F07A8C", "F29A45"][k % 3], rnd, name="rm"))
    E["ActivityC"] = ((c0.x - 0.05, c0.y + 0.05), (c0.x + 0.3, c0.y - 1.0))
    # a couple of pines behind
    pine = a_nature.build_pine()
    for (x, y, s_) in [(2.2, 2.0, 1.2), (-3.0, 1.6, 1.0)]:
        pr = a_nature.build_pine() if (x, y) != (2.2, 2.0) else pine
        P += C.harvest(pr, (x, y, 0), rnd.uniform(0, 360), s_)
    keep = [(T.x, T.y, 1.4), (lx, ly, 0.5), (a.x, a.y, 1.0), (b.x, b.y, 0.8), (c0.x, c0.y, 0.8), (2.2, 2.0, 1.0), (-3.0, 1.6, 0.9)] + \
           [(q.x, q.y, 0.6) for q in samp]
    return P, E, keep, dict(n_tuft=26, flowers=["White", "FlowerYellow"], n_flower=5, n_rock=8)


# =============================================================================== BEACH
def trip_beach(rnd):
    P, E = [], {}
    # lagoon (front-right) with shallow ring
    lag = Vector((2.1, -1.7))
    water = C.mat("Water", "4FC6D8", rough=0.08, spec=0.8)
    lagoon = C.lathe("lagoon", [(0, 0.02), (1.25, 0.02), (1.25, 0.021)], seg=40, mat=water, rfun=lambda t, z: 1 + 0.1 * math.sin(3 * t))
    lagoon.data.transform(Matrix.Diagonal((1.3, 1.0, 1, 1)))
    lagoon.location = (lag.x, lag.y, 0)
    P.append(lagoon)
    sh = C.lathe("shallow", [(0, 0.012), (1.45, 0.012), (1.45, 0.013)], seg=40, mat=M("Shallow", "8FE3E0", rough=0.1), rfun=lambda t, z: 1 + 0.1 * math.sin(3 * t))
    sh.data.transform(Matrix.Diagonal((1.3, 1.0, 1, 1)))
    sh.location = (lag.x, lag.y, 0)
    P.append(sh)
    # Seashell Bungalow: spiral shell hut
    L = Vector((-0.6, 1.8, 0))
    shell = []
    sm = M("ShellPink", "F7D3C8", rough=0.6)
    sm2 = M("ShellCream", "FFF1E6", rough=0.6)
    n = 10
    for k in range(n):
        t = k / n
        R = 1.25 * (1 - t) ** 0.85 + 0.12
        z = 0.35 + 2.6 * t ** 0.9
        tor = C.torus("whorl", (L.x + 0.12 * math.sin(k), L.y + 0.12 * math.cos(k), z), R=R, r=0.28 * (1 - t) + 0.08, mat=sm if k % 2 else sm2, seg=28, mseg=10)
        shell.append(tor)
    shell.append(C.cyl("base", L, r=1.35, h=0.4, mat=sm2, seg=28, base=True, bevel=0.1, bseg=2))
    shell.append(C.sphere("pearl", (L.x + 0.1, L.y + 0.1, 3.15), r=0.14, mat=M("Pearl", "FFFFFF", rough=0.2, spec=0.8), seg=12, rings=8))
    P += shell
    fy = L.y - 1.56
    P.append(C.box("porch", (L.x, fy + 0.15, 0.0), (0.9, 0.5, 0.08), mat=M("ShellCream", "FFF1E6"), bevel=0.03, bseg=2, base=True))
    P += door(L.x, fy, 0.05, 0.6, 1.05)
    P += round_window(L.x + 0.62, fy + 0.35, 1.45, r=0.15)
    P += sign(L.x - 1.3, fy - 0.3, col="WoodLight")
    E["StayPoint"] = ((L.x, fy - 0.6), (L.x, fy - 3))
    # A sandcastle
    a = Vector((-2.3, -0.9))
    sand = M("CastleSand", "E6C98E", rough=0.95)
    P.append(C.box("keep", (a.x, a.y, 0), (0.55, 0.45, 0.35), mat=sand, bevel=0.03, bseg=1, base=True))
    for (dx, dy) in [(-0.3, -0.25), (0.3, -0.25), (-0.3, 0.25), (0.3, 0.25)]:
        P.append(C.cyl("tower", (a.x + dx, a.y + dy, 0), r=0.13, h=0.5, mat=sand, seg=12, base=True, bevel=0.02, bseg=1))
        for k in range(6):
            ang = k * 60
            P.append(C.box("crenel", (a.x + dx + 0.11 * math.cos(math.radians(ang)), a.y + dy + 0.11 * math.sin(math.radians(ang)), 0.5), (0.05, 0.05, 0.06), mat=sand,
                           bevel=0.0, smooth=False, base=True))
    P.append(C.cyl("ctop", (a.x, a.y, 0.35), r=0.14, h=0.28, mat=sand, seg=12, base=True))
    P.append(C.cyl("flagpole", (a.x, a.y, 0.63), r=0.008, h=0.3, mat=C.mat("WoodDark"), seg=4, base=True))
    P.append(C.prism("flag", [(0, 0), (0.15, -0.04), (0, -0.09)], -0.004, 0.004, M("FlagRed", "E0674F"), smooth=False))
    P[-1].location = (a.x + 0.005, a.y, 0.92); C.bake_transform(P[-1])
    P.append(C.box("bucket", (a.x + 0.55, a.y - 0.3, 0), (0.18, 0.18, 0.18), mat=M("BucketBlue", "6FA8F5", rough=0.6), bevel=0.04, bseg=2, base=True))
    E["ActivityA"] = ((a.x + 0.2, a.y - 0.8), a)
    # B towel + parasol
    b = Vector((-0.9, -2.3))
    P.append(C.box("towel", (b.x, b.y, 0.0), (0.7, 1.2, 0.02), mat=M("TowelStripe", "4FA3A5", rough=0.95), bevel=0.005, bseg=1, base=True, rot=(0, 0, 12)))
    for k in range(3):
        P.append(C.box("tstripe", (b.x - 0.1 * math.sin(math.radians(12)) * 0 + 0.0, b.y - 0.35 + k * 0.35, 0.021), (0.7, 0.1, 0.004), mat=C.mat("White"), bevel=0.0, smooth=False, rot=(0, 0, 12)))
    P.append(C.cyl("upole", (b.x - 0.6, b.y + 0.3, 0), r=0.03, h=1.7, mat=C.mat("Cream"), seg=8, base=True))
    um = C.lathe("umb", [(0, 1.8), (0.95, 1.52), (1.02, 1.46), (0, 1.5)], seg=16, mats=[M("UmbRed", "E0674F"), C.mat("Cream")], caps=False)
    for p in um.data.polygons:
        p.material_index = int((math.atan2(p.center.y, p.center.x) + math.pi) / (2 * math.pi) * 8) % 2
    um.location = (b.x - 0.6, b.y + 0.3, 0)
    P.append(um)
    E["ActivityB"] = ((b.x, b.y - 0.25), (b.x, b.y - 2.0))
    # C tiny pier with a fishing rod over the lagoon
    c0 = Vector((1.0, -0.8))
    for k in range(6):
        P.append(C.box("plank", (c0.x + 0.2 + k * 0.28, c0.y - 0.1 - k * 0.12, 0.2), (0.26, 0.7, 0.05), mat=C.mat("Wood") if k % 2 else C.mat("WoodLight"), bevel=0.01, bseg=1,
                       rot=(0, 0, -23)))
    for k in (0, 2, 4):
        for s in (-1, 1):
            P.append(C.cyl("post", (c0.x + 0.2 + k * 0.28 + s * 0.12, c0.y - 0.1 - k * 0.12 + s * 0.3, -0.1), r=0.04, h=0.35, mat=C.mat("WoodDark"), seg=6, base=True))
    tipp = Vector((c0.x + 2.2, c0.y - 1.2, 1.4))
    rodbase = Vector((c0.x + 1.3, c0.y - 0.55, 0.25))
    P.append(C.tube("rod", [rodbase, rodbase + (tipp - rodbase) * 0.5 + Vector((0, 0, 0.1)), tipp], r=0.012, radii=[1.4, 1, 0.6], mat=C.mat("WoodDark"), seg=5, res=3))
    bob = Vector((tipp.x + 0.2, tipp.y - 0.2, 0.05))
    P.append(C.tube("line", [tipp, bob + Vector((0, 0, 0.02))], r=0.003, mat=M("Line", "FFFFFF"), seg=3, res=1))
    P.append(C.sphere("bobber", bob, r=0.05, mat=M("BobberRed", "E0674F", rough=0.5), seg=10, rings=6))
    spot = Vector((c0.x + 1.0, c0.y - 0.45))
    E["ActivityC"] = (spot, (bob.x, bob.y))
    # palm-ish tree + shells
    trunk = C.tube("palm", [(-3.0, 0.8, 0), (-2.9, 0.9, 1.4), (-2.6, 1.0, 2.6)], r=0.13, radii=[1.2, 1.0, 0.8], mat=C.mat("Wood"), seg=8, res=4)
    P.append(trunk)
    for k in range(6):
        lf = C.leaf("frond", length=1.1, width=0.28, thick=0.03, curl=-0.35, mat=C.mat("Leaf"), seg=10, rings=6, fold=0.3)
        lf.data.transform(C.xform(rot=(0, 10, k * 60)))
        lf.location = (-2.6, 1.0, 2.6)
        C.bake_transform(lf)
        P.append(lf)
    for k in range(3):
        P.append(C.sphere("coco", (-2.6 + 0.12 * math.cos(k * 2.1), 1.0 + 0.12 * math.sin(k * 2.1), 2.5), r=0.09, mat=C.mat("WoodDark"), seg=8, rings=6))
    for k in range(8):
        x, y = rnd.uniform(-3, 1.5), rnd.uniform(-3, 0.5)
        sh_ = C.lathe("shell", [(0, 0), (0.08, 0.01), (0, 0.05)], seg=10, mat=C.mat("ShellPink"), rfun=lambda t, z: 0.7 + 0.3 * abs(math.cos(4 * t)))
        sh_.location = (x, y, 0.0)
        P.append(sh_)
    keep = [(L.x, L.y, 1.8), (a.x, a.y, 0.8), (b.x, b.y, 1.0), (lag.x, lag.y, 1.9), (-2.8, 0.9, 0.6)]
    return P, E, keep, dict(n_tuft=12, flowers=None, n_flower=0, n_rock=10, tuft_scale=1.2)


# =============================================================================== MUSHROOM
def trip_mushroom(rnd):
    P, E = [], {}
    L = Vector((-0.4, 1.8, 0))
    P.append(mushroom((L.x, L.y, 0), 1.7, 2.2, "E0503F", rnd, name="inn"))
    win = glow("GlowWindow", "FFD58A", base="FFE6A8")
    fy = L.y - 0.7
    P += door(L.x, fy, 0.0, 0.55, 0.95)
    for (dx, z) in [(-0.45, 1.1), (0.48, 0.8), (0.1, 1.55)]:
        P += round_window(L.x + dx, fy + 0.06, z, r=0.13, mat=win)
    P.append(C.cyl("chim", (L.x + 0.9, L.y + 0.2, 2.8), r=0.12, h=0.5, mat=C.mat("Rock"), seg=10, base=True))
    P += sign(L.x + 1.2, fy - 0.3)
    E["StayPoint"] = ((L.x, fy - 0.6), (L.x, fy - 3))
    # A bouncy mushroom caps
    a = Vector((-2.3, -1.0))
    for (dx, dy, r, h, col) in [(-0.3, 0.2, 0.55, 0.45, "F07A8C"), (0.45, -0.1, 0.45, 0.3, "6FA8F5"), (0.1, 0.65, 0.35, 0.65, "B79BE8")]:
        caps = mushroom((a.x + dx, a.y + dy, 0), r, h, col, rnd, spots=True, name="bounce")
        for v in caps.data.vertices:            # flatten into a trampoline top
            if v.co.z > h * 1.05:
                v.co.z = h * 1.05 + (v.co.z - h * 1.05) * 0.35
        P.append(caps)
    E["ActivityA"] = ((a.x + 0.4, a.y - 0.8), a)
    # B glowing spore-lantern path
    spore = glow("GlowSpore", "B8FFD8", base="D8FFE8", strength=1.0)
    b = Vector((1.6, -0.5))
    for k in range(7):
        x = 0.4 + k * 0.45
        y = -2.4 + k * 0.45 + 0.2 * math.sin(k)
        h = 0.35 + 0.1 * (k % 2)
        P.append(C.tube("sst", [(x, y, 0), (x + 0.03, y, h * 0.6), (x, y, h)], r=0.012, mat=M("SporeStem", "8FD6C4"), seg=4, res=2))
        P.append(C.sphere("spore", (x, y, h + 0.05), r=0.07, mat=spore, seg=10, rings=6))
        P.append(C.cyl("ss", (x - 0.1, y + 0.05, 0.005), r=0.13, h=0.03, mat=C.mat("Pebble"), seg=8))
    E["ActivityB"] = ((b.x - 0.4, b.y - 0.6), (b.x + 0.9, b.y + 0.9))
    # C tiny tea table on a stump
    c0 = Vector((2.5, 0.9))
    P += [C.cyl("stump", (c0.x, c0.y, 0), r=0.3, h=0.45, mat=C.mat("WoodDark"), seg=16, base=True, bevel=0.03, bseg=1),
          C.cyl("stumptop", (c0.x, c0.y, 0.45), r=0.3, h=0.02, mat=C.mat("WoodLight"), seg=16, base=True)]
    pot = C.sphere("teapot", (c0.x, c0.y + 0.05, 0.56), r=0.1, scale=(1, 1, 0.8), mat=M("TeaPink", "F4A0B5", rough=0.4), seg=12, rings=8)
    P += [pot, C.tube("spout", [(c0.x + 0.08, c0.y + 0.05, 0.55), (c0.x + 0.18, c0.y + 0.05, 0.62)], r=0.015, mat=M("TeaPink", "F4A0B5"), seg=5, res=1),
          C.sphere("lidknob", (c0.x, c0.y + 0.05, 0.65), r=0.02, mat=C.mat("White"), seg=6, rings=4)]
    for s in (-1, 1):
        cup = C.lathe("cup", [(0, 0.47), (0.035, 0.47), (0.045, 0.52), (0.04, 0.52), (0.03, 0.48), (0, 0.48)], seg=10, mat=C.mat("White"))
        cup.location = (c0.x + s * 0.14, c0.y - 0.13, 0)
        P.append(cup)
    E["ActivityC"] = ((c0.x - 0.15, c0.y - 0.7), c0)
    for (x, y, r, h, col) in [(2.6, 2.3, 0.6, 0.9, "F29A45"), (-2.9, 1.2, 0.5, 0.7, "F07A8C"), (-3.2, -0.2, 0.3, 0.4, "E0503F")]:
        P.append(mushroom((x, y, 0), r, h, col, rnd, name="deco"))
    for k in range(18):
        P.append(C.sphere("ff", (rnd.uniform(-3, 3), rnd.uniform(-2.5, 2.5), rnd.uniform(0.6, 2.4)), r=0.03, mat=glow("GlowFirefly", "E8FF8A", base="F4FFC8"), seg=6, rings=4))
    keep = [(L.x, L.y, 2.0), (a.x, a.y, 1.0), (c0.x, c0.y, 0.6), (2.6, 2.3, 0.7), (-2.9, 1.2, 0.6), (-3.2, -0.2, 0.4)] + \
           [(0.4 + k * 0.45, -2.4 + k * 0.45, 0.35) for k in range(7)]
    return P, E, keep, dict(n_tuft=20, flowers=["Purple", "BlossomLight"], n_flower=6, n_rock=6)


# =============================================================================== HARBOR
def trip_harbor(rnd):
    P, E = [], {}
    L = Vector((-0.5, 1.9, 0))
    floors = [("HotelPink", "F7B7C9"), ("HotelMint", "A8E0C8"), ("HotelButter", "FFE9A8")]
    win = glow("GlowWindow", "FFD58A", base="FFE6A8")
    z = 0.0
    for i, (n_, col) in enumerate(floors):
        w = 1.9 - i * 0.25
        h = 0.95
        P.append(C.box("floor%d" % i, (L.x, L.y, z), (w, 1.5 - i * 0.15, h), mat=M(n_, col, rough=0.8), bevel=0.05, bseg=2, base=True))
        fy = L.y - (1.5 - i * 0.15) / 2
        for k in range(3 if i < 2 else 2):
            x = L.x - w / 2 + (k + 0.5) * w / (3 if i < 2 else 2)
            if i == 0 and k == 1:
                continue
            P += [C.box("w", (x, fy - 0.01, z + 0.35), (0.3, 0.04, 0.38), mat=win, bevel=0.0, smooth=False, base=True),
                  C.box("wf", (x, fy - 0.02, z + 0.33), (0.38, 0.03, 0.46), mat=C.mat("White"), bevel=0.01, bseg=1, base=True)]
        if i > 0:
            P.append(C.box("balcony", (L.x, fy - 0.2, z), (w * 0.7, 0.4, 0.06), mat=C.mat("White"), bevel=0.015, bseg=1, base=True))
            for k in range(8):
                P.append(C.cyl("bal", (L.x - w * 0.33 + k * w * 0.66 / 7, fy - 0.38, z + 0.06), r=0.015, h=0.28, mat=C.mat("White"), seg=5, base=True))
            P.append(C.box("balrail", (L.x, fy - 0.38, z + 0.33), (w * 0.7, 0.04, 0.04), mat=C.mat("White"), bevel=0.01, bseg=1, base=True))
        z += h
    dome = C.lathe("dome", [(0, z), (0.6, z), (0.55, z + 0.3), (0.35, z + 0.55), (0, z + 0.65)], seg=20, mat=M("HotelDome", "6FA8F5", rough=0.6))
    dome.location = (L.x, L.y, 0)
    P.append(dome)
    for (dx, col) in [(-0.7, "E0674F"), (0.0, "FFD65A"), (0.7, "4FA3A5")]:
        P.append(C.cyl("fp", (L.x + dx, L.y, z + (0.6 if dx == 0 else 0.0)), r=0.015, h=0.6, mat=C.mat("White"), seg=5, base=True))
        fl = C.prism("flag", [(0, 0), (0.28, -0.07), (0, -0.16)], -0.006, 0.006, M("Flag" + col, col), smooth=False)
        fl.location = (L.x + dx + 0.01, L.y, z + (0.6 if dx == 0 else 0.0) + 0.58)
        C.bake_transform(fl)
        P.append(fl)
    fy0 = L.y - 0.75
    P += door(L.x, fy0, 0.0, 0.55, 0.8)
    P.append(C.box("awning", (L.x, fy0 - 0.25, 0.9), (0.9, 0.5, 0.06), mat=M("Awning", "E86A5C"), bevel=0.02, bseg=1, rot=(-12, 0, 0)))
    E["StayPoint"] = ((L.x, fy0 - 0.6), (L.x, fy0 - 3))
    # A dock off the right rim with a moored mini balloon + boat
    a = Vector((2.6, -0.6))
    for k in range(8):
        P.append(C.box("plank", (a.x + k * 0.26, a.y, 0.12), (0.24, 0.9, 0.05), mat=C.mat("Wood") if k % 2 else C.mat("WoodLight"), bevel=0.01, bseg=1))
    for k in (0, 3, 6):
        for s in (-1, 1):
            P.append(C.cyl("post", (a.x + k * 0.26, a.y + s * 0.42, -0.3), r=0.045, h=0.62, mat=C.mat("WoodDark"), seg=6, base=True))
    boat = C.lathe("hull", [(0, 0.0), (0.3, 0.05), (0.4, 0.25), (0.36, 0.27), (0, 0.27)], seg=16, mat=M("BoatRed", "E0674F", rough=0.7))
    boat.data.transform(Matrix.Diagonal((0.8, 2.0, 1, 1)))
    boat.location = (a.x + 2.45, a.y - 0.05, -0.25)
    P.append(boat)
    bal = a_balloon.build_balloon()
    for o in bal.children_recursive:
        if o.type == 'MESH':
            for i, m_ in enumerate(o.data.materials):
                if m_ and m_.name == "BalloonGreen":
                    o.data.materials[i] = M("BalloonCoral", "F2866B", rough=0.75)
    P += C.harvest(bal, (a.x + 1.7, a.y + 0.2, 0.15), -20, 0.8)
    P.append(C.tube("mooring", [(a.x + 1.55, a.y + 0.05, 0.2), (a.x + 1.62, a.y + 0.15, 0.2)], r=0.01, mat=C.mat("Rope", "D9BE8C"), seg=4, res=1))
    E["ActivityA"] = ((a.x + 0.9, a.y - 0.1), (a.x + 1.7, a.y + 0.2))
    # B lighthouse
    b = Vector((-2.6, -1.0))
    lh = C.lathe("lighthouse", [(0, 0), (0.45, 0), (0.42, 0.5), (0.39, 1.0), (0.36, 1.5), (0.33, 2.0), (0, 2.0)], seg=16,
                 mats=[C.mat("White"), M("LHRed", "E0674F")], mat_idx=[0, 1, 0, 1, 0, 0])
    lh.location = (b.x, b.y, 0)
    P += [lh, C.cyl("gallery", (b.x, b.y, 2.0), r=0.45, h=0.06, mat=C.mat("Iron", rough=0.6), seg=16, base=True),
          C.cyl("lamp", (b.x, b.y, 2.06), r=0.25, h=0.35, mat=glow("GlowLamp", "FFD58A", base="FFE6A8"), seg=12, base=True),
          C.cyl("lhroof", (b.x, b.y, 2.41), r=0.33, r2=0.0, h=0.35, mat=M("LHRed", "E0674F"), seg=16, base=True)]
    P += door(b.x, b.y - 0.43, 0.0, 0.3, 0.55)
    E["ActivityB"] = ((b.x + 0.55, b.y - 0.75), b)
    # C café table with a cloud cake
    c0 = Vector((0.4, -2.2))
    P += [C.cyl("tabletop", (c0.x, c0.y, 0.68), r=0.38, h=0.04, mat=C.mat("White"), seg=20, base=True, bevel=0.01, bseg=1),
          C.cyl("tleg", (c0.x, c0.y, 0.0), r=0.04, h=0.68, mat=C.mat("Iron"), seg=8, base=True),
          C.cyl("tfoot", (c0.x, c0.y, 0.0), r=0.2, h=0.03, mat=C.mat("Iron"), seg=12, base=True),
          C.cyl("plate", (c0.x, c0.y, 0.72), r=0.16, h=0.015, mat=M("Plate", "F6EEDC"), seg=16, base=True)]
    cake = C.blob("cloudcake", [((c0.x, c0.y, 0.8), 0.1), ((c0.x - 0.07, c0.y, 0.78), 0.07), ((c0.x + 0.07, c0.y, 0.78), 0.07), ((c0.x, c0.y, 0.87), 0.07)],
                  mat=M("CloudCake", "FFFFFF", rough=1.0), voxel=0.012, smooth_iter=3, target=500, flat_bottom=0.735)
    P += [cake, C.sphere("berry", (c0.x, c0.y, 0.94), r=0.025, mat=M("Berry", "E5484D", rough=0.5), seg=8, rings=5)]
    for s in (-1, 1):
        cx = c0.x + s * 0.6
        P += [C.cyl("seat", (cx, c0.y, 0.45), r=0.2, h=0.05, mat=M("SeatTeal", "4FA3A5"), seg=14, base=True, bevel=0.015, bseg=1),
              C.cyl("sleg", (cx, c0.y, 0), r=0.025, h=0.45, mat=C.mat("Iron"), seg=6, base=True)]
    P.append(C.cyl("parasolpole", (c0.x, c0.y, 0.72), r=0.02, h=1.2, mat=C.mat("White"), seg=6, base=True))
    um = C.lathe("umb", [(0, 2.0), (0.75, 1.75), (0.8, 1.7), (0, 1.73)], seg=12, mats=[M("HotelMint", "A8E0C8"), C.mat("White")], caps=False)
    for p in um.data.polygons:
        p.material_index = int((math.atan2(p.center.y, p.center.x) + math.pi) / (2 * math.pi) * 6) % 2
    um.location = (c0.x, c0.y, 0)
    P.append(um)
    E["ActivityC"] = ((c0.x + 0.6, c0.y - 0.05), (c0.x, c0.y))
    # clouds hugging the rim
    ca = a_nature.build_cloud_a(); cb = a_nature.build_cloud_b()
    P += C.harvest(ca, (-3.2, 2.6, -0.6), 30, 0.7)
    P += C.harvest(cb, (3.4, 2.2, -0.5), -20, 0.7)
    keep = [(L.x, L.y, 1.6), (a.x + 0.8, a.y, 1.0), (b.x, b.y, 0.8), (c0.x, c0.y, 1.0), (-3.2, 2.6, 1.3), (3.4, 2.2, 1.2)]
    return P, E, keep, dict(n_tuft=16, flowers=["White", "Blossom"], n_flower=6, n_rock=4)


# =============================================================================== CAVES
def trip_caves(rnd):
    P, E = [], {}
    cry = glow("GlowCrystal", "B8A8FF", base="D8CCFF", strength=1.0)
    stone = M("LodgeStone", "A8A0B8", rough=0.9)
    L = Vector((-0.4, 1.9, 0))
    # rock arch over a stone lodge front
    arch = []
    for k in range(9):
        t = k / 8
        ang = math.pi * t
        arch.append(((L.x + 1.5 * math.cos(ang), L.y + 0.2, 0.2 + 2.2 * math.sin(ang)), 0.55))
    ab = C.blob("arch", arch + [((L.x - 1.6, L.y + 0.3, 0.3), 0.7), ((L.x + 1.6, L.y + 0.3, 0.3), 0.7)], mat=M("ArchRock", "6E6690", rough=0.9),
                voxel=0.08, smooth_iter=3, target=1800)
    C.jitter(ab, 0.06, 2.5, 4)
    C.shade(ab, 50)
    P.append(ab)
    P.append(C.box("lodge", (L.x, L.y + 0.3, 0), (2.0, 1.2, 1.5), mat=stone, bevel=0.05, bseg=2, base=True))
    for k in range(10):
        P.append(C.box("brick", (L.x - 0.9 + rnd.uniform(0, 1.8), L.y - 0.31, rnd.uniform(0.2, 1.4)), (0.18, 0.03, 0.09), mat=M("Brick", "8E869E", rough=0.9), bevel=0.01, bseg=1))
    fy = L.y - 0.3
    P += door(L.x, fy, 0.0, 0.55, 0.95)
    P += round_window(L.x - 0.65, fy, 0.95, r=0.14) + round_window(L.x + 0.65, fy, 0.95, r=0.14)
    P.append(C.box("lodgeroof", (L.x, L.y + 0.2, 1.5), (2.2, 1.4, 0.15), mat=C.mat("WoodDark"), bevel=0.04, bseg=2, base=True))
    def cluster(x, y, z, s, n=6, tilt=30):
        out = []
        for k in range(n):
            h = s * rnd.uniform(0.6, 1.4)
            r = s * rnd.uniform(0.12, 0.2)
            o = C.lathe("crys", [(0, 0), (r, 0), (r * 1.05, h * 0.8), (0, h)], seg=6, mat=cry, smooth=False)
            o.rotation_euler = (math.radians(rnd.uniform(-tilt, tilt)), math.radians(rnd.uniform(-tilt, tilt)), rnd.uniform(0, 6))
            o.location = (x + rnd.uniform(-0.15, 0.15) * s, y + rnd.uniform(-0.15, 0.15) * s, z)
            C.bake_transform(o)
            out.append(o)
        return out
    P += cluster(L.x + 1.3, L.y + 0.1, 1.9, 0.5, 5) + cluster(L.x - 1.2, L.y + 0.1, 2.0, 0.4, 4)
    E["StayPoint"] = ((L.x, fy - 0.6), (L.x, fy - 3))
    # A mine cart on rails
    a = Vector((2.2, -0.2))
    for s in (-1, 1):
        P.append(C.box("rail", (a.x + s * 0.25, a.y - 0.6, 0.04), (0.04, 2.4, 0.05), mat=C.mat("Iron", rough=0.5), bevel=0.0, smooth=False, base=True, rot=(0, 0, 0)))
    for k in range(9):
        P.append(C.box("sleeper", (a.x, a.y - 1.7 + k * 0.28, 0.0), (0.7, 0.1, 0.05), mat=C.mat("WoodDark"), bevel=0.01, bseg=1, base=True))
    cart = C.lathe("cart", [(0.0, 0.18), (0.32, 0.18), (0.42, 0.58), (0.38, 0.58), (0.3, 0.24), (0, 0.24)], seg=4, mat=M("CartIron", "7A6F8C", rough=0.6), rot=(0, 0, 45), smooth=False)
    cart.data.transform(Matrix.Diagonal((0.9, 1.2, 1, 1)))
    cart.location = (a.x, a.y, 0)
    P.append(cart)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(C.cyl("wheel", (a.x + sx * 0.28, a.y + sy * 0.26, 0.12), r=0.1, h=0.05, rot=(0, 90, 0), mat=C.mat("Iron"), seg=12))
    P += cluster(a.x, a.y, 0.5, 0.3, 4, 20)
    E["ActivityA"] = ((a.x - 0.75, a.y - 0.4), a)
    # B big glowing crystal cluster
    b = Vector((-2.4, -0.8))
    P += cluster(b.x, b.y, 0.0, 1.1, 7, 25)
    E["ActivityB"] = ((b.x + 0.75, b.y - 0.6), b)
    # C underground-style pool with a rock rim
    c0 = Vector((0.5, -2.2))
    P.append(C.cyl("pool", (c0.x, c0.y, 0.02), r=0.8, h=0.02, mat=C.mat("Water", "6EC8E6", rough=0.08, spec=0.7), seg=28, smooth=False))
    for k in range(12):
        ang = 2 * math.pi * k / 12
        rk = I.rock("rim", rnd, rnd.uniform(0.14, 0.2), mats=("ArchRock", "Rock"), sub=1)
        rk.location = (c0.x + 0.9 * math.cos(ang), c0.y + 0.75 * math.sin(ang), 0.05)
        C.bake_transform(rk)
        P.append(rk)
    P += cluster(c0.x + 0.75, c0.y + 0.4, 0.0, 0.35, 3)
    E["ActivityC"] = ((c0.x - 0.35, c0.y + 0.95), c0)
    for (x, y, s) in [(2.8, 1.8, 0.6), (-3.1, 1.0, 0.5), (1.4, 2.8, 0.45)]:
        P += cluster(x, y, 0.0, s, 5)
    keep = [(L.x, L.y, 2.0), (a.x, a.y - 0.6, 1.3), (b.x, b.y, 0.9), (c0.x, c0.y, 1.1), (2.8, 1.8, 0.5), (-3.1, 1.0, 0.5), (1.4, 2.8, 0.4)]
    return P, E, keep, dict(n_tuft=6, flowers=None, n_flower=0, n_rock=14)


# =============================================================================== PEAKS
def trip_peaks(rnd):
    P, E = [], {}
    snow = M("SnowCap", "F7FAFF", rough=0.85)
    L = Vector((-0.4, 1.9, 0))
    P.append(C.box("fnd", L, (2.1, 1.7, 0.35), mat=C.mat("Rock", rough=0.9), bevel=0.05, bseg=2, base=True))
    P.append(C.box("chalet", (L.x, L.y, 0.35), (1.9, 1.5, 1.15), mat=M("ChaletWood", "B5764A", rough=0.8), bevel=0.04, bseg=2, base=True))
    for k in range(6):
        P.append(C.box("log", (L.x, L.y - 0.76, 0.45 + k * 0.18), (1.92, 0.03, 0.03), mat=C.mat("WoodDark"), bevel=0.0, smooth=False))
    gable = C.prism("gable", [(-0.95, 1.5), (0.95, 1.5), (0.0, 2.45)], L.y - 0.75, L.y + 0.75, M("ChaletWood", "B5764A"), bevel=0.02)
    gable.data.transform(Matrix.Translation((L.x, 0, 0)))
    P.append(gable)
    for sx in (-1, 1):
        rf = C.box("roof", (0, 0, 0), (1.45, 1.95, 0.14), mat=M("ChaletRoof", "7A4F3A"), bevel=0.04, bseg=2)
        rf.data.transform(C.xform(rot=(0, sx * 44, 0)))
        rf.location = (L.x + sx * 0.5, L.y, 2.0)
        C.bake_transform(rf)
        sn = C.box("snowroof", (0, 0, 0), (1.45, 2.0, 0.12), mat=snow, bevel=0.05, bseg=2)
        sn.data.transform(C.xform(rot=(0, sx * 44, 0)))
        sn.location = (L.x + sx * 0.46, L.y, 2.1)
        C.bake_transform(sn)
        P += [rf, sn]
    P.append(C.box("chim", (L.x + 0.55, L.y + 0.3, 1.8), (0.3, 0.3, 0.9), mat=C.mat("Rock"), bevel=0.03, bseg=1, base=True))
    P.append(C.box("chimsnow", (L.x + 0.55, L.y + 0.3, 2.7), (0.36, 0.36, 0.08), mat=snow, bevel=0.03, bseg=2, base=True))
    fy = L.y - 0.76
    P += door(L.x, fy, 0.35, 0.5, 0.8)
    for dx in (-0.6, 0.6):
        P += [C.box("win", (dx + L.x, fy - 0.01, 0.95), (0.34, 0.03, 0.34), mat=glow("GlowWindow", "FFD58A", base="FFE6A8"), bevel=0.0, smooth=False),
              C.box("shut", (dx + L.x - 0.24, fy - 0.02, 0.95), (0.1, 0.03, 0.4), mat=M("Shutter", "4FA3A5"), bevel=0.01, bseg=1),
              C.box("shut", (dx + L.x + 0.24, fy - 0.02, 0.95), (0.1, 0.03, 0.4), mat=M("Shutter", "4FA3A5"), bevel=0.01, bseg=1)]
    P.append(C.box("balcony", (L.x, fy - 0.2, 1.5), (1.4, 0.4, 0.06), mat=C.mat("WoodDark"), bevel=0.015, bseg=1, base=True))
    for k in range(8):
        P.append(C.box("bal", (L.x - 0.65 + k * 1.3 / 7, fy - 0.38, 1.56), (0.05, 0.03, 0.28), mat=C.mat("Wood"), bevel=0.0, smooth=False, base=True))
    P.append(C.box("steps", (L.x, fy - 0.25, 0.0), (0.7, 0.4, 0.35), mat=C.mat("Rock"), bevel=0.03, bseg=1, base=True))
    E["StayPoint"] = ((L.x, fy - 0.8), (L.x, fy - 3))
    # A sled at the top of a little snow slope
    a = Vector((-2.4, -0.6))
    hill = C.blob("slope", [((a.x, a.y + 0.4, -0.3), 1.0, (1.0, 1.3, 0.8))], mat=snow, voxel=0.08, smooth_iter=4, target=500, flat_bottom=0.0)
    P.append(hill)
    C.update()
    ok, top, n, _ = hill.ray_cast(Vector((a.x, a.y + 0.4, 5)), Vector((0, 0, -1)))
    sz = top.z if ok else 0.4
    sled = [C.box("sledtop", (0, 0, 0.12), (0.4, 0.75, 0.04), mat=C.mat("Wood"), bevel=0.012, bseg=1, base=True)]
    for s in (-1, 1):
        sled.append(C.tube("runner", [(s * 0.17, 0.4, 0.2), (s * 0.17, 0.42, 0.02), (s * 0.17, 0.0, 0.0), (s * 0.17, -0.4, 0.02)], r=0.018, mat=M("SledRed", "E0674F"), seg=5, res=3))
        sled.append(C.cyl("strut", (s * 0.17, 0.0, 0.0), r=0.015, h=0.12, mat=M("SledRed", "E0674F"), seg=5, base=True))
    so = C.join(sled)
    C.set_origin(so, (0, 0, 0))
    so.data.transform(C.xform(rot=(-12, 0, 20)))
    so.location = (a.x + 0.15, a.y + 0.4, sz - 0.05)
    C.bake_transform(so)
    P.append(so)
    E["ActivityA"] = ((a.x + 0.9, a.y - 0.55), (a.x, a.y + 0.4))
    # B snowman
    b = Vector((2.3, -0.4))
    P += [C.sphere("sb1", (b.x, b.y, 0.32), r=0.36, mat=snow, seg=16, rings=10), C.sphere("sb2", (b.x, b.y, 0.82), r=0.26, mat=snow, seg=16, rings=10),
          C.sphere("sb3", (b.x, b.y, 1.2), r=0.19, mat=snow, seg=16, rings=10),
          C.cyl("nose", (b.x, b.y - 0.24, 1.2), r=0.035, r2=0.0, h=0.16, rot=(90, 0, 0), mat=C.mat("Carrot"), seg=8),
          C.torus("scarf", (b.x, b.y, 1.02), R=0.18, r=0.05, mat=M("ScarfRed", "E0674F"), seg=16, mseg=6),
          C.box("scarftail", (b.x + 0.12, b.y - 0.15, 0.9), (0.08, 0.04, 0.22), mat=M("ScarfRed", "E0674F"), bevel=0.015, bseg=1, rot=(0, -15, 0)),
          C.cyl("hat", (b.x, b.y, 1.34), r=0.13, h=0.2, mat=C.mat("Iron"), seg=12, base=True),
          C.cyl("brim", (b.x, b.y, 1.34), r=0.2, h=0.03, mat=C.mat("Iron"), seg=14, base=True)]
    for s in (-1, 1):
        P.append(C.sphere("eye", (b.x + s * 0.06, b.y - 0.17, 1.26), r=0.02, mat=C.mat("SproutEye", rough=0.2), seg=6, rings=4))
        P.append(C.tube("arm", [(b.x + s * 0.2, b.y, 0.85), (b.x + s * 0.45, b.y, 1.0), (b.x + s * 0.55, b.y - 0.05, 1.12)], r=0.015, mat=C.mat("WoodDark"), seg=4, res=2))
    for k in range(3):
        P.append(C.sphere("btn", (b.x, b.y - 0.25, 0.72 + k * 0.1), r=0.022, mat=C.mat("SproutEye"), seg=6, rings=4))
    E["ActivityB"] = ((b.x - 0.3, b.y - 0.85), b)
    # C steaming hot spring
    c0 = Vector((0.4, -2.2))
    P.append(C.cyl("spring", (c0.x, c0.y, 0.02), r=0.85, h=0.02, mat=C.mat("Water", "7FD6E6", rough=0.08, spec=0.7), seg=28, smooth=False))
    for k in range(13):
        ang = 2 * math.pi * k / 13
        rk = I.rock("rim", rnd, rnd.uniform(0.14, 0.2), sub=1)
        rk.location = (c0.x + 0.95 * math.cos(ang), c0.y + 0.8 * math.sin(ang), 0.05)
        C.bake_transform(rk)
        P.append(rk)
    steam = M("Steam", "FFFFFF", rough=1.0)
    for k in range(4):
        base = Vector((c0.x - 0.4 + k * 0.28, c0.y + 0.1 * (k % 2), 0.05))
        pts = [base + Vector((0.05 * math.sin(i * 1.3 + k), 0, i * 0.18)) for i in range(5)]
        P.append(C.tube("steam", pts, r=0.035, radii=[0.6, 1, 1, 0.8, 0.4], mat=steam, seg=6, res=3))
    E["ActivityC"] = ((c0.x + 0.9, c0.y + 0.85), c0)
    # snowy pines
    for (x, y, s_) in [(2.7, 1.8, 1.0), (-3.0, 1.9, 1.1), (3.2, 0.3, 0.8)]:
        pn = a_nature.build_pine()
        for o in C.harvest(pn, (x, y, 0), rnd.uniform(0, 360), s_):
            C.paint_faces(o, snow, lambda c, n: n.z > 0.55 and c.z > 0.5)
            P.append(o)
    keep = [(L.x, L.y, 1.7), (a.x, a.y + 0.3, 1.2), (b.x, b.y, 0.6), (c0.x, c0.y, 1.1), (2.7, 1.8, 1.0), (-3.0, 1.9, 1.0), (3.2, 0.3, 0.8)]
    return P, E, keep, dict(n_tuft=0, flowers=None, n_flower=0, n_rock=6)


# =============================================================================== MOON
def trip_moon(rnd):
    P, E = [], {}
    L = Vector((-0.4, 1.9, 0))
    silver = M("ObsSilver", "D9DEEA", rough=0.5)
    navy = M("ObsNavy", "34497A", rough=0.6)
    P.append(C.cyl("obsbase", (L.x, L.y, 0), r=1.1, h=1.5, mat=silver, seg=24, base=True, bevel=0.04, bseg=2))
    P.append(C.torus("band", (L.x, L.y, 1.5), R=1.1, r=0.06, mat=navy, seg=24, mseg=6))
    dome = C.lathe("dome", [(0, 1.5 + 1.05), (0.5, 1.5 + 0.95), (0.85, 1.5 + 0.65), (1.05, 1.5 + 0.2), (1.08, 1.5)], seg=28, mat=navy, caps=False)
    dome.location = (L.x, L.y, 0)
    P.append(dome)
    P.append(C.box("slot", (L.x, L.y - 0.55, 2.2), (0.3, 0.9, 0.5), mat=M("SlotDark", "1C2340", rough=0.8), bevel=0.02, bseg=1, rot=(-40, 0, 0)))
    P.append(C.cyl("scope", (L.x, L.y - 0.6, 2.45), r=0.12, h=0.9, rot=(-40, 0, 0), mat=C.mat("Brass", rough=0.45), seg=12))
    for k in range(6):
        a_ = math.radians(-90 + (k - 2.5) * 22)
        P.append(C.sphere("star", (L.x + 0.95 * math.cos(a_), L.y + 0.95 * math.sin(a_), 2.0 + 0.2 * (k % 2)), r=0.035, mat=glow("GlowStar", "FFF3C8"), seg=6, rings=4))
    fy = L.y - 1.08
    P += door(L.x, fy, 0.0, 0.55, 0.95)
    P += round_window(L.x + 0.62, fy + 0.12, 1.0, r=0.14) + round_window(L.x - 0.62, fy + 0.12, 1.0, r=0.14)
    E["StayPoint"] = ((L.x, fy - 0.6), (L.x, fy - 3))
    # A telescope on a tripod
    a = Vector((2.2, -0.6))
    P += C.harvest(a_props.build_telescope(), (a.x, a.y, 0), -30, 1.1)
    E["ActivityA"] = ((a.x - 0.2, a.y - 0.7), (a.x + 0.3, a.y + 0.8))
    # B hammock between two posts
    b = Vector((-2.3, -0.5))
    for s in (-1, 1):
        P.append(C.cyl("hpost", (b.x, b.y + s * 0.95, 0), r=0.06, h=1.3, mat=C.mat("Wood"), seg=8, base=True, bevel=0.015, bseg=1))
        P.append(C.sphere("hknob", (b.x, b.y + s * 0.95, 1.33), r=0.07, mat=C.mat("WoodDark"), seg=8, rings=5))
    bm = bmesh.new()
    rows = []
    for i in range(11):
        t = i / 10
        y = b.y - 0.8 + 1.6 * t
        z = 1.05 - 0.55 * math.sin(math.pi * t)
        rows.append([bm.verts.new((b.x + o * (0.25 + 0.1 * math.sin(math.pi * t)), y, z + 0.05 * abs(o) * math.sin(math.pi * t) * 2)) for o in (-1, -0.5, 0, 0.5, 1)])
    for i in range(10):
        for j in range(4):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
            f.material_index = (j + i // 2) % 2
    hm = C.mk("hammock", bm, [M("HammockBlue", "8FB5FF", rough=0.9), M("HammockCream", "F6EEDC", rough=0.9)])
    so = hm.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.03
    C.apply_mods(hm)
    C.shade(hm, 60)
    P.append(hm)
    for s in (-1, 1):
        P.append(C.tube("hrope", [(b.x, b.y + s * 0.95, 1.2), (b.x, b.y + s * 0.8, 1.05)], r=0.012, mat=C.mat("Rope", "D9BE8C"), seg=4, res=1))
    E["ActivityB"] = ((b.x + 0.65, b.y - 0.1), b)
    # C reflecting pool
    c0 = Vector((0.5, -2.3))
    P.append(C.box("pool", (c0.x, c0.y, 0.0), (1.6, 0.9, 0.03), mat=C.mat("Water", "6E8FD8", rough=0.05, spec=0.8), bevel=0.0, smooth=False, base=True))
    for (cx, cy, sx, sy) in [(c0.x, c0.y - 0.5, 1.8, 0.12), (c0.x, c0.y + 0.5, 1.8, 0.12), (c0.x - 0.86, c0.y, 0.12, 0.9), (c0.x + 0.86, c0.y, 0.12, 0.9)]:
        P.append(C.box("coping", (cx, cy, 0.0), (sx, sy, 0.08), mat=M("MoonStone", "B8C0D8", rough=0.9), bevel=0.02, bseg=1, base=True))
    E["ActivityC"] = ((c0.x, c0.y + 0.85), c0)
    # moonflowers
    mf = glow("GlowMoonflower", "D8E8FF", base="EAF2FF", strength=1.0)
    for k in range(26):
        t = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(1.2, 3.6)
        x, y = rr * math.cos(t), rr * math.sin(t)
        if any(math.hypot(x - p_[0], y - p_[1]) < r_ for p_, r_ in [((L.x, L.y), 1.6), ((a.x, a.y), 0.8), ((b.x, b.y), 1.2), ((c0.x, c0.y), 1.2)]):
            continue
        h = rnd.uniform(0.25, 0.55)
        P.append(C.tube("mst", [(x, y, 0), (x + 0.02, y, h * 0.6), (x, y, h)], r=0.01, mat=M("MoonStem", "6FA59A"), seg=4, res=2))
        fl = C.lathe("mf", [(0, 0), (0.05, 0.03), (0.1, 0.08), (0.085, 0.09), (0, 0.035)], seg=10, mat=mf, rfun=lambda t_, z: 0.75 + 0.25 * abs(math.cos(2.5 * t_)))
        fl.location = (x, y, h)
        P.append(fl)
    keep = [(L.x, L.y, 1.6), (a.x, a.y, 0.8), (b.x, b.y, 1.2), (c0.x, c0.y, 1.1)]
    return P, E, keep, dict(n_tuft=18, flowers=None, n_flower=0, n_rock=6)


BUILD = {k: globals()["trip_" + k] for k in TRIPS}


def build_trip(theme):
    rnd = random.Random(sum(map(ord, theme)) * 3)
    root = C.empty("Trip")
    body, under, spin = base_island(theme, rnd)
    P, E, keep, sc = BUILD[theme](rnd)
    keep = keep + [(p[0][0], p[0][1], 0.45) for p in E.values()]
    P += scatter(body, rnd, spin, keep, **sc)
    decor = C.join([under] + P, "TripDecor")
    C.set_origin(decor, (0, 0, 0))
    C.set_parent(body, root)
    C.set_parent(decor, root)
    cam = Vector((math.sin(math.radians(28)), -math.cos(math.radians(28))))     # toward the front-right camera
    for name, (spot, target) in E.items():
        if name.startswith("Activity"):
            d = (Vector(target) - Vector(spot)).normalized() + cam * 0.9          # 3/4: toward the prop, face still visible
            target = (spot[0] + d.x, spot[1] + d.y)
        C.slot(name, (spot[0], spot[1], 0.0), root, rz=face_rz(spot, target))
    C.empty("IslandCenter", (0, -0.2, 1.0), parent=root)
    return root


for _t in TRIPS:
    globals()["build_trip_" + _t] = (lambda t=_t: build_trip(t))

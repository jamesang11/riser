"""Critters: butterfly, bird."""
import math
from mathutils import Vector, Matrix
import common as C


# ============================================================================ BUTTERFLY
def butterfly_wing(sx):
    """Wing on the +X side (mirrored for sx<0): fore + hind lobes, orange rim under yellow face."""
    wing_m = C.mat("ButterflyWing", "FFE89A", rough=0.8)
    edge_m = C.mat("ButterflyWingEdge", "F7A25A", rough=0.8)
    parts = []
    lobes = [((0.05, -0.016), (0.046, 0.034), -25), ((0.036, 0.024), (0.033, 0.026), 30)]
    for (cx, cy), (rx, ry), rot in lobes:
        e = C.sphere("we", (cx, cy, 0.0), r=1, scale=(rx, ry, 0.0022), rot=(0, 0, rot), mat=edge_m, seg=20, rings=6)
        f = C.sphere("wf", (cx - 0.004, cy + 0.0005, 0.0012), r=1, scale=(rx * 0.8, ry * 0.8, 0.0022), rot=(0, 0, rot), mat=wing_m, seg=20, rings=6)
        parts += [e, f]
    # little spots
    parts.append(C.sphere("sp", (0.062, -0.022, 0.0028), r=1, scale=(0.009, 0.008, 0.0012), mat=edge_m, seg=10, rings=4))
    w = C.join(parts)
    C.set_origin(w, (0, 0, 0))
    w.data.transform(C.xform(rot=(0, -18, 0)))       # dihedral: tips raised
    if sx < 0:
        w.data.transform(C.xform(scale=(-1, 1, 1)))
        w.data.flip_normals()
    C.shade(w, 180)
    return w


def build_butterfly():
    root = C.empty("Butterfly")
    dark = C.mat("ButterflyBody", "3B3040", rough=0.7)
    zc = 0.012
    body = [C.sphere("thorax", (0, -0.004, zc), r=1, scale=(0.0075, 0.012, 0.0075), mat=dark, seg=12, rings=8),
            C.sphere("abdomen", (0, 0.02, zc - 0.001), r=1, scale=(0.0055, 0.022, 0.0055), mat=dark, seg=12, rings=8),
            C.sphere("head", (0, -0.02, zc + 0.001), r=0.0065, mat=dark, seg=12, rings=8)]
    for sx in (-1, 1):
        p0 = Vector((sx * 0.002, -0.024, zc + 0.004))
        body.append(C.tube("ant", [p0, p0 + Vector((sx * 0.006, -0.012, 0.012)), p0 + Vector((sx * 0.012, -0.018, 0.022))], r=0.0012, mat=dark, seg=4, res=3))
        body.append(C.sphere("antb", p0 + Vector((sx * 0.012, -0.018, 0.022)), r=0.0028, mat=dark, seg=8, rings=5))
    b = C.join(body, "ButterflyBody")
    C.set_origin(b, (0, 0, 0))
    C.set_parent(b, root)
    for side, sx in (("L", -1), ("R", 1)):
        w = butterfly_wing(sx)
        w.name = w.data.name = "Wing" + side
        w.location = (sx * 0.004, 0, zc)
        C.set_parent(w, root)
    return root


# ============================================================================ BIRD
def build_bird():
    root = C.empty("Bird")
    bodym = C.mat("BirdBody", "8FA6C4", rough=0.8)
    belly = C.mat("BirdBelly", "F6E9D2", rough=0.85)
    wingm = C.mat("BirdWing", "6F88AB", rough=0.8)
    beak = C.mat("Beak", "F2A04A", rough=0.6)
    eye = C.mat("SproutEye", rough=0.12, spec=0.6, coat=0.6)
    shine = C.mat("EyeShine", "FFFFFF", rough=0.25, emit="FFFFFF", strength=0.6)
    legm = C.mat("BirdLeg", "E58F45", rough=0.7)
    b = C.blob("BirdBody", [((0, 0.01, 0.1), 0.085, (1.0, 1.2, 0.95)), ((0, -0.06, 0.155), 0.062), ((0, 0.075, 0.085), 0.05, (0.9, 1.2, 0.8))],
               mat=bodym, voxel=0.008, smooth_iter=6, target=1400)
    C.paint_faces(b, belly, lambda c, n: n.y < -0.1 and n.z < 0.35 and c.z < 0.15)
    tail = C.sphere("tail", (0, 0.135, 0.12), r=1, scale=(0.035, 0.06, 0.011), rot=(-28, 0, 0), mat=wingm, seg=12, rings=6)
    bk = C.cyl("beak", (0, -0.126, 0.152), r=0.017, r2=0.001, h=0.036, rot=(90, 0, 0), mat=beak, seg=10)
    parts = [b, tail, bk]
    for sx in (-1, 1):
        e = C.sphere("eye", (sx * 0.04, -0.097, 0.172), r=1, scale=(0.011, 0.009, 0.013), rot=(0, 0, sx * 35), mat=eye, seg=12, rings=8)
        s = C.sphere("sh", (sx * 0.043, -0.106, 0.178), r=0.0035, mat=shine, seg=8, rings=5)
        ck = C.sphere("ck", (sx * 0.048, -0.092, 0.147), r=1, scale=(0.012, 0.006, 0.008), rot=(0, 0, sx * 40), mat=C.mat("SproutCheek", rough=0.85), seg=10, rings=6)
        leg = C.tube("leg", [(sx * 0.025, -0.005, 0.04), (sx * 0.026, -0.01, 0.0)], r=0.0045, mat=legm, seg=4, res=1)
        foot = C.sphere("foot", (sx * 0.026, -0.022, 0.003), r=1, scale=(0.009, 0.018, 0.004), mat=legm, seg=8, rings=5)
        parts += [e, s, ck, leg, foot]
    bo = C.join(parts, "BirdBody")
    C.set_origin(bo, (0, 0, 0))
    C.set_parent(bo, root)
    for side, sx in (("L", -1), ("R", 1)):
        sh = Vector((sx * 0.075, -0.005, 0.125))
        w = C.sphere("Wing" + side, r=1, scale=(0.014, 0.065, 0.04), mat=wingm, seg=14, rings=8)
        for v in w.data.vertices:          # teardrop: taper toward the back
            t = max(0.0, v.co.y / 0.065)
            v.co.z *= 1 - 0.55 * t
            v.co.x *= 1 - 0.4 * t
        w.data.transform(Matrix.Translation((0, 0.045, -0.012)))
        w.data.transform(C.xform(rot=(-12, sx * -8, sx * 8)))
        w.location = sh
        C.shade(w, 180)
        C.set_parent(w, root)
    # scale down to ~0.25 m long (baked into children; root stays identity)
    k = 0.76
    for ch in root.children:
        ch.data.transform(Matrix.Scale(k, 4))
        ch.location = ch.location * k
    return root

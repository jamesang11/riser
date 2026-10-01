"""Decor set 2 (well, fountain, gazebo, beehive, swing, lighthouse, bushes, boulders, signpost,
picnic, archway, hammock) + expansion islands (isle_meadow, isle_beach) + rope bridge."""
import math, random
import bmesh
from mathutils import Vector, Matrix, noise
import common as C
import a_island as I
import a_nature as N

TAU = 2 * math.pi


# ============================================================================ helpers
def M(name, hexc=None, rough=0.82, **kw):
    return C.mat(name, hexc, rough=rough, **kw)


def ROPE():
    return M("Rope", "D6B585", rough=0.9)


def WATER():
    return C.mat("Water", "6EC8E6", rough=0.15, spec=0.6)


def attach(root, parts, name, origin=(0, 0, 0)):
    o = C.join(parts, name)
    C.set_origin(o, origin)
    C.set_parent(o, root)
    return o


def beam(name, p0, p1, w, t, mat, side=(1, 0, 0), bevel=0.008, bseg=1):
    """Box from p0 to p1; w along `side` (orthogonalised), t along the remaining axis."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    z = d / L
    x = Vector(side)
    x = x - z * x.dot(z)
    if x.length < 1e-5:
        x = Vector((0, 1, 0)) - z * z.y
    x.normalize()
    y = z.cross(x)
    o = C.box(name, (0, 0, 0), (w, t, L), mat=mat, bevel=bevel, bseg=bseg)
    o.data.transform(Matrix((x, y, z)).transposed().to_4x4())
    o.location = (p0 + p1) / 2
    return o


def stone(name, rnd, mat, scale, rot_z, loc, seed, jit=0.09, floor=None):
    st = C.ico(name, r=1, sub=2, mat=C.mat(mat, rough=0.9))
    C.jitter(st, jit, 1.3, seed)
    st.data.transform(C.xform(scale=scale, rot=(0, 0, rot_z)))
    if floor is not None:
        for v in st.data.vertices:
            v.co.z = max(v.co.z, floor)
    st.location = loc
    C.shade(st, 180)
    return st


def blossom(col, center="FlowerYellow", s=1.0):
    """Tiny 5-petal flower facing +Z, origin at its base."""
    petal = C.lathe("fp", [(0, 0.0), (0.045 * s, 0.012 * s), (0.0, 0.02 * s)], seg=15, mat=C.mat(col),
                    rfun=lambda t, z: 0.55 + 0.45 * abs(math.cos(2.5 * t)) ** 0.6, sharp=80)
    ctr = C.sphere("fc", (0, 0, 0.02 * s), r=0.018 * s, scale=(1, 1, 0.6), mat=C.mat(center), seg=6, rings=3)
    C.bake_transform(ctr)
    return C.join([petal, ctr])


def orient(o, nrm, loc, spin=0.0):
    """Rotate object data so +Z follows nrm, then place at loc."""
    q = Vector(nrm).normalized().to_track_quat('Z', 'Y')
    o.data.transform(q.to_matrix().to_4x4() @ Matrix.Rotation(spin, 4, 'Z'))
    o.location = loc
    C.bake_transform(o)
    return o


def tuft(rnd, x, y, s=1.0, z=0.0):
    t = I.grass_tuft("tuft", rnd, s=s)
    t.data.transform(C.xform(rot=(0, 0, rnd.uniform(0, 360))))
    t.location = (x, y, z)
    C.bake_transform(t)
    return t


# ============================================================================ WELL
def build_well():
    rnd = random.Random(21)
    root = C.empty("Well")
    wood, woodd = M("Wood", rough=0.8), M("WoodDark", rough=0.8)
    rope = ROPE()
    parts = [C.lathe("wall", [(0, 0), (0.4, 0), (0.4, 0.5), (0.3, 0.5), (0.3, 0.22), (0, 0.22)], seg=24,
                     mat=M("RockDark", rough=0.9), sharp=50)]
    k = 0
    for ci, z in enumerate((0.085, 0.245, 0.405)):
        n = 11
        for i in range(n):
            a = TAU * (i + 0.5 * (ci % 2)) / n + rnd.uniform(-0.05, 0.05)
            s = rnd.uniform(0.9, 1.08)
            col = rnd.choice(["Rock", "Rock", "Pebble", "Pebble", "RockDark"])
            parts.append(stone("st", rnd, col, (0.06 * s, 0.122 * s, 0.07 * s), math.degrees(a),
                               (0.39 * math.cos(a), 0.39 * math.sin(a), z + rnd.uniform(-0.01, 0.01)), k))
            k += 1
    parts.append(C.torus("rim", (0, 0, 0.53), R=0.36, r=0.09, scale=(1, 1, 0.55), mat=M("Pebble", rough=0.9), seg=28, mseg=10))
    # posts, ridge, roof
    for sx in (-1, 1):
        parts.append(C.box("post", (sx * 0.36, 0, 0.5), (0.085, 0.085, 0.95), mat=wood, bevel=0.018, bseg=2, base=True))
    parts.append(C.cyl("ridge", (0, 0, 1.47), r=0.04, h=0.8, rot=(0, 90, 0), mat=woodd, seg=10))
    ang = 38
    ra = math.radians(ang)
    P = Vector((0, 0, 1.5))
    for sy in (-1, 1):
        dirv = Vector((0, sy * math.cos(ra), -math.sin(ra)))
        nrm = Vector((0, sy * math.sin(ra), math.cos(ra)))
        under = C.box("under", (0, 0, 0), (0.78, 0.5, 0.02), mat=woodd, bevel=0.006, bseg=1)
        under.data.transform(C.xform(rot=(-ang * sy, 0, 0)))
        under.location = P + dirv * 0.25 - nrm * 0.005
        parts.append(under)
        for j, d in enumerate((0.085, 0.25, 0.415)):
            sl = C.box("slat", (0, 0, 0), (0.8, 0.165, 0.042), mat=wood if j != 1 else M("WoodLight", rough=0.8), bevel=0.014, bseg=2)
            sl.data.transform(C.xform(rot=(-ang * sy + rnd.uniform(-1.5, 1.5), 0, 0)))
            sl.location = P + dirv * d + nrm * (0.026 + 0.004 * j)
            parts.append(sl)
    parts.append(C.cyl("cap", (0, 0, 1.535), r=0.045, h=0.84, rot=(0, 90, 0), mat=woodd, seg=10, bevel=0.01, bseg=1))
    # windlass + crank
    zA = 1.08
    parts.append(C.cyl("axle", (0, 0, zA), r=0.04, h=0.86, rot=(0, 90, 0), mat=wood, seg=12))
    parts.append(C.box("crank", (0.455, 0, zA - 0.07), (0.03, 0.035, 0.16), mat=woodd, bevel=0.01, bseg=1))
    parts.append(C.cyl("handle", (0.49, 0, zA - 0.14), r=0.02, h=0.08, rot=(0, 90, 0), mat=woodd, seg=8))
    for i in range(5):
        parts.append(C.torus("coil", (-0.08 + 0.04 * i, 0, zA), R=0.052, r=0.014, rot=(0, 90, 0), mat=rope, seg=14, mseg=6))
    # bucket on rope
    bz, by = 0.66, -0.055
    parts.append(C.tube("rope", [(0, by, zA - 0.01), (0, by, bz + 0.2)], r=0.011, mat=rope, seg=5, res=1))
    bk = [C.lathe("bucket", [(0, 0), (0.07, 0), (0.088, 0.13), (0.078, 0.13), (0.062, 0.02), (0, 0.02)], seg=16, mat=wood, sharp=60)]
    for z, rr in ((0.025, 0.073), (0.105, 0.085)):
        bk.append(C.torus("band", (0, 0, z), R=rr, r=0.008, mat=M("Iron", rough=0.6), seg=16, mseg=4))
    bk.append(C.torus("bail", (0, 0, 0.12), R=0.085, r=0.007, rot=(90, 0, 0), mat=M("Iron", rough=0.6), seg=12, mseg=4, arc=180))
    bk.append(C.lathe("bwater", [(0, 0.1), (0.08, 0.1)], seg=16, mat=WATER()))
    for o in bk:
        o.location = Vector(o.location) + Vector((0, by, bz))
    parts += bk
    # water inside the well
    water = C.lathe("Water", [(0, 0.0), (0.31, 0.0)], seg=24, mat=WATER())
    water.location = (0, 0, 0.4)
    # grass + flowers around the base
    for i, a in enumerate((200, 250, 310, 35, 120)):
        ar = math.radians(a)
        parts.append(tuft(rnd, 0.47 * math.cos(ar), 0.47 * math.sin(ar), s=rnd.uniform(0.8, 1.0)))
    for (a, col) in ((228, "White"), (283, "FlowerYellow"), (60, "Blossom")):
        ar = math.radians(a)
        f = blossom(col, s=1.3)
        f.location = (0.49 * math.cos(ar), 0.49 * math.sin(ar), 0.0)
        parts.append(f)
    attach(root, parts, "WellBody")
    C.set_parent(water, root)
    return root


# ============================================================================ FOUNTAIN
def build_fountain():
    rnd = random.Random(5)
    root = C.empty("Fountain")
    rock, peb, rockd = M("Rock", rough=0.9), M("Pebble", rough=0.9), M("RockDark", rough=0.9)
    parts = [C.lathe("core", [(0, 0), (0.69, 0), (0.69, 0.27), (0.6, 0.27), (0.6, 0.12), (0, 0.12)], seg=32, mat=rockd, sharp=50)]
    for ci, (z0, h) in enumerate(((0.0, 0.14), (0.14, 0.13))):
        n = 14
        for i in range(n):
            a = TAU * (i + 0.5 * ci) / n
            b = C.box("blk", (0, 0, 0), (0.13, TAU * 0.7 / n - 0.014, h - 0.012), mat=peb if (i * 7 + ci * 3) % 5 == 0 else rock,
                      bevel=0.022, bseg=2)
            b.data.transform(C.xform(rot=(0, 0, math.degrees(a))))
            b.location = (0.68 * math.cos(a), 0.68 * math.sin(a), z0 + h / 2 + 0.004)
            parts.append(b)
    parts.append(C.lathe("cap", [(0.58, 0.27), (0.77, 0.27), (0.787, 0.30), (0.77, 0.335), (0.6, 0.338), (0.58, 0.31), (0.58, 0.27)],
                         seg=40, mat=peb, caps=False, sharp=60))
    # pedestal, upper bowl, top
    parts.append(C.lathe("ped", [(0, 0.12), (0.2, 0.12), (0.2, 0.19), (0.14, 0.24), (0.1, 0.34), (0.088, 0.5), (0.11, 0.62), (0.1, 0.7), (0, 0.7)],
                         seg=20, mats=[rock, peb], mat_idx=[1, 1, 1, 0, 0, 0, 1, 1], sharp=50))
    parts.append(C.lathe("bowl", [(0, 0.66), (0.12, 0.68), (0.27, 0.76), (0.345, 0.84), (0.36, 0.885), (0.33, 0.905), (0.3, 0.86), (0, 0.84)],
                         seg=28, mats=[rock, peb], mat_idx=[0, 0, 0, 1, 1, 1, 1], sharp=55))
    parts.append(C.lathe("top", [(0, 0.84), (0.055, 0.84), (0.04, 0.98), (0.085, 1.02), (0.075, 1.06), (0, 1.07)], seg=16, mat=peb, sharp=60))
    for (x, y, r, rot) in ((-0.36, -0.3, 0.1, 40), (0.42, 0.12, 0.085, 200)):
        pad = C.lathe("pad", [(0, 0.0), (r, 0.0), (r, 0.01), (0, 0.012)], seg=18, mat=M("Leaf", rough=0.7),
                      rfun=lambda t, z: 0.25 if (t < 0.35) else 1.0, sharp=60)
        pad.data.transform(C.xform(rot=(0, 0, rot)))
        pad.location = (x, y, 0.298)
        parts.append(pad)
    parts.append(C.sphere("lily", (-0.36, -0.3, 0.325), r=0.03, scale=(1, 1, 0.7), mat=M("BlossomDeep"), seg=8, rings=5))
    attach(root, parts, "FountainStone")
    # water (material Water): basin, upper bowl, jet, spill streams
    w = WATER()
    wp = [C.lathe("wb", [(0, 0.3), (0.6, 0.3)], seg=40, mat=w),
          C.lathe("wu", [(0, 0.875), (0.318, 0.875)], seg=28, mat=w),
          C.lathe("jet", [(0, 1.06), (0.045, 1.07), (0.035, 1.13), (0.012, 1.17), (0, 1.18)], seg=12, mat=w, sharp=80)]
    for i in range(8):
        a = TAU * i / 8 + 0.2
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * 0.35 + Vector((0, 0, 0.9)), d * 0.42 + Vector((0, 0, 0.87)), d * 0.48 + Vector((0, 0, 0.7)), d * 0.5 + Vector((0, 0, 0.3))]
        wp.append(C.tube("spill", pts, r=0.012, radii=[1.3, 1.0, 0.8, 1.0], mat=w, seg=6, res=4))
    wo = C.join(wp, "Water")
    C.set_origin(wo, (0, 0, 0))
    C.set_parent(wo, root)
    return root


# ============================================================================ GAZEBO
def build_gazebo():
    rnd = random.Random(9)
    root = C.empty("Gazebo")
    wood, woodd, woodl = M("Wood", rough=0.8), M("WoodDark", rough=0.8), M("WoodLight", rough=0.8)
    cream = M("Cream", rough=0.8)
    A = 1.0
    S3 = math.sqrt(3)
    parts = [C.lathe("floor", [(0, 0), (A, 0), (A, 0.1), (0, 0.1)], seg=6, mat=woodd, sharp=30),
             C.lathe("deck", [(0, 0.1), (A - 0.05, 0.1), (A - 0.05, 0.14), (0, 0.14)], seg=6, mat=wood, sharp=30)]
    a2 = A - 0.05
    y = -0.78
    while y < 0.8:
        L = 2 * (a2 - abs(y) / S3) - 0.06
        if L > 0.1:
            parts.append(C.box("groove", (0, y, 0.141), (L, 0.012, 0.006), mat=woodd, bevel=0.0))
        y += 0.13
    parts.append(C.box("step", (0, -0.95, 0), (0.62, 0.16, 0.07), mat=wood, bevel=0.02, bseg=2, base=True))
    Rp = 0.87
    V = [Vector((Rp * math.cos(math.radians(60 * k)), Rp * math.sin(math.radians(60 * k)), 0)) for k in range(6)]
    for k in range(6):
        p = C.box("post", (0, 0, 0), (0.085, 0.085, 1.46), mat=wood, bevel=0.018, bseg=2, base=True)
        p.data.transform(C.xform(rot=(0, 0, 60 * k)))
        p.location = V[k] + Vector((0, 0, 0.14))
        parts.append(p)
        parts.append(C.box("pfoot", (0, 0, 0), (0.12, 0.12, 0.06), mat=woodd, bevel=0.015, bseg=1, base=True, rot=(0, 0, 60 * k)))
        parts[-1].location = V[k] + Vector((0, 0, 0.14))
    for k in range(6):
        p0, p1 = V[k], V[(k + 1) % 6]
        mid = (p0 + p1) / 2
        up = Vector((0, 0, 1))
        # fretwork arch under the eave (all sides)
        parts.append(C.tube("fret", [p0 + up * 1.34, mid + up * 1.5, p1 + up * 1.34], r=0.022, mat=cream, seg=6, res=6))
        parts.append(beam("lintel", p0 + up * 1.555, p1 + up * 1.555, 0.06, 0.07, woodd, side=(0, 0, 1)))
        if k == 4:          # front side (-Y) stays open
            continue
        parts.append(beam("rail", p0 + up * 0.62, p1 + up * 0.62, 0.05, 0.075, woodl, side=(0, 0, 1)))
        parts.append(beam("rail", p0 + up * 0.26, p1 + up * 0.26, 0.04, 0.05, woodl, side=(0, 0, 1)))
        for f in (0.25, 0.5, 0.75):
            q = p0 + (p1 - p0) * f
            parts.append(C.box("bal", (q.x, q.y, 0.26), (0.035, 0.035, 0.36), mat=woodl, bevel=0.008, bseg=1, base=True))
    # roof (hex, aligned with posts)
    teal, teald = M("RoofTeal", rough=0.75), M("RoofTealDark", rough=0.75)
    prof = [(0, 1.59), (1.08, 1.585), (1.08, 1.645), (0.8, 1.8), (0.48, 2.02), (0.2, 2.25), (0, 2.34)]
    parts.append(C.lathe("roof", prof, seg=6, mats=[woodd, teald, teal], mat_idx=[0, 1, 2, 2, 2, 2], sharp=20))
    for k in range(6):
        a = math.radians(60 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * 1.03 + Vector((0, 0, 1.672)), d * 0.8 + Vector((0, 0, 1.815)), d * 0.48 + Vector((0, 0, 2.035)), d * 0.18 + Vector((0, 0, 2.28))]
        parts.append(C.tube("hip", pts, r=0.028, mat=teald, seg=6, res=4))
    parts.append(C.sphere("knob", (0, 0, 2.36), r=0.07, mat=M("Brass", rough=0.45), seg=12, rings=8))
    parts.append(C.cyl("spire", (0, 0, 2.4), r=0.025, r2=0.0, h=0.12, mat=M("Brass", rough=0.45), seg=8, base=True))
    # bench along the back (+Y) side
    parts.append(C.box("seat", (0, 0.56, 0.45), (0.8, 0.27, 0.05), mat=wood, bevel=0.018, bseg=2))
    for sx in (-1, 1):
        parts.append(C.box("bleg", (sx * 0.33, 0.56, 0.14), (0.05, 0.22, 0.29), mat=woodd, bevel=0.012, bseg=1, base=True))
    # potted flowers flanking the entrance
    for sx in (-1, 1):
        px, py = sx * 0.52, -0.6
        parts.append(C.lathe("pot", [(0, 0.14), (0.07, 0.14), (0.09, 0.28), (0.1, 0.3), (0.08, 0.3), (0, 0.29)], seg=14,
                             mat=M("Pot", "C9774E", rough=0.85), loc=(px, py, 0)))
        parts.append(C.sphere("bushp", (px, py, 0.36), r=0.1, mat=M("Leaf", rough=0.85), seg=12, rings=8))
        for j in range(5):
            a = TAU * j / 5 + sx
            nv = Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.7)).normalized()
            parts.append(orient(blossom("Blossom" if sx < 0 else "White", s=0.9), nv, Vector((px, py, 0.36)) + nv * 0.095))
    attach(root, parts, "GazeboBody")
    # hanging lantern
    lp = [C.tube("cord", [(0, 0, 1.6), (0, 0, 1.42)], r=0.008, mat=M("Cord", "5A4636", rough=0.9), seg=4, res=1),
          C.lathe("lan", [(0, -0.09), (0.05, -0.09), (0.09, -0.05), (0.1, 0.0), (0.09, 0.05), (0.05, 0.09), (0, 0.09)], seg=14,
                  mat=M("GlowLantern", "FFD58A", rough=0.6, emit="FFD58A", strength=1.0), loc=(0, 0, 1.32),
                  rfun=lambda t, z: 1 + 0.05 * math.cos(8 * t), sharp=70),
          C.cyl("lcap", (0, 0, 1.415), r=0.04, h=0.03, mat=woodd, seg=10),
          C.cyl("lcap", (0, 0, 1.225), r=0.04, h=0.03, mat=woodd, seg=10)]
    attach(root, lp, "Lantern")
    C.empty("LightPoint", (0, 0, 1.32), parent=root)
    return root


# ============================================================================ BEEHIVE
def skep(name, R0, H, seed):
    straw, strawd = M("Straw", "E8C06A", rough=0.9), M("StrawDark", "C99A48", rough=0.9)
    coils = 6
    pitch = H / coils
    prof = [(0, 0.0)]
    n = 36
    for i in range(n + 1):
        z = H * 0.97 * i / n
        base = R0 * max(0.0, 1 - (z / H) ** 2.3) ** 0.5
        rib = 0.93 + 0.07 * abs(math.sin(math.pi * z / pitch)) ** 0.7
        prof.append((max(0.004, base * rib), z))
    prof.append((0.0, H))
    idx = [1]
    for (r0, z0), (r1, z1) in zip(prof[1:-1], prof[2:]):
        zm = (z0 + z1) / 2
        idx.append(1 if abs(math.sin(math.pi * zm / pitch)) < 0.3 else 0)
    o = C.lathe(name, prof, seg=20, mats=[straw, strawd], mat_idx=idx, sharp=85)
    door = C.prism("door", C.arch_pts(0.075, 0.065, 8, 0.0), -R0 - 0.012, -R0 + 0.05, M("Interior", rough=0.9), bevel=0.0)
    board = C.box("board", (0, -R0 - 0.015, 0.006), (0.12, 0.05, 0.012), mat=M("WoodLight", rough=0.8), bevel=0.004, bseg=1)
    return C.join([o, door, board], name)


def build_beehive():
    rnd = random.Random(14)
    root = C.empty("Beehive")
    wood, woodd = M("Wood", rough=0.8), M("WoodDark", rough=0.8)
    TOP = 0.35
    parts = [C.box("plank", (0, 0, TOP - 0.025), (0.72, 0.3, 0.05), mat=wood, bevel=0.016, bseg=2)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.box("leg", (sx * 0.29, sy * 0.1, 0), (0.05, 0.05, TOP - 0.04), mat=woodd, bevel=0.01, bseg=1, base=True))
        parts.append(C.box("xbar", (sx * 0.29, 0, 0.12), (0.035, 0.2, 0.035), mat=woodd, bevel=0.008, bseg=1))
    parts.append(C.box("shelf", (0, 0, 0.12), (0.56, 0.035, 0.035), mat=woodd, bevel=0.008, bseg=1))
    for sx, s, rz in ((-1, 1.0, -8), (1, 0.9, 10)):
        sk = skep("skep", 0.15 * s, 0.34 * s, 3)
        sk.data.transform(C.xform(rot=(0, 0, rz)))
        sk.location = (sx * 0.175, 0.0, TOP)
        parts.append(sk)
    # flowers + tufts at the feet
    fl = [((-0.34, -0.2), "t", "Purple"), ((0.36, -0.17), "d", "White"), ((0.04, -0.3), "d", "FlowerYellow"),
          ((-0.32, 0.2), "t", "BlossomDeep"), ((0.3, 0.24), "t", "FlowerYellow"), ((-0.14, -0.3), "t", "Blossom")]
    for (x, y), kind, col in fl:
        f = N.tulip(rnd, col) if kind == "t" else N.daisy(rnd, col)
        C.set_origin(f, (0, 0, 0))
        f.data.transform(C.xform(scale=(0.72, 0.72, 0.72)))
        f.location = (x, y, 0)
        parts.append(f)
    for (x, y) in ((0.2, -0.28), (-0.4, 0.02), (0.4, 0.05), (0.0, 0.28)):
        parts.append(tuft(rnd, x, y, s=0.8))
    attach(root, parts, "BeehiveBody")
    return root


# ============================================================================ SWING
def build_swing():
    rnd = random.Random(4)
    root = C.empty("Swing")
    wood, woodd, woodl = M("Wood", rough=0.8), M("WoodDark", rough=0.8), M("WoodLight", rough=0.8)
    rope = ROPE()
    ZB = 1.62
    X = 0.55
    FY = 0.31
    parts = [C.cyl("bar", (0, 0, ZB), r=0.05, h=1.24, rot=(0, 90, 0), mat=wood, seg=12, bevel=0.012, bseg=1)]
    for sx in (-1, 1):
        x = sx * X
        for sy in (-1, 1):
            parts.append(C.tube("leg", [(x, 0, ZB + 0.02), (x, sy * FY, 0.02)], r=0.045, mat=woodd, seg=8, res=1))
            parts.append(C.box("foot", (x, sy * FY, 0), (0.1, 0.11, 0.04), mat=woodd, bevel=0.012, bseg=1, base=True))
        yb = FY * (1 - 0.55 / ZB)
        parts.append(beam("brace", (x, -yb - 0.03, 0.55), (x, yb + 0.03, 0.55), 0.06, 0.05, wood, side=(0, 0, 1)))
        parts.append(C.box("joint", (x, 0, ZB), (0.11, 0.15, 0.13), mat=woodd, bevel=0.02, bseg=2))
    attach(root, parts, "SwingFrame")
    # seat + ropes (pivot = top bar)
    sp = [C.box("plank", (0, 0, 0.45), (0.66, 0.24, 0.05), mat=woodl, bevel=0.018, bseg=2)]
    for sx in (-1, 1):
        x = sx * 0.28
        sp.append(C.torus("loop", (x, 0, ZB), R=0.066, r=0.015, rot=(0, 90, 0), mat=rope, seg=14, mseg=6))
        for sy in (-1, 1):
            sp.append(C.tube("rope", [(x, 0, ZB - 0.07), (x, sy * 0.09, 0.47)], r=0.012, mat=rope, seg=5, res=1))
        sp.append(C.cyl("knot", (x, 0, 0.42), r=0.03, h=0.03, mat=rope, seg=8))
    seat = C.join(sp, "Seat")
    C.set_origin(seat, (0, 0, ZB))
    C.set_parent(seat, root)
    return root


# ============================================================================ LIGHTHOUSE
def build_lighthouse():
    rnd = random.Random(11)
    root = C.empty("Lighthouse")
    red, cream = M("RoofRed", rough=0.8), M("Cream", rough=0.8)
    iron = M("Iron", rough=0.6)
    parts = [C.lathe("plinth", [(0, 0), (0.45, 0), (0.47, 0.05), (0.43, 0.15), (0, 0.15)], seg=24, mat=M("RockDark", rough=0.9), sharp=50)]
    n = 10
    for i in range(n):
        a = TAU * i / n + rnd.uniform(-0.1, 0.1)
        s = rnd.uniform(0.85, 1.1)
        parts.append(stone("st", rnd, ["Rock", "Pebble", "RockDark"][i % 3], (0.08 * s, 0.12 * s, 0.085 * s), math.degrees(a) + 90,
                           (0.44 * math.cos(a), 0.44 * math.sin(a), 0.06), i, floor=-0.7))
    z0, z1 = 0.12, 1.5
    rb, rt = 0.34, 0.245
    rz = lambda z: rb + (rt - rb) * (z - z0) / (z1 - z0)
    zs = [z0, 0.4, 0.68, 0.96, 1.24, z1]
    prof = [(0, z0)] + [(rz(z), z) for z in zs] + [(0, z1)]
    parts.append(C.lathe("tower", prof, seg=24, mats=[red, cream], mat_idx=[0, 0, 1, 0, 1, 0, 0], sharp=50))
    # door
    parts.append(C.prism("dframe", C.arch_pts(0.19, 0.31, 10, 0.12), -0.35, -0.28, cream, bevel=0.01))
    parts.append(C.prism("door", C.arch_pts(0.14, 0.26, 10, 0.13), -0.365, -0.3, M("WoodDark", rough=0.8), bevel=0.008))
    parts.append(C.sphere("knob", (0.035, -0.37, 0.25), r=0.014, mat=M("Brass", rough=0.45), seg=8, rings=5))
    # round windows
    glow_w = M("GlowWindow", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0)
    for (z, a) in ((0.82, -90), (1.1, 0), (0.55, 150)):
        ar = math.radians(a)
        d = Vector((math.cos(ar), math.sin(ar), 0))
        r = rz(z)
        w = C.cyl("win", (0, 0, 0), r=0.05, h=0.06, rot=(90, 0, 0), mat=glow_w, seg=14)
        fr = C.torus("wfr", (0, 0, 0), R=0.055, r=0.014, rot=(90, 0, 0), mat=cream if 0.68 < z < 0.96 else red, seg=16, mseg=6)
        for o in (w, fr):
            o.data.transform(C.xform(rot=(0, 0, a + 90)))
            o.location = d * (r - 0.012) + Vector((0, 0, z))
            parts.append(o)
    # gallery + railing
    parts.append(C.lathe("gallery", [(0, 1.48), (0.37, 1.48), (0.385, 1.51), (0.375, 1.55), (0, 1.56)], seg=24, mat=iron, sharp=50))
    for k in range(8):
        a = TAU * k / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(C.tube("corbel", [d * 0.25 + Vector((0, 0, 1.36)), d * 0.34 + Vector((0, 0, 1.48))], r=0.016, mat=iron, seg=5, res=1))
    for k in range(14):
        a = TAU * k / 14
        parts.append(C.cyl("rp", (0.35 * math.cos(a), 0.35 * math.sin(a), 1.55), r=0.011, h=0.18, mat=iron, seg=6, base=True))
    parts.append(C.torus("rail", (0, 0, 1.73), R=0.35, r=0.014, mat=iron, seg=28, mseg=6))
    parts.append(C.torus("rail2", (0, 0, 1.64), R=0.35, r=0.008, mat=iron, seg=28, mseg=4))
    # lamp room
    parts.append(C.lathe("drum", [(0, 1.55), (0.21, 1.55), (0.21, 1.61), (0, 1.61)], seg=16, mat=red, sharp=50))
    parts.append(C.lathe("glass", [(0, 1.61), (0.17, 1.61), (0.17, 1.86), (0, 1.86)], seg=8, mat=M("GlowLighthouse", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0),
                         rot=(0, 0, 22.5), sharp=30))
    for k in range(8):
        a = TAU * k / 8 + math.pi / 8
        parts.append(C.box("mull", (0.172 * math.cos(a), 0.172 * math.sin(a), 1.61), (0.022, 0.022, 0.25), rot=(0, 0, math.degrees(a)),
                           mat=iron, bevel=0.004, bseg=1, base=True))
    parts.append(C.lathe("roof", [(0, 1.86), (0.25, 1.86), (0.265, 1.9), (0.13, 2.05), (0.03, 2.13), (0, 2.14)], seg=16, mat=red, sharp=50))
    parts.append(C.sphere("ball", (0, 0, 2.165), r=0.035, mat=M("Brass", rough=0.45), seg=10, rings=6))
    parts.append(C.cyl("spike", (0, 0, 2.19), r=0.012, r2=0.0, h=0.05, mat=M("Brass", rough=0.45), seg=6, base=True))
    # a few tufts between the rocks
    for a in (60, 200, 300):
        ar = math.radians(a)
        parts.append(tuft(rnd, 0.5 * math.cos(ar), 0.5 * math.sin(ar), s=0.75, z=0.0))
    attach(root, parts, "LighthouseBody")
    C.empty("LightPoint", (0, 0, 1.735), parent=root)
    return root


# ============================================================================ BUSHES
def bush(name, rnd, cx, cy, R, seed):
    c = Vector((cx, cy, R * 0.78))
    sph = [(c, R, (1.0, 1.0, 0.92))]
    for k in range(6):
        a = TAU * k / 6 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        sph.append((c + d * R * 0.55 + Vector((0, 0, rnd.uniform(-0.15, 0.25) * R)), R * rnd.uniform(0.5, 0.62)))
    sph.append((c + Vector((0, 0, R * 0.45)), R * 0.62))
    o = C.blob(name, sph, mat=M("Leaf", rough=0.85), voxel=0.03, smooth_iter=5, target=1400, flat_bottom=0.004, seed=seed, jit=0.012)
    N.tone_canopy(o, M("LeafLight", rough=0.85), M("LeafDark", rough=0.85), seed=seed, up=0.45)
    return o, c


def surface_hits(o, center, n, rnd, zmin_dir=-0.1, sep=0.07, reach=1.5):
    C.update()
    pts = []
    tries = 0
    while len(pts) < n and tries < 800:
        tries += 1
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), abs(rnd.gauss(0, 1)) * 1.2)).normalized()
        if d.z < zmin_dir:
            continue
        ok, loc, nrm, _ = o.ray_cast(center + d * reach, -d)
        if not ok or loc.z < 0.08:
            continue
        if all((loc - q).length > sep for q, _ in pts):
            pts.append((loc.copy(), nrm.copy()))
    return pts


def dot(col, nrm, p, r):
    """Little blossom bead half-sunk into a surface."""
    d = C.sphere("dot", (0, 0, 0), r=r, scale=(1, 1, 0.75), mat=M(col), seg=7, rings=4)
    return orient(d, nrm, p + Vector(nrm) * r * 0.25)


def build_bushes():
    rnd = random.Random(33)
    root = C.empty("Bushes")
    parts = []
    specs = [((-0.2, 0.12), 0.31, ("Blossom", "BlossomDeep")), ((0.27, 0.13), 0.27, ("White", "BlossomLight")),
             ((0.03, -0.27), 0.24, ("FlowerYellow", "Orange"))]
    for i, ((x, y), R, cols) in enumerate(specs):
        b, c = bush("b%d" % i, rnd, x, y, R, i + 3)
        parts.append(b)
        for j, (p, nrm) in enumerate(surface_hits(b, c, 34 + 4 * i, rnd, sep=0.055)):
            parts.append(dot(cols[j % 2], nrm, p, rnd.uniform(0.022, 0.03)))
    for (x, y) in ((0.45, -0.1), (-0.4, -0.2), (0.28, -0.38)):
        parts.append(tuft(rnd, x, y, s=0.8))
    attach(root, parts, "BushCluster")
    return root


# ============================================================================ BOULDERS
def boulder(name, rnd, size, sq, seed, loc):
    o = C.ico(name, r=1.0, sub=3, mat=M("Rock", rough=0.9))
    C.jitter(o, 0.17, 1.1, seed)
    C.jitter(o, 0.035, 3.2, seed + 5)
    sc = (size * sq[0], size * sq[1], size * sq[2])
    o.data.transform(C.xform(scale=sc, rot=(0, 0, rnd.uniform(0, 360))))
    zf = -sc[2] * 0.35
    for v in o.data.vertices:
        if v.co.z < zf:
            v.co.z = zf
    o.data.transform(Matrix.Translation((0, 0, -zf)))
    o.location = loc
    C.update()
    off = Vector((seed * 2.3, seed * 1.1, 0.4))
    C.paint_faces(o, M("RockDark", rough=0.9), lambda c, n: n.z < -0.3)
    C.shade(o, 180)
    # soft moss cap: a thin shell over the upward-facing faces
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()
    ctr = Vector(loc)
    drop = set(f for f in bm.faces if f.normal.z + 0.32 * noise.noise((f.calc_center_median() + ctr) * 3.5 + off) < 0.5)
    shift = []
    for v in bm.verts:
        fs = list(v.link_faces)
        kept = [f for f in fs if f not in drop]
        if kept:
            shift.append((v, v.normal.copy() * (0.005 if len(kept) < len(fs) else 0.018)))
    for v, dv in shift:
        v.co += dv
    bmesh.ops.delete(bm, geom=list(drop), context='FACES')
    for f in bm.faces:
        f.material_index = 0
    moss = C.mk(name + "Moss", bm, [M("Moss", "68A84F", rough=0.95)], loc=loc)
    C.shade(moss, 180)
    return [o, moss]


def mushroom(x, y, s, rnd):
    parts = [C.cyl("mst", (x, y, 0), r=0.018 * s, r2=0.014 * s, h=0.07 * s, mat=M("Cream", rough=0.8), seg=8, base=True)]
    cap = C.lathe("mcap", [(0, 0.06 * s), (0.05 * s, 0.058 * s), (0.052 * s, 0.07 * s), (0.035 * s, 0.1 * s), (0, 0.108 * s)], seg=14,
                  mat=M("Apple", rough=0.6), sharp=70)
    cap.location = (x, y, 0)
    parts.append(cap)
    for k in range(4):
        a = TAU * k / 4 + 0.5
        parts.append(C.sphere("dot", (x + 0.03 * s * math.cos(a), y + 0.03 * s * math.sin(a), 0.087 * s), r=0.009 * s, mat=M("White"), seg=6, rings=4))
    return parts


def build_boulders():
    rnd = random.Random(41)
    root = C.empty("Boulders")
    parts = boulder("b1", rnd, 0.3, (1.0, 0.9, 0.95), 2, (-0.1, 0.1, 0)) + \
        boulder("b2", rnd, 0.2, (1.1, 0.9, 0.8), 6, (0.3, -0.13, 0)) + \
        boulder("b3", rnd, 0.13, (1.0, 0.85, 0.75), 9, (-0.12, -0.32, 0))
    for (x, y, s) in ((0.12, -0.36, 0.05), (0.38, 0.14, 0.045), (-0.3, 0.33, 0.05), (0.2, 0.33, 0.04)):
        parts.append(stone("pb", rnd, "Pebble", (s * 1.2, s, s * 0.6), rnd.uniform(0, 180), (x, y, s * 0.3), int(x * 100), floor=-0.5))
    parts += mushroom(-0.34, -0.1, 1.0, rnd) + mushroom(-0.41, -0.02, 0.75, rnd) + mushroom(0.25, 0.22, 0.8, rnd)
    for (x, y) in ((-0.38, 0.22), (0.47, -0.02), (0.05, -0.47), (-0.35, -0.35)):
        parts.append(tuft(rnd, x, y, s=0.85))
    attach(root, parts, "BoulderCluster")
    return root


# ============================================================================ SIGNPOST
def build_signpost():
    rnd = random.Random(2)
    root = C.empty("Signpost")
    woodd = M("WoodDark", rough=0.8)
    parts = [C.box("post", (0, 0, 0), (0.08, 0.08, 1.3), mat=M("Wood", rough=0.8), bevel=0.016, bseg=2, base=True),
             C.cyl("cap", (0, 0, 1.3), r=0.068, r2=0.0, h=0.08, seg=4, rot=(0, 0, 45), mat=woodd, base=True, smooth=False)]
    shape = [(-0.17, -0.055), (0.2, -0.055), (0.27, 0.0), (0.2, 0.055), (-0.17, 0.055)]
    cols = ["WoodLight", "Cream", "RoofTeal"]
    for i, (z, rot, side) in enumerate(((1.13, 26, -1), (0.95, 170, 1), (0.77, 64, -1))):
        yy0 = side * 0.04
        yy1 = yy0 + side * 0.035
        b = C.prism("board", shape, min(yy0, yy1), max(yy0, yy1), M(cols[i], rough=0.8), bevel=0.01)
        f = side * 1.0
        yf = max(yy0, yy1) if side > 0 else min(yy0, yy1)
        lines = [C.box("txt", (x0, yf + side * 0.002, dz), (w, 0.006, 0.012), mat=woodd, bevel=0.0)
                 for (x0, w, dz) in ((0.0, 0.26, 0.015), (-0.03, 0.2, -0.018))]
        nails = [C.sphere("nail", (-0.13, yf + side * 0.003, 0.0), r=0.011, mat=M("Iron", rough=0.6), seg=6, rings=4)]
        bd = C.join([b] + lines + nails)
        C.set_origin(bd, (0, 0, 0))
        bd.data.transform(C.xform(rot=(rnd.uniform(-3, 3), 0, rot)))
        bd.location = (0, 0, z)
        parts.append(bd)
    for i in range(5):
        a = TAU * i / 5 + 0.3
        parts.append(stone("st", rnd, ["Rock", "Pebble"][i % 2], (0.06, 0.05, 0.04), math.degrees(a), (0.1 * math.cos(a), 0.1 * math.sin(a), 0.015), i, floor=-0.5))
    parts.append(tuft(rnd, -0.13, -0.12, s=0.85))
    parts.append(tuft(rnd, 0.14, 0.1, s=0.75))
    f = blossom("White", s=1.2)
    f.location = (0.14, -0.13, 0)
    parts.append(f)
    attach(root, parts, "SignpostBody")
    return root


# ============================================================================ PICNIC
def checker_cloth(w, top, drape, zt, cell, mats):
    bm = bmesh.new()
    nx = round(w / cell)
    ntop = round(top * 2 / cell)
    nd = max(1, round(drape / cell))
    ss = [(-top - drape) + j * (drape / nd) for j in range(nd)] + [-top + j * (2 * top / ntop) for j in range(ntop)] + \
         [top + j * (drape / nd) for j in range(nd + 1)]
    xs = [-w / 2 + i * w / nx for i in range(nx + 1)]
    def pos(x, s):
        if abs(s) <= top + 1e-6:
            return (x, s, zt)
        sg = 1 if s > 0 else -1
        return (x, sg * (top + 0.004), zt - (abs(s) - top))
    grid = [[bm.verts.new(pos(x, s)) for x in xs] for s in ss]
    for j in range(len(ss) - 1):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.material_index = (i + j) % 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    topf = [f for f in bm.faces if f.calc_center_median().z > zt - 1e-4]
    if sum(f.normal.z for f in topf) < 0:          # make the sheet face outward (up / away from the table)
        for f in bm.faces:
            f.normal_flip()
    o = C.mk("cloth", bm, mats)
    sol = o.modifiers.new("Sol", 'SOLIDIFY')
    sol.thickness = 0.008
    sol.offset = 1.0
    C.apply_mods(o)
    C.shade(o, 30)
    return o


def build_picnic():
    rnd = random.Random(8)
    root = C.empty("Picnic")
    wood, woodd, woodl = M("Wood", rough=0.8), M("WoodDark", rough=0.8), M("WoodLight", rough=0.8)
    ZT = 0.72
    parts = []
    for y in (-0.205, 0.0, 0.205):
        parts.append(C.box("top", (rnd.uniform(-0.01, 0.01), y, ZT - 0.025), (0.92, 0.19, 0.05), mat=wood, bevel=0.018, bseg=2))
    for sy in (-1, 1):
        parts.append(C.box("bench", (0, sy * 0.5, 0.425), (0.92, 0.22, 0.05), mat=wood, bevel=0.018, bseg=2))
    for sx in (-1, 1):
        x = sx * 0.34
        for sy in (-1, 1):
            parts.append(beam("leg", (x, sy * 0.1, ZT - 0.05), (x, sy * 0.54, 0.0), 0.07, 0.09, woodd, side=(1, 0, 0)))
        parts.append(beam("bsup", (x, -0.6, 0.37), (x, 0.6, 0.37), 0.06, 0.06, woodd, side=(0, 0, 1)))
        parts.append(beam("tsup", (x, -0.28, ZT - 0.075), (x, 0.28, ZT - 0.075), 0.05, 0.06, woodd, side=(0, 0, 1)))
    parts.append(beam("brace", (-0.34, 0, 0.37), (0.34, 0, 0.37), 0.05, 0.05, woodd, side=(0, 0, 1)))
    # checked blanket over the table
    cloth = checker_cloth(0.62, 0.305, 0.09, ZT + 0.003, 0.0775, [M("RoofRed", rough=0.85), M("Cream", rough=0.85)])
    parts.append(cloth)
    zc = ZT + 0.011
    # wicker basket
    wick, wickd = M("Wicker", "D6A45F", rough=0.9), M("WickerDark", "B8864A", rough=0.9)
    bk = [C.lathe("basket", [(0, 0), (0.1, 0), (0.122, 0.1), (0.11, 0.105), (0.09, 0.02), (0, 0.02)], seg=18, mat=wick, sharp=60)]
    for z, rr in ((0.03, 0.106), (0.065, 0.114)):
        bk.append(C.torus("weave", (0, 0, z), R=rr, r=0.007, mat=wickd, seg=18, mseg=4))
    bk.append(C.torus("rimw", (0, 0, 0.102), R=0.117, r=0.011, mat=wickd, seg=18, mseg=6))
    bk.append(C.torus("handle", (0, 0, 0.1), R=0.115, r=0.011, rot=(90, 0, 0), mat=wickd, seg=14, mseg=6, arc=180))
    bk.append(C.sphere("napkin", (0, 0, 0.08), r=0.1, scale=(1, 1, 0.35), mat=M("Cream", rough=0.85), seg=12, rings=6))
    bk.append(C.sphere("apple", (0.035, 0.035, 0.11), r=0.042, mat=M("Apple", rough=0.55), seg=12, rings=8))
    bk.append(C.sphere("apple", (-0.04, 0.03, 0.105), r=0.04, mat=M("Apple", rough=0.55), seg=12, rings=8))
    bk.append(C.sphere("bread", (0.0, -0.035, 0.11), r=1, scale=(0.1, 0.035, 0.035), rot=(0, -25, 10), mat=M("WoodLight", rough=0.8), seg=12, rings=6))
    basket = C.join(bk)
    C.set_origin(basket, (0, 0, 0))
    basket.data.transform(C.xform(scale=(1.15, 0.9, 1.0)))
    basket.data.transform(C.xform(rot=(0, 0, 15)))
    basket.location = (0.15, 0.05, zc)
    parts.append(basket)
    # pie on a plate + a cup
    parts.append(C.lathe("plate", [(0, 0), (0.09, 0), (0.105, 0.012), (0.1, 0.014), (0, 0.006)], seg=18, mat=M("White"), loc=(-0.17, -0.06, zc)))
    parts.append(C.lathe("pie", [(0, 0.006), (0.07, 0.006), (0.075, 0.025), (0.06, 0.04), (0, 0.045)], seg=18, mat=M("WoodLight", rough=0.8), loc=(-0.17, -0.06, zc), sharp=70))
    for k in range(3):
        a = TAU * k / 3
        parts.append(C.box("slit", (-0.17 + 0.03 * math.cos(a), -0.06 + 0.03 * math.sin(a), zc + 0.044), (0.03, 0.008, 0.006), rot=(0, 0, math.degrees(a)),
                           mat=M("Apple", rough=0.6), bevel=0.0))
    parts.append(C.lathe("cup", [(0, 0), (0.028, 0), (0.034, 0.07), (0.029, 0.07), (0.024, 0.01), (0, 0.01)], seg=12, mat=M("Mail", rough=0.7), loc=(-0.05, 0.16, zc)))
    parts.append(C.lathe("juice", [(0, 0.055), (0.031, 0.055)], seg=12, mat=M("Orange"), loc=(-0.05, 0.16, zc)))
    attach(root, parts, "PicnicTable")
    return root


# ============================================================================ ARCHWAY
def arch_band(name, r_in, r_out, y0, y1, zc, mat, n=24):
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        a = math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * c, y, zc + r * s)) for (r, y) in ((r_in, y0), (r_out, y0), (r_out, y1), (r_in, y1))])
    for i in range(n):
        a, b = rings[i], rings[i + 1]
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C.mk(name, bm, [mat])
    C.add_bevel(o, 0.006, 1, limit=True, angle=40)
    C.apply_mods(o)
    C.shade(o, 40)
    return o


def build_archway():
    rnd = random.Random(19)
    root = C.empty("Archway")
    white = M("PaintWhite", "F4EFE4", rough=0.75)
    X0, D, ZS = 0.5, 0.17, 1.36
    parts = []
    for sx in (-1, 1):
        x = sx * X0
        for sy in (-1, 1):
            parts.append(C.box("post", (x, sy * D, 0), (0.06, 0.06, ZS), mat=white, bevel=0.012, bseg=1, base=True))
            parts.append(C.box("foot", (x, sy * D, 0), (0.09, 0.09, 0.05), mat=M("WoodDark", rough=0.8), bevel=0.012, bseg=1, base=True))
        for z in (0.12, ZS - 0.04):
            parts.append(beam("rail", (x, -D, z), (x, D, z), 0.035, 0.035, white, side=(1, 0, 0)))
        # diamond lattice in the side panel (YZ plane)
        ya, yb, za, zb = -D + 0.03, D - 0.03, 0.14, ZS - 0.06
        step = 0.16
        for sgn in (1, -1):
            c = za - (yb - ya) - step
            while c < zb + step:
                # line: z = c + sgn*(y - ya)  (sgn=1 rising), clipped to rect
                pts = []
                for y in (ya, yb):
                    z = c + (y - ya) if sgn > 0 else c + (yb - y)
                    if za <= z <= zb:
                        pts.append((y, z))
                for z in (za, zb):
                    y = ya + (z - c) if sgn > 0 else yb - (z - c)
                    if ya <= y <= yb:
                        pts.append((y, z))
                pts = sorted(set((round(p[0], 5), round(p[1], 5)) for p in pts))
                if len(pts) >= 2 and math.dist(pts[0], pts[-1]) > 0.05:
                    (y0, z0), (y1, z1) = pts[0], pts[-1]
                    parts.append(beam("lat", (x + sgn * 0.006, y0, z0), (x + sgn * 0.006, y1, z1), 0.012, 0.026, white, side=(1, 0, 0), bevel=0.0))
                c += step
    # the arch: front + back bands and rungs across the top
    for y0, y1 in ((-D - 0.03, -D + 0.03), (D - 0.03, D + 0.03)):
        parts.append(arch_band("arch", X0 - 0.03, X0 + 0.03, y0, y1, ZS, white))
    for i in range(1, 12):
        a = math.pi * i / 12
        p = Vector((X0 * math.cos(a), 0, ZS + X0 * math.sin(a)))
        parts.append(beam("rung", p + Vector((0, -D, 0)), p + Vector((0, D, 0)), 0.03, 0.022, white, side=(math.cos(a), 0, math.sin(a)), bevel=0.0))
    frame = attach(root, parts, "ArchFrame")
    # climbing foliage: leafy clumps along the arch (dense) + up the posts (fuller on the left)
    clumps = []
    for i in range(22):
        a = math.pi * (i + 0.5) / 22 + rnd.uniform(-0.03, 0.03)
        top = math.sin(a)
        for yy in (-D, 0.0, D):
            if (yy == 0.0 and rnd.random() < 0.55) or (yy != 0.0 and rnd.random() < 0.12):
                continue
            rr = X0 + rnd.uniform(0.0, 0.035)
            p = Vector((rr * math.cos(a), yy + rnd.uniform(-0.03, 0.03), ZS + rr * math.sin(a)))
            clumps.append((p, rnd.uniform(0.07, 0.095) * (0.9 + 0.25 * top), Vector((math.cos(a), 0, math.sin(a)))))
    for sx in (-1, 1):
        for sy in (-1, 1):
            z = 0.12 if sx < 0 else (0.75 if sy > 0 else 0.95)
            while z < ZS:
                y = sy * D + rnd.uniform(-0.035, 0.035)
                clumps.append((Vector((sx * (X0 + rnd.uniform(0.0, 0.025)), y, z)), rnd.uniform(0.06, 0.08), Vector((sx, 0, 0))))
                z += rnd.uniform(0.1, 0.16) if sx < 0 else rnd.uniform(0.12, 0.2)
    for (x, y, r) in ((-X0, -0.02, 0.1), (X0, 0.05, 0.085), (X0 + 0.02, -D, 0.07)):
        clumps.append((Vector((x, y, r * 0.7)), r, Vector((math.copysign(1, x), 0, 0.3)).normalized()))
    fl = []
    greens = ["Leaf", "Leaf", "LeafDark", "Leaf"]
    cols = ["Blossom", "BlossomDeep", "White", "BlossomLight", "Blossom", "BlossomDeep"]
    k = 0
    for i, (p, r, out) in enumerate(clumps):
        cl = C.ico("clump", r=1, sub=2, mat=M(greens[i % 4], rough=0.85))
        C.jitter(cl, 0.16, 1.4, i)
        cl.data.transform(C.xform(scale=(r, r, r * 0.88), rot=(rnd.uniform(0, 40), 0, rnd.uniform(0, 360))))
        cl.location = p
        C.update()
        N.tone_canopy(cl, M("LeafLight", rough=0.85), None, seed=i, up=0.55)
        C.shade(cl, 180)
        fl.append(cl)
        for j in range(rnd.choice((0, 1, 2, 2, 3))):
            d = (out * 1.0 + Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-1.0, 1.0), rnd.uniform(-0.5, 0.8)))).normalized()
            fl.append(dot(cols[k % len(cols)], d, p + d * r * 0.86, rnd.uniform(0.026, 0.036)))
            k += 1
    for (x, y) in ((-0.46, -0.26), (0.47, 0.24), (-0.36, 0.3), (0.38, -0.3)):
        fl.append(tuft(rnd, x, y, s=0.75))
    attach(root, fl, "Blossoms")
    return root


# ============================================================================ HAMMOCK
def build_hammock():
    rnd = random.Random(27)
    root = C.empty("Hammock")
    wood, woodd = M("Wood", rough=0.8), M("WoodDark", rough=0.8)
    rope = ROPE()
    PX = 0.8
    parts = []
    for sx in (-1, 1):
        x = sx * PX
        parts.append(C.cyl("post", (x, 0, 0), r=0.06, h=1.14, mat=wood, seg=12, base=True, bevel=0.015, bseg=1))
        parts.append(C.sphere("pcap", (x, 0, 1.15), r=0.068, scale=(1, 1, 0.6), mat=woodd, seg=12, rings=6))
        parts.append(C.cyl("pbase", (x, 0, 0), r=0.085, r2=0.07, h=0.07, mat=woodd, seg=12, base=True, bevel=0.012, bseg=1))
        parts.append(C.torus("wrap", (x, 0, 0.98), R=0.066, r=0.016, mat=rope, seg=16, mseg=6))
        parts.append(C.torus("wrap", (x, 0, 1.01), R=0.066, r=0.016, mat=rope, seg=16, mseg=6))
    attach(root, parts, "HammockPosts")
    # fabric: trough sagging between the posts
    zE, S, CU, HL, HW = 0.74, 0.34, 0.1, 0.52, 0.25
    nu, nv = 26, 12
    stripe = [M("RoofTeal", rough=0.85), M("Cream", rough=0.85), M("Coral", rough=0.85)]
    band = [0, 0, 1, 1, 2, 1, 1, 2, 1, 1, 0, 0]
    bm = bmesh.new()
    grid = []
    for i in range(nu + 1):
        u = -1 + 2 * i / nu
        row = []
        for j in range(nv + 1):
            v = -1 + 2 * j / nv
            w = HW * (1 - 0.8 * abs(u) ** 2.5)
            z = zE - S * (1 - u * u) + CU * v * v * (1 - u * u) ** 0.5
            row.append(bm.verts.new((u * HL, v * w, z)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            f.material_index = band[j]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    fab = C.mk("fabric", bm, stripe)
    sol = fab.modifiers.new("Sol", 'SOLIDIFY')
    sol.thickness = 0.016
    sol.offset = 0.0
    C.apply_mods(fab)
    C.shade(fab, 60)
    hp = [fab]
    for sx in (-1, 1):
        end = Vector((sx * HL, 0, zE))
        ring = Vector((sx * (PX - 0.066), 0, 0.99))
        hp.append(C.sphere("knot", end, r=0.035, mat=rope, seg=10, rings=6))
        for dy in (-0.045, 0.0, 0.045):
            hp.append(C.tube("cord", [end + Vector((sx * 0.01, dy, 0)), ring], r=0.008, mat=rope, seg=4, res=1))
    # pillow at the -X end
    u = -0.62
    zf = zE - S * (1 - u * u)
    slope = math.degrees(math.atan(2 * S * u / HL))
    pil = C.box("pillow", (0, 0, 0), (0.18, 0.28, 0.08), mat=M("Cream", rough=0.85), bevel=0.035, bseg=3)
    pil.data.transform(C.xform(rot=(0, -slope, 0)))
    pil.location = (u * HL, 0, zf + 0.06)
    hp.append(pil)
    attach(root, hp, "HammockBed")
    return root


# ============================================================================ EXPANSION ISLANDS
ISLE_R0 = 3.74
FLAT_R = 3.32
ISLE_SEG = 88
ISLE_DEPTH = 3.3
ISLE_Z0 = -0.53
ISLE_BAND_EDGES = [0.0, 0.14, 0.33, 0.55, 0.78, 1.0]
ISLE_TIP = Vector((0.15, -0.1, 0))


class Isle:
    def __init__(self, ph, nz, bands, top="Grass", lip="GrassDark", sand_top=False, drip=0.14):
        self.ph, self.nz, self.bands, self.top, self.lip, self.sand_top, self.drip = ph, nz, bands, top, lip, sand_top, drip

    def R(self, t):
        p = self.ph
        return ISLE_R0 * (1 + 0.018 * math.sin(2 * t + 0.6 + p) + 0.012 * math.sin(3 * t + 2.1 + 1.7 * p)
                          + 0.007 * math.sin(5 * t + 4.0 + 0.5 * p))

    def band_of(self, u):
        E = ISLE_BAND_EDGES
        for k in range(5):
            if u < E[k + 1] or k == 4:
                return k, max(0.0, min(1.0, (u - E[k]) / (E[k + 1] - E[k])))

    def under_r(self, t, u):
        u1 = min(u, 1)
        shape = 0.05 + 0.95 * (1 - u1) ** 0.9 * (1 + 0.45 * u1 * (1 - u1))
        bulge = 0.05 * math.sin(math.pi * self.band_of(u)[1]) ** 0.6
        base = (self.R(t) - 0.1) * shape * (1 + bulge)
        x, y = math.cos(t), math.sin(t)
        z = ISLE_Z0 - ISLE_DEPTH * u
        n1 = noise.noise(Vector((x * 1.6, y * 1.6, z * 0.5 + self.nz)))
        n2 = noise.noise(Vector((x * 4.5, y * 4.5, z * 1.2 + 9.0 + self.nz)))
        return base * (1 + 0.09 * n1 + 0.035 * n2 * min(1, u * 4))

    def under_z(self, t, u):
        x, y = math.cos(t), math.sin(t)
        return ISLE_Z0 - ISLE_DEPTH * u + 0.18 * noise.noise(Vector((x * 2.2, y * 2.2, u * 3 + 17 + self.nz))) * min(1, u * 6)

    def under_pt(self, t, u, inset=1.0):
        r = self.under_r(t, u) * inset
        off = ISLE_TIP * (u ** 2)
        return Vector((r * math.cos(t) + off.x, r * math.sin(t) + off.y, self.under_z(t, u)))

    def lump(self, t):
        x, y = math.cos(t), math.sin(t)
        return 0.035 * max(0.0, noise.noise(Vector((x * 2.5, y * 2.5, 0.7 + self.nz))) + 0.1)

    def sand_edge(self, t):
        p = self.ph
        return 3.02 + 0.13 * math.sin(4 * t + p) + 0.07 * math.sin(7 * t + 2 * p) + 0.03 * math.sin(13 * t)


def isle_body(isle, name):
    mats = [C.mat(isle.top, rough=0.9), C.mat(isle.lip, rough=0.9)] + [C.mat(n, rough=0.9) for n in dict.fromkeys(isle.bands)]
    if isle.sand_top:
        mats.append(C.mat("Grass", rough=0.9))
    mi = {m.name: i for i, m in enumerate(mats)}
    bm = bmesh.new()
    S = ISLE_SEG
    ang = [TAU * i / S for i in range(S)]
    rings = []
    center = bm.verts.new((0, 0, 0))
    inner = "Grass"
    for r in (0.9, 1.8, 2.5):
        rings.append(([bm.verts.new((r * math.cos(t), r * math.sin(t), 0)) for t in ang], mi[inner]))
    if isle.sand_top:
        rings.append(([bm.verts.new((isle.sand_edge(t) * math.cos(t), isle.sand_edge(t) * math.sin(t), 0)) for t in ang], mi[inner]))
        rings.append(([bm.verts.new((FLAT_R * math.cos(t), FLAT_R * math.sin(t), 0)) for t in ang], mi[isle.top]))
    else:
        rings.append(([bm.verts.new((FLAT_R * math.cos(t), FLAT_R * math.sin(t), 0)) for t in ang], mi[inner]))
    rim = [(-0.24, 0.0, isle.top, 0.5, 0), (-0.12, 0.0, isle.top, 1.0, 0), (-0.04, -0.045, isle.top, 0.3, 0),
           (0.03, -0.14, isle.top, 0, 0), (0.08, -0.27, isle.lip, 0, 0.2), (0.09, -0.39, isle.lip, 0, 0.7),
           (0.03, -0.49, isle.lip, 0, 1.0), (-0.08, -0.54, isle.lip, 0, 0.8)]
    for (d, z, m, lw, dw) in rim:
        ring = []
        for t in ang:
            drip = isle.drip * max(0.0, math.sin(13 * t + 2 * noise.noise(Vector((math.cos(t) * 3, math.sin(t) * 3, 1.1 + isle.nz))))) ** 3
            rr = isle.R(t) + d
            ring.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), z + isle.lump(t) * lw - drip * dw)))
        rings.append((ring, mi[m]))
    rows = []
    E = ISLE_BAND_EDGES
    for k in range(5):
        for fr in (0.0, 0.15, 0.5, 0.82):
            rows.append((E[k] + (E[k + 1] - E[k]) * fr, k))
    rows = rows[1:] + [(0.95, 4)]
    for (u, k) in rows:
        rings.append(([bm.verts.new(isle.under_pt(t, u)) for t in ang], mi[isle.bands[k]]))
    tip = bm.verts.new((ISLE_TIP.x, ISLE_TIP.y, ISLE_Z0 - ISLE_DEPTH - 0.25))
    for i in range(S):
        f = bm.faces.new((center, rings[0][0][i], rings[0][0][(i + 1) % S]))
        f.material_index = mi[inner]
    for k in range(len(rings) - 1):
        a, b = rings[k][0], rings[k + 1][0]
        m = rings[k + 1][1]
        for i in range(S):
            f = bm.faces.new((a[i], b[i], b[(i + 1) % S], a[(i + 1) % S]))
            f.material_index = m
    last = rings[-1][0]
    for i in range(S):
        f = bm.faces.new((last[i], tip, last[(i + 1) % S]))
        f.material_index = mi[isle.bands[-1]]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C.mk(name, bm, mats)
    C.shade(o, 55)
    return o


def isle_root(isle, rnd, t, length, mat="WoodDark"):
    u0 = 0.02
    d = Vector((math.cos(t), math.sin(t), 0))
    start = isle.under_pt(t, u0) - d * 0.05 - Vector((0, 0, 0.05))
    pts = [start]
    p = start.copy()
    for i in range(5):
        p = p + d * (0.1 if i < 2 else 0.03) + Vector((rnd.uniform(-0.07, 0.07), rnd.uniform(-0.07, 0.07), -length / 5))
        pts.append(p.copy())
    return C.tube("root", pts, r=0.065, radii=[1, 0.85, 0.65, 0.45, 0.3, 0.15], mat=C.mat(mat, rough=0.9), seg=6, res=4)


def isle_vine(isle, rnd, t, length):
    d = Vector((math.cos(t), math.sin(t), 0))
    Rt = isle.R(t)
    pts = [d * (Rt - 0.22), d * (Rt + 0.02) + Vector((0, 0, -0.1)), d * (Rt + 0.13) + Vector((0, 0, -0.38))]
    p = pts[-1].copy()
    for i in range(4):
        side = Vector((-d.y, d.x, 0)) * (0.06 * (1 if i % 2 else -1))
        p = p + side + Vector((0, 0, -length / 4)) - d * 0.03
        pts.append(p.copy())
    parts = [C.tube("vine", pts, r=0.025, mat=C.mat("LeafDark", rough=0.85), seg=5, res=4)]
    for i in range(2, len(pts)):
        for k in (0, 1):
            q = pts[i] + (pts[i - 1] - pts[i]) * (0.3 + 0.4 * k)
            lf = C.leaf("vl", length=0.17, width=0.07, thick=0.011, curl=0.02, mat=C.mat("Leaf", rough=0.8), seg=8, rings=5)
            a = math.degrees(t) + (70 if (i + k) % 2 else -70) + rnd.uniform(-20, 20)
            lf.data.transform(C.xform(rot=(rnd.uniform(-20, 20), 30, a)))
            lf.location = q + d * 0.02
            C.bake_transform(lf)
            parts.append(lf)
    return C.join(parts)


def isle_underside(isle, rnd, rocks, roots, vines, rock_mats=("Rock", "RockDark")):
    parts = []
    for (t, u, s) in rocks:
        rk = I.rock("rk", rnd, s, mats=rock_mats, flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.data.transform(C.xform(rot=(rnd.uniform(-30, 30), rnd.uniform(-30, 30), 0), scale=(1, 1, 1.3)))
        rk.location = isle.under_pt(t, u, 0.97)
        C.bake_transform(rk)
        parts.append(rk)
    for (dx, dy, dz, s) in ((0.2, 0.05, -3.55, 0.42), (-0.2, 0.18, -3.3, 0.36), (0.05, -0.25, -3.15, 0.34)):
        rk = I.rock("rt", rnd, s, mats=(rock_mats[1], rock_mats[1]), flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.location = (dx + ISLE_TIP.x, dy + ISLE_TIP.y, dz)
        C.bake_transform(rk)
        parts.append(rk)
    for t, L in roots:
        parts.append(isle_root(isle, rnd, t, L))
    for t, L in vines:
        parts.append(isle_vine(isle, rnd, t, L))
    return parts


def rim_spots(isle, rnd, n, placed, sep, rmin=3.45, off=0.14):
    out = []
    tries = 0
    while len(out) < n and tries < 5000:
        tries += 1
        t = rnd.uniform(0, TAU)
        rmax = isle.R(t) - off
        if rmax <= rmin:
            continue
        r = rnd.uniform(rmin, rmax)
        x, y = r * math.cos(t), r * math.sin(t)
        if any(math.hypot(x - a, y - b) < sep for a, b in placed):
            continue
        placed.append((x, y))
        out.append((x, y))
    return out


def float_rock(name, size, seed, mats):
    """Mini floating chunk (like a_island.float_rock) with a configurable top/strata."""
    rnd = random.Random(seed)
    ms = [C.mat(m, rough=0.9) for m in mats]
    wob = lambda t, z: 1 + 0.08 * math.sin(3 * t + seed) + 0.05 * math.sin(5 * t + 2 * seed)
    prof = [(0, 0.06), (0.6, 0.05), (0.92, 0.0), (1.0, -0.1), (0.9, -0.18), (0.82, -0.3), (0.7, -0.55), (0.45, -0.85), (0.2, -1.1), (0, -1.25)]
    o = C.lathe(name, [(r * size, z * size) for r, z in prof], seg=28, mats=ms, mat_idx=[0, 0, 1, 1, 2, 2, 3, 3, 3], rfun=wob, sharp=60)
    C.jitter(o, 0.05 * size, 2.0, seed)
    return o


def add_float_rocks(root, specs, maker):
    for name, pos, size, seed in specs:
        fr = maker(name, size, seed)
        fr.location = pos
        C.update()
        mn, mx = C.world_bbox([fr])
        C.set_origin(fr, (mn + mx) / 2)
        C.set_parent(fr, root)


def build_isle_meadow():
    rnd = random.Random(52)
    root = C.empty("IsleMeadow")
    isle = Isle(ph=1.3, nz=5.0, bands=["Dirt", "DirtDeep", "Rock", "DirtDeep", "RockDark"])
    body = isle_body(isle, "IsleBody")
    C.update()
    parts = isle_underside(isle, rnd,
                           rocks=[(-1.1, 0.34, 0.5), (-2.3, 0.5, 0.42), (-0.2, 0.58, 0.45), (1.0, 0.3, 0.55), (2.5, 0.44, 0.48),
                                  (3.7, 0.3, 0.45), (-1.7, 0.72, 0.36), (0.5, 0.76, 0.33)],
                           roots=[(-1.3, 1.3), (-2.1, 0.9), (-0.6, 1.1), (0.5, 1.4), (2.8, 1.1), (1.9, 1.2)],
                           vines=[(-1.65, 1.2), (-0.35, 0.9), (1.2, 1.1), (-2.6, 1.3), (2.3, 1.0)])
    placed = []
    for (x, y) in rim_spots(isle, rnd, 24, placed, 0.42):
        z, n = I.surface_z(body, x, y)
        if z is not None:
            parts.append(tuft(rnd, x, y, s=rnd.uniform(0.9, 1.25), z=z))
    cols = ["White", "FlowerYellow", "Blossom", "Purple", "White", "BlossomDeep"]
    for i, (cx, cy) in enumerate(rim_spots(isle, rnd, 8, placed, 0.5)):
        for k in range(3):
            a = rnd.uniform(0, TAU)
            x, y = cx + 0.12 * math.cos(a), cy + 0.12 * math.sin(a)
            if math.hypot(x, y) < 3.42:
                continue
            z, n = I.surface_z(body, x, y)
            if z is None:
                continue
            fl = I.tiny_flower(rnd, cols[i % len(cols)])
            s = rnd.uniform(1.3, 1.6)
            fl.data.transform(C.xform(scale=(s, s, s), rot=(0, 0, rnd.uniform(0, 360))))
            fl.location = (x, y, z + 0.006)
            C.bake_transform(fl)
            parts.append(fl)
    for (x, y) in rim_spots(isle, rnd, 7, placed, 0.4):
        z, n = I.surface_z(body, x, y)
        if z is not None:
            rk = I.rock("st", rnd, rnd.uniform(0.07, 0.13), sub=1)
            rk.location = (x, y, z + 0.01)
            C.bake_transform(rk)
            parts.append(rk)
    decor = attach(root, parts, "IsleDecor")
    C.set_parent(body, root)
    add_float_rocks(root, [("FloatRock1", (-4.9, 1.4, -1.3), 0.6, 23), ("FloatRock2", (4.6, -2.0, -1.9), 0.46, 29)],
                    lambda n, s, sd: I.float_rock(n, s, sd))
    return root


def shell(rnd, col):
    o = C.lathe("shell", [(0, 0), (0.045, 0.0), (0.035, 0.02), (0.0, 0.028)], seg=12, mat=C.mat(col, rough=0.6),
                rfun=lambda t, z: (0.75 + 0.25 * abs(math.cos(3 * t))) * (0.7 + 0.3 * math.cos(t) ** 2), sharp=70)
    return o


def starfish(col):
    pts = []
    for k in range(10):
        a = TAU * k / 10 + math.pi / 2
        r = 0.075 if k % 2 == 0 else 0.03
        pts.append((r * math.cos(a), r * math.sin(a)))
    bm = bmesh.new()
    top = [bm.verts.new((x, y, 0.018)) for x, y in pts]
    bot = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    c = bm.verts.new((0, 0, 0.03))
    for i in range(10):
        j = (i + 1) % 10
        bm.faces.new((top[i], top[j], c))
        bm.faces.new((bot[i], top[i], top[j], bot[j]))
    bm.faces.new(list(reversed(bot)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C.mk("star", bm, [C.mat(col, rough=0.7)])
    C.add_bevel(o, 0.006, 1, limit=True, angle=40)
    C.apply_mods(o)
    C.shade(o, 50)
    return o


def beach_grass(rnd, s=1.0):
    parts = []
    nb = rnd.randint(4, 6)
    for i in range(nb):
        a = TAU * i / nb + rnd.uniform(-0.4, 0.4)
        h = rnd.uniform(0.22, 0.36) * s
        b = C.cyl("bg", r=0.022 * s, r2=0.0, h=h, seg=5, base=True, mat=C.mat("Reed", rough=0.9), scale=(1, 0.55, 1), smooth=False)
        b.data.transform(C.xform(rot=(0, rnd.uniform(14, 30), math.degrees(a))))
        b.data.transform(Matrix.Translation((math.cos(a) * 0.02 * s, math.sin(a) * 0.02 * s, -0.01)))
        parts.append(b)
    t = C.join(parts, "bgrass")
    C.shade(t, 50)
    return t


def build_isle_beach():
    rnd = random.Random(64)
    root = C.empty("IsleBeach")
    M("Sand", rough=0.92)
    M("SandWet", "D7BE8E", rough=0.9)
    M("Sandstone", "D4B383", rough=0.9)
    M("SandstoneDark", "B08A5E", rough=0.9)
    M("RockWarm", "CDB89A", rough=0.9)
    M("RockWarmDark", "9E8B73", rough=0.9)
    isle = Isle(ph=3.9, nz=11.0, bands=["Sandstone", "SandstoneDark", "RockWarm", "SandstoneDark", "RockWarmDark"],
                top="Sand", lip="SandWet", sand_top=True, drip=0.06)
    body = isle_body(isle, "IsleBody")
    C.update()
    parts = isle_underside(isle, rnd,
                           rocks=[(-0.9, 0.36, 0.5), (-2.0, 0.52, 0.44), (0.2, 0.6, 0.42), (1.4, 0.32, 0.52), (2.7, 0.46, 0.46),
                                  (4.0, 0.28, 0.44), (-1.4, 0.74, 0.34), (0.9, 0.72, 0.34)],
                           roots=[(-1.0, 1.1), (0.3, 0.9), (2.4, 1.2), (-2.3, 0.9)],
                           vines=[(-1.9, 1.0), (0.9, 0.8)],
                           rock_mats=("RockWarm", "RockWarmDark"))
    placed = []
    for (x, y) in rim_spots(isle, rnd, 30, placed, 0.3, rmin=3.4, off=0.1):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        s = rnd.uniform(0.045, 0.085)
        parts.append(stone("pb", rnd, rnd.choice(["Pebble", "Pebble", "Rock", "RockWarm", "White"]), (s * 1.25, s, s * 0.6),
                           rnd.uniform(0, 180), (x, y, z + s * 0.25), rnd.randint(0, 999), floor=-0.45))
    for (x, y) in rim_spots(isle, rnd, 10, placed, 0.45, rmin=3.42):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        g = beach_grass(rnd, s=rnd.uniform(0.9, 1.2))
        g.location = (x, y, z)
        C.bake_transform(g)
        parts.append(g)
    for i, (x, y) in enumerate(rim_spots(isle, rnd, 7, placed, 0.35, rmin=3.4)):
        z, n = I.surface_z(body, x, y)
        if z is None:
            continue
        sh = shell(rnd, ["BlossomLight", "Cream", "Coral"][i % 3]) if i != 3 else starfish("Coral")
        s = rnd.uniform(1.0, 1.3)
        sh.data.transform(C.xform(scale=(s, s, s), rot=(0, 0, rnd.uniform(0, 360))))
        sh.location = (x, y, z)
        C.bake_transform(sh)
        parts.append(sh)
    # a driftwood log on the rim
    t = 0.9
    d = Vector((math.cos(t), math.sin(t), 0))
    p = d * 3.52
    z, n = I.surface_z(body, p.x, p.y)
    dw = C.cyl("drift", (0, 0, 0), r=0.055, h=0.5, rot=(0, 90, 0), mat=M("Driftwood", "C9B79C", rough=0.9), seg=8, bevel=0.015, bseg=1)
    C.paint_faces(dw, M("WoodLight", rough=0.8), lambda c, n: abs(n.x) > 0.85)
    dw.data.transform(C.xform(rot=(0, 0, math.degrees(t) + 90)))
    dw.location = (p.x, p.y, (z or 0) + 0.045)
    C.bake_transform(dw)
    parts.append(dw)
    attach(root, parts, "IsleDecor")
    C.set_parent(body, root)
    add_float_rocks(root, [("FloatRock1", (-4.8, -1.2, -1.4), 0.58, 37), ("FloatRock2", (4.5, 2.1, -2.0), 0.44, 41)],
                    lambda n, s, sd: float_rock(n, s, sd, ["Sand", "SandWet", "Sandstone", "RockWarm"]))
    return root


# ============================================================================ ROPE BRIDGE
def build_bridge():
    rnd = random.Random(71)
    root = C.empty("Bridge")
    L, SAG, W = 6.0, 0.25, 0.78
    rope = ROPE()
    woods = [M("Wood", rough=0.8), M("Wood", rough=0.8), M("WoodLight", rough=0.8), M("WoodDark", rough=0.8)]
    zb = lambda y: -SAG * 4 * (-y / L) * (1 + y / L)
    dz = lambda y: (zb(y + 0.001) - zb(y - 0.001)) / 0.002
    parts = []
    n = 26
    PD, PT = 0.19, 0.045
    for i in range(n):
        yc = -(PD / 2 + i * (L - PD) / (n - 1))
        ang = math.degrees(math.atan(dz(yc)))
        pl = C.box("plank", (0, 0, 0), (W * rnd.uniform(0.94, 1.0), PD, PT), mat=woods[i * 7 % 4 if i % 3 else 0], bevel=0.014, bseg=2)
        pl.data.transform(C.xform(rot=(ang, 0, rnd.uniform(-2.5, 2.5))))
        nrm = Vector((0, -math.sin(math.radians(ang)), math.cos(math.radians(ang))))
        pl.location = Vector((rnd.uniform(-0.02, 0.02), yc, zb(yc))) + nrm * (PT / 2)
        parts.append(pl)
    ys = [-L * k / 24 for k in range(25)]
    for sx in (-1, 1):
        # stringer ropes under the plank ends
        parts.append(C.tube("string", [(sx * (W / 2 - 0.06), y, zb(y) - 0.012) for y in ys], r=0.02, mat=rope, seg=6, res=3))
        # handrail rope between the posts
        zh = lambda y: 0.86 - (SAG + 0.08) * 4 * (-y / L) * (1 + y / L)
        hy = [-0.07 - (L - 0.14) * k / 24 for k in range(25)]
        parts.append(C.tube("rail", [(sx * 0.47, y, zh(y)) for y in hy], r=0.022, mat=rope, seg=6, res=3))
        # hangers
        for k in range(1, 13):
            y = -0.07 - (L - 0.14) * k / 13
            parts.append(C.tube("hang", [(sx * 0.465, y, zh(y)), (sx * (W / 2 - 0.02), y, zb(y) + 0.03)], r=0.009, mat=rope, seg=4, res=1))
        # posts at both ends
        for y in (-0.07, -L + 0.07):
            parts.append(C.cyl("post", (sx * 0.47, y, 0), r=0.055, h=0.92, mat=M("WoodDark", rough=0.8), seg=10, base=True, bevel=0.012, bseg=1))
            parts.append(C.cyl("ptop", (sx * 0.47, y, 0.92), r=0.06, r2=0.03, h=0.06, mat=M("WoodDark", rough=0.8), seg=10, base=True))
            parts.append(C.torus("wrap", (sx * 0.47, y, 0.86), R=0.06, r=0.016, mat=rope, seg=14, mseg=6))
            parts.append(C.torus("wrap", (sx * 0.47, y, 0.1), R=0.06, r=0.014, mat=rope, seg=14, mseg=6))
    attach(root, parts, "BridgeBody")
    return root

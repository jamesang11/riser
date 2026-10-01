"""Floating sky-island diorama (hero asset)."""
import math, random
from mathutils import Vector, Matrix, noise
import common as C

SEG = 112
RIM_IN = 0.62              # width of the rim zone (flat top ends at R - RIM_IN)

SLOTS = {  # name: (x, y, r)
    "home": (0, 0.6, 1.4), "campfire": (1.8, -1.6, 0.9), "lamppost": (-1.4, -2.4, 0.9),
    "treeA": (-3.2, 1.2, 0.9), "treeB": (3.2, 1.6, 0.9), "garden": (-2.6, -0.8, 1.0),
    "pond": (2.6, -0.2, 1.1), "windmill": (-1.6, 3.2, 1.1), "bench": (0.2, -2.9, 0.9),
    "mailbox": (1.2, -3.4, 0.5), "telescope": (3.3, -2.3, 0.9), "flowers": (-3.5, -2.1, 0.9),
    "lanterns": (0.0, 2.9, 0.9), "pine": (1.8, 3.4, 0.9),
}

def R(t):
    return 6.0 * (1 + 0.045 * math.sin(2 * t + 0.6) + 0.035 * math.sin(3 * t + 2.1)
                  + 0.02 * math.sin(5 * t + 4.0) + 0.012 * math.sin(7 * t + 1.3))

# ---------------------------------------------------------------- path
PATH_CTRL = [(0.1, -5.45), (0.45, -4.5), (0.74, -3.45), (0.62, -2.45), (0.25, -1.6), (0.0, -0.95)]

def catmull(pts, n=12):
    P = [Vector((p[0], p[1], 0)) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out

PATH = catmull(PATH_CTRL, 10)

def path_dist(x, y):
    p = Vector((x, y, 0))
    best = 1e9
    for a, b in zip(PATH[:-1], PATH[1:]):
        ab = b - a
        t = max(0, min(1, (p - a).dot(ab) / ab.length_squared))
        best = min(best, (a + ab * t - p).length)
    return min(best, (Vector((x / 0.75, (y + 0.95) / 0.62, 0))).length * 0.6)   # plaza ellipse

def free(x, y, margin=0.15, path_margin=0.45):
    for (sx, sy, sr) in SLOTS.values():
        if math.hypot(x - sx, y - sy) < sr + margin:
            return False
    if path_dist(x, y) < path_margin:
        return False
    return True

def lump(t):
    x, y = math.cos(t), math.sin(t)
    n = noise.noise(Vector((x * 2.5, y * 2.5, 0.7)))
    v = 0.07 * max(0.0, n + 0.15)
    # keep the path entrance flat
    px, py = R(t) * x, R(t) * y
    if abs(px - 0.2) < 1.0 and py < 0:
        v *= max(0, abs(px - 0.2) - 0.4) / 0.6
    return v

# ---------------------------------------------------------------- underside shape
NB = 5
BAND_MATS = ["Dirt", "DirtDeep", "Rock", "DirtDeep", "RockDark"]
BAND_EDGES = [0.0, 0.14, 0.33, 0.55, 0.78, 1.0]   # uneven strata thickness

def band_of(u):
    for k in range(NB):
        if u < BAND_EDGES[k + 1] or k == NB - 1:
            a, b = BAND_EDGES[k], BAND_EDGES[k + 1]
            return k, max(0.0, min(1.0, (u - a) / (b - a)))
DEPTH = 5.6
Z0 = -0.62

def under_r(t, u):
    """radius of the underside at angle t, depth fraction u (0 under lip, 1 tip)."""
    u1 = min(u, 1)
    shape = (1 - u1) ** 0.95 * (1 + 0.45 * u1 * (1 - u1)) * (1 - 0.08 * math.sin(math.pi * min(1, u1 * 3)) ** 2 * 0)
    shape = 0.05 + 0.95 * shape
    frac = (band_of(u)[1])
    bulge = 0.05 * math.sin(math.pi * frac) ** 0.6
    base = (R(t) - 0.12) * shape * (1 + bulge)
    x, y = math.cos(t), math.sin(t)
    z = Z0 - DEPTH * u
    n1 = noise.noise(Vector((x * 1.6, y * 1.6, z * 0.35 + 3.0)))
    n2 = noise.noise(Vector((x * 4.5, y * 4.5, z * 0.9 + 9.0)))
    return base * (1 + 0.09 * n1 + 0.035 * n2 * min(1, u * 4))

def under_z(t, u):
    x, y = math.cos(t), math.sin(t)
    return Z0 - DEPTH * u + 0.25 * noise.noise(Vector((x * 2.2, y * 2.2, u * 3 + 17))) * min(1, u * 6)

TIP_OFF = Vector((0.25, 0.15, 0))

def build_body():
    import bmesh
    mats = [C.mat("Grass", rough=0.9), C.mat("GrassDark", rough=0.9)] + [C.mat(n, rough=0.9) for n in dict.fromkeys(BAND_MATS)]
    mi = {m.name: i for i, m in enumerate(mats)}
    bm = bmesh.new()
    angles = [2 * math.pi * i / SEG for i in range(SEG)]
    rings = []   # (verts, material index for faces BELOW this ring)
    center = bm.verts.new((0, 0, 0))
    # flat top
    for f in (0.3, 0.6, 0.85, 1.0):
        rings.append(([bm.verts.new(((R(t) - RIM_IN) * f * math.cos(t), (R(t) - RIM_IN) * f * math.sin(t), 0)) for t in angles], mi["Grass"]))
    # rim + lip (offset from R, z, material, lump weight, drip weight)
    rim = [(-0.40, 0.0, "Grass", 1.0, 0), (-0.2, 0.0, "Grass", 0.8, 0), (-0.06, -0.05, "Grass", 0.2, 0),
           (0.03, -0.17, "Grass", 0, 0), (0.1, -0.33, "GrassDark", 0, 0.2), (0.11, -0.47, "GrassDark", 0, 0.7),
           (0.04, -0.58, "GrassDark", 0, 1.0), (-0.1, -0.64, "GrassDark", 0, 0.8)]
    for (d, z, m, lw, dw) in rim:
        ring = []
        for t in angles:
            drip = 0.17 * max(0.0, math.sin(15 * t + 2 * noise.noise(Vector((math.cos(t) * 3, math.sin(t) * 3, 1.1))))) ** 3
            zz = z + lump(t) * lw - drip * dw
            rr = R(t) + d
            ring.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), zz)))
        rings.append((ring, mi[m]))
    # underside strata
    rows = []
    for k in range(NB):
        a, b = BAND_EDGES[k], BAND_EDGES[k + 1]
        for fr in (0.0, 0.15, 0.5, 0.82):
            rows.append((a + (b - a) * fr, k))
    rows = rows[1:]  # first row coincides with the lip bottom
    rows.append((0.95, NB - 1))
    for (u, k) in rows:
        ring = []
        for t in angles:
            r = under_r(t, u)
            off = TIP_OFF * (u ** 2)
            ring.append(bm.verts.new((r * math.cos(t) + off.x, r * math.sin(t) + off.y, under_z(t, u))))
        rings.append((ring, mi[BAND_MATS[k]]))
    tip = bm.verts.new((TIP_OFF.x, TIP_OFF.y, Z0 - DEPTH - 0.35))
    # faces
    for i in range(SEG):
        f = bm.faces.new((center, rings[0][0][i], rings[0][0][(i + 1) % SEG]))
        f.material_index = mi["Grass"]
    for k in range(len(rings) - 1):
        a, b = rings[k][0], rings[k + 1][0]
        m = rings[k + 1][1] if k + 1 < len(rings) else rings[k][1]
        # material: faces take the material of the lower ring, except rim faces use the upper-ring def
        for i in range(SEG):
            f = bm.faces.new((a[i], b[i], b[(i + 1) % SEG], a[(i + 1) % SEG]))
            f.material_index = m
    last = rings[-1][0]
    for i in range(SEG):
        f = bm.faces.new((last[i], tip, last[(i + 1) % SEG]))
        f.material_index = mi[BAND_MATS[-1]]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C.mk("IslandBody", bm, mats)
    C.shade(o, 55)
    return o

# ---------------------------------------------------------------- decor
def surface_z(body, x, y):
    ok, loc, n, _ = body.ray_cast(Vector((x, y, 3)), Vector((0, 0, -1)))
    return (loc.z, n) if ok else (None, None)

def grass_tuft(name, rnd, s=1.0):
    parts = []
    nb = rnd.randint(3, 5)
    for i in range(nb):
        a = 2 * math.pi * i / nb + rnd.uniform(-0.4, 0.4)
        h = rnd.uniform(0.13, 0.24) * s
        b = C.cyl("b", r=0.035 * s, r2=0.0, h=h, seg=5, base=True, mat=C.mat("GrassTuft", rough=0.9),
                  scale=(1, 0.55, 1), smooth=False)
        tilt = rnd.uniform(18, 34)
        b.data.transform(C.xform(rot=(0, tilt, math.degrees(a))))
        b.data.transform(Matrix.Translation((math.cos(a) * 0.025 * s, math.sin(a) * 0.025 * s, -0.01)))
        parts.append(b)
    t = C.join(parts, name)
    C.shade(t, 50)
    return t

def tiny_flower(rnd, col):
    petal = C.lathe("fp", [(0, 0.0), (0.045, 0.012), (0.0, 0.02)], seg=15, mat=C.mat(col),
                    rfun=lambda t, z: 0.55 + 0.45 * abs(math.cos(2.5 * t)) ** 0.6, sharp=80)
    ctr = C.sphere("fc", r=0.018, seg=6, rings=3, mat=C.mat("FlowerYellow"), scale=(1, 1, 0.6), loc=(0, 0, 0.02))
    C.bake_transform(ctr)
    f = C.join([petal, ctr])
    f.data.transform(Matrix.Translation(-f.location))
    f.location = (0, 0, 0)
    return f

def rock(name, rnd, size, mats=("Rock", "RockDark"), sub=2, flat_bottom=True, jit=0.25, sharp=180):
    o = C.ico(name, r=1.0, sub=sub, mat=C.mat(mats[0], rough=0.9))
    C.jitter(o, jit, 1.1, rnd.randint(0, 999))
    sc = (size * rnd.uniform(0.9, 1.2), size * rnd.uniform(0.8, 1.1), size * rnd.uniform(0.55, 0.8))
    o.data.transform(C.xform(scale=sc, rot=(0, 0, rnd.uniform(0, 360))))
    if flat_bottom:
        for v in o.data.vertices:
            if v.co.z < -sc[2] * 0.3:
                v.co.z = -sc[2] * 0.3
    if len(mats) > 1:
        C.paint_faces(o, C.mat(mats[1], rough=0.9), lambda c, n: n.z < -0.2)
    C.shade(o, sharp)
    return o

def build_path(body):
    sand = C.mat("Sand", rough=0.92)
    import bmesh
    bm = bmesh.new()
    rows = []
    n = len(PATH)
    for i, p in enumerate(PATH):
        a = PATH[max(0, i - 1)]; b = PATH[min(n - 1, i + 1)]
        tang = (b - a).normalized()
        nrm = Vector((-tang.y, tang.x, 0))
        w = 0.58 + 0.06 * math.sin(i * 0.9)
        if i < 4:
            w *= 0.75 + 0.25 * i / 4
        prof = [(-w / 2 - 0.06, -0.02), (-w / 2, 0.013), (-w / 4, 0.018), (w / 4, 0.018), (w / 2, 0.013), (w / 2 + 0.06, -0.02)]
        rows.append([bm.verts.new(p + nrm * o + Vector((0, 0, z))) for o, z in prof])
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for j in range(len(r0) - 1):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
    bm.faces.new(list(reversed(rows[0])))
    o = C.mk("path", bm, [sand])
    plaza = C.lathe("plaza", [(0, 0.019), (0.62, 0.016), (0.72, 0.012), (0.8, -0.02)], seg=32, mat=sand,
                    loc=(0, -1.0, 0), scale=(1.15, 0.7, 1))
    C.bake_transform(plaza)
    out = C.join([o, plaza], "path")
    C.shade(out, 40)
    return out

def hanging_root(rnd, t, length):
    u0 = 0.02
    r0 = under_r(t, u0) - 0.05
    d = Vector((math.cos(t), math.sin(t), 0))
    start = d * r0 + Vector((0, 0, under_z(t, u0) - 0.05))
    pts = [start]
    p = start.copy()
    steps = 5
    for i in range(steps):
        p = p + d * (0.12 if i < 2 else 0.03) + Vector((rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), -length / steps))
        pts.append(p.copy())
    return C.tube("root", pts, r=0.075, radii=[1, 0.85, 0.65, 0.45, 0.3, 0.15], mat=C.mat("WoodDark", rough=0.9), seg=6, res=4)

def hanging_vine(rnd, t, length):
    d = Vector((math.cos(t), math.sin(t), 0))
    Rt = R(t)
    pts = [d * (Rt - 0.25) + Vector((0, 0, 0.0)), d * (Rt + 0.02) + Vector((0, 0, -0.12)), d * (Rt + 0.14) + Vector((0, 0, -0.42))]
    p = pts[-1].copy()
    for i in range(4):
        side = Vector((-d.y, d.x, 0)) * (0.07 * (1 if i % 2 else -1))
        p = p + side + Vector((0, 0, -length / 4)) - d * 0.03
        pts.append(p.copy())
    vine = C.tube("vine", pts, r=0.028, mat=C.mat("LeafDark", rough=0.85), seg=5, res=4)
    leaves = [vine]
    for i in range(2, len(pts)):
        for k in (0, 1):
            q = pts[i] + (pts[i - 1] - pts[i]) * (0.3 + 0.4 * k)
            lf = C.leaf("vl", length=0.19, width=0.08, thick=0.012, curl=0.02, mat=C.mat("Leaf", rough=0.8), seg=8, rings=5)
            ang = math.degrees(t) + (70 if (i + k) % 2 else -70) + rnd.uniform(-20, 20)
            lf.data.transform(C.xform(rot=(rnd.uniform(-20, 20), 30, ang)))
            lf.location = q + d * 0.02
            C.bake_transform(lf)
            leaves.append(lf)
    return C.join(leaves)

def float_rock(name, size, seed):
    rnd = random.Random(seed)
    mats = [C.mat("Grass", rough=0.9), C.mat("GrassDark", rough=0.9), C.mat("Dirt", rough=0.9), C.mat("Rock", rough=0.9)]
    wob = lambda t, z: 1 + 0.08 * math.sin(3 * t + seed) + 0.05 * math.sin(5 * t + 2 * seed)
    prof = [(0, 0.06), (0.6, 0.05), (0.92, 0.0), (1.0, -0.1), (0.9, -0.18), (0.82, -0.3), (0.7, -0.55), (0.45, -0.85), (0.2, -1.1), (0, -1.25)]
    o = C.lathe(name, [(r * size, z * size) for r, z in prof], seg=28, mats=mats, mat_idx=[0, 0, 1, 1, 2, 2, 3, 3, 3], rfun=wob, sharp=60)
    C.jitter(o, 0.05 * size, 2.0, seed)
    # a mini tuft on top
    t = grass_tuft(name + "_t", rnd, s=size * 0.9)
    t.location = (0.15 * size, -0.1 * size, 0.05 * size)
    C.bake_transform(t)
    o = C.join([o, t], name)
    return o

def build_island():
    rnd = random.Random(7)
    root = C.empty("Island")
    body = build_body()
    C.update()
    parts = []

    # jutting rocks on the underside + chunky tip cluster
    for (t, u, s) in [(-1.2, 0.36, 0.8), (-2.2, 0.5, 0.65), (-0.3, 0.58, 0.7), (0.9, 0.3, 0.85), (2.4, 0.42, 0.75),
                      (3.6, 0.3, 0.7), (-1.75, 0.7, 0.55), (0.3, 0.75, 0.5), (4.6, 0.62, 0.55), (-0.8, 0.2, 0.6), (-2.7, 0.25, 0.6)]:
        r = under_r(t, u)
        p = Vector((math.cos(t) * r * 0.97, math.sin(t) * r * 0.97, under_z(t, u)))
        rk = rock("rk", rnd, s, mats=("Rock", "RockDark"), flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.data.transform(C.xform(rot=(rnd.uniform(-30, 30), rnd.uniform(-30, 30), 0), scale=(1, 1, 1.3)))
        rk.location = p + TIP_OFF * u * u
        C.bake_transform(rk)
        parts.append(rk)
    for (dx, dy, dz, s) in [(0.3, 0.1, -5.5, 0.55), (-0.25, 0.25, -5.2, 0.5), (0.1, -0.3, -5.0, 0.5)]:
        rk = rock("rt", rnd, s, mats=("RockDark", "RockDark"), flat_bottom=False, sub=1, jit=0.18, sharp=30)
        rk.location = (dx + TIP_OFF.x, dy + TIP_OFF.y, dz)
        C.bake_transform(rk)
        parts.append(rk)

    for t, L in [(-1.35, 1.9), (-2.05, 1.3), (-0.75, 1.5), (0.45, 2.0), (2.9, 1.6), (-2.9, 1.7), (-1.0, 1.1)]:
        parts.append(hanging_root(rnd, t, L))
    for t, L in [(-1.62, 1.7), (-0.45, 1.3), (-2.55, 1.9), (0.95, 1.5), (-1.95, 1.1)]:
        parts.append(hanging_vine(rnd, t, L))

    # top decor
    parts.append(build_path(body))
    placed = []
    def try_place(n, margin, pm, rmin=0.0, rmax_off=0.3, sep=0.35):
        pts = []
        tries = 0
        while len(pts) < n and tries < 5000:
            tries += 1
            t = rnd.uniform(0, 2 * math.pi)
            rr = math.sqrt(rnd.uniform(0, 1)) * (R(t) - rmax_off)
            if rr < rmin:
                continue
            x, y = rr * math.cos(t), rr * math.sin(t)
            if not free(x, y, margin, pm):
                continue
            if any(math.hypot(x - a, y - b) < sep for a, b in placed):
                continue
            placed.append((x, y))
            pts.append((x, y))
        return pts

    # soft lighter-grass patches (flat decals hugging the ground)
    for (x, y) in try_place(12, 0.0, 0.3, rmin=0.5, rmax_off=0.9, sep=1.4):
        sc = rnd.uniform(0.35, 0.7)
        ph = rnd.uniform(0, 6)
        pt = C.lathe("patch", [(0, 0.006), (sc * 0.85, 0.005), (sc, 0.002)], seg=24, mat=C.mat("GrassLight", "86D07A", rough=0.9),
                     rfun=lambda t, z, ph=ph: 1 + 0.18 * math.sin(3 * t + ph) + 0.1 * math.sin(5 * t + 2 * ph), smooth=False)
        pt.data.transform(C.xform(scale=(1, rnd.uniform(0.6, 0.9), 1), rot=(0, 0, rnd.uniform(0, 360))))
        pt.location = (x, y, 0)
        C.bake_transform(pt)
        parts.append(pt)
    placed.clear()
    for i, (x, y) in enumerate(try_place(34, 0.12, 0.45, sep=0.6)):
        z, n = surface_z(body, x, y)
        if z is None:
            continue
        tf = grass_tuft("tuft", rnd, s=rnd.uniform(0.95, 1.35))
        tf.data.transform(C.xform(rot=(0, 0, rnd.uniform(0, 360))))
        tf.location = (x, y, z)
        C.bake_transform(tf)
        parts.append(tf)
    for (x, y) in try_place(16, 0.1, 0.4, sep=0.5):
        z, n = surface_z(body, x, y)
        if z is None:
            continue
        rk = rock("st", rnd, rnd.uniform(0.07, 0.16), sub=1)
        rk.location = (x, y, z + 0.01)
        C.bake_transform(rk)
        parts.append(rk)
    cols = ["White", "FlowerYellow", "Blossom", "Purple", "White", "BlossomDeep"]
    fpts = []
    for i, (cx, cy) in enumerate(try_place(15, 0.25, 0.6, sep=0.6)):
        for k in range(rnd.randint(3, 5)):
            a = rnd.uniform(0, 6.3); d = rnd.uniform(0.05, 0.28)
            fpts.append((cx + d * math.cos(a), cy + d * math.sin(a), cols[i % len(cols)]))
    for (x, y, col) in fpts:
        z, n = surface_z(body, x, y)
        if z is None:
            continue
        fl = tiny_flower(rnd, col)
        s = rnd.uniform(1.3, 1.7)
        fl.data.transform(C.xform(scale=(s, s, s), rot=(rnd.uniform(-10, 10), rnd.uniform(-10, 10), rnd.uniform(0, 360))))
        fl.location = (x, y, z + 0.008)
        C.bake_transform(fl)
        parts.append(fl)
    # pebbles lining the path
    for i in range(6, len(PATH) - 4, 5):
        p = PATH[i]
        a = PATH[i + 1] - PATH[i - 1]
        nrm = Vector((-a.y, a.x, 0)).normalized()
        for side in (-1, 1):
            if rnd.random() < 0.35:
                continue
            q = p + nrm * side * rnd.uniform(0.42, 0.5)
            if not free(q.x, q.y, 0.0, 0.0):
                continue
            rk = rock("pb", rnd, rnd.uniform(0.05, 0.08), mats=("Pebble", "Rock"), sub=1)
            rk.location = (q.x, q.y, 0.01)
            C.bake_transform(rk)
            parts.append(rk)

    decor = C.join(parts, "IslandDecor")
    C.set_origin(decor, (0, 0, 0))
    C.set_parent(body, root)
    C.set_parent(decor, root)

    for name, pos, size, seed in [("FloatRock1", (-7.5, -1.4, -1.7), 1.05, 3), ("FloatRock2", (7.1, 1.9, -2.6), 0.85, 5),
                                  ("FloatRock3", (6.4, -4.4, -2.1), 0.7, 11)]:
        fr = float_rock(name, size, seed)
        fr.location = pos
        C.update()
        mn, mx = C.world_bbox([fr])
        C.set_origin(fr, (mn + mx) / 2)
        C.set_parent(fr, root)
    return root

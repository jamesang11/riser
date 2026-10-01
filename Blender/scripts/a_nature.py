"""Nature: trees, pine, garden, pond, flower patch, clouds."""
import math, random
from mathutils import Vector, Matrix, noise
import common as C


def tone_canopy(o, light, dark, seed=0, up=0.35):
    """Two/three-tone foliage: light on sun-facing tops (noisy), dark underneath."""
    off = Vector((seed * 3.1, seed * 1.7, 0))
    C.paint_faces(o, light, lambda c, n: n.z + 0.12 * noise.noise(c * 1.2 + off) > up)
    if dark:
        C.paint_faces(o, dark, lambda c, n: n.z < -0.55)


def surface_points(o, n, rnd, zmin, zmax, center):
    """Random points on the object's surface via rays from outside toward center."""
    pts = []
    C.update()
    tries = 0
    while len(pts) < n and tries < 500:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi)
        z = rnd.uniform(zmin, zmax)
        d = Vector((math.cos(a), math.sin(a), 0))
        origin = Vector((center.x, center.y, z)) + d * 5
        ok, loc, nrm, _ = o.ray_cast(o.matrix_world.inverted() @ origin, -d)
        if ok:
            p = o.matrix_world @ loc
            if all((p - q).length > 0.3 for q, _ in pts):
                pts.append((p, nrm))
    return pts


def trunk(pts, r, radii, mat="Wood"):
    t = C.tube("trunk", pts, r=r, radii=radii, mat=C.mat(mat, rough=0.85), seg=10, res=5)
    parts = [t]
    for k in range(4):
        a = math.radians(k * 90 + 20)
        parts.append(C.sphere("flare", (r * 1.1 * math.cos(a), r * 1.1 * math.sin(a), 0.05), r=1, scale=(0.14, 0.07, 0.1),
                              rot=(0, -20, k * 90 + 20), mat=C.mat(mat), seg=10, rings=6))
    return C.join(parts, "Trunk")


# ============================================================================ ROUND TREE
def build_tree_round():
    rnd = random.Random(1)
    root = C.empty("TreeRound")
    top = Vector((0.03, 0, 1.12))
    tr = trunk([(0, 0, -0.02), (0.05, 0, 0.4), (-0.04, 0.02, 0.8), tuple(top + Vector((0, 0, 0.25)))], 0.14, [1.25, 1.0, 0.85, 0.7])
    C.set_origin(tr, (0, 0, 0))
    C.set_parent(tr, root)
    c = Vector((0, 0, 1.78))
    spheres = [(c, 0.78), (c + Vector((0.6, 0.05, -0.2)), 0.52), (c + Vector((-0.62, -0.05, -0.18)), 0.54),
               (c + Vector((0.05, 0.55, -0.12)), 0.52), (c + Vector((0.0, -0.58, -0.16)), 0.52),
               (c + Vector((0.32, 0.25, 0.42)), 0.5), (c + Vector((-0.3, -0.2, 0.44)), 0.48), (c + Vector((0.35, -0.35, 0.2)), 0.45),
               (c + Vector((-0.4, 0.35, 0.15)), 0.45)]
    can = C.blob("Canopy", [(p, r) for p, r in spheres], mat=C.mat("Leaf", rough=0.85), voxel=0.045, smooth_iter=5, target=3000)
    tone_canopy(can, C.mat("LeafLight", rough=0.85), None, seed=1, up=0.5)
    apples = []
    for p, nrm in surface_points(can, 7, rnd, 1.3, 2.2, c):
        apples.append(C.sphere("apple", p + nrm * 0.02, r=0.075, scale=(1, 1, 0.9), mat=C.mat("Apple", rough=0.55), seg=12, rings=8))
        apples.append(C.cyl("astem", p + nrm * 0.02 + Vector((0, 0, 0.08)), r=0.008, h=0.05, mat=C.mat("WoodDark"), seg=4))
    can = C.join([can] + apples, "Canopy")
    C.set_origin(can, top)
    C.set_parent(can, root)
    return root


# ============================================================================ BLOSSOM TREE
def build_tree_blossom():
    rnd = random.Random(8)
    root = C.empty("TreeBlossom")
    top = Vector((0.0, 0.02, 1.2))
    tr = trunk([(0, 0, -0.02), (-0.06, 0, 0.35), (0.06, 0.02, 0.75), tuple(top)], 0.16, [1.25, 0.95, 0.8, 0.7], mat="WoodDark")
    br = [C.tube("br", [tuple(top + Vector((0, 0, -0.1))), (0.4, 0.05, 1.45), (0.62, 0.0, 1.6)], r=0.06, radii=[1, 0.7, 0.5], mat=C.mat("WoodDark"), seg=8, res=4),
          C.tube("br", [tuple(top + Vector((0, 0, -0.05))), (-0.35, -0.05, 1.5), (-0.55, 0.05, 1.65)], r=0.055, radii=[1, 0.7, 0.5], mat=C.mat("WoodDark"), seg=8, res=4)]
    tr = C.join([tr] + br, "Trunk")
    C.set_origin(tr, (0, 0, 0))
    C.set_parent(tr, root)
    c = Vector((0, 0, 1.85))
    spheres = [(c, 0.62, (1.25, 1.1, 0.85)), (c + Vector((0.72, 0.0, -0.1)), 0.5), (c + Vector((-0.72, 0.05, -0.08)), 0.5),
               (c + Vector((0.1, 0.55, 0.0)), 0.5), (c + Vector((0.0, -0.55, -0.05)), 0.48), (c + Vector((0.3, 0.2, 0.38)), 0.48),
               (c + Vector((-0.35, -0.15, 0.36)), 0.46), (c + Vector((0.55, -0.4, 0.1)), 0.38), (c + Vector((-0.5, 0.4, 0.1)), 0.4),
               (c + Vector((0.95, 0.1, -0.25)), 0.32), (c + Vector((-0.95, -0.1, -0.2)), 0.32)]
    can = C.blob("Canopy", spheres, mat=C.mat("Blossom", rough=0.85), voxel=0.045, smooth_iter=5, target=3000)
    tone_canopy(can, C.mat("BlossomLight", rough=0.85), None, seed=4, up=0.5)
    # a few little blossom clusters popping out
    extra = []
    for p, nrm in surface_points(can, 0, rnd, 1.4, 2.3, c):
        extra.append(C.sphere("bl", p + nrm * 0.02, r=0.055, mat=C.mat("BlossomDeep"), seg=8, rings=5))
    can = C.join([can] + extra, "Canopy")
    C.set_origin(can, top)
    C.set_parent(can, root)
    # fallen petals
    pet = []
    for i in range(18):
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0.3, 1.2)
        p = C.sphere("pt", (d * math.cos(a), d * math.sin(a), 0.008), r=1, scale=(0.045, 0.03, 0.006), rot=(0, 0, rnd.uniform(0, 180)),
                     mat=C.mat("Blossom" if i % 3 else "BlossomDeep"), seg=8, rings=4)
        pet.append(p)
    po = C.join(pet, "Petals")
    C.set_origin(po, (0, 0, 0))
    C.set_parent(po, root)
    return root


# ============================================================================ PINE
def build_pine():
    root = C.empty("Pine")
    tr = C.cyl("Trunk", (0, 0, 0), r=0.16, r2=0.11, h=0.6, mat=C.mat("WoodDark", rough=0.85), seg=10, base=True, bevel=0.03)
    C.set_parent(tr, root)
    tiers = []
    specs = [(0.95, 0.42, 0.95), (0.78, 0.95, 0.85), (0.6, 1.45, 0.78), (0.42, 1.92, 0.88)]
    for i, (rb, zb, h) in enumerate(specs):
        last = i == len(specs) - 1
        prof = [(0, zb + 0.1), (rb * 0.82, zb), (rb, zb + 0.05), (rb * 0.97, zb + 0.13), (rb * 0.72, zb + 0.28), (rb * 0.42, zb + h * 0.62)]
        prof += [(rb * 0.12, zb + h * 0.95), (0, zb + h)] if last else [(rb * 0.25, zb + h * 0.85), (0, zb + h * 0.88)]
        ph = i * 0.7
        t = C.lathe("tier", prof, seg=24, mat=C.mat("Pine", rough=0.85),
                    rfun=lambda a, z, ph=ph, zb=zb: 1 + 0.07 * math.cos(9 * a + ph) * max(0, 1 - (z - zb) / 0.5), sharp=80)
        C.paint_faces(t, C.mat("PineLight", rough=0.85), lambda c, n: n.z > 0.45 and n.x + n.y * -0.3 > -0.25)
        C.paint_faces(t, C.mat("LeafDark", rough=0.85), lambda c, n: n.z < -0.3)
        tiers.append(t)
    can = C.join(tiers, "Canopy")
    C.set_origin(can, (0, 0, 0.45))
    C.set_parent(can, root)
    return root


# ============================================================================ GARDEN
def build_garden():
    rnd = random.Random(3)
    root = C.empty("Garden")
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    W, D, H = 1.3, 0.8, 0.3
    parts = []
    for sy in (-1, 1):
        for k in range(2):
            parts.append(C.box("pl", (0, sy * D / 2, 0.075 + k * 0.14), (W, 0.07, 0.13), mat=wood, bevel=0.022, bseg=2))
    for sx in (-1, 1):
        for k in range(2):
            parts.append(C.box("pl", (sx * W / 2, 0, 0.075 + k * 0.14), (0.07, D, 0.13), mat=wood, bevel=0.022, bseg=2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.box("cp", (sx * W / 2, sy * D / 2, 0), (0.1, 0.1, H + 0.06), mat=woodd, bevel=0.03, bseg=2, base=True))
    soil = C.box("soil", (0, 0, H - 0.1), (W - 0.04, D - 0.04, 0.14), mat=C.mat("Soil", rough=0.95), bevel=0.03, bseg=2)
    for v in soil.data.vertices:
        if v.co.z > 0.0:
            v.co.z += 0.02 * noise.noise(Vector((v.co.x * 5, v.co.y * 5, 0)))
    parts.append(soil)
    zt = H - 0.02
    # cabbages (front row)
    for i, x in enumerate((-0.4, 0.0, 0.4)):
        cx, cy = x + rnd.uniform(-0.03, 0.03), -0.17
        parts.append(C.sphere("cab", (cx, cy, zt + 0.08), r=0.1, mat=C.mat("Cabbage", rough=0.8), seg=12, rings=8))
        for k in range(6):
            a = k * 60 + rnd.uniform(-10, 10)
            lf = C.sphere("cl", (0, 0, 0), r=1, scale=(0.1, 0.075, 0.02), mat=C.mat("LeafLight", rough=0.8), seg=10, rings=6)
            for v in lf.data.vertices:
                v.co.z += 3 * v.co.x ** 2
            lf.data.transform(C.xform(rot=(0, -35, a)))
            lf.location = (cx + 0.08 * math.cos(math.radians(a)), cy + 0.08 * math.sin(math.radians(a)), zt + 0.05)
            parts.append(lf)
    # carrots (back row)
    for i, x in enumerate((-0.45, -0.15, 0.15, 0.45)):
        cx, cy = x, 0.17
        parts.append(C.cyl("car", (cx, cy, zt - 0.02), r=0.045, r2=0.035, h=0.06, mat=C.mat("Carrot", rough=0.8), seg=10, base=True, bevel=0.01, bseg=1))
        for k in range(3):
            a = math.radians(k * 120 + i * 20)
            p0 = Vector((cx, cy, zt + 0.03))
            p1 = p0 + Vector((0.05 * math.cos(a), 0.05 * math.sin(a), 0.14))
            p2 = p0 + Vector((0.1 * math.cos(a), 0.1 * math.sin(a), 0.24))
            parts.append(C.tube("ct", [p0, p1, p2], r=0.018, radii=[0.7, 1.0, 0.4], mat=C.mat("Leaf", rough=0.8), seg=5, res=3))
    bed = C.join(parts, "GardenBed")
    C.set_origin(bed, (0, 0, 0))
    C.set_parent(bed, root)
    # watering can
    teal = C.mat("RoofTeal", rough=0.7)
    wc = [C.lathe("wcb", [(0, 0), (0.1, 0), (0.11, 0.02), (0.11, 0.17), (0.09, 0.2), (0, 0.2)], seg=16, mat=teal),
          C.tube("spout", [(0.08, 0, 0.05), (0.2, 0, 0.14), (0.27, 0, 0.24)], r=0.018, radii=[1.2, 0.9, 0.8], mat=teal, seg=6, res=3),
          C.cyl("rose", (0.285, 0, 0.255), r=0.035, r2=0.025, h=0.04, rot=(0, -50, 0), mat=C.mat("RoofTealDark"), seg=10),
          C.torus("handle", (-0.02, 0, 0.2), R=0.09, r=0.016, rot=(90, 0, 0), mat=C.mat("RoofTealDark"), seg=14, mseg=6, arc=180)]
    can = C.join(wc, "WateringCan")
    C.set_origin(can, (0, 0, 0))
    can.data.transform(C.xform(rot=(0, 0, 200)))
    can.location = (W / 2 + 0.28, -0.22, 0)
    C.set_parent(can, root)
    return root


# ============================================================================ POND
def build_pond():
    rnd = random.Random(6)
    root = C.empty("Pond")
    R = 0.86
    parts = []
    parts.append(C.lathe("bed", [(0, -0.14), (R * 0.7, -0.12), (R, -0.02), (R + 0.12, 0.012), (0, 0.012)][:4] + [(0, 0.0)], seg=32,
                         mat=C.mat("PondBed", rough=0.9)))
    parts.append(C.lathe("sandring", [(R - 0.05, 0.0), (R + 0.16, 0.0), (R + 0.2, 0.015), (R - 0.05, 0.02)], seg=32, mat=C.mat("Sand", rough=0.9)))
    n = 15
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.06, 0.06)
        s = rnd.uniform(0.85, 1.15)
        st = C.ico("st", r=1, sub=2, mat=C.mat(["Rock", "Pebble", "RockDark"][i % 3], rough=0.9))
        C.jitter(st, 0.1, 1.3, i)
        st.data.transform(C.xform(scale=(0.16 * s, 0.12 * s, 0.09 * s), rot=(0, 0, math.degrees(a) + 90)))
        for v in st.data.vertices:
            v.co.z = max(v.co.z, -0.03)
        st.location = ((R + 0.08) * math.cos(a), (R + 0.08) * math.sin(a), 0.04)
        C.shade(st, 180)
        parts.append(st)
    # lily pads
    pad_m = C.mat("Leaf", rough=0.7)
    for k, (x, y, r, rot) in enumerate([(-0.35, -0.2, 0.15, 30), (0.2, -0.38, 0.12, 140), (0.1, 0.25, 0.14, 250)]):
        pad = C.lathe("pad", [(0, 0.0), (r, 0.0), (r, 0.012), (0, 0.014)], seg=20, mat=pad_m,
                      rfun=lambda t, z: 0.25 if (t < 0.35) else 1.0, sharp=60)
        pad.data.transform(C.xform(rot=(0, 0, rot)))
        pad.location = (x, y, 0.028)
        parts.append(pad)
        if k == 0:
            fl = []
            for j in range(7):
                a = j * 360 / 7
                p = C.sphere("fp", (0, 0, 0), r=1, scale=(0.05, 0.022, 0.014), mat=C.mat("Blossom" if j % 2 else "BlossomDeep", rough=0.75), seg=10, rings=5)
                for v in p.data.vertices:
                    v.co.z += 6 * max(0, v.co.x) ** 2
                p.data.transform(Matrix.Translation((0.04, 0, 0)))
                p.data.transform(C.xform(rot=(0, -30, a)))
                p.location = (x, y, 0.06)
                fl.append(p)
            fl.append(C.sphere("fc", (x, y, 0.065), r=0.025, mat=C.mat("FlowerYellow"), seg=8, rings=5))
            parts += fl
    # reeds + cattails on the back-right side
    for i in range(9):
        a = math.radians(rnd.uniform(15, 75))
        d = R + rnd.uniform(-0.05, 0.12)
        p0 = Vector((d * math.cos(a), d * math.sin(a), 0.0))
        h = rnd.uniform(0.45, 0.8)
        lean = Vector((rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), 0))
        parts.append(C.tube("reed", [p0, p0 + lean * 0.4 + Vector((0, 0, h * 0.5)), p0 + lean + Vector((0, 0, h))], r=0.016,
                            radii=[1, 0.8, 0.3], mat=C.mat("Reed", rough=0.85), seg=4, res=3))
        if i % 3 == 0:
            tip = p0 + lean + Vector((0, 0, h))
            parts.append(C.cyl("cat", tip - lean * 0.1 - Vector((0, 0, 0.12)), r=0.028, h=0.14, mat=C.mat("Cattail", rough=0.9), seg=8, bevel=0.012, bseg=2))
    rim = C.join(parts, "PondRim")
    C.set_origin(rim, (0, 0, 0))
    C.set_parent(rim, root)
    water = C.lathe("Water", [(0, 0.0), (R + 0.02, 0.0)], seg=32, mat=C.mat("Water", "6EC8E6", rough=0.15, spec=0.6), smooth=True)
    water.location = (0, 0, 0.03)
    C.set_parent(water, root)
    return root


# ============================================================================ FLOWERS
def tulip(rnd, col):
    h = rnd.uniform(0.22, 0.36)
    lean = Vector((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), 0))
    top = lean + Vector((0, 0, h))
    parts = [C.tube("st", [(0, 0, 0), tuple(lean * 0.4 + Vector((0, 0, h * 0.5))), tuple(top)], r=0.011, mat=C.mat("Stem", rough=0.8), seg=4, res=2)]
    cup = C.lathe("cup", [(0, -0.01), (0.035, 0.0), (0.05, 0.03), (0.048, 0.06), (0.036, 0.085)], seg=12, mat=C.mat(col, rough=0.75),
                  rfun=lambda t, z: 1 + (0.18 * math.cos(3 * t) if z > 0.05 else 0.04 * math.cos(3 * t)), sharp=80)
    cup.location = top
    parts.append(cup)
    for k in range(2):
        lf = C.leaf("lf", length=0.16, width=0.035, thick=0.008, curl=0.06, mat=C.mat("LeafDark", rough=0.8), seg=8, rings=5)
        lf.data.transform(C.xform(rot=(0, -60, rnd.uniform(0, 360))))
        lf.location = (0, 0, 0.02)
        parts.append(lf)
    return C.join(parts)


def daisy(rnd, col):
    h = rnd.uniform(0.14, 0.26)
    top = Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), h))
    parts = [C.tube("st", [(0, 0, 0), tuple(top * 0.5), tuple(top)], r=0.009, mat=C.mat("Stem", rough=0.8), seg=4, res=2)]
    pet = C.lathe("pet", [(0, 0.0), (0.06, 0.008), (0.0, 0.016)], seg=16, mat=C.mat(col, rough=0.75),
                  rfun=lambda t, z: 0.55 + 0.45 * abs(math.cos(4 * t)) ** 0.5, sharp=80)
    ctr = C.sphere("c", (0, 0, 0.014), r=0.022, scale=(1, 1, 0.6), mat=C.mat("FlowerYellow"), seg=8, rings=4)
    hd = C.join([pet, ctr])
    C.set_origin(hd, (0, 0, 0))
    hd.data.transform(C.xform(rot=(rnd.uniform(-25, 5), rnd.uniform(-15, 15), 0)))
    hd.location = top
    parts.append(hd)
    return C.join(parts)


def build_flowers():
    rnd = random.Random(12)
    root = C.empty("Flowers")
    parts = [C.blob("mound", [((0, 0, -0.05), 0.5, (1.25, 1.0, 0.3)), ((0.3, 0.2, -0.05), 0.3, (1, 1, 0.4)), ((-0.35, -0.15, -0.05), 0.3, (1, 1, 0.4))],
                    mat=C.mat("LeafDark", rough=0.9), voxel=0.05, smooth_iter=4, target=700, flat_bottom=0.0)]
    tul = ["Apple", "FlowerYellow", "Blossom", "Orange", "Purple", "BlossomDeep"]
    dai = ["White", "White", "Purple", "BlossomLight"]
    pts = []
    tries = 0
    while len(pts) < 28 and tries < 3000:
        tries += 1
        x, y = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.45, 0.45)
        if (x / 0.62) ** 2 + (y / 0.48) ** 2 > 1:
            continue
        if any(math.hypot(x - a, y - b) < 0.13 for a, b in pts):
            continue
        pts.append((x, y))
    C.update()
    mound = parts[0]
    for i, (x, y) in enumerate(pts):
        ok, loc, n, _ = mound.ray_cast(Vector((x, y, 2)), Vector((0, 0, -1)))
        z = loc.z - 0.02 if ok else 0.0
        f = tulip(rnd, tul[i % len(tul)]) if i % 2 == 0 else daisy(rnd, dai[i % len(dai)])
        C.set_origin(f, (0, 0, 0))
        f.location = (x, y, z)
        parts.append(f)
    patch = C.join(parts, "FlowerPatch")
    C.set_origin(patch, (0, 0, 0))
    C.set_parent(patch, root)
    return root


# ============================================================================ CLOUDS
def cloud(name, spheres, seed):
    root = C.empty(name)
    m = C.mat("Cloud", "FFFFFF", rough=1.0, spec=0.2)
    o = C.blob(name + "Puff", spheres, mat=m, voxel=0.07, smooth_iter=6, target=2400, flat_bottom=0.12, seed=seed)
    C.update()
    mn, mx = C.world_bbox([o])
    o.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    C.set_parent(o, root)
    return root


def build_cloud_a():
    return cloud("CloudA", [((-1.25, 0, 0.42), 0.5), ((-0.5, 0.05, 0.62), 0.75), ((0.35, -0.05, 0.72), 0.82), ((1.2, 0.05, 0.45), 0.55),
                            ((0.0, 0.35, 0.45), 0.6), ((-0.2, -0.35, 0.45), 0.55), ((0.75, 0.3, 0.4), 0.5), ((1.6, 0, 0.3), 0.3)], 1)


def build_cloud_b():
    return cloud("CloudB", [((-1.0, 0, 0.4), 0.48), ((-0.3, 0.0, 0.62), 0.7), ((0.5, 0.05, 0.5), 0.6), ((1.1, -0.05, 0.36), 0.42),
                            ((0.1, 0.3, 0.4), 0.5), ((-0.55, -0.25, 0.35), 0.42)], 2)

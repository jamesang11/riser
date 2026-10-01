"""Food props for feeding + UI thumbnails (root `Food`, mesh `FoodMesh`, origin at base)."""
import math, random
from mathutils import Vector, Matrix
import common as C


def finish(parts):
    root = C.empty("Food")
    o = C.join(parts, "FoodMesh")
    C.set_origin(o, (0, 0, 0))
    C.set_parent(o, root)
    return root


def build_food_apple():
    red = C.mat("AppleRed", "E0463C", rough=0.35, spec=0.6, coat=0.4)
    prof = [(0, 0.014)]
    for i in range(1, 16):
        a = math.pi * i / 16
        r = 0.078 * math.sin(a) ** 0.85 * (1 - 0.12 * math.cos(a))
        z = 0.07 - 0.068 * math.cos(a) + 0.012 * math.sin(a) ** 6
        prof.append((r, z))
    prof.append((0, 0.122))
    apple = C.lathe("apple", prof, seg=32, mat=red, rfun=lambda t, z: 1 + 0.03 * math.cos(5 * t) * (z > 0.08))
    C.shade(apple, 180)
    C.paint_faces(apple, C.mat("AppleBlush", "F2705A", rough=0.35, spec=0.6), lambda c, n: n.z > 0.35 and n.x - n.y > 0.1)
    stem = C.tube("stem", [(0, 0, 0.115), (0.004, 0, 0.15), (0.016, 0, 0.172)], r=0.006, radii=[1.2, 1, 0.8], mat=C.mat("WoodDark", rough=0.8), seg=6, res=3)
    lf = C.leaf("leaf", length=0.07, width=0.028, thick=0.005, curl=0.02, mat=C.mat("Leaf", rough=0.6), seg=8, rings=5, fold=0.35)
    C.paint_faces(lf, C.mat("LeafLight", rough=0.6), lambda c, n: n.z > 0.5 and c.x > 0.02)
    lf.data.transform(C.xform(rot=(0, -25, 30)))
    lf.location = (0.008, 0, 0.152)
    C.bake_transform(lf)
    return finish([apple, stem, lf])


def build_food_soup():
    rnd = random.Random(4)
    bowl = C.lathe("bowl", [(0, 0.0), (0.045, 0.0), (0.05, 0.012), (0.075, 0.03), (0.1, 0.07), (0.106, 0.09), (0.098, 0.092),
                            (0.09, 0.075), (0.065, 0.035), (0, 0.028)], seg=32, mats=[C.mat("BowlTeal", "5DB3B5", rough=0.45, spec=0.5), C.mat("BowlCream", "F6EEDC", rough=0.5)],
                   mat_idx=[0, 0, 0, 0, 0, 1, 1, 1, 1])
    soup = C.cyl("soup", (0, 0, 0.068), r=0.088, h=0.006, mat=C.mat("Soup", "F2A65A", rough=0.3, spec=0.6), seg=28, smooth=False)
    parts = [bowl, soup]
    for i in range(7):
        a = rnd.uniform(0, 6.28); d = rnd.uniform(0.0, 0.065)
        p = (d * math.cos(a), d * math.sin(a), 0.072)
        k = i % 4
        if k == 0:
            parts.append(C.cyl("carrot", p, r=0.014, h=0.006, mat=C.mat("Carrot", rough=0.7), seg=10, rot=(rnd.uniform(-10, 10), 0, 0)))
        elif k == 1:
            parts.append(C.sphere("pea", p, r=0.007, mat=C.mat("PeaGreen", "7CC85A", rough=0.6), seg=8, rings=5))
        elif k == 2:
            parts.append(C.box("potato", p, (0.016, 0.016, 0.012), mat=C.mat("Potato", "F2E0A8", rough=0.8), bevel=0.004, bseg=1, rot=(0, 0, rnd.uniform(0, 90))))
        else:
            lf = C.leaf("herb", length=0.022, width=0.01, thick=0.002, curl=0.0, mat=C.mat("Leaf"), seg=6, rings=4)
            lf.data.transform(C.xform(rot=(0, 0, rnd.uniform(0, 360))))
            lf.location = p
            C.bake_transform(lf)
            parts.append(lf)
    for i in range(4):
        a = rnd.uniform(0, 6.28); d = rnd.uniform(0.02, 0.06)
        parts.append(C.sphere("pea", (d * math.cos(a), d * math.sin(a), 0.072), r=0.007, mat=C.mat("PeaGreen"), seg=8, rings=5))
    spoon = [C.tube("sh", [(0.03, 0.02, 0.07), (0.1, 0.06, 0.13), (0.14, 0.085, 0.16)], r=0.006, mat=C.mat("Wood", rough=0.7), seg=6, res=3),
             C.sphere("bowlsp", (0.025, 0.017, 0.07), r=1, scale=(0.025, 0.018, 0.006), rot=(0, -30, 30), mat=C.mat("Wood"), seg=10, rings=5)]
    return finish(parts + spoon)


def build_food_cake():
    sponge = C.mat("CakeSponge", "F3C66D", rough=0.85)
    cream = C.mat("CakeCream", "FFF3D6", rough=0.7)
    honey = C.mat("Honey", "E8A33A", rough=0.2, spec=0.7)
    tri = [(-0.095, 0.075), (0.095, 0.075), (0.0, -0.13)]          # (x, -y): wide face toward the viewer (-Y)
    parts = []
    z = 0.0
    for i, (h, m) in enumerate([(0.035, sponge), (0.012, cream), (0.035, sponge), (0.012, cream), (0.03, sponge), (0.014, cream)]):
        sl = C.prism("layer", tri, z, z + h, m, bevel=0.006 if m is sponge else 0.004, bseg=2, sharp=40)
        sl.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
        if m is cream:
            sl.data.transform(Matrix.Diagonal((1.02, 1.02, 1, 1)))
        parts.append(sl)
        z += h
    top = z
    # honey drizzle along the top + drips down the front face
    pts = [(-0.08, -0.06, top + 0.004), (-0.03, -0.02, top + 0.006), (0.02, -0.05, top + 0.006), (0.05, 0.0, top + 0.005), (0.0, 0.07, top + 0.005)]
    parts.append(C.tube("drizzle", pts, r=0.0055, mat=honey, seg=6, res=4))
    for x, L in [(-0.065, 0.022), (-0.02, 0.045), (0.03, 0.03), (0.07, 0.016)]:
        parts.append(C.tube("drip", [(x, -0.077, top + 0.002), (x, -0.079, top - L * 0.6), (x, -0.078, top - L)], r=0.0045, radii=[1.3, 0.9, 1.0], mat=honey, seg=6, res=2))
        parts.append(C.sphere("dripend", (x, -0.078, top - L), r=0.0065, mat=honey, seg=8, rings=5))
    # tiny bee topper
    yel = C.mat("BeeYellow", "FFD34D", rough=0.6)
    blk = C.mat("BeeBlack", "2B2530", rough=0.5)
    wing = C.mat("BeeWing", "F4FAFF", rough=0.3)
    bz = top + 0.03
    bee = [C.sphere("bb", (0, 0.01, bz), r=1, scale=(0.022, 0.03, 0.021), mat=yel, seg=14, rings=8),
           C.torus("s1", (0, 0.016, bz), R=0.0215, r=0.004, rot=(90, 0, 0), scale=(1, 1, 0.97), mat=blk, seg=14, mseg=4),
           C.torus("s2", (0, 0.03, bz), R=0.017, r=0.004, rot=(90, 0, 0), mat=blk, seg=14, mseg=4),
           C.sphere("bh", (0, -0.025, bz + 0.004), r=0.016, mat=blk, seg=12, rings=8),
           C.cyl("sting", (0, 0.045, bz), r=0.004, r2=0.0, h=0.012, rot=(-90, 0, 0), mat=blk, seg=6)]
    for s in (-1, 1):
        bee.append(C.sphere("wing", (s * 0.018, 0.012, bz + 0.024), r=1, scale=(0.017, 0.011, 0.003), rot=(0, s * -25, s * 20), mat=wing, seg=10, rings=5))
        bee.append(C.sphere("eye", (s * 0.007, -0.038, bz + 0.009), r=0.0035, mat=C.mat("EyeShine", "FFFFFF", rough=0.25, emit="FFFFFF", strength=0.6), seg=6, rings=4))
        bee.append(C.tube("ant", [(s * 0.005, -0.03, bz + 0.018), (s * 0.012, -0.036, bz + 0.03)], r=0.0015, mat=blk, seg=4, res=1))
        bee.append(C.sphere("cheek", (s * 0.012, -0.036, bz - 0.002), r=0.003, mat=C.mat("SproutCheek"), seg=6, rings=4))
    parts += bee
    return finish(parts)

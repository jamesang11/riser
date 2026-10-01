"""Farm crops, each with Stage1 / Stage2 / Ripe / Withered sibling nodes (origin = plot centre on soil)."""
import math, random
from mathutils import Vector, Matrix
import common as C
import a_harvest

CROPS = ["turnip", "carrot", "strawberry", "corn", "pumpkin", "sunflower"]
P5 = [(-0.24, -0.24), (0.24, -0.24), (0.0, 0.0), (-0.24, 0.24), (0.24, 0.24)]
P4 = [(-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2)]


def M(name):
    tbl = {"CropLeaf": "6CC265", "CropLeafLight": "8BD67A", "CropLeafDark": "4FA85A", "Withered": "9A7650", "WitheredDark": "76583A",
           "TurnipWhite": "F4EEE6", "TurnipPurple": "B26BB5", "Carrot": "F28C3A", "Berry": "E5484D", "CornYellow": "F7D154",
           "Husk": "B8D07A", "Tassel": "E3C47A", "SunPetal": "FFC93C", "SunCenter": "6B4226", "Stem": "7FBF5F", "White": "FFFFFF",
           "FlowerYellow": "FFD65A"}
    return C.mat(name, tbl[name], rough=0.6 if name == "Berry" else 0.8)


def lf(length, width, mat="CropLeaf", curl=0.03, fold=0.3, thick=0.01):
    return C.leaf("lf", length=length, width=width, thick=thick, curl=curl, mat=M(mat), seg=6, rings=4, fold=fold)


def put(o, p, rz=0.0, rx=0.0, ry=0.0, s=1.0):
    o.data.transform(C.xform(rot=(rx, ry, rz), scale=(s, s, s)))
    o.location = (p[0], p[1], p[2] if len(p) > 2 else 0.0)
    C.bake_transform(o)
    return o


def rosette(p, rnd, n, length, width, tilt, mat="CropLeaf", z=0.0, light=True):
    out = []
    for k in range(n):
        a = 360 * k / n + rnd.uniform(-15, 15)
        l = lf(length * rnd.uniform(0.85, 1.1), width, mat if (k % 2 or not light) else "CropLeafLight")
        out.append(put(l, (p[0], p[1], z), rz=a, ry=-tilt))
    return out


def stem(p, h, r=0.012, bend=(0, 0), mat="Stem"):
    return C.tube("st", [(p[0], p[1], -0.01), (p[0] + bend[0] * 0.4, p[1] + bend[1] * 0.4, h * 0.55), (p[0] + bend[0], p[1] + bend[1], h)],
                  r=r, radii=[1.1, 1.0, 0.8], mat=M(mat), seg=5, res=2)


# ------------------------------------------------------------------ generic stages
def stage1(rnd, pts):
    parts = []
    for p in pts:
        h = rnd.uniform(0.05, 0.08)
        parts.append(stem(p, h, r=0.008))
        for s in (0, 180):
            l = lf(0.045, 0.024, "CropLeafLight", curl=0.01, fold=0.2, thick=0.007)
            parts.append(put(l, (p[0], p[1], h), rz=s + rnd.uniform(-20, 20), ry=-25))
    return parts


def withered(rnd, pts, h):
    parts = []
    for p in pts:
        hh = h * rnd.uniform(0.8, 1.1)
        a = rnd.uniform(0, 2 * math.pi)
        d = Vector((math.cos(a), math.sin(a), 0))
        top = Vector((p[0], p[1], 0)) + d * hh * 0.35 + Vector((0, 0, hh * 0.6))
        parts.append(C.tube("wst", [(p[0], p[1], -0.01), (p[0], p[1], hh * 0.55), tuple(top)], r=0.011, radii=[1, 0.9, 0.6], mat=M("Withered"), seg=5, res=3))
        for k in range(3):
            l = lf(hh * 0.45, 0.03, "WitheredDark" if k % 2 else "Withered", curl=-0.04, fold=0.6)
            parts.append(put(l, (p[0], p[1], hh * (0.2 + 0.2 * k)), rz=rnd.uniform(0, 360), ry=rnd.uniform(25, 55)))
    return parts


# ------------------------------------------------------------------ crops
def turnip(stage, rnd):
    if stage == "Stage2":
        return sum((rosette(p, rnd, 4, 0.13, 0.05, 45) for p in P5), [])
    parts = []
    for p in P5:
        b = C.lathe("bulb", [(0, -0.07), (0.035, -0.055), (0.065, -0.01), (0.068, 0.02), (0.05, 0.055), (0.018, 0.07), (0, 0.072)], seg=12,
                    mats=[M("TurnipWhite"), M("TurnipPurple")], mat_idx=[0, 0, 0, 1, 1, 1])
        parts.append(put(b, p))
        parts += rosette((p[0], p[1]), rnd, 5, 0.2, 0.065, 50, z=0.065)
    return parts


def carrot(stage, rnd):
    parts = []
    for p in P5:
        if stage == "Ripe":
            c = C.lathe("car", [(0, -0.12), (0.03, -0.06), (0.048, 0.0), (0.05, 0.03), (0.03, 0.045), (0, 0.047)], seg=10, mat=M("Carrot"),
                        rfun=lambda t, z: 1 + 0.04 * math.cos(3 * t))
            parts.append(put(c, p))
        n, L = (4, 0.13) if stage == "Stage2" else (6, 0.21)
        z0 = 0.04 if stage == "Ripe" else 0.0
        for k in range(n):
            a = 360 * k / n + rnd.uniform(-20, 20)
            parts.append(put(lf(L, 0.022, "CropLeafDark" if k % 2 else "CropLeaf", curl=0.05, fold=0.1), (p[0], p[1], z0), rz=a, ry=-62))
    return parts


def strawberry(stage, rnd):
    parts = []
    for i, p in enumerate(P5):
        n, L, W = (5, 0.1, 0.05) if stage == "Stage2" else (6, 0.14, 0.065)
        for k in range(n):
            a = 360 * k / n + rnd.uniform(-15, 15)
            l = C.lathe("rl", [(0, 0.0), (1.0, 0.02), (0, 0.035)], seg=8, mat=M("CropLeaf" if k % 2 else "CropLeafDark"),
                        rfun=lambda t, z: 0.8 + 0.2 * abs(math.cos(1.5 * t)))
            l.data.transform(Matrix.Diagonal((W, W * 0.9, 1, 1)))
            l.data.transform(Matrix.Translation((L * 0.6, 0, 0)))
            parts.append(put(l, (p[0], p[1], 0.05 + 0.02 * (k % 2)), rz=a, ry=-20))
        parts.append(C.sphere("bush", (p[0], p[1], 0.04), r=1, scale=(0.08, 0.08, 0.05), mat=M("CropLeafDark"), seg=8, rings=5))
        if stage == "Ripe":
            for k in range(3 if i != 2 else 2):
                a = math.radians(rnd.uniform(0, 360))
                q = (p[0] + 0.12 * math.cos(a), p[1] + 0.12 * math.sin(a), 0.03)
                b = C.lathe("berry", [(0, -0.035), (0.022, -0.02), (0.03, 0.005), (0.022, 0.02), (0, 0.022)], seg=8, mat=M("Berry"))
                cap = C.lathe("cal", [(0, 0.018), (0.024, 0.02), (0, 0.03)], seg=6, mat=M("CropLeaf"), rfun=lambda t, z: 0.6 + 0.4 * abs(math.cos(2.5 * t)))
                bb = C.join([b, cap])
                parts.append(put(bb, (q[0], q[1], q[2] + 0.035), rx=rnd.uniform(-20, 20)))
            f = C.lathe("wf", [(0, 0.0), (0.03, 0.005), (0, 0.01)], seg=10, mat=M("White"), rfun=lambda t, z: 0.6 + 0.4 * abs(math.cos(2.5 * t)))
            parts.append(put(f, (p[0], p[1], 0.11)))
    return parts


def corn(stage, rnd):
    parts = []
    for p in P4:
        if stage == "Stage2":
            parts.append(stem(p, 0.2, r=0.016))
            for k in range(3):
                parts.append(put(lf(0.3, 0.035, "CropLeaf" if k % 2 else "CropLeafLight", curl=-0.06, fold=0.15), (p[0], p[1], 0.05 + 0.05 * k), rz=120 * k + rnd.uniform(-20, 20), ry=-55))
            continue
        h = rnd.uniform(0.95, 1.1)
        parts.append(C.tube("stalk", [(p[0], p[1], -0.01), (p[0], p[1], h * 0.5), (p[0] + 0.01, p[1], h)], r=0.022, radii=[1.1, 1, 0.7], mat=M("Stem"), seg=6, res=2))
        for k in range(5):
            parts.append(put(lf(0.38, 0.04, "CropLeaf" if k % 2 else "CropLeafDark", curl=-0.12, fold=0.15), (p[0], p[1], 0.12 + k * 0.17), rz=k * 137 + rnd.uniform(-15, 15), ry=-35))
        a = rnd.uniform(0, 360)
        cob = C.lathe("cob", [(0, -0.09), (0.03, -0.075), (0.036, 0.0), (0.03, 0.07), (0, 0.09)], seg=10, mat=M("CornYellow"),
                      rfun=lambda t, z: 1 + 0.05 * math.cos(10 * t))
        hk = []
        for s in (-1, 1):
            hk.append(put(lf(0.17, 0.035, "Husk", curl=0.0, fold=0.4), (0, 0, -0.08), ry=-90 + s * 12, rz=90 * s + 90))
        cb = C.join([cob] + hk)
        C.set_origin(cb, (0, 0, 0))
        cb.data.transform(C.xform(rot=(0, 28, a)))
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        cb.location = Vector((p[0], p[1], h * 0.55)) + d * 0.05
        C.bake_transform(cb)
        parts.append(cb)
        for k in range(4):
            t0 = Vector((p[0] + 0.01, p[1], h))
            parts.append(C.tube("tassel", [t0, t0 + Vector((0.07 * math.cos(k * 1.6), 0.07 * math.sin(k * 1.6), 0.1))], r=0.007, radii=[1, 0.5], mat=M("Tassel"), seg=4, res=1))
    return parts


def pumpkin_crop(stage, rnd):
    parts = []
    vine = [(-0.35, -0.3, 0.02), (-0.1, -0.1, 0.03), (0.15, 0.05, 0.02), (0.35, 0.3, 0.02)]
    parts.append(C.tube("vine", vine, r=0.016, mat=M("Stem"), seg=5, res=4))
    parts.append(C.tube("vine2", [(-0.1, -0.1, 0.03), (-0.3, 0.2, 0.02), (-0.28, 0.35, 0.03)], r=0.013, mat=M("Stem"), seg=5, res=3))
    nleaf = 5
    for k in range(nleaf):
        q = [(-0.3, -0.28), (0.05, -0.02), (0.3, 0.25), (-0.28, 0.18), (0.2, -0.3), (-0.05, 0.32), (0.38, -0.05)][k]
        rl = a_harvest.round_leaf("pl", 0.13 if stage == "Stage2" else 0.15)
        for m in rl.data.materials:
            pass
        parts.append(put(rl, (q[0], q[1], 0.03), rz=rnd.uniform(0, 360), rx=rnd.uniform(-15, 15)))
    if stage == "Stage2":
        f = C.lathe("pf", [(0, 0), (0.04, 0.05), (0.035, 0.06), (0, 0.02)], seg=8, mat=M("FlowerYellow"), rfun=lambda t, z: 0.75 + 0.25 * abs(math.cos(2.5 * t)))
        parts.append(put(f, (0.12, 0.1, 0.03)))
        return parts
    for (x, y, r) in [(-0.12, -0.18, 0.2), (0.22, 0.12, 0.15)]:
        pk = a_harvest.pumpkin("pk", r, ("PumpkinOrange", "F28C3A"), rnd, 0.72)
        parts.append(put(pk, (x, y, -0.01), rz=rnd.uniform(0, 360)))
    return parts


def sunflower(stage, rnd):
    parts = []
    for p in P4:
        h = 0.35 if stage == "Stage2" else rnd.uniform(1.0, 1.2)
        parts.append(stem(p, h, r=0.018 if stage == "Ripe" else 0.013, bend=(0, -0.04)))
        for k in range(3 if stage == "Stage2" else 5):
            z = 0.08 + k * (h * 0.8 / 5 if stage == "Ripe" else 0.08)
            parts.append(put(lf(0.14 if stage == "Stage2" else 0.18, 0.08, "CropLeaf" if k % 2 else "CropLeafDark", curl=-0.03),
                             (p[0], p[1] - 0.01, z), rz=k * 150 + rnd.uniform(-20, 20), ry=-25))
        if stage == "Ripe":
            petals = C.lathe("petals", [(0, 0.0), (0.17, -0.01), (0.12, 0.01), (0, 0.012)], seg=40, mat=M("SunPetal"),
                             rfun=lambda t, z: 0.62 + 0.38 * abs(math.cos(6 * t)) ** 0.6, sharp=80)
            disc = C.sphere("disc", (0, 0, 0.012), r=1, scale=(0.085, 0.085, 0.03), mat=M("SunCenter"), seg=14, rings=6)
            back = C.cyl("back", (0, 0, -0.02), r=0.08, r2=0.05, h=0.04, mat=M("CropLeafDark"), seg=10)
            head = C.join([petals, disc, back])
            C.set_origin(head, (0, 0, 0))
            head.data.transform(C.xform(rot=(72, 0, rnd.uniform(-15, 15))))     # face the viewer (-Y), slightly up
            head.location = (p[0], p[1] - 0.05, h + 0.02)
            C.bake_transform(head)
            parts.append(head)
    return parts


SPEC = {  # stage2/ripe builder, Stage1 points, withered height
    "turnip": (turnip, P5, 0.14), "carrot": (carrot, P5, 0.16), "strawberry": (strawberry, P5, 0.12),
    "corn": (corn, P4, 0.5), "pumpkin": (pumpkin_crop, P5, 0.14), "sunflower": (sunflower, P4, 0.55),
}


def build_crop(kind):
    rnd = random.Random(sum(map(ord, kind)))
    root = C.empty("Crop")
    fn, pts, wh = SPEC[kind]
    stages = {"Stage1": stage1(rnd, pts), "Stage2": fn("Stage2", rnd), "Ripe": fn("Ripe", rnd), "Withered": withered(rnd, pts, wh)}
    if kind == "pumpkin":
        stages["Withered"] += [C.tube("wv", [(-0.35, -0.3, 0.01), (0.0, 0.0, 0.015), (0.35, 0.3, 0.01)], r=0.012, mat=M("WitheredDark"), seg=4, res=3)]
    for name, parts in stages.items():
        o = C.join(parts, name)
        C.set_origin(o, (0, 0, 0))
        C.shade(o, 70)
        C.set_parent(o, root)
    return root


for _k in CROPS:
    globals()["build_crop_" + _k] = (lambda k=_k: build_crop(k))

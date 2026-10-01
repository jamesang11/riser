"""Sprout - the mochi spirit companion."""
import math
from mathutils import Vector, Matrix, Quaternion
import common as C

H = 0.335       # body height
W = 0.232       # body max radius (x)
DEPTH = 0.9     # y squash

def body_profile(n=22):
    prof = []
    for i in range(n + 1):
        phi = math.pi * i / n          # 0 bottom pole -> pi top pole
        s, c = math.sin(phi), math.cos(phi)
        r = W * (abs(s) ** 0.78) * (1 + 0.13 * c)       # wider low
        # flatter bottom, taller dome
        z = (1 - c) / 2
        z = z ** 1.12 if c > 0 else z
        prof.append((r if 0 < i < n else 0.0, z * H))
    return prof

def surf(body, x, z, push=0.0):
    """Front surface point + normal of body at (x, z) (ray along +Y)."""
    ok, loc, nrm, _ = body.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    assert ok, (x, z)
    return loc + nrm * push, nrm

def orient(o, nrm, tilt=0.0):
    q = Vector((0, -1, 0)).rotation_difference(nrm)
    o.data.transform(q.to_matrix().to_4x4())

def build_sprout():
    body_m = C.mat("SproutBody", rough=0.72, spec=0.3)
    eye_m = C.mat("SproutEye", rough=0.12, spec=0.6, coat=0.6)
    shine_m = C.mat("EyeShine", "FFFFFF", rough=0.25, emit="FFFFFF", strength=0.6)
    cheek_m = C.mat("SproutCheek", rough=0.85)
    stem_m = C.mat("Stem", rough=0.75)
    leaf_m = C.mat("Leaf", rough=0.7)
    leafl_m = C.mat("LeafLight", rough=0.7)
    yel_m = C.mat("FlowerYellow", rough=0.7)
    pet_m = C.mat("Blossom", rough=0.7)
    petd_m = C.mat("BlossomDeep", rough=0.7)

    root = C.empty("Sprout")

    body = C.lathe("Body", body_profile(), seg=40, mat=body_m, scale=(1, DEPTH, 1))
    C.shade(body, 180)
    C.set_parent(body, root)
    C.update()

    # --- eyes: tall glossy ovals, set low & wide
    ex, ez = 0.074, 0.132
    for side, sx in (("L", -1), ("R", 1)):
        # viewer faces -Y; character's left is +X from its own view, but we name by screen: L = -X
        p, n = surf(body, sx * ex, ez)
        eye = C.sphere("Eye" + side, r=1, seg=18, rings=10, mat=eye_m, scale=(0.037, 0.017, 0.054))
        orient(eye, n)
        eye.location = p - n * 0.004
        C.set_parent(eye, body)
        # shine: big + tiny sparkle, upper-outer
        c = eye.location
        up = Vector((0, 0, 1))
        side_v = n.cross(up).normalized() * (-sx)
        s1 = C.sphere("s1", r=0.0145, seg=12, rings=8, mat=shine_m, scale=(1, 0.5, 1.15))
        orient(s1, n)
        s1.location = c + up * 0.02 + Vector((-0.012, 0, 0)) + n * 0.012
        s2 = C.sphere("s2", r=0.0068, seg=10, rings=6, mat=shine_m, scale=(1, 0.5, 1))
        orient(s2, n)
        s2.location = c - up * 0.018 + Vector((0.011, 0, 0)) + n * 0.010
        for s in (s1, s2):
            C.bake_transform(s)
        sh = C.join([s1, s2], "EyeShine" + side)
        C.set_parent(sh, eye)

        # cheeks
        cp, cn = surf(body, sx * 0.135, 0.096)
        ck = C.sphere("Cheek" + side, r=1, seg=16, rings=8, mat=cheek_m, scale=(0.03, 0.008, 0.018))
        orient(ck, cn)
        ck.location = cp - cn * 0.001
        C.set_parent(ck, body)

    # --- mouth: tiny smile arc hugging the surface
    pts = []
    for i in range(7):
        t = -1 + 2 * i / 6
        x = t * 0.019
        z = 0.1 - 0.009 * (1 - t * t)
        p, n = surf(body, x, z, 0.002)
        pts.append(p)
    mouth = C.tube("Mouth", pts, r=0.0042, mat=eye_m, seg=6, res=3)
    mc = sum(pts, Vector()) / len(pts)
    C.set_origin(mouth, mc)
    C.set_parent(mouth, body)

    # --- feet
    for side, sx in (("L", -1), ("R", 1)):
        f = C.sphere("Foot" + side, r=1, seg=16, rings=10, mat=body_m, scale=(0.05, 0.062, 0.034), rot=(0, 0, sx * -12))
        f.location = (sx * 0.085, -0.115, 0.03)
        C.update()
        # flatten bottom
        for v in f.data.vertices:
            if v.co.z < -0.012:
                v.co.z = -0.012 + (v.co.z + 0.012) * 0.3
        C.set_origin(f, (sx * 0.085, -0.115, 0.03))
        C.set_parent(f, root)

    # --- stem, leaves, bud, flower
    top = Vector((0, 0.005, H - 0.012))
    st_pts = [top, top + Vector((0, 0.004, 0.05)), top + Vector((0.004, -0.004, 0.10)), top + Vector((0.0, -0.012, 0.135))]
    stem = C.tube("Stem", st_pts, r=0.011, radii=[1.25, 1.0, 0.9, 0.85], mat=stem_m, seg=8)
    C.set_origin(stem, top)
    C.set_parent(stem, body)
    tip = st_pts[-1]

    att = top + Vector((0, 0.003, 0.045))
    for side, sx in (("L", -1), ("R", 1)):
        lf = C.leaf("Leaf" + side, length=0.105, width=0.042, thick=0.008, curl=0.05, mat=leaf_m, fold=0.35)
        # midrib highlight: paint upper faces lighter
        C.paint_faces(lf, leafl_m, lambda c, n: n.z > 0.55 and c.x > 0.02)
        lf.data.transform(C.xform(rot=(0, -28, 0)))                 # tilt upward
        lf.data.transform(C.xform(rot=(0, 0, 180 if sx < 0 else 0)))
        lf.data.transform(C.xform(rot=(0, 0, sx * -8)))
        lf.location = att + Vector((sx * 0.006, 0, 0))
        C.set_parent(lf, stem)

    # bud: closed teardrop with sepals
    bud_prof = [(0, -0.004), (0.012, 0.002), (0.02, 0.014), (0.021, 0.024), (0.016, 0.036), (0.008, 0.046), (0, 0.052)]
    bud = C.lathe("Bud", bud_prof, seg=16, mats=[pet_m, petd_m], mat_idx=[0, 0, 0, 0, 1, 1])
    sep = C.lathe("sep", [(0, -0.006), (0.014, 0.0), (0.0225, 0.012), (0.019, 0.02), (0, 0.02)], seg=16, mat=leaf_m,
                  rfun=lambda t, z: 1 + (0.12 * math.cos(5 * t) if z > 0.008 else 0))
    bud = C.join([bud, sep], "Bud")
    bud.data.transform(C.xform(rot=(-10, 0, 0)))
    bud.location = tip
    C.set_parent(bud, stem)

    # flower: 5 petals + yellow center, facing up-front
    parts = []
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 2
        p = C.sphere("p", r=1, seg=12, rings=6, mat=pet_m, scale=(0.033, 0.023, 0.008))
        for v in p.data.vertices:  # cup the petals slightly
            v.co.z += 12 * (v.co.x ** 2 + v.co.y ** 2) * 0.5
        p.data.transform(Matrix.Translation((0.029, 0, 0)))
        p.data.transform(C.xform(rot=(0, 0, math.degrees(a))))
        parts.append(p)
    ctr = C.sphere("c", r=0.018, seg=10, rings=6, mat=yel_m, scale=(1, 1, 0.6), loc=(0, 0, 0.004))
    C.bake_transform(ctr)
    for v in ctr.data.vertices:
        v.co += Vector((0, 0, 0.004))
    base = C.lathe("fb", [(0, -0.012), (0.01, -0.006), (0.013, 0.0), (0, 0.001)], seg=12, mat=leaf_m)
    fl = C.join(parts + [ctr, base], "Flower")
    fl.data.transform(C.xform(rot=(-42, 0, 0)))
    fl.data.transform(Matrix.Translation((0, 0, 0.012)))
    fl.location = tip
    C.set_parent(fl, stem)
    add_expressions(body, eye_m, cheek_m, body_m, mc)
    return root


# ---------------------------------------------------------------- expression / accessory parts
EX, EZ = 0.074, 0.132          # eye placement (matches EyeL/EyeR)


def surface_arc(body, fn, n=9, push=0.003):
    """Points on the front surface: fn(s) -> (x, z) for s in [-1, 1]."""
    pts = []
    for i in range(n):
        s = -1 + 2 * i / (n - 1)
        x, z = fn(s)
        p, nr = surf(body, x, z, push)
        pts.append(p)
    return pts


def arc_eye(name, body, sx, fn, eye_m):
    pts = surface_arc(body, lambda s: fn(s, sx))
    o = C.tube(name, pts, r=0.0068, radii=[0.55, 0.8, 0.95, 1, 1, 1, 0.95, 0.8, 0.55], mat=eye_m, seg=6, res=2)
    ctr = bpy_eye_center(body, sx)
    C.set_origin(o, ctr)
    C.set_parent(o, body)
    return o


def bpy_eye_center(body, sx):
    p, n = surf(body, sx * EX, EZ)
    return p - n * 0.004          # identical to EyeL/EyeR origin


def add_expressions(body, eye_m, cheek_m, body_m, mouth_center):
    # happy "^ ^"
    for side, sx in (("L", -1), ("R", 1)):
        arc_eye("EyeHappy" + side, body, sx, lambda s, sx: (sx * EX + s * 0.028, EZ - 0.012 + 0.024 * (1 - s * s) ** 0.8), eye_m)
    # sleepy "u u" (gentle downward U, lashes-down closed eyes)
    for side, sx in (("L", -1), ("R", 1)):
        arc_eye("EyeSleep" + side, body, sx, lambda s, sx: (sx * EX + s * 0.027, EZ - 0.012 + 0.012 * s * s), eye_m)

    # sad eyes: glossy ovals with the upper-outer part lidded (worried slant) + a little tear
    tear_m = C.mat("Tear", "A8DDF7", rough=0.08, spec=0.8, emit="CFEFFF", strength=0.3)
    shine_m = C.mat("EyeShine")
    for side, sx in (("L", -1), ("R", 1)):
        p, n = surf(body, sx * EX, EZ)
        c = p - n * 0.004
        eye = C.sphere("es", r=1, seg=18, rings=10, mat=eye_m, scale=(0.037, 0.017, 0.054))
        for v in eye.data.vertices:
            cut = 0.02 - 0.5 * (v.co.x * sx)
            if v.co.z > cut:
                v.co.z = cut + (v.co.z - cut) * 0.12
        orient(eye, n)
        eye.location = c
        up = Vector((0, 0, 1))
        s1 = C.sphere("s1", r=0.0125, seg=10, rings=6, mat=shine_m, scale=(1, 0.5, 1.1))
        orient(s1, n)
        s1.location = c - up * 0.004 + Vector((-sx * 0.009, 0, 0)) + n * 0.012
        s2 = C.sphere("s2", r=0.006, seg=8, rings=5, mat=shine_m, scale=(1, 0.5, 1))
        orient(s2, n)
        s2.location = c - up * 0.03 + Vector((sx * 0.012, 0, 0)) + n * 0.01
        tp, tn = surf(body, sx * (EX + 0.028), EZ - 0.058, 0.004)
        tear = C.sphere("tear", r=1, seg=8, rings=6, mat=tear_m, scale=(0.0085, 0.0055, 0.012))
        for v in tear.data.vertices:            # teardrop: pinch the top
            if v.co.z > 0:
                k = 1 - 0.75 * (v.co.z / 0.012)
                v.co.x *= k
                v.co.y *= k
        orient(tear, tn)
        tear.location = tp
        for o in (eye, s1, s2, tear):
            C.bake_transform(o)
        es = C.join([eye, s1, s2, tear], "EyeSad" + side)
        C.set_origin(es, c)
        C.set_parent(es, body)

    # sad frown
    pts = surface_arc(body, lambda t: (t * 0.018, 0.093 + 0.008 * (1 - t * t)), n=7, push=0.002)
    ms = C.tube("MouthSad", pts, r=0.0042, mat=eye_m, seg=6, res=3)
    C.set_origin(ms, mouth_center)
    C.set_parent(ms, body)

    # open "o" mouth with a tiny tongue
    mp, mn = surf(body, 0.0, 0.098)
    outer = C.sphere("mo", r=1, seg=12, rings=7, mat=eye_m, scale=(0.016, 0.006, 0.015))
    orient(outer, mn)
    outer.location = mp + mn * 0.0005
    tongue = C.sphere("mt", r=1, seg=10, rings=5, mat=cheek_m, scale=(0.0105, 0.004, 0.0065))
    orient(tongue, mn)
    tongue.location = mp + mn * 0.0042 + Vector((0, 0, -0.0055))
    for o in (outer, tongue):
        C.bake_transform(o)
    mo = C.join([outer, tongue], "MouthOpen")
    C.set_origin(mo, mouth_center)
    C.set_parent(mo, body)

    # stubby nub arms at ~40% height, hanging slightly down & out
    za = 0.4 * H
    for side, sx in (("L", -1), ("R", 1)):
        ok, sh, nrm, _ = body.ray_cast(Vector((sx * 1.0, -0.045, za)), Vector((-sx, 0, 0)))
        shoulder = sh - nrm * 0.012
        arm = C.sphere("Arm" + side, r=1, seg=14, rings=8, mat=body_m, scale=(0.05, 0.033, 0.031))
        # long axis out (+X side) then droop 38 deg
        arm.data.transform(Matrix.Translation((0.037, 0, 0)))
        arm.data.transform(C.xform(rot=(0, 38, 0)))
        if sx < 0:
            arm.data.transform(C.xform(scale=(-1, 1, 1)))
            arm.data.flip_normals()
        arm.location = shoulder
        C.shade(arm, 180)
        C.set_parent(arm, body)

    # nightcap: floppy striped cone sitting tilted on the left of the head, stem pokes out beside it
    ok, hp, hn, _ = body.ray_cast(Vector((-0.062, 0.01, 1.0)), Vector((0, 0, -1)))
    base_c = hp - hn * 0.013
    rb, hc = 0.105, 0.23
    nb = 8
    prof = [(0, 0.0)]
    for i in range(nb + 1):
        t = i / nb
        prof.append((rb * (1 - t) ** 0.85 + 0.004, hc * t))
    prof[-1] = (0, hc)
    mats = [C.mat("NightcapCream", "F6EEDC", rough=0.9), C.mat("NightcapBlue", "9DC2E8", rough=0.9)]
    cap = C.lathe("capcone", prof, seg=20, mats=mats, mat_idx=[0] + [(i % 2) for i in range(nb)], smooth=True)
    # floppy bend: droop toward -X and forward as height increases
    for v in cap.data.vertices:
        t = max(0.0, v.co.z / hc)
        v.co.x -= 0.17 * t ** 2
        v.co.z -= 0.13 * t ** 2.4
        v.co.y -= 0.03 * t ** 2
    tip = Vector((-0.17, -0.03, hc - 0.13))
    cuff = C.torus("cuff", (0, 0, 0.004), R=rb - 0.004, r=0.017, mat=C.mat("NightcapCuff", "FFFFFF", rough=0.95), seg=20, mseg=6)
    pom = C.sphere("pom", tip, r=0.03, mat=C.mat("NightcapCuff"), seg=10, rings=7)
    C.jitter(pom, 0.003, 60, 2)
    capo = C.join([cap, cuff, pom], "Nightcap")
    C.set_origin(capo, (0, 0, 0))
    # tilt the cap's up-axis to the head normal, plus extra jaunty tilt to the left
    axis = (hn + Vector((-0.15, -0.05, 0))).normalized()
    q = Vector((0, 0, 1)).rotation_difference(axis)
    capo.data.transform(q.to_matrix().to_4x4())
    capo.location = base_c
    C.shade(capo, 60)
    C.set_parent(capo, body)

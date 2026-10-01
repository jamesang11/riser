"""Props: campfire, lamppost, bench, mailbox, telescope, lanterns."""
import math, random
from mathutils import Vector, Matrix
import common as C


def log(name, length, r, rnd, bark="Wood"):
    """Log along +X centered at origin with light end caps."""
    o = C.cyl(name, r=r, h=length, rot=(0, 90, 0), mat=C.mat(bark, rough=0.85), seg=10, bevel=0.012, bseg=1)
    C.paint_faces(o, C.mat("WoodLight", rough=0.8), lambda c, n: abs(n.x) > 0.85)
    C.jitter(o, 0.006, 10, rnd.randint(0, 99))
    return o


# ============================================================================ CAMPFIRE
def build_campfire():
    rnd = random.Random(2)
    root = C.empty("Campfire")
    parts = []
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.08, 0.08)
        s = rnd.uniform(0.85, 1.1)
        st = C.ico("st", r=1, sub=2, mat=C.mat(["Rock", "RockDark", "Pebble"][i % 3], rough=0.9))
        C.jitter(st, 0.12, 1.3, i)
        st.data.transform(C.xform(scale=(0.11 * s, 0.085 * s, 0.075 * s), rot=(0, 0, math.degrees(a) + 90)))
        for v in st.data.vertices:
            v.co.z = max(v.co.z, -0.02)
        st.location = (0.38 * math.cos(a), 0.38 * math.sin(a), 0.03)
        C.shade(st, 180)
        parts.append(st)
    # ember bed
    emb = C.sphere("emb", (0, 0, 0.02), r=1, scale=(0.24, 0.24, 0.05), mat=C.mat("GlowEmbers", "E2552E", rough=0.9, emit="FF8A3D", strength=1.0), seg=18, rings=8)
    parts.append(emb)
    for i in range(7):
        a = rnd.uniform(0, 6.28); d = rnd.uniform(0.02, 0.16)
        parts.append(C.ico("coal", (d * math.cos(a), d * math.sin(a), 0.05), r=0.035, sub=1, scale=(1, 0.8, 0.6), mat=C.mat("Iron" if i % 2 else "GlowEmbers")))
    # teepee logs
    for i in range(4):
        a = 2 * math.pi * i / 4 + 0.4
        lg = log("lg", 0.5, 0.042, rnd)
        lg.data.transform(C.xform(rot=(0, 58, 0)))           # lean in (+X end goes down)
        lg.data.transform(Matrix.Translation((0.11, 0, 0.2)))
        lg.data.transform(C.xform(rot=(0, 0, math.degrees(a))))
        parts.append(lg)
    # two crossed ground logs
    for a in (25, -25):
        lg = log("gl", 0.58, 0.05, rnd, bark="WoodDark" if a > 0 else "Wood")
        lg.data.transform(C.xform(rot=(0, 0, a + 90)))
        lg.location = (0, 0, 0.055 if a > 0 else 0.1)
        parts.append(lg)
    # stumps as seats
    for (a, s) in ((200, 1.0), (-22, 0.9)):
        ar = math.radians(a)
        p = Vector((0.78 * math.cos(ar), 0.78 * math.sin(ar), 0))
        stp = C.cyl("stump", (0, 0, 0), r=0.15 * s, h=0.28 * s, mat=C.mat("WoodDark", rough=0.85), seg=14, base=True, bevel=0.02, bseg=2)
        C.paint_faces(stp, C.mat("WoodLight", rough=0.8), lambda c, n: n.z > 0.8)
        C.jitter(stp, 0.008, 8, int(a))
        ring = C.torus("ring", (0, 0, 0.281 * s), R=0.08 * s, r=0.008, mat=C.mat("Wood", rough=0.8), seg=16, mseg=4, scale=(1, 1, 0.3))
        rts = []
        for k in range(3):
            ra = math.radians(k * 120 + 30)
            rts.append(C.sphere("root", (0.14 * s * math.cos(ra), 0.14 * s * math.sin(ra), 0.03), r=1, scale=(0.07, 0.04, 0.05),
                                rot=(0, 0, k * 120 + 30), mat=C.mat("WoodDark"), seg=10, rings=6))
        st = C.join([stp, ring] + rts)
        st.location = p
        parts.append(st)
    body = C.join(parts, "CampfireBody")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    C.empty("FirePoint", (0, 0, 0.3), parent=root)
    return root


# ============================================================================ LAMPPOST
def build_lamppost():
    root = C.empty("Lamppost")
    iron = C.mat("Iron", rough=0.6)
    glow = C.mat("GlowLamp", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0)
    parts = []
    parts.append(C.lathe("base", [(0, 0), (0.17, 0), (0.17, 0.05), (0.14, 0.08), (0.1, 0.1), (0.08, 0.2), (0.065, 0.26), (0, 0.26)], seg=16, mat=iron, sharp=50))
    parts.append(C.cyl("pole", (0, 0, 0.2), r=0.038, h=1.15, mat=iron, seg=12, base=True))
    for z in (0.62, 1.3):
        parts.append(C.torus("collar", (0, 0, z), R=0.045, r=0.018, mat=C.mat("Brass", rough=0.45), seg=14, mseg=6))
    # little scroll brackets under the lantern
    for k in range(4):
        a = math.radians(90 * k + 45)
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * 0.035 + Vector((0, 0, 1.2)), d * 0.1 + Vector((0, 0, 1.3)), d * 0.1 + Vector((0, 0, 1.36))]
        parts.append(C.tube("scroll", pts, r=0.012, mat=iron, seg=5, res=4))
    # lantern
    z0 = 1.36
    parts.append(C.lathe("plate", [(0, z0), (0.13, z0), (0.14, z0 + 0.03), (0.12, z0 + 0.05), (0, z0 + 0.05)], seg=6, mat=iron, rot=(0, 0, 30), sharp=40))
    parts.append(C.lathe("glass", [(0, z0 + 0.05), (0.095, z0 + 0.05), (0.115, z0 + 0.24), (0, z0 + 0.24)], seg=6, mat=glow, rot=(0, 0, 30), sharp=40))
    for k in range(6):
        a = math.radians(60 * k + 30)
        p0 = Vector((0.1 * math.cos(a), 0.1 * math.sin(a), z0 + 0.05))
        p1 = Vector((0.12 * math.cos(a), 0.12 * math.sin(a), z0 + 0.24))
        parts.append(C.tube("bar", [p0, p1], r=0.012, mat=iron, seg=4, res=1))
    parts.append(C.lathe("roof", [(0, z0 + 0.23), (0.17, z0 + 0.23), (0.18, z0 + 0.26), (0.1, z0 + 0.33), (0.03, z0 + 0.38), (0, z0 + 0.39)], seg=6, mat=iron, rot=(0, 0, 30), sharp=40))
    parts.append(C.sphere("fin", (0, 0, z0 + 0.42), r=0.035, mat=C.mat("Brass", rough=0.45), seg=10, rings=6))
    body = C.join(parts, "LamppostBody")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    C.empty("LightPoint", (0, 0, z0 + 0.145), parent=root)
    return root


# ============================================================================ BENCH
def build_bench():
    root = C.empty("Bench")
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    parts = []
    W = 1.25
    for i, y in enumerate((-0.15, -0.02, 0.11)):
        parts.append(C.box("seat", (0, y, 0.43), (W, 0.12, 0.055), mat=wood, bevel=0.022, bseg=2))
    for i, z in enumerate((0.62, 0.78)):
        b = C.box("back", (0, 0, 0), (W, 0.13, 0.05), mat=wood, bevel=0.022, bseg=2)
        b.data.transform(C.xform(rot=(-78, 0, 0)))
        b.location = (0, 0.2 + (z - 0.62) * 0.2, z)
        parts.append(b)
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.1)
        parts.append(C.box("fl", (x, -0.17, 0), (0.08, 0.08, 0.43), mat=woodd, bevel=0.02, bseg=2, base=True))
        bl = C.box("bl", (0, 0, 0), (0.08, 0.08, 0.88), mat=woodd, bevel=0.02, bseg=2, base=True)
        bl.data.transform(C.xform(rot=(-10, 0, 0)))
        bl.location = (x, 0.13, 0)
        parts.append(bl)
        parts.append(C.box("rail", (x, -0.02, 0.39), (0.07, 0.4, 0.06), mat=woodd, bevel=0.02, bseg=2))
        parts.append(C.box("arm", (sx * (W / 2 - 0.06), -0.05, 0.62), (0.1, 0.46, 0.055), mat=woodd, bevel=0.024, bseg=2))
        parts.append(C.cyl("armpost", (sx * (W / 2 - 0.06), -0.23, 0.43), r=0.03, h=0.2, mat=woodd, seg=8, base=True))
        parts.append(C.sphere("armend", (sx * (W / 2 - 0.06), -0.28, 0.62), r=0.045, scale=(1.1, 1, 0.8), mat=woodd, seg=10, rings=6))
        parts.append(C.box("foot", (x, -0.02, 0.02), (0.1, 0.46, 0.05), mat=woodd, bevel=0.02, bseg=2))
    body = C.join(parts, "BenchBody")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    return root


# ============================================================================ MAILBOX
def build_mailbox():
    root = C.empty("Mailbox")
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    mail = C.mat("Mail", rough=0.75)
    maild = C.mat("RoofTealDark", rough=0.75)
    parts = [C.box("post", (0, 0.02, 0), (0.1, 0.1, 0.88), mat=wood, bevel=0.025, bseg=2, base=True),
             C.box("shelf", (0, 0, 0.86), (0.2, 0.46, 0.04), mat=woodd, bevel=0.015, bseg=2),
             C.box("brace", (0, 0.1, 0.76), (0.05, 0.05, 0.2), mat=woodd, bevel=0.012, bseg=1, rot=(-40, 0, 0))]
    body = C.prism("box", C.arch_pts(0.26, 0.3, 12, 0.88), -0.21, 0.21, mail, bevel=0.02, bseg=2)
    parts.append(body)
    parts.append(C.prism("door", C.arch_pts(0.22, 0.26, 12, 0.9), -0.225, -0.2, maild, bevel=0.01, bseg=1))
    parts.append(C.box("handle", (0, -0.235, 1.1), (0.06, 0.02, 0.02), mat=C.mat("Brass", rough=0.45), bevel=0.006, bseg=1))
    parts.append(C.sphere("tuft", (0.0, 0.0, 0.03), r=1, scale=(0.16, 0.14, 0.08), mat=C.mat("GrassTuft", rough=0.9), seg=12, rings=6))
    for i, (x, y, col) in enumerate([(-0.09, -0.08, "FlowerYellow"), (0.1, -0.06, "White"), (0.03, -0.12, "Blossom")]):
        parts.append(C.sphere("fl", (x, y, 0.1), r=0.03, mat=C.mat(col), seg=8, rings=5))
    mb = C.join(parts, "MailboxBody")
    C.set_origin(mb, (0, 0, 0))
    C.set_parent(mb, root)
    # flag on the +X side, hinge pivot; raised position (vertical)
    hinge = Vector((0.145, 0.08, 1.02))
    red = C.mat("RoofRed", rough=0.8)
    fp = [C.box("fstick", (0.0, 0, 0.1), (0.02, 0.03, 0.22), mat=red, bevel=0.006, bseg=1),
          C.box("fflag", (0.0, -0.06, 0.18), (0.02, 0.12, 0.08), mat=red, bevel=0.01, bseg=1),
          C.cyl("fpin", (0, 0, 0), r=0.022, h=0.03, rot=(0, 90, 0), mat=C.mat("Iron", rough=0.6), seg=10)]
    flag = C.join(fp, "Flag")
    C.set_origin(flag, (0, 0, 0))
    flag.location = hinge
    C.set_parent(flag, root)
    return root


# ============================================================================ TELESCOPE
def build_telescope():
    root = C.empty("Telescope")
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    brass = C.mat("Brass", rough=0.45)
    navy = C.mat("Navy", rough=0.6)
    head = Vector((0, 0, 0.95))
    parts = []
    for k in range(3):
        a = math.radians(90 + 120 * k)
        foot = Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 0.0))
        parts.append(C.tube("leg", [head + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), -0.02)), foot + Vector((0, 0, 0.02))],
                            r=0.028, mat=wood, radii=[1, 0.8], seg=6, res=1))
        parts.append(C.sphere("foot", foot + Vector((0, 0, 0.02)), r=0.035, mat=woodd, seg=8, rings=5))
    parts.append(C.lathe("mount", [(0, 0.86), (0.07, 0.86), (0.09, 0.9), (0.08, 0.96), (0, 0.98)], seg=12, mat=brass))
    parts.append(C.box("yoke", (0, 0, 1.0), (0.2, 0.05, 0.1), mat=woodd, bevel=0.02, bseg=2))
    # spreader ring
    parts.append(C.torus("spread", (0, 0, 0.45), R=0.2, r=0.012, mat=woodd, seg=18, mseg=4))
    tri = C.join(parts, "Tripod")
    C.set_origin(tri, (0, 0, 0))
    C.set_parent(tri, root)
    # tube tilted 35 deg up, pointing toward +Y (away from the viewer) and slightly +X
    tp = [C.cyl("tube", (0, 0.1, 0), r=0.075, r2=0.065, h=0.72, rot=(-90, 0, 0), mat=navy, seg=16, bevel=0.01, bseg=1),
          C.cyl("dew", (0, 0.52, 0), r=0.092, r2=0.085, h=0.18, rot=(-90, 0, 0), mat=navy, seg=16, bevel=0.012, bseg=1),
          C.torus("r1", (0, 0.43, 0), R=0.085, r=0.016, rot=(90, 0, 0), mat=brass, seg=16, mseg=6),
          C.torus("r2", (0, 0.61, 0), R=0.092, r=0.016, rot=(90, 0, 0), mat=brass, seg=16, mseg=6),
          C.torus("r3", (0, -0.1, 0), R=0.078, r=0.014, rot=(90, 0, 0), mat=brass, seg=16, mseg=6),
          C.cyl("lens", (0, 0.6, 0), r=0.078, h=0.02, rot=(-90, 0, 0), mat=C.mat("Lens", "BFE6F2", rough=0.2), seg=16),
          C.cyl("eye", (0, -0.34, 0), r=0.035, r2=0.045, h=0.12, rot=(-90, 0, 0), mat=brass, seg=10),
          C.cyl("eyecap", (0, -0.41, 0), r=0.03, h=0.03, rot=(-90, 0, 0), mat=woodd, seg=10),
          C.cyl("finder", (0, 0.05, 0.1), r=0.022, h=0.26, rot=(-90, 0, 0), mat=brass, seg=8),
          C.box("fmount", (0, 0.05, 0.075), (0.03, 0.06, 0.04), mat=brass, bevel=0.005, bseg=1),
          C.cyl("axle", (0, 0, 0), r=0.03, h=0.24, rot=(0, 90, 0), mat=brass, seg=8)]
    tube = C.join(tp, "Tube")
    C.set_origin(tube, (0, 0, 0))
    tube.data.transform(C.xform(rot=(35, 0, -20)))
    tube.location = (0, 0, 1.06)
    C.set_parent(tube, root)
    return root


# ============================================================================ LANTERNS
def build_lanterns():
    root = C.empty("Lanterns")
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    cord = C.mat("Cord", "5A4636", rough=0.9)
    glows = [C.mat("GlowLantern", "FFD58A", rough=0.6, emit="FFD58A", strength=1.0),
             C.mat("GlowLanternPink", "F7A8B8", rough=0.6, emit="FFB3C0", strength=1.0),
             C.mat("GlowLanternOrange", "F6A04D", rough=0.6, emit="FFB060", strength=1.0)]
    X, Hp = 1.2, 1.95
    parts = []
    for sx in (-1, 1):
        parts.append(C.cyl("pole", (sx * X, 0, 0), r=0.05, h=Hp, mat=wood, seg=10, base=True, bevel=0.015))
        parts.append(C.sphere("knob", (sx * X, 0, Hp + 0.03), r=0.07, mat=woodd, seg=10, rings=6))
        parts.append(C.box("arm", (sx * (X - 0.08), 0, Hp - 0.12), (0.2, 0.05, 0.05), mat=woodd, bevel=0.015, bseg=1))
        parts.append(C.cyl("base", (sx * X, 0, 0), r=0.1, r2=0.07, h=0.1, mat=woodd, seg=10, base=True, bevel=0.02))
    # catenary cord
    a0, a1 = -X + 0.16, X - 0.16
    zc = Hp - 0.14
    sag = 0.34
    def cz(x):
        t = (x - a0) / (a1 - a0)
        return zc - sag * 4 * t * (1 - t)
    pts = [Vector((a0 + (a1 - a0) * i / 12, 0, cz(a0 + (a1 - a0) * i / 12))) for i in range(13)]
    parts.append(C.tube("cord", pts, r=0.01, mat=cord, seg=4, res=3))
    body = C.join(parts, "LanternPoles")
    C.set_origin(body, (0, 0, 0))
    C.set_parent(body, root)
    lan = []
    n = 7
    for i in range(n):
        x = a0 + (a1 - a0) * (i + 0.5) / n
        z = cz(x)
        s = 1.3 + 0.2 * ((i * 37) % 3) / 2
        drop = 0.1 + 0.05 * (i % 2)
        lan.append(C.tube("hang", [(x, 0, z), (x, 0, z - drop)], r=0.006, mat=cord, seg=4, res=1))
        cz0 = z - drop - 0.11 * s
        body_l = C.lathe("lan", [(0, -0.1), (0.05, -0.1), (0.1, -0.06), (0.12, 0.0), (0.1, 0.06), (0.05, 0.1), (0, 0.1)], seg=14,
                         mat=glows[i % 3], rfun=lambda t, z: 1 + 0.05 * math.cos(8 * t), sharp=70)
        body_l.data.transform(C.xform(scale=(s, s, s)))
        body_l.location = (x, 0, cz0)
        lan.append(body_l)
        lan.append(C.cyl("cap", (x, 0, cz0 + 0.1 * s), r=0.045 * s, h=0.03, mat=woodd, seg=10))
        lan.append(C.cyl("cap", (x, 0, cz0 - 0.1 * s), r=0.045 * s, h=0.03, mat=woodd, seg=10))
        lan.append(C.tube("tassel", [(x, 0, cz0 - 0.11 * s), (x, 0, cz0 - 0.19 * s)], r=0.01, radii=[0.6, 1.0], mat=C.mat("RoofRed"), seg=4, res=1))
    lo = C.join(lan, "LanternBulbs")
    C.set_origin(lo, (0, 0, 0))
    C.set_parent(lo, root)
    return root

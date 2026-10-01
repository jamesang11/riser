"""Player furniture (root `Furniture`, mesh `FurnitureMesh`).
Floor items: origin at base centre. Wall items: origin at the back-centre wall-contact point (item extends toward -Y).
Front faces Blender -Y (= SceneKit +Z)."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import common as C

FLOOR = ["armchair", "beanbag", "aquarium", "recordplayer", "plant", "floorlamp", "teddy", "desk", "toychest", "rocker"]
WALL = ["poster_sun", "clock", "garland", "shelf"]


def finish(parts):
    root = C.empty("Furniture")
    o = C.join(parts, "FurnitureMesh")
    C.set_origin(o, (0, 0, 0))
    C.set_parent(o, root)
    return root


def M(name, hexc, rough=0.8, **kw):
    return C.mat(name, hexc, rough=rough, **kw)


# ------------------------------------------------------------------ floor items
def furn_armchair():
    vel = M("VelvetMustard", "E3B342", rough=0.9)
    veld = M("VelvetMustardDark", "C9962E", rough=0.9)
    wood = C.mat("WoodDark", rough=0.8)
    W, D = 0.92, 0.82
    p = [C.box("base", (0, 0, 0.14), (W - 0.1, D - 0.05, 0.28), mat=vel, bevel=0.1, bseg=3, base=True),
         C.box("seat", (0, -0.05, 0.4), (W - 0.36, D - 0.2, 0.16), mat=veld, bevel=0.07, bseg=3, base=True),
         C.box("back", (0, D / 2 - 0.14, 0.38), (W - 0.2, 0.26, 0.58), mat=vel, bevel=0.12, bseg=3, base=True)]
    for v in p[2].data.vertices:            # rounded top of the back
        if v.co.z > 0.45:
            v.co.z -= 0.08 * (v.co.x / 0.36) ** 2
    for s in (-1, 1):
        p.append(C.box("arm", (s * (W / 2 - 0.1), 0.0, 0.14), (0.2, D - 0.05, 0.42), mat=vel, bevel=0.08, bseg=3, base=True))
        p.append(C.cyl("roll", (s * (W / 2 - 0.1), -0.02, 0.58), r=0.12, h=D - 0.03, rot=(90, 0, 0), mat=vel, seg=16, bevel=0.03, bseg=2))
        for sy in (-1, 1):
            p.append(C.cyl("leg", (s * (W / 2 - 0.12), sy * (D / 2 - 0.1), 0.0), r=0.03, r2=0.022, h=0.14, mat=wood, seg=8, base=True))
    for (x, z) in [(-0.14, 0.72), (0.14, 0.72), (0.0, 0.6), (-0.14, 0.5), (0.14, 0.5)]:
        p.append(C.sphere("btn", (x, D / 2 - 0.275, z), r=0.018, mat=veld, seg=8, rings=5))
    p.append(C.box("pillow", (0.12, 0.12, 0.62), (0.34, 0.12, 0.3), mat=M("PillowPink", "F7B7C9", rough=0.9), bevel=0.05, bseg=2, rot=(-12, 0, 15)))
    return finish(p)


def furn_beanbag():
    pink = M("BeanbagPink", "F4A0B5", rough=0.9)
    o = C.blob("bb", [((0, 0.02, 0.24), 0.4, (1.05, 1.0, 0.62)), ((0, 0.2, 0.45), 0.3, (1.1, 0.8, 0.8)), ((0, -0.1, 0.2), 0.3, (1.0, 1.0, 0.6))],
               mat=pink, voxel=0.03, smooth_iter=5, target=1800, flat_bottom=0.0)
    for v in o.data.vertices:              # sitting dent
        d = math.hypot(v.co.x / 0.3, (v.co.y + 0.05) / 0.3)
        if d < 1 and v.co.z > 0.3:
            v.co.z -= 0.07 * (1 - d * d)
    C.shade(o, 180)
    return finish([o])


def furn_aquarium():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    water = C.mat("Water", "6EC8E6", rough=0.1, spec=0.7)
    frame = M("TankFrame", "3E4658", rough=0.5)
    W, D, H0, TH = 0.82, 0.42, 0.6, 0.46
    p = [C.box("stand", (0, 0, 0.05), (W, D, H0 - 0.05), mat=wood, bevel=0.025, bseg=2, base=True),
         C.box("top", (0, 0, H0 - 0.02), (W + 0.04, D + 0.04, 0.04), mat=woodd, bevel=0.012, bseg=1, base=True),
         C.box("doorL", (-W / 4, -D / 2 - 0.005, 0.1), (W / 2 - 0.05, 0.02, H0 - 0.2), mat=C.mat("WoodLight", rough=0.8), bevel=0.01, bseg=1, base=True),
         C.box("doorR", (W / 4, -D / 2 - 0.005, 0.1), (W / 2 - 0.05, 0.02, H0 - 0.2), mat=C.mat("WoodLight", rough=0.8), bevel=0.01, bseg=1, base=True)]
    for s in (-1, 1):
        p.append(C.sphere("knob", (s * 0.05, -D / 2 - 0.025, 0.35), r=0.018, mat=C.mat("Brass", rough=0.45), seg=8, rings=5))
        for sy in (-1, 1):
            p.append(C.box("foot", (s * (W / 2 - 0.05), sy * (D / 2 - 0.05), 0), (0.07, 0.07, 0.06), mat=woodd, bevel=0.01, bseg=1, base=True))
    z0 = H0 + 0.02
    iw, idp = W - 0.08, D - 0.06
    # water shown as back + sides + surface; the front is open glass so the fish read clearly
    p += [C.box("wback", (0, idp / 2 - 0.01, z0), (iw, 0.02, TH - 0.06), mat=water, bevel=0.0, smooth=False, base=True),
          C.box("wside1", (-iw / 2 + 0.01, 0.0, z0), (0.02, idp, TH - 0.06), mat=water, bevel=0.0, smooth=False, base=True),
          C.box("wside2", (iw / 2 - 0.01, 0.0, z0), (0.02, idp, TH - 0.06), mat=water, bevel=0.0, smooth=False, base=True),
          C.box("wtop", (0, 0.0, z0 + TH - 0.08), (iw, idp, 0.02), mat=water, bevel=0.0, smooth=False, base=True),
          C.box("gravel", (0, 0, z0), (iw, idp, 0.06), mat=M("Gravel", "E8D2A6", rough=0.95), bevel=0.01, bseg=1, base=True)]
    for (x, z) in [(-W / 2 + 0.03, None), (W / 2 - 0.03, None)]:
        for y in (-D / 2 + 0.03, D / 2 - 0.03):
            p.append(C.box("post", (x, y, z0 - 0.02), (0.03, 0.03, TH), mat=frame, bevel=0.005, bseg=1, base=True))
    for zz in (z0 - 0.02, z0 + TH - 0.04):
        p.append(C.box("rimF", (0, -D / 2 + 0.03, zz), (W - 0.04, 0.03, 0.04), mat=frame, bevel=0.005, bseg=1, base=True))
        p.append(C.box("rimB", (0, D / 2 - 0.03, zz), (W - 0.04, 0.03, 0.04), mat=frame, bevel=0.005, bseg=1, base=True))
    p.append(C.box("lid", (0, 0, z0 + TH - 0.02), (W, D, 0.04), mat=frame, bevel=0.01, bseg=1, base=True))
    rnd = random.Random(3)
    for k in range(6):
        x = rnd.uniform(-0.3, 0.3)
        h = rnd.uniform(0.15, 0.33)
        p.append(C.tube("weed", [(x, 0.1, z0 + 0.05), (x + 0.02, 0.1, z0 + 0.05 + h / 2), (x - 0.01, 0.1, z0 + 0.05 + h)], r=0.012, radii=[1, 0.8, 0.4], mat=C.mat("Leaf", rough=0.8), seg=5, res=3))
    p.append(C.ico("rock", (0.22, 0.06, z0 + 0.07), r=0.06, sub=1, scale=(1.2, 0.8, 0.8), mat=C.mat("Rock", rough=0.9)))
    for (x, z, col, flip) in [(-0.12, z0 + 0.25, "F2A15A", 1), (0.14, z0 + 0.16, "6FA8F5", -1)]:
        body = C.sphere("fish", (x, -0.05, z), r=1, scale=(0.055, 0.02, 0.035), mat=M("Fish" + col, col, rough=0.5), seg=12, rings=8)
        tail = C.cyl("tail", (x - flip * 0.06, -0.05, z), r=0.028, r2=0.0, h=0.04, rot=(0, flip * 90, 0), scale=(1, 0.3, 1), mat=M("Fish" + col, col), seg=6)
        eye = C.sphere("eye", (x + flip * 0.03, -0.068, z + 0.008), r=0.006, mat=C.mat("SproutEye", rough=0.2), seg=6, rings=4)
        p += [body, tail, eye]
    for k in range(4):
        p.append(C.sphere("bubble", (-0.1 + 0.02 * k, -0.08, z0 + 0.32 + 0.03 * k), r=0.008 + 0.002 * k, mat=M("Bubble", "E8F8FF", rough=0.1), seg=6, rings=4))
    return finish(p)


def furn_recordplayer():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    teal = M("PlayerTeal", "4FA3A5", rough=0.6)
    vinyl = M("Vinyl", "2B2530", rough=0.35)
    p = [C.box("tabletop", (0, 0, 0.56), (0.62, 0.46, 0.05), mat=wood, bevel=0.015, bseg=2, base=True),
         C.box("shelf", (0, 0, 0.18), (0.54, 0.38, 0.03), mat=wood, bevel=0.01, bseg=1, base=True)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(C.cyl("leg", (sx * 0.26, sy * 0.18, 0), r=0.025, r2=0.02, h=0.56, mat=woodd, seg=8, base=True))
    for k, col in enumerate(["E0674F", "F2B45A", "6FA8F5", "F59BB6"]):
        p.append(C.box("sleeve", (-0.2 + k * 0.035, 0.0, 0.21), (0.02, 0.3, 0.3), mat=M("Sleeve" + col, col), bevel=0.004, bseg=1, base=True, rot=(0, -12, 0)))
    z = 0.61
    p += [C.box("player", (0, 0, z), (0.5, 0.38, 0.1), mat=woodd, bevel=0.02, bseg=2, base=True),
          C.box("deck", (0, 0, z + 0.1), (0.46, 0.34, 0.012), mat=teal, bevel=0.004, bseg=1, base=True),
          C.cyl("platter", (-0.05, 0.0, z + 0.112), r=0.15, h=0.012, mat=vinyl, seg=28, base=True),
          C.cyl("label", (-0.05, 0.0, z + 0.124), r=0.05, h=0.003, mat=M("Label", "F7B7C9"), seg=16, base=True),
          C.cyl("spindle", (-0.05, 0.0, z + 0.127), r=0.006, h=0.02, mat=C.mat("Brass", rough=0.45), seg=6, base=True),
          C.cyl("pivot", (0.17, 0.11, z + 0.112), r=0.025, h=0.03, mat=C.mat("Brass"), seg=10, base=True),
          C.tube("arm", [(0.17, 0.11, z + 0.14), (0.13, 0.0, z + 0.14), (0.06, -0.06, z + 0.135)], r=0.006, mat=C.mat("Brass"), seg=5, res=3),
          C.box("head", (0.055, -0.065, z + 0.13), (0.03, 0.02, 0.015), mat=vinyl, bevel=0.003, bseg=1)]
    for x in (0.13, 0.19):
        p.append(C.cyl("knob", (x, -0.19, z + 0.05), r=0.018, h=0.02, rot=(90, 0, 0), mat=C.mat("Brass"), seg=10))
    for k in range(3):
        a = k * 0.8
        p.append(C.box("note", (0.22 + 0.03 * k, -0.05, z + 0.25 + 0.06 * k), (0.02, 0.005, 0.05), mat=vinyl, bevel=0.0, smooth=False, rot=(0, 10, 0)))
        p.append(C.sphere("notehead", (0.21 + 0.03 * k, -0.05, z + 0.225 + 0.06 * k), r=1, scale=(0.018, 0.006, 0.013), mat=vinyl, seg=8, rings=4))
    return finish(p)


def furn_plant():
    rnd = random.Random(7)
    weave = M("Basket", "D9B98A", rough=0.95)
    weaved = M("BasketDark", "B89468", rough=0.95)
    basket = C.lathe("basket", [(0, 0), (0.2, 0), (0.24, 0.06), (0.26, 0.34), (0.27, 0.38), (0.25, 0.38), (0.23, 0.08), (0, 0.06)], seg=32, mat=weave,
                     rfun=lambda t, z: 1 + 0.025 * math.cos(24 * t + z * 40))
    C.paint_faces(basket, weaved, lambda c, n: int(c.z / 0.05) % 2 == 0 and abs(n.z) < 0.5)
    p = [basket, C.cyl("soil", (0, 0, 0.33), r=0.23, h=0.02, mat=C.mat("Soil", rough=0.95), seg=18),
         C.torus("rim", (0, 0, 0.37), R=0.26, r=0.025, mat=weaved, seg=28, mseg=6)]
    for k in range(9):
        a = k * 40 + rnd.uniform(-12, 12)
        L = rnd.uniform(0.5, 0.95)
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        top = Vector((0, 0, 0.34)) + d * L * 0.35 + Vector((0, 0, L))
        p.append(C.tube("st", [(0, 0, 0.34), tuple(Vector((0, 0, 0.34)) + d * L * 0.1 + Vector((0, 0, L * 0.6))), tuple(top)], r=0.012, mat=C.mat("Stem"), seg=5, res=3))
        lf = C.leaf("mon", length=0.42, width=0.24, thick=0.02, curl=-0.1, mat=C.mat("LeafDark" if k % 2 else "Leaf", rough=0.8), seg=10, rings=6, fold=0.25)
        # monstera splits: pinch notches along the leaf edge
        for v in lf.data.vertices:
            if abs(v.co.y) > 0.07:
                ph = math.sin(v.co.x / 0.42 * math.pi * 5)
                if ph > 0.6:
                    v.co.y *= 0.72
        lf.data.transform(C.xform(rot=(0, rnd.uniform(-10, 25), a)))
        lf.location = top
        C.bake_transform(lf)
        p.append(lf)
    root = finish(p)
    root.children[0].data.transform(Matrix.Scale(0.8, 4))      # keep the leaf spread within ~1 m
    return root


def furn_floorlamp():
    brass = C.mat("Brass", rough=0.45)
    p = [C.lathe("base", [(0, 0), (0.18, 0), (0.18, 0.03), (0.1, 0.06), (0.03, 0.08), (0, 0.08)], seg=24, mat=brass),
         C.cyl("pole", (0, 0, 0.08), r=0.018, h=1.26, mat=brass, seg=8, base=True),
         C.torus("ring", (0, 0, 0.75), R=0.025, r=0.01, mat=brass, seg=10, mseg=4),
         C.sphere("bulb", (0, 0, 1.36), r=0.05, mat=M("GlowLamp", "FFF1C8", rough=0.8, emit="FFD58A", strength=1.0), seg=10, rings=6)]
    shade = C.lathe("shade", [(0.26, 1.28), (0.3, 1.3), (0.2, 1.6), (0.16, 1.6)], seg=28, mat=C.mat("GlowLamp"), caps=False, sharp=80,
                    rfun=lambda t, z: 1 + 0.02 * math.cos(16 * t))
    so = shade.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.012
    C.apply_mods(shade)
    p.append(shade)
    p.append(C.torus("trim", (0, 0, 1.29), R=0.28, r=0.012, mat=M("LampTrim", "E0674F"), seg=28, mseg=4))
    p.append(C.tube("chain", [(0.1, 0, 1.33), (0.1, 0, 1.18)], r=0.004, mat=brass, seg=4, res=1))
    p.append(C.sphere("pull", (0.1, 0, 1.17), r=0.014, mat=brass, seg=8, rings=5))
    return finish(p)


def furn_teddy():
    fur = M("TeddyFur", "C98A5A", rough=0.95)
    furl = M("TeddyMuzzle", "F0D2A8", rough=0.95)
    dark = C.mat("SproutEye", rough=0.2)
    p = []
    body = C.sphere("body", (0, 0.02, 0.27), r=1, scale=(0.26, 0.22, 0.28), mat=fur, seg=18, rings=12)
    belly = C.sphere("belly", (0, -0.17, 0.25), r=1, scale=(0.16, 0.06, 0.17), mat=furl, seg=14, rings=8)
    head = C.sphere("head", (0, -0.02, 0.63), r=0.2, mat=fur, seg=18, rings=12)
    p += [body, belly, head]
    for s in (-1, 1):
        p.append(C.sphere("ear", (s * 0.15, 0.0, 0.79), r=0.075, scale=(1, 0.6, 1), mat=fur, seg=14, rings=8))
        p.append(C.sphere("earin", (s * 0.15, -0.035, 0.79), r=0.045, scale=(1, 0.4, 1), mat=furl, seg=12, rings=6))
        p.append(C.sphere("eye", (s * 0.075, -0.18, 0.67), r=0.022, mat=dark, seg=10, rings=6))
        p.append(C.sphere("cheek", (s * 0.12, -0.16, 0.6), r=1, scale=(0.03, 0.01, 0.02), mat=C.mat("SproutCheek"), seg=10, rings=5))
        p.append(C.sphere("arm", (s * 0.25, -0.08, 0.32), r=1, scale=(0.08, 0.1, 0.16), rot=(25, s * -30, 0), mat=fur, seg=14, rings=8))
        p.append(C.sphere("leg", (s * 0.14, -0.2, 0.09), r=1, scale=(0.09, 0.15, 0.09), mat=fur, seg=14, rings=8))
        p.append(C.sphere("pad", (s * 0.14, -0.33, 0.09), r=1, scale=(0.055, 0.015, 0.055), mat=furl, seg=12, rings=6))
    p.append(C.sphere("muzzle", (0, -0.16, 0.6), r=1, scale=(0.09, 0.07, 0.065), mat=furl, seg=14, rings=8))
    p.append(C.sphere("nose", (0, -0.225, 0.625), r=1, scale=(0.03, 0.02, 0.022), mat=dark, seg=10, rings=6))
    p.append(C.tube("smile", [(-0.025, -0.225, 0.575), (0, -0.23, 0.565), (0.025, -0.225, 0.575)], r=0.004, mat=dark, seg=4, res=3))
    red = M("RibbonRed", "E0674F", rough=0.7)
    p.append(C.torus("ribbon", (0, -0.01, 0.46), R=0.14, r=0.022, scale=(1, 0.9, 0.6), mat=red, seg=24, mseg=6))
    for s in (-1, 1):
        p.append(C.sphere("bow", (s * 0.05, -0.15, 0.47), r=1, scale=(0.05, 0.02, 0.035), rot=(0, s * 20, 0), mat=red, seg=10, rings=6))
    p.append(C.sphere("knot", (0, -0.16, 0.47), r=0.022, mat=red, seg=8, rings=5))
    return finish(p)


def furn_desk():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    W, D, H = 0.95, 0.5, 0.74
    p = [C.box("top", (0, 0, H - 0.04), (W, D, 0.04), mat=wood, bevel=0.012, bseg=2, base=True),
         C.box("apron", (0, -0.0, H - 0.16), (W - 0.1, D - 0.08, 0.12), mat=wood, bevel=0.01, bseg=1, base=True),
         C.box("drawer", (0.18, -D / 2 + 0.035, H - 0.15), (0.34, 0.02, 0.1), mat=C.mat("WoodLight", rough=0.8), bevel=0.008, bseg=1, base=True),
         C.sphere("knob", (0.18, -D / 2 + 0.02, H - 0.1), r=0.015, mat=C.mat("Brass", rough=0.45), seg=8, rings=5),
         C.box("hutch", (0, D / 2 - 0.07, H), (W, 0.12, 0.28), mat=wood, bevel=0.012, bseg=1, base=True),
         C.box("cubby", (-0.22, D / 2 - 0.12, H + 0.02), (0.3, 0.04, 0.22), mat=woodd, bevel=0.0, smooth=False, base=True)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(C.cyl("leg", (sx * (W / 2 - 0.05), sy * (D / 2 - 0.05), 0), r=0.025, r2=0.02, h=H - 0.04, mat=woodd, seg=8, base=True))
    t = H
    # tiny lamp
    p += [C.cyl("lbase", (0.33, 0.08, t), r=0.05, h=0.02, mat=C.mat("Brass"), seg=12, base=True),
          C.tube("lneck", [(0.33, 0.08, t + 0.02), (0.33, 0.06, t + 0.18), (0.3, 0.0, t + 0.24)], r=0.008, mat=C.mat("Brass"), seg=5, res=3)]
    sh = C.lathe("lshade", [(0.02, 0.0), (0.075, -0.08), (0.08, -0.085), (0.0, -0.085)], seg=14, mat=M("GlowLamp", "FFF1C8", rough=0.8, emit="FFD58A", strength=1.0))
    sh.location = (0.3, 0.0, t + 0.27)
    p.append(sh)
    # notebook + pencil
    p.append(C.box("nb", (-0.08, -0.06, t), (0.26, 0.2, 0.02), mat=M("Notebook", "6FA8F5", rough=0.8), bevel=0.004, bseg=1, base=True, rot=(0, 0, -8)))
    p.append(C.box("pages", (-0.08, -0.06, t + 0.02), (0.24, 0.19, 0.004), mat=M("Paper", "FFFFFF", rough=0.9), bevel=0.0, smooth=False, base=True, rot=(0, 0, -8)))
    p.append(C.cyl("pencil", (0.08, -0.12, t + 0.012), r=0.006, h=0.16, rot=(0, 90, 20), mat=M("PencilYellow", "FFD65A"), seg=6))
    cup = C.lathe("cup", [(0, t), (0.04, t), (0.042, t + 0.1), (0.036, t + 0.1), (0.034, t + 0.01), (0, t + 0.01)], seg=12, mat=M("CupPink", "F59BB6", rough=0.6))
    cup.location = (-0.32, 0.05, 0)
    p.append(cup)
    for k, col in enumerate(["E0674F", "4FA3A5", "FFD65A"]):
        a = math.radians(k * 120)
        p.append(C.cyl("pc", (-0.32 + 0.012 * math.cos(a), 0.05 + 0.012 * math.sin(a), t + 0.02), r=0.006, h=0.16, rot=(8 * math.cos(a), 8 * math.sin(a), 0),
                       mat=M("Pencil" + col, col), seg=6, base=True))
    return finish(p)


def furn_toychest():
    teal = M("ChestTeal", "7DC4BF", rough=0.75)
    pink = M("ChestPink", "F4A0B5", rough=0.75)
    yel = M("ChestPaint", "FFD65A", rough=0.75)
    W, D, H = 0.82, 0.5, 0.42
    p = [C.box("chest", (0, 0, 0.04), (W, D, H), mat=teal, bevel=0.03, bseg=2, base=True),
         C.box("lid", (0, 0, H + 0.04), (W + 0.04, D + 0.04, 0.1), mat=pink, bevel=0.04, bseg=3, base=True),
         C.box("band", (0, 0, 0.06), (W + 0.02, D + 0.02, 0.05), mat=pink, bevel=0.015, bseg=1, base=True)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(C.sphere("foot", (sx * (W / 2 - 0.06), sy * (D / 2 - 0.06), 0.03), r=0.035, mat=pink, seg=8, rings=5))
    p.append(C.box("latch", (0, -D / 2 - 0.02, H), (0.08, 0.02, 0.1), mat=C.mat("Brass", rough=0.45), bevel=0.006, bseg=1))
    # painted stars + heart on the front
    for (x, z, s, mat) in [(-0.25, 0.26, 1.0, yel), (0.25, 0.3, 0.8, yel), (0.0, 0.18, 0.7, C.mat("White"))]:
        pts = []
        for i in range(10):
            t = math.pi / 2 + i * math.pi / 5
            r = (0.07 if i % 2 == 0 else 0.03) * s
            pts.append((x + r * math.cos(t), z + r * math.sin(t)))
        p.append(C.prism("star", pts, -D / 2 - 0.006, -D / 2 + 0.002, mat, smooth=False))
    for s in (-1, 1):
        p.append(C.sphere("heart", (s * 0.018, -D / 2 - 0.004, 0.36), r=1, scale=(0.028, 0.004, 0.028), rot=(0, s * -45, 0), mat=pink, seg=10, rings=5))
    # toy peeking out: a little ball on the lid
    p.append(C.sphere("ball", (0.27, 0.05, H + 0.2), r=0.06, mat=M("BallRed", "E0674F", rough=0.6), seg=12, rings=8))
    p.append(C.torus("ballband", (0.27, 0.05, H + 0.2), R=0.06, r=0.008, rot=(90, 0, 0), mat=C.mat("White"), seg=16, mseg=4))
    return finish(p)


def furn_rocker():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    p = []
    for s in (-1, 1):
        pts = [(s * 0.24, -0.45 + 0.9 * t, 0.05 + 0.18 * (2 * t - 1) ** 2) for t in [i / 8 for i in range(9)]]
        p.append(C.tube("rocker", pts, r=0.025, mat=woodd, seg=6, res=3))
        for (y0, y1, h) in [(-0.2, -0.2, 0.42), (0.18, 0.2, 0.42)]:
            p.append(C.tube("leg", [(s * 0.22, y0, 0.07), (s * 0.22, y1, h)], r=0.022, mat=wood, seg=6, res=1))
        p.append(C.tube("backpost", [(s * 0.21, 0.2, 0.42), (s * 0.21, 0.3, 0.8), (s * 0.2, 0.36, 1.05)], r=0.022, mat=wood, seg=6, res=3))
        p.append(C.tube("armrest", [(s * 0.25, -0.22, 0.62), (s * 0.25, 0.26, 0.64)], r=0.022, mat=wood, seg=6, res=1))
        p.append(C.tube("armpost", [(s * 0.23, -0.2, 0.43), (s * 0.25, -0.2, 0.62)], r=0.018, mat=wood, seg=6, res=1))
    p.append(C.box("seat", (0, 0.0, 0.42), (0.46, 0.44, 0.04), mat=wood, bevel=0.015, bseg=2, base=True))
    p.append(C.box("cushion", (0, -0.01, 0.46), (0.4, 0.38, 0.05), mat=M("CushionSage", "A9CFA4", rough=0.9), bevel=0.02, bseg=2, base=True))
    p.append(C.tube("toprail", [(-0.2, 0.36, 1.05), (0, 0.38, 1.08), (0.2, 0.36, 1.05)], r=0.03, mat=wood, seg=6, res=3))
    for k in range(5):
        x = -0.14 + k * 0.07
        p.append(C.tube("spindle", [(x, 0.21, 0.46), (x, 0.36, 1.04)], r=0.012, mat=wood, seg=5, res=1))
    # knitted blanket draped over the back
    bm = bmesh.new()
    rows = []
    for i in range(10):
        t = i / 9
        y = 0.4 - 0.05 * t
        z = 1.1 - 0.55 * t
        row = []
        for j in range(9):
            u = j / 8
            x = -0.2 + 0.4 * u
            row.append(bm.verts.new((x, y + 0.03 * math.sin(u * math.pi * 3) + 0.03 * math.sin(t * math.pi), z)))
        rows.append(row)
    for i in range(9):
        for j in range(8):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
            f.material_index = (i // 2) % 2
    bl = C.mk("blanket", bm, [M("KnitCream", "F6EEDC", rough=0.95), M("KnitRose", "F2A6B4", rough=0.95)])
    for v in bl.data.vertices:                 # drape over the top rail toward the front
        if v.co.z > 1.02:
            v.co.y -= (v.co.z - 1.02) * 2.0
    so = bl.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.025
    C.apply_mods(bl)
    C.shade(bl, 60)
    p.append(bl)
    return finish(p)


# ------------------------------------------------------------------ wall items (origin: back-centre contact point; extend toward -Y)
def furn_poster_sun():
    frame = C.mat("WoodDark", rough=0.8)
    W, H = 0.6, 0.8
    p = [C.box("frame", (0, -0.02, 0), (W, 0.04, H), mat=frame, bevel=0.01, bseg=1)]
    bands = ["FFB35C", "FF9E7A", "F28FB0", "B79BE8", "7C74C9"]
    bh = (H - 0.08) / len(bands)
    for k, col in enumerate(bands):
        z = -H / 2 + 0.04 + bh * (k + 0.5)
        p.append(C.box("band", (0, -0.042, z), (W - 0.08, 0.004, bh + 0.001), mat=M("Poster" + col, col, rough=0.9), bevel=0.0, smooth=False))
    p.append(C.cyl("sun", (0, -0.046, -0.12), r=0.16, h=0.004, rot=(90, 0, 0), mat=M("PosterSun", "FFD65A", rough=0.8), seg=28, smooth=False))
    p.append(C.cyl("sunring", (0, -0.044, -0.12), r=0.2, h=0.003, rot=(90, 0, 0), mat=M("PosterSunGlow", "FFC88A", rough=0.8), seg=28, smooth=False))
    hill = C.sphere("hill", (0, -0.048, -H / 2 + 0.04), r=1, scale=(0.3, 0.004, 0.14), mat=M("PosterHill", "7BC96F", rough=0.9), seg=24, rings=8)
    for v in hill.data.vertices:
        v.co.z = max(v.co.z, -H / 2 + 0.04 - (-H / 2 + 0.04))
    p.append(hill)
    p.append(C.box("hillcut", (0, -0.048, -H / 2 + 0.06), (W - 0.08, 0.005, 0.04), mat=M("PosterHill", "7BC96F"), bevel=0.0, smooth=False))
    for k in range(3):
        p.append(C.sphere("bird", (-0.15 + k * 0.06, -0.049, 0.18 + 0.03 * (k % 2)), r=1, scale=(0.02, 0.002, 0.006), rot=(0, 15 - 30 * (k % 2), 0),
                          mat=M("PosterInk", "3B3040"), seg=8, rings=4))
    return finish(p)


def furn_clock():
    wood = C.mat("Wood", rough=0.8)
    face = M("ClockFace", "FFF6E6", rough=0.85)
    ink = M("ClockInk", "3B3040", rough=0.6)
    R = 0.22
    p = [C.cyl("back", (0, -0.03, 0), r=R, h=0.06, rot=(90, 0, 0), mat=wood, seg=32, bevel=0.012, bseg=1),
         C.torus("rim", (0, -0.06, 0), R=R - 0.01, r=0.025, rot=(90, 0, 0), mat=M("ClockRim", "E0674F", rough=0.6), seg=32, mseg=6),
         C.cyl("face", (0, -0.062, 0), r=R - 0.03, h=0.004, rot=(90, 0, 0), mat=face, seg=32, smooth=False)]
    for k in range(12):
        a = math.radians(90 - k * 30)
        rr = R - 0.07
        big = k % 3 == 0
        p.append(C.sphere("tick", (rr * math.cos(a), -0.066, rr * math.sin(a)), r=0.013 if big else 0.007, scale=(1, 0.3, 1), mat=ink, seg=8, rings=4))
    for (ang, L, w) in [(60, 0.09, 0.012), (-80, 0.13, 0.008)]:
        a = math.radians(90 - ang)
        hand = C.box("hand", (0, 0, 0), (w, 0.004, L), mat=ink, bevel=0.0, smooth=False)
        hand.data.transform(Matrix.Translation((0, 0, L / 2)))
        hand.data.transform(Matrix.Rotation(-math.radians(ang), 4, 'Y'))
        hand.location = (0, -0.07, 0)
        C.bake_transform(hand)
        p.append(hand)
    p.append(C.cyl("pin", (0, -0.074, 0), r=0.012, h=0.008, rot=(90, 0, 0), mat=C.mat("Brass", rough=0.45), seg=10))
    for s in (-1, 1):
        p.append(C.sphere("bell", (s * 0.12, -0.03, R + 0.03), r=0.05, scale=(1, 1, 0.8), mat=C.mat("Brass"), seg=12, rings=6))
    return finish(p)


def furn_garland():
    glow = M("GlowLamp", "FFF1C8", rough=0.6, emit="FFD58A", strength=1.0)
    wire = M("Cord", "5A4636", rough=0.9)
    p = []
    anchors = [-0.55, 0.0, 0.55]
    for x in anchors:
        p.append(C.cyl("nail", (x, -0.01, 0.0), r=0.01, h=0.03, rot=(90, 0, 0), mat=C.mat("Brass", rough=0.45), seg=6))
    pts = []
    for i in range(21):
        t = i / 20
        x = -0.55 + 1.1 * t
        seg_t = (t * 2) % 1.0
        z = -0.16 * math.sin(math.pi * seg_t)
        pts.append(Vector((x, -0.03, z)))
    p.append(C.tube("wire", pts, r=0.005, mat=wire, seg=4, res=2))
    cols = ["FFD58A", "FFB3C0", "FFD58A", "B8E6FF"]
    for i in range(1, 20, 2):
        q = pts[i]
        p.append(C.cyl("cap", q + Vector((0, 0, -0.015)), r=0.012, h=0.02, mat=wire, seg=6))
        p.append(C.sphere("bulb", q + Vector((0, -0.005, -0.045)), r=1, scale=(0.022, 0.022, 0.03), mat=glow, seg=10, rings=6))
    return finish(p)


def furn_shelf():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    W, D = 0.72, 0.2
    p = [C.box("plank", (0, -D / 2, 0.0), (W, D, 0.04), mat=wood, bevel=0.012, bseg=2, base=True)]
    for s in (-1, 1):
        br = C.prism("bracket", [(0, 0), (0.0, -0.16), (-0.14, 0)], -0.015, 0.015, woodd, bevel=0.005, bseg=1)
        br.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
        br.location = (s * (W / 2 - 0.1), 0, 0)
        C.bake_transform(br)
        p.append(br)
    t = 0.04
    for (x, col) in [(-0.24, "D9804F"), (0.02, "5DB3B5")]:
        pot = C.lathe("pot", [(0, t), (0.045, t), (0.055, t + 0.09), (0, t + 0.09)], seg=12, mat=M("Pot" + col, col, rough=0.8))
        pot.location = (x, -D / 2, 0)
        p.append(pot)
        p.append(C.sphere("leafy", (x, -D / 2, t + 0.13), r=1, scale=(0.07, 0.07, 0.06), mat=C.mat("Leaf", rough=0.8), seg=10, rings=6))
    # trailing ivy from the second pot
    ivy = [Vector((0.06, -D / 2 - 0.02, t + 0.1)), Vector((0.1, -D - 0.02, t)), Vector((0.14, -D - 0.03, -0.12)), Vector((0.12, -D - 0.02, -0.26))]
    p.append(C.tube("vine", ivy, r=0.006, mat=C.mat("Stem"), seg=4, res=4))
    for k in range(5):
        q = ivy[1] + (ivy[3] - ivy[1]) * (k / 4)
        lf = C.leaf("ivy", length=0.05, width=0.03, thick=0.005, curl=0.0, mat=C.mat("LeafDark", rough=0.8), seg=6, rings=4)
        lf.data.transform(C.xform(rot=(80, 0, 90 + 60 * (-1) ** k)))
        lf.location = q
        C.bake_transform(lf)
        p.append(lf)
    jar = C.lathe("jar", [(0, t), (0.05, t), (0.055, t + 0.12), (0.035, t + 0.14), (0, t + 0.14)], seg=14, mat=M("Jar", "CFE8F5", rough=0.15, spec=0.8))
    jar.location = (0.25, -D / 2, 0)
    p += [jar, C.cyl("jarlid", (0.25, -D / 2, t + 0.14), r=0.038, h=0.025, mat=M("JarLid", "E0674F"), seg=12, base=True)]
    for k in range(3):
        p.append(C.cyl("cookie", (0.25, -D / 2, t + 0.02 + k * 0.035), r=0.035, h=0.015, rot=(0, 0, 0), mat=M("Cookie", "D9A45F"), seg=10, base=True))
    return finish(p)


for _n in FLOOR + WALL:
    globals()["build_furn_" + _n] = globals()["furn_" + _n]

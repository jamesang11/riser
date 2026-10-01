"""Cozy outdoor sick bed for the sprout (root `SickBed`)."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import common as C
import a_sprout

MAT_TOP = 0.45          # mattress top
SCALE = 2.1             # app scale of the sprout
LIE_Y = -0.55           # sprout origin (bottom centre) along the bed; head (top) toward the pillow (+Y)
HALF_DEPTH = 0.21 * SCALE   # sprout body half-depth -> how high its origin sits above the mattress when lying


def pose_sprout(sp):
    sp.scale = (SCALE,) * 3
    sp.rotation_euler = (math.radians(-90), 0, 0)
    sp.location = (0, LIE_Y, MAT_TOP + HALF_DEPTH)
    C.update()


def sprout_height(bodies, x, y):
    best = None
    for b in bodies:
        ok, loc, n, _ = body_ray(b, Vector((x, y, 5)), Vector((0, 0, -1)))
        if ok and (best is None or loc.z > best):
            best = loc.z
    return best


def body_ray(obj, origin, direction):
    mi = obj.matrix_world.inverted()
    o = mi @ origin
    d = (mi.to_3x3() @ direction).normalized()
    ok, loc, n, idx = obj.ray_cast(o, d)
    if ok:
        return ok, obj.matrix_world @ loc, n, idx
    return ok, None, None, None


def quilt(body):
    cols = [C.mat("QuiltPink", "F7B7C9", rough=0.95), C.mat("QuiltBlue", "A8D0F0", rough=0.95), C.mat("QuiltMint", "A8E0C8", rough=0.95),
            C.mat("QuiltButter", "FFE9A8", rough=0.95), C.mat("QuiltLilac", "D0B8F0", rough=0.95)]
    back = C.mat("QuiltBack", "F6EEDC", rough=0.95)
    x0, x1, y0, y1 = -0.76, 0.76, -1.02, -0.43
    nx, ny = 24, 16
    H = [[0.0] * (ny + 1) for _ in range(nx + 1)]
    S = [[None] * (ny + 1) for _ in range(nx + 1)]
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            z = MAT_TOP + 0.03
            if abs(x) > 0.66:
                z -= min(0.22, (abs(x) - 0.66) * 2.4)
            if y < -0.94:
                z -= min(0.22, (-0.94 - y) * 2.8)
            sz = sprout_height(body, x, y) if body else None
            S[i][j] = sz
            if sz is not None:
                z = max(z, sz + 0.045)
            H[i][j] = z
    for it in range(4):                          # soften into a drape, never cutting into the body
        N = [row[:] for row in H]
        for i in range(1, nx):
            for j in range(1, ny):
                N[i][j] = (H[i][j] * 2 + H[i - 1][j] + H[i + 1][j] + H[i][j - 1] + H[i][j + 1]) / 6
                if S[i][j] is not None:
                    N[i][j] = max(N[i][j], S[i][j] + 0.04)
        H = N
    bm = bmesh.new()
    V = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, H[i][j])) for j in range(ny + 1)] for i in range(nx + 1)]
    patch = 0.19
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            c = f.calc_center_median()
            f.material_index = int(math.floor(c.x / patch) * 2 + math.floor(c.y / patch) * 3) % len(cols)
    q = C.mk("quiltsheet", bm, cols)
    so = q.modifiers.new("Sol", 'SOLIDIFY')
    so.thickness = 0.035
    so.offset = -1
    so.material_offset_rim = 0
    C.apply_mods(q)
    C.shade(q, 60)
    # folded-back top edge (cream underside showing), tucked under the chin
    fold = []
    j = ny
    pts = [Vector((x0 + (x1 - x0) * i / nx, y1, H[i][j])) for i in range(nx + 1)]
    bm = bmesh.new()
    rowA = [bm.verts.new(p + Vector((0, 0.01, 0.012))) for p in pts]
    rowB = [bm.verts.new(p + Vector((0, -0.11, 0.02))) for p in pts]
    for i in range(nx):
        bm.faces.new((rowA[i], rowA[i + 1], rowB[i + 1], rowB[i]))
    fo = C.mk("fold", bm, [back])
    for k, v in enumerate(fo.data.vertices):             # rest the fold on the quilt surface
        if k >= nx + 1:
            ii = k - (nx + 1)
            jj = max(0, ny - int(0.11 / ((y1 - y0) / ny)))
            v.co.z = max(v.co.z, H[ii][jj] + 0.03)
    so = fo.modifiers.new("Sol", 'SOLIDIFY'); so.thickness = 0.03
    C.apply_mods(fo)
    roll = C.tube("roll", [p + Vector((0, -0.005, 0.012)) for p in pts[::3]], r=0.018, mat=back, seg=6, res=3)
    # hot-water bottle resting on the quilt at the foot
    hx, hy = 0.42, -0.8
    hz = H[int((hx - x0) / (x1 - x0) * nx)][int((hy - y0) / (y1 - y0) * ny)]
    hwb = [C.box("hwb", (hx, hy, hz + 0.035), (0.26, 0.34, 0.07), mat=C.mat("HotWater", "F28B8B", rough=0.6), bevel=0.03, bseg=3),
           C.cyl("neck", (hx, hy + 0.2, hz + 0.035), r=0.035, h=0.06, rot=(90, 0, 0), mat=C.mat("HotWater"), seg=10),
           C.cyl("cap", (hx, hy + 0.24, hz + 0.035), r=0.04, h=0.03, rot=(90, 0, 0), mat=C.mat("HotWaterCap", "F6EEDC", rough=0.5), seg=10),
           C.sphere("heart", (hx, hy - 0.02, hz + 0.072), r=1, scale=(0.05, 0.045, 0.006), mat=C.mat("QuiltBack"), seg=10, rings=4)]
    return C.join([q, fo, roll] + hwb, "Quilt")


def bed_frame():
    wood = C.mat("Wood", rough=0.8)
    woodd = C.mat("WoodDark", rough=0.8)
    W, L = 1.4, 2.0
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = 1.2 if sy > 0 else 0.72
            parts.append(C.cyl("post", (sx * (W / 2 - 0.05), sy * (L / 2 - 0.05), 0), r=0.06, h=h, mat=woodd, seg=12, base=True, bevel=0.02, bseg=1))
            parts.append(C.sphere("knob", (sx * (W / 2 - 0.05), sy * (L / 2 - 0.05), h + 0.04), r=0.075, mat=woodd, seg=12, rings=8))
    for sx in (-1, 1):
        parts.append(C.box("rail", (sx * (W / 2 - 0.05), 0, 0.26), (0.07, L - 0.12, 0.14), mat=wood, bevel=0.025, bseg=2))
    head = C.prism("head", C.arch_pts(W - 0.14, 1.12, 16, 0.2), L / 2 - 0.09, L / 2 - 0.02, wood, bevel=0.02, bseg=2)
    for v in head.data.vertices:                        # flatten the arch a bit
        if v.co.z > 0.9:
            v.co.z = 0.9 + (v.co.z - 0.9) * 0.55
    parts.append(head)
    parts.append(C.sphere("heart1", (-0.05, L / 2 - 0.1, 0.92), r=1, scale=(0.07, 0.02, 0.07), rot=(0, 45, 0), mat=C.mat("Blossom"), seg=12, rings=6))
    parts.append(C.sphere("heart2", (0.05, L / 2 - 0.1, 0.92), r=1, scale=(0.07, 0.02, 0.07), rot=(0, -45, 0), mat=C.mat("Blossom"), seg=12, rings=6))
    foot = C.prism("foot", C.arch_pts(W - 0.14, 0.5, 12, 0.2), -L / 2 + 0.02, -L / 2 + 0.09, wood, bevel=0.02, bseg=2)
    parts.append(foot)
    mattress = C.box("mattress", (0, 0, MAT_TOP - 0.2), (W - 0.16, L - 0.2, 0.2), mat=C.mat("Mattress", "F7F2E8", rough=0.9), bevel=0.06, bseg=3, base=True)
    parts.append(mattress)
    parts.append(C.box("sheetband", (0, 0, MAT_TOP - 0.17), (W - 0.14, L - 0.18, 0.05), mat=C.mat("QuiltBlue", "A8D0F0", rough=0.95), bevel=0.02, bseg=1, base=True))
    pil = C.box("pillow", (0, 0.66, MAT_TOP), (0.92, 0.46, 0.2), mat=C.mat("Pillow", "FFFFFF", rough=0.9), bevel=0.09, bseg=4, base=True)
    for v in pil.data.vertices:                         # puffy middle, pinched corners
        k = 1 - min(1, (abs(v.co.x) / 0.46) ** 2 + (abs(v.co.y - 0.0) / 0.23) ** 2) * 0.35
        v.co.z = MAT_TOP + (v.co.z - MAT_TOP) * (0.6 + 0.6 * k)
    pil.data.transform(Matrix.Translation((0, 0, 0)))
    parts.append(pil)
    return parts


def stool():
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    sx, sy = 1.02, 0.6
    parts = [C.cyl("seat", (sx, sy, 0.42), r=0.2, h=0.06, mat=wood, seg=18, base=True, bevel=0.02, bseg=2)]
    for k in range(3):
        a = math.radians(90 + 120 * k)
        parts.append(C.tube("leg", [(sx + 0.13 * math.cos(a), sy + 0.13 * math.sin(a), 0.42), (sx + 0.17 * math.cos(a), sy + 0.17 * math.sin(a), 0.0)],
                            r=0.025, mat=woodd, seg=6, res=1))
    top = 0.48
    mug = C.lathe("mug", [(0, top), (0.055, top), (0.06, top + 0.11), (0.052, top + 0.11), (0.048, top + 0.015), (0, top + 0.015)], seg=16,
                  mat=C.mat("MugTeal", "5DB3B5", rough=0.5))
    mug.location = (sx - 0.06, sy - 0.05, 0)
    parts.append(mug)
    parts.append(C.torus("handle", (sx - 0.06 + 0.065, sy - 0.05, top + 0.055), R=0.03, r=0.009, rot=(90, 0, 0), mat=C.mat("MugTeal"), seg=12, mseg=5))
    parts.append(C.cyl("cocoa", (sx - 0.06, sy - 0.05, top + 0.09), r=0.05, h=0.004, mat=C.mat("Cocoa", "8B5A3C", rough=0.4), seg=14))
    steam = C.mat("Steam", "FFFFFF", rough=1.0)
    for k, dx in enumerate((-0.02, 0.02)):
        base = Vector((sx - 0.06 + dx, sy - 0.05, top + 0.12))
        pts = [base + Vector((0.015 * math.sin(i * 1.3 + k), 0, i * 0.035)) for i in range(5)]
        parts.append(C.tube("steam", pts, r=0.008, radii=[1.0, 1.0, 0.9, 0.7, 0.4], mat=steam, seg=6, res=3))
    parts.append(C.box("tissuebox", (sx + 0.08, sy + 0.07, top), (0.16, 0.11, 0.1), mat=C.mat("TissueBox", "F7B7C9", rough=0.8), bevel=0.012, bseg=2, base=True))
    parts.append(C.box("tbstripe", (sx + 0.08, sy + 0.07, top + 0.045), (0.165, 0.115, 0.018), mat=C.mat("QuiltBack", "F6EEDC", rough=0.95), bevel=0.004, bseg=1))
    t = C.lathe("tissue", [(0, top + 0.1), (0.035, top + 0.12), (0.02, top + 0.17), (0, top + 0.16)], seg=8, mat=C.mat("Pillow", "FFFFFF", rough=0.9),
                rfun=lambda a, z: 1 + 0.35 * math.cos(2 * a))
    t.location = (sx + 0.08, sy + 0.07, 0)
    parts.append(t)
    return parts


def build_sickbed(keep_sprout=False):
    root = C.empty("SickBed")
    sp = a_sprout.build_sprout()
    pose_sprout(sp)
    body = [o for o in sp.children_recursive if o.type == 'MESH' and o.name in ("Body", "ArmL", "ArmR", "FootL", "FootR")]
    frame = C.join(bed_frame() + stool(), "BedFrame")
    C.set_origin(frame, (0, 0, 0))
    C.set_parent(frame, root)
    q = quilt(body)
    C.set_origin(q, (0, -0.65, MAT_TOP))
    C.set_parent(q, root)
    C.empty("LiePoint", (0, LIE_Y, MAT_TOP), parent=root)
    C.empty("SproutOrigin", (0, LIE_Y, MAT_TOP + HALF_DEPTH), parent=root)
    C.empty("QuiltCover", (0, -0.65, MAT_TOP), parent=root)
    if keep_sprout:
        return root, sp
    for o in [sp] + list(sp.children_recursive):
        bpy.data.objects.remove(o)
    return root

"""Puffy cloud clock glyphs: 0-9, colon, A, P, M, plus R, I, S, E for the "RISER" logo.

Each glyph = stroke skeleton (XZ plane, cap height 1) -> spheres along strokes + outward cumulus
puffs -> voxel remesh + smooth -> flattened bottom -> normalised to cap height 1.0.
"""
import math, random
from mathutils import Vector, Matrix
import common as C

W, B, T = 0.2, 0.115, 0.885          # skeleton half-width, bottom, top (stroke radius ~0.115)
R = 0.102                            # core stroke radius
DEPTH = 1.45                         # y stretch of puffs (depth ~0.33)


def arc(cx, cz, rx, rz, a0, a1, n=None):
    n = n or max(4, int(abs(a1 - a0) / 12))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + rz * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


COUNTERS = {"0": [(0, 0.5)], "4": [(-0.02, 0.5)], "6": [(0, 0.315)], "8": [(0, 0.7), (0, 0.3)], "9": [(0, 0.685)],
            "A": [(0, 0.6)], "P": [(0.0, 0.69)], "R": [(0.0, 0.69)], "2": [(0, 0.62)], "3": [(-0.05, 0.7), (-0.05, 0.3)], "5": [(-0.05, 0.3)]}


def strokes(ch):
    if ch == "0":
        return [arc(0, 0.5, W, 0.385, 0, 360, 36)]
    if ch == "1":
        return [[(0.04, B), (0.04, T), (-0.15, T - 0.16)], [(-0.13, B), (0.19, B)]]
    if ch == "2":
        return [arc(0, 0.7, W, 0.185, 155, -35) + [(-W, B), (W + 0.01, B)]]
    if ch == "3":
        return [arc(0, 0.705, W * 0.9, 0.18, 150, -90), arc(0, 0.305, W, 0.19, 90, -150)]
    if ch == "4":
        return [[(-0.03, T), (-W - 0.01, 0.36), (W + 0.02, 0.36)], [(0.11, 0.63), (0.11, B)]]
    if ch == "5":
        return [[(W, T), (-0.15, T), (-0.17, 0.53)] + arc(0.0, 0.33, W, 0.215, 125, -150)]
    if ch == "6":
        return [arc(0.05, 0.33, 0.25, 0.555, 72, 180, 10), arc(0, 0.315, W, 0.2, 0, 360, 30)]
    if ch == "7":
        return [[(-W, T), (W, T), (-0.05, B)]]
    if ch == "8":
        return [arc(0, 0.7, 0.175, 0.185, 0, 360, 26), arc(0, 0.3, W, 0.19, 0, 360, 30)]
    if ch == "9":
        return [arc(-0.05, 0.667, 0.25, 0.555, -108, 0, 10), arc(0, 0.685, W, 0.2, 0, 360, 30)]
    if ch == "A":
        return [[(-0.26, B), (-0.2, 0.66)] + arc(0, 0.68, 0.2, 0.205, 180, 0, 12) + [(0.2, 0.66), (0.26, B)], [(-0.2, 0.39), (0.2, 0.39)]]
    if ch == "P":
        return [[(-0.17, B), (-0.17, T), (0.02, T)] + arc(0.02, 0.695, 0.18, 0.19, 90, -90) + [(-0.17, 0.505)]]
    if ch == "R":
        return [[(-0.17, B), (-0.17, T), (0.02, T)] + arc(0.02, 0.695, 0.18, 0.19, 90, -90) + [(-0.17, 0.505)], [(0.02, 0.505), (0.23, B)]]
    if ch == "I":
        return [[(0.0, B), (0.0, T)]]
    if ch == "S":
        return [arc(0, 0.705, W * 0.95, 0.18, 25, 270) + arc(0, 0.3, W, 0.2, 90, -155)]
    if ch == "E":
        return [[(0.18, T), (-0.17, T), (-0.17, B), (0.18, B)], [(-0.17, 0.5), (0.11, 0.5)]]
    if ch == "M":
        return [[(-0.31, B), (-0.3, T), (0.0, 0.44), (0.3, T), (0.31, B)]]
    raise ValueError(ch)


def resample(poly, step):
    pts = [Vector((x, 0, z)) for x, z in poly]
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        d = (b - a).length
        n = max(1, int(d / step))
        for i in range(1, n + 1):
            out.append(a + (b - a) * (i / n))
    return out


def glyph_spheres(ch, rnd):
    sph = []
    if ch == "colon":
        for z in (0.29, 0.71):
            c = Vector((0, 0, z))
            sph.append((c, 0.1, (1, DEPTH * 0.95, 1)))
            for k in range(5):
                a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
                sph.append((c + Vector((0.07 * math.cos(a), rnd.uniform(-0.02, 0.02), 0.07 * math.sin(a))), 0.055, (1, DEPTH * 0.9, 1)))
        return sph
    for poly in strokes(ch):
        pts = resample(poly, 0.035)
        for p in pts:
            sph.append((p, R, (1, DEPTH, 1)))
        # cumulus puffs: bulge outward on alternating sides + a few on the front face
        acc = rnd.uniform(0, 0.06)
        cnt = COUNTERS.get(ch, [])
        for i in range(1, len(pts) - 1):
            acc += (pts[i] - pts[i - 1]).length
            if acc < 0.12:
                continue
            acc = rnd.uniform(-0.015, 0.015)
            t = (pts[i + 1] - pts[i - 1]).normalized()
            nrm = Vector((-t.z, 0, t.x))
            if cnt:
                # bulge away from the nearest counter (keeps holes open)
                c = min(cnt, key=lambda q: (Vector((q[0], 0, q[1])) - pts[i]).length)
                cv = Vector((c[0], 0, c[1]))
                side = 1 if (pts[i] + nrm - cv).length > (pts[i] - nrm - cv).length else -1
                if (pts[i] - cv).length > 0.33:
                    side = rnd.choice((-1, 1))
            else:
                side = rnd.choice((-1, 1))
            off = nrm * side * rnd.uniform(0.065, 0.08)
            sph.append((pts[i] + off, rnd.uniform(0.085, 0.1), (1, DEPTH * 0.95, 1)))
            if rnd.random() < 0.6:
                sph.append((pts[i] + Vector((rnd.uniform(-0.02, 0.02), -0.075, rnd.uniform(-0.02, 0.02))), rnd.uniform(0.068, 0.08), (1, 1.1, 1)))
        # rounded end caps
        for p in (pts[0], pts[-1]):
            sph.append((p, R * 1.08, (1, DEPTH, 1)))
    return sph


def build_glyph(ch):
    rnd = random.Random(sum(map(ord, ch)) * 7 + 3)
    root = C.empty("Glyph")
    m = C.mat("CloudGlyph", "FFFFFF", rough=1.0, spec=0.2)
    o = C.blob("GlyphMesh", glyph_spheres(ch, rnd), mat=m, voxel=0.021, smooth_iter=3, target=3000)
    C.update()
    mn, mx = C.world_bbox([o])
    # flatter cloud bottom: squash the lowest band
    zb = mn.z + 0.035
    for v in o.data.vertices:
        if v.co.z < zb:
            v.co.z = zb + (v.co.z - zb) * 0.35
    C.update()
    mn, mx = C.world_bbox([o])
    if ch != "colon":
        k = 1.0 / (mx.z - mn.z)
        o.data.transform(Matrix.Scale(k, 4))
        if ch.isdigit():
            # tabular digits: nudge every digit toward 0.64 wide
            w = (mx.x - mn.x) * k
            kx = max(0.85, min(1.15, 0.64 / w))
            o.data.transform(Matrix.Diagonal((kx, 1, 1, 1)))
        C.update()
        mn, mx = C.world_bbox([o])
        o.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    else:
        o.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, 0)))
    C.shade(o, 180)
    import bpy
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    o.data.name = "GlyphMesh"
    C.set_parent(o, root)
    return root


GLYPHS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "colon", "A", "P", "M", "R", "I", "S", "E"]

for _g in GLYPHS:
    globals()["build_glyph_" + _g] = (lambda g=_g: build_glyph(g))

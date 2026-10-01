"""Illustrated postcards (1200x800 JPEG) built from the Riser asset kit.

Blender -b -P postcards.py -- <id ...|all> [--small]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler, noise
import common as C
import a_nature, a_balloon, a_sprout, a_island, a_props, a_buildings, a_harvest, a_farm, a_crops

OUT_DIR = "/Users/jamesangrellera/RIZER/Riser/Resources/Images"
IDS = ["meadow", "woods", "beach", "mushroom", "harbor", "caves", "peaks", "moon", "farm"]


# ------------------------------------------------------------------------------------ helpers
def world(bottom, mid, top, amb_col, amb, mid_pos=0.45):
    w = bpy.data.worlds.new("PCWorld")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].color = C.hex_lin(bottom)
    cr.elements[1].color = C.hex_lin(top)
    cr.elements.new(mid_pos).color = C.hex_lin(mid)
    bgc = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(ramp.outputs[0], bgc.inputs[0])
    bgl = nt.nodes.new("ShaderNodeBackground")
    bgl.inputs[0].default_value = C.hex_lin(amb_col)
    bgl.inputs[1].default_value = amb
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bgl.outputs[0], mix.inputs[1])
    nt.links.new(bgc.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return w


def glare(threshold=0.9, strength=0.6, size=0.6):
    s = bpy.context.scene
    ng = bpy.data.node_groups.new("PCComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    g = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    for attr, val in (("glare_type", 'FOG_GLOW'), ("quality", 'HIGH'), ("size", 8), ("threshold", threshold), ("mix", 0.0)):
        try:
            setattr(g, attr, val)
        except Exception:
            pass
    for key, val in (("Type", 'Fog Glow'), ("Quality", 'High'), ("Threshold", threshold), ("Size", size), ("Strength", strength)):
        if key in g.inputs:
            try:
                g.inputs[key].default_value = val
            except Exception:
                pass
    ng.links.new(rl.outputs["Image"], g.inputs["Image"])
    ng.links.new(g.outputs["Image"], out.inputs[0])
    s.compositing_node_group = ng


def cam(loc, target, lens=35):
    d = Vector(loc) - Vector(target)
    return C.camera(target, d.normalized(), d.length, lens=lens, name="PCCam")


def dup(root, loc=(0, 0, 0), rz=0.0, s=1.0, copy_data=False):
    """Instance a hierarchy (linked mesh data unless copy_data)."""
    mp = {}
    for o in [root] + list(root.children_recursive):
        n = o.copy()
        if copy_data and o.data is not None:
            n.data = o.data.copy()
        C.link(n)
        mp[o] = n
    for o, n in mp.items():
        if o.parent in mp:
            n.parent = mp[o.parent]
    r = mp[root]
    r.location = loc
    r.rotation_euler = (0, 0, math.radians(rz))
    r.scale = (s, s, s)
    return r


def hide_tree(root):
    for o in [root] + list(root.children_recursive):
        o.hide_render = True
        o.hide_viewport = True
    return root


def blob_hill(name, loc, scale, col, seg=64, rough=0.95):
    return C.sphere(name, loc, r=1, scale=scale, mat=C.mat(name + "M", col, rough=rough), seg=seg, rings=seg // 2)


def sprout_default(sp):
    for o in sp.children_recursive:
        base = o.name.split(".")[0]
        if base in ("Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"):
            o.hide_render = True


def balloon_with_sprout(loc, s=1.0, rz=0.0):
    b = a_balloon.build_balloon()
    sp = a_sprout.build_sprout()
    sprout_default(sp)
    seat = [o for o in b.children if o.name.startswith("SeatPoint")][0]
    C.update()
    sp.location = seat.matrix_world.to_translation()
    sp.scale = (0.8,) * 3
    C.set_parent(sp, b)
    b.location = loc
    b.rotation_euler = (0, math.radians(8), math.radians(rz))
    b.scale = (s, s, s)
    return b


def recolor(root, old, new):
    for o in [root] + list(root.children_recursive):
        if o.type == 'MESH':
            for i, m in enumerate(o.data.materials):
                if m and m.name == old:
                    o.data.materials[i] = new


def sun(rot, strength, col, angle=4):
    return C.sun(rot, strength, col=col, angle=angle, name="PCSun")


def emit_mat(name, col, strength, base=None):
    return C.mat(name, base or col, rough=0.8, emit=col, strength=strength)


def blended_emission(name, col_a, col_b, alpha=0.6, strength=3.0, streaks=False):
    """Emissive, semi-transparent material with a vertical fade (for aurora curtains / rays)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        m.blend_method = 'BLEND'
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = C.hex_lin(col_a)
    ramp.color_ramp.elements[1].color = C.hex_lin(col_b)
    fade = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs["Z"], fade.inputs[0])
    fr = fade.color_ramp
    fr.elements[0].position = 0.0
    fr.elements[0].color = (0, 0, 0, 1)
    fr.elements[1].position = 1.0
    fr.elements[1].color = (0, 0, 0, 1)
    fr.elements.new(0.25).color = (alpha, alpha, alpha, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[1].default_value = strength
    nt.links.new(ramp.outputs[0], em.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    fac = fade.outputs[0]
    if streaks:
        xf = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(sep.outputs["X"], xf.inputs[0])
        xr = xf.color_ramp
        xr.elements[0].color = (0, 0, 0, 1)
        xr.elements[1].color = (0, 0, 0, 1)
        xr.elements.new(0.2).color = (1, 1, 1, 1)
        xr.elements.new(0.8).color = (1, 1, 1, 1)
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type = 'BANDS'
        wv.bands_direction = 'X'
        wv.inputs["Scale"].default_value = 6.0
        wv.inputs["Distortion"].default_value = 6.0
        nt.links.new(tc.outputs["Generated"], wv.inputs["Vector"])
        m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'
        m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'
        m3 = nt.nodes.new("ShaderNodeMath"); m3.operation = 'MULTIPLY_ADD'
        nt.links.new(wv.outputs["Fac"], m3.inputs[0]); m3.inputs[1].default_value = 0.7; m3.inputs[2].default_value = 0.3
        nt.links.new(fade.outputs[0], m1.inputs[0]); nt.links.new(xf.outputs[0], m1.inputs[1])
        nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(m3.outputs[0], m2.inputs[1])
        fac = m2.outputs[0]
    nt.links.new(fac, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def scatter_flowers(rnd, n, xr, yr, zfun, cols, scale=(1.4, 2.0)):
    for i in range(n):
        x, y = rnd.uniform(*xr), rnd.uniform(*yr)
        f = a_island.tiny_flower(rnd, cols[i % len(cols)])
        s = rnd.uniform(*scale)
        f.scale = (s, s, s)
        f.location = (x, y, zfun(x, y))


def hill_z(hills, x, y):
    best = 0.0
    for h in hills:
        ok, loc, n, _ = h.ray_cast(h.matrix_world.inverted() @ Vector((x, y, 50)), Vector((0, 0, -1)))
        if ok:
            best = max(best, (h.matrix_world @ loc).z)
    return best


# ------------------------------------------------------------------------------------ scenes
def scene_meadow():
    rnd = random.Random(1)
    world("FFE6CF", "CDEBF7", "7CC4EE", "D9ECF7", 0.7)
    sun((62, 0, -40), 3.2, "FFE8C8")
    hills = [blob_hill("h1", (0, 2, -6.2), (14, 7, 6.6), "86CF73"),
             blob_hill("h2", (-9, 20, -7.5), (16, 9, 9), "9ED88A"),
             blob_hill("h3", (12, 26, -8.5), (18, 10, 10.5), "AEDC98"),
             blob_hill("h4", (0, 45, -9), (40, 14, 11), "BCE3AA")]
    hz = lambda x, y: hill_z(hills[:1], x, y)
    tuft_src = a_island.grass_tuft("tuftsrc", rnd, 2.2)
    tree = a_nature.build_tree_round()
    for (x, y, s) in [(-7, 17, 1.2), (-4.5, 19, 0.9), (8, 22, 1.4), (11, 24, 1.1), (3, 33, 1.3), (-12, 30, 1.2)]:
        dup(tree, (x, y, hill_z(hills[1:3], x, y) - 0.1), rnd.uniform(0, 360), s)
    hide_tree(tree)
    patch = a_nature.build_flowers()
    for (x, y, s) in [(-3.2, 2.5, 1.3), (2.8, 4.0, 1.1), (-0.6, 6.5, 1.0), (4.6, 1.6, 1.2)]:
        dup(patch, (x, y, hz(x, y) - 0.08), rnd.uniform(0, 360), s)
    hide_tree(patch)
    scatter_flowers(rnd, 150, (-7, 7), (-1.5, 9), hz, ["White", "FlowerYellow", "Blossom", "Purple", "BlossomDeep", "White"], scale=(2.0, 3.0))
    for i in range(40):
        x, y = rnd.uniform(-7, 7), rnd.uniform(0.5, 9)
        t = tuft_src.copy(); C.link(t)
        t.location = (x, y, hz(x, y) - 0.02)
        t.rotation_euler = (0, 0, rnd.uniform(0, 6))
    hide_tree(tuft_src)
    # morning dew: glossy droplets catching light
    dew = C.mat("Dew", "DFF6FF", rough=0.05, emit="FFFFFF", strength=1.6, spec=1.0)
    for i in range(140):
        x, y = rnd.uniform(-5.5, 5.5), rnd.uniform(-1.2, 5)
        C.sphere("dew", (x, y, hz(x, y) + rnd.uniform(0.04, 0.16)), r=rnd.uniform(0.02, 0.04), mat=dew, seg=10, rings=6)
    for fn, loc, s in [(a_nature.build_cloud_a, (-9, 40, 9), 2.4), (a_nature.build_cloud_b, (10, 42, 12), 2.0), (a_nature.build_cloud_a, (2, 50, 15), 1.6)]:
        cl = fn(); cl.location = loc; cl.scale = (s,) * 3
    balloon_with_sprout((5.5, 16, 6.8), 1.8, -20)
    cam((0.6, -7.5, 1.9), (0.8, 8, 2.8), 32)
    glare(1.1, 0.35)


def scene_woods():
    rnd = random.Random(2)
    world("C8E6C0", "A9D6C4", "7DB8C9", "CFE8D8", 0.55, 0.5)
    sun((50, 0, 150), 3.0, "FFEBC2", angle=2)
    ground = blob_hill("g", (0, 10, -40), (60, 60, 40), "6DAE5F", seg=96)
    moss = C.mat("Moss", "7FC46A", rough=0.95)
    pine = a_nature.build_pine()
    tree = a_nature.build_tree_round()
    blossom_dark = C.mat("LeafDeep", "4E9E62", rough=0.85)
    spots = []
    for i in range(46):
        x, y = rnd.uniform(-14, 14), rnd.uniform(3, 30)
        if abs(x) < 2.2 and y < 12:
            continue
        spots.append((x, y))
    for i, (x, y) in enumerate(spots):
        src = pine if i % 3 else tree
        dup(src, (x, y, -0.05), rnd.uniform(0, 360), rnd.uniform(1.6, 2.6) if src is pine else rnd.uniform(1.3, 1.8))
    for (x, y, s) in [(-4.6, 4.0, 2.4), (5.0, 5.0, 2.6)]:
        dup(pine, (x, y, -0.05), rnd.uniform(0, 360), s)
    hide_tree(pine); hide_tree(tree)
    # mossy logs
    for (x, y, a, L) in [(-1.6, 0.2, 20, 2.2), (1.9, 3.5, -35, 2.6)]:
        lg = a_props.log("log", L, 0.22, rnd, bark="WoodDark")
        lg.data.transform(C.xform(rot=(0, 0, a)))
        lg.location = (x, y, 0.2)
        mb = C.blob("moss", [((x + (k - 2) * L / 5 * math.cos(math.radians(a)), y + (k - 2) * L / 5 * math.sin(math.radians(a)), 0.37), 0.13) for k in range(5)],
                    mat=moss, voxel=0.04, smooth_iter=4, target=600, flat_bottom=0.33)
        for k in range(3):
            m = C.sphere("mush", (x + 0.3 * k - 0.3, y - 0.18, 0.46), r=1, scale=(0.06, 0.06, 0.035), mat=C.mat("RoofRed", rough=0.7), seg=12, rings=6)
            C.cyl("mst", (x + 0.3 * k - 0.3, y - 0.18, 0.38), r=0.018, h=0.08, mat=C.mat("Cream"), seg=8, base=True)
    ferns = a_nature.build_flowers()
    dup(ferns, (0.4, -0.5, -0.02), 30, 0.8)
    hide_tree(ferns)
    tuft = a_island.grass_tuft("tf", rnd, 2.5)
    for i in range(60):
        t = tuft.copy(); C.link(t)
        t.location = (rnd.uniform(-6, 6), rnd.uniform(-1.5, 8), -0.02)
        t.rotation_euler = (0, 0, rnd.uniform(0, 6))
    hide_tree(tuft)
    # soft light shafts (additive translucent beams)
    ray = blended_emission("Ray", "FFF6D6", "FFF6D6", alpha=0.12, strength=1.5)
    for i in range(4):
        x = -2.5 + i * 1.9 + rnd.uniform(-0.4, 0.4)
        b = C.box("ray", (x, 9, 5), (rnd.uniform(0.5, 1.1), 0.02, 16), mat=ray, bevel=0.0, smooth=False)
        b.rotation_euler = (0, math.radians(-22), 0)
    balloon_with_sprout((0.6, 22, 9.5), 1.6, 15)
    cam((0, -5.5, 1.6), (0.2, 10, 3.6), 30)
    glare(1.0, 0.4)


def scene_beach():
    rnd = random.Random(3)
    world("FFE9D6", "BDE8F5", "6FC3EE", "D8EEF7", 0.75)
    sun((58, 0, -30), 3.4, "FFEFD6")
    sand = C.mat("BeachSand", "F2DDB0", rough=0.95)
    beach = C.lathe("shore", [(0, 0.0), (9, 0.0), (10, -0.4), (0, -0.4)], seg=64, mat=sand)
    beach.scale = (1.0, 2.2, 1)
    beach.location = (-4, 6, 0.0)
    water = C.cyl("sea", (20, 10, -0.08), r=40, h=0.1, mat=C.mat("Water", "4FC6D8", rough=0.08, spec=0.8), seg=64, smooth=False)
    shallow = C.lathe("shallow", [(0, 0.0), (10.6, 0.0), (0, 0.001)], seg=64, mat=C.mat("Shallow", "8FE3E0", rough=0.1))
    shallow.scale = (1.0, 2.2, 1); shallow.location = (-4, 6, -0.02)
    foam = C.torus("foam", (-4, 6, -0.015), R=10.25, r=0.08, scale=(1, 2.2, 0.3), mat=C.mat("Foam", "FFFFFF", rough=0.6), seg=96, mseg=6)
    # pebbles
    for i in range(80):
        a = rnd.uniform(-1.2, 1.2); d = rnd.uniform(6.5, 9.8)
        x, y = -4 + d * math.cos(a), 6 + 2.2 * d * math.sin(a)
        rk = a_island.rock("pb", rnd, rnd.uniform(0.06, 0.18), mats=(rnd.choice(["Pebble", "Rock", "RockDark", "BlossomLight"]), "Rock"), sub=1)
        rk.location = (x, y, 0.02)
    for (x, y, s) in [(3.5, -1, 0.6), (4.3, 0.2, 0.4), (2.9, 1.2, 0.35)]:
        rk = a_island.rock("br", rnd, s, sub=2)
        rk.location = (x, y, 0.1)
    # tiny pier
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    for k in range(10):
        C.box("plank", (5.2 + k * 0.42, 4.6, 0.32), (0.36, 1.1, 0.07), mat=wood if k % 2 else C.mat("WoodLight"), bevel=0.02, bseg=2)
    for k in range(4):
        for sy in (-1, 1):
            C.cyl("post", (5.3 + k * 1.3, 4.6 + sy * 0.5, -0.4), r=0.07, h=0.95, mat=woodd, seg=10, base=True, bevel=0.02, bseg=1)
    boat = C.lathe("boat", [(0, 0.0), (0.35, 0.05), (0.5, 0.3), (0.45, 0.32), (0, 0.32)], seg=24, mat=C.mat("RoofTeal", rough=0.7))
    boat.scale = (1, 2.2, 1); boat.location = (8.2, 3.2, -0.08); boat.rotation_euler = (0, 0, 0.3)
    C.torus("brim", (8.2, 3.2, 0.24), R=0.47, r=0.04, scale=(1, 2.2, 1), mat=C.mat("Cream"), seg=32, mseg=6).rotation_euler = (0, 0, 0.3)
    # beach umbrella + towel
    C.cyl("upole", (-1.5, 1.5, 0), r=0.035, h=1.8, mat=C.mat("Cream"), seg=8, base=True)
    um = C.lathe("umb", [(0, 1.9), (0.9, 1.62), (1.0, 1.55), (0, 1.58)], seg=16, mats=[C.mat("RoofRed"), C.mat("Cream")], caps=False)
    for p in um.data.polygons:
        p.material_index = int((math.atan2(p.center.y, p.center.x) + math.pi) / (2 * math.pi) * 8) % 2
    um.location = (-1.5, 1.5, 0)
    C.box("towel", (-0.8, 1.2, 0.01), (0.9, 1.6, 0.02), mat=C.mat("Rug", "4FA3A5"), bevel=0.005, bseg=1, rot=(0, 0, 15))
    for (x, y) in [(-2.5, -0.5), (0.8, -0.8)]:
        shell = C.lathe("shell", [(0, 0), (0.1, 0.01), (0.0, 0.06)], seg=10, mat=C.mat("BlossomLight"), rfun=lambda t, z: 0.7 + 0.3 * abs(math.cos(4 * t)))
        shell.location = (x, y, 0.0)
    for fn, loc, s in [(a_nature.build_cloud_a, (14, 40, 7), 2.5), (a_nature.build_cloud_b, (-6, 45, 9), 2.0)]:
        cl = fn(); cl.location = loc; cl.scale = (s,) * 3
    isl = blob_hill("isle", (13, 34, -1.2), (4.5, 3.0, 2.0), "7BC96F")
    blob_hill("isleSand", (13, 34, -1.45), (5.2, 3.6, 1.6), "F2DDB0")
    tr = a_nature.build_tree_round(); tr.location = (12.2, 34, 0.6); tr.scale = (1.3,) * 3
    tb = a_nature.build_tree_blossom(); tb.location = (14.4, 34.5, 0.5); tb.scale = (1.1,) * 3
    lh = C.cyl("lighthouse", (10.5, 33.5, 0.3), r=0.45, r2=0.32, h=3.2, mat=C.mat("Cream"), seg=16, base=True)
    C.paint_faces(lh, C.mat("RoofRed"), lambda c, n: int(c.z / 0.7) % 2 == 1)
    C.cyl("lhtop", (10.5, 33.5, 3.5), r=0.4, r2=0.0, h=0.6, mat=C.mat("RoofRed"), seg=16, base=True)
    C.cyl("lhglass", (10.5, 33.5, 3.3), r=0.3, h=0.3, mat=C.mat("GlowLamp", "FFE6A8", rough=0.35, emit="FFD58A", strength=1.0), seg=16, base=True)
    balloon_with_sprout((10.5, 20, 5.5), 1.8, -25)
    cam((-2.5, -6.5, 3.2), (4, 10, 1.2), 30)
    glare(1.2, 0.3)


def mushroom(name, loc, r, h, cap="MushRed", seed=0, lean=0.0):
    rnd = random.Random(seed)
    capm = C.mat(cap, {"MushRed": "E0503F", "MushPink": "F07A8C", "MushOrange": "F29A45"}[cap], rough=0.6)
    cream = C.mat("MushCream", "F6EAD2", rough=0.85)
    stem = C.lathe(name + "st", [(0, 0), (r * 0.42, 0), (r * 0.36, h * 0.3), (r * 0.3, h * 0.7), (r * 0.32, h), (0, h)], seg=20, mat=cream)
    capo = C.lathe(name + "cap", [(0, h * 0.92), (r * 0.9, h * 0.9), (r * 1.02, h * 0.98), (r * 0.95, h * 1.12), (r * 0.7, h * 1.3), (r * 0.3, h * 1.42), (0, h * 1.44)],
                   seg=32, mat=capm)
    parts = [stem, capo]
    C.update()
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0.15, 0.8) * r
        ok, p, n, _ = capo.ray_cast(Vector((d * math.cos(a), d * math.sin(a), h * 3)), Vector((0, 0, -1)))
        if ok:
            sp = C.sphere("spot", p, r=r * rnd.uniform(0.09, 0.15), scale=(1, 1, 0.3), mat=cream, seg=10, rings=5)
            q = Vector((0, 0, 1)).rotation_difference(n)
            sp.data.transform(q.to_matrix().to_4x4())
            parts.append(sp)
    o = C.join(parts, name)
    C.set_origin(o, (0, 0, 0))
    o.rotation_euler = (lean, 0, 0)
    o.location = loc
    return o


def scene_mushroom():
    rnd = random.Random(4)
    world("F7A76C", "B884C6", "3B3F8C", "8A7CC0", 0.45, 0.4)
    sun((78, 0, -60), 1.6, "FFB27A")
    ground = blob_hill("g", (0, 8, -30), (40, 40, 30), "4E8F73", seg=96)
    blob_hill("g2", (-10, 30, -12), (20, 12, 13), "5D8FA0")
    blob_hill("g3", (12, 34, -13), (22, 12, 14.5), "6B8DB0")
    mushroom("m1", (-2.2, 4, 0), 1.6, 2.4, "MushRed", 1)
    mushroom("m2", (2.6, 6.5, 0), 2.1, 3.4, "MushRed", 2)
    mushroom("m3", (0.3, 2.2, 0), 0.6, 0.8, "MushPink", 3)
    mushroom("m4", (-4.6, 8.5, 0), 1.2, 1.7, "MushOrange", 5)
    mushroom("m5", (5.4, 3.0, 0), 0.7, 1.0, "MushPink", 6)
    mushroom("m6", (1.1, 1.2, 0), 0.35, 0.45, "MushRed", 7)
    # mushroom house door + glowing window on the big one
    C.prism("door", C.arch_pts(0.6, 1.0, 10, 0.0), 6.5 - 0.93, 6.5 - 0.84, C.mat("Wood", rough=0.8)).location = (2.6, 0, 0)
    win = C.cyl("win", (2.6, 6.5 - 0.72, 1.6), r=0.22, h=0.05, rot=(90, 0, 0), mat=emit_mat("GlowWindowPC", "FFD58A", 4.0), seg=20)
    C.torus("winf", (2.6, 6.5 - 0.75, 1.6), R=0.24, r=0.04, rot=(90, 0, 0), mat=C.mat("WoodDark"), seg=20, mseg=6)
    C.point_light("wl", (2.6, 5.2, 1.5), 60, "FFC27A", 0.2)
    tuft = a_island.grass_tuft("tf", rnd, 2.2)
    for i in range(50):
        t = tuft.copy(); C.link(t)
        t.location = (rnd.uniform(-6, 7), rnd.uniform(-1, 9), -0.02)
        t.rotation_euler = (0, 0, rnd.uniform(0, 6))
    hide_tree(tuft)
    fly = emit_mat("Firefly", "E8FF8A", 12.0)
    for i in range(55):
        C.sphere("ff", (rnd.uniform(-6, 7), rnd.uniform(-1, 12), rnd.uniform(0.3, 4.5)), r=rnd.uniform(0.025, 0.05), mat=fly, seg=8, rings=5)
    for i in range(6):
        C.point_light("fl", (rnd.uniform(-4, 5), rnd.uniform(0, 8), rnd.uniform(0.5, 2)), 6, "E8FF8A", 0.1)
    star = emit_mat("PCStar", "FFFFFF", 5.0)
    for i in range(40):
        C.ico("st", (rnd.uniform(-30, 30), 60, rnd.uniform(12, 30)), r=rnd.uniform(0.06, 0.14), sub=1, mat=star)
    balloon_with_sprout((-5.5, 22, 7.5), 1.6, 20)
    cam((0.4, -6.0, 1.3), (0.4, 8, 2.6), 30)
    glare(0.9, 0.7)


def scene_harbor():
    rnd = random.Random(5)
    world("FFE3F0", "C9E6FA", "7DBFF0", "DDEBF8", 0.8)
    sun((55, 0, -35), 2.2, "FFF0DC")
    ca, cb = a_nature.build_cloud_a(), a_nature.build_cloud_b()
    C.mat("Cloud", "FFFFFF", rough=1.0).node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = C.hex_lin("F4F7FF")
    for i in range(46):
        x, y = rnd.uniform(-24, 24), rnd.uniform(3, 45)
        if abs(x) < 3 and y < 9:
            continue
        dup(ca if i % 2 else cb, (x, y, rnd.uniform(-3.2, -1.8) - y * 0.04), rnd.uniform(0, 360), rnd.uniform(1.4, 2.6))
    hide_tree(ca); hide_tree(cb)
    wood, woodd = C.mat("Wood", rough=0.8), C.mat("WoodDark", rough=0.8)
    lamp = emit_mat("GlowLampPC", "FFD58A", 3.0)
    for (x0, y0, L, ang) in [(-1.5, 2.0, 7, 70), (3.5, 8.0, 6, 110), (-5.5, 12.0, 5, 80)]:
        d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
        nrm = Vector((-d.y, d.x, 0))
        for k in range(int(L / 0.45)):
            p = Vector((x0, y0, 0.2)) + d * (k * 0.45)
            pl = C.box("pl", p, (0.4, 1.3, 0.08), mat=wood if k % 2 else C.mat("WoodLight"), bevel=0.02, bseg=1)
            pl.rotation_euler = (0, 0, math.radians(ang - 90 + 90))
            if k % 4 == 0:
                for s in (-1, 1):
                    q = p + nrm * s * 0.62
                    C.cyl("post", q - Vector((0, 0, 0.9)), r=0.07, h=1.9, mat=woodd, seg=8, base=True)
                    if k % 8 == 0:
                        C.sphere("lamp", q + Vector((0, 0, 1.08)), r=0.09, mat=lamp, seg=10, rings=6)
    # little sky-boats with sails
    for (x, y, z, rz, col) in [(2.5, 3.5, 0.2, 20, "RoofRed"), (-3.8, 7.5, 0.4, -30, "RoofTeal"), (6.0, 13, 0.6, 50, "FlowerYellow")]:
        hull = C.lathe("hull", [(0, 0.0), (0.4, 0.08), (0.55, 0.35), (0.5, 0.38), (0, 0.38)], seg=20, mat=C.mat(col, rough=0.7))
        hull.scale = (0.8, 2.0, 1); hull.location = (x, y, z); hull.rotation_euler = (0, 0, math.radians(rz))
        C.cyl("mast", (x, y, z + 0.3), r=0.03, h=1.4, mat=woodd, seg=8, base=True)
        sail = C.prism("sail", [(0, 0), (0.7, 0), (0, 1.1)], -0.01, 0.01, C.mat("TentCream"), smooth=False)
        sail.location = (x + 0.04, y, z + 0.5); sail.rotation_euler = (0, 0, math.radians(rz + 90))
    # a flotilla of balloons in other colours + ours
    ours = balloon_with_sprout((0.8, 5.5, 2.6), 1.3, -10)
    for (x, y, z, s, col) in [(-6, 16, 4.5, 1.4, "E0674F"), (7.5, 20, 6.0, 1.5, "F2B45A"), (-2.5, 28, 7.5, 1.6, "B79BE8"), (11, 32, 4.0, 1.4, "F59BB6")]:
        b = a_balloon.build_balloon()
        recolor(b, "BalloonGreen", C.mat("Bal" + col, col, rough=0.75))
        b.location = (x, y, z); b.scale = (s,) * 3
    cam((0, -7.5, 4.6), (0.5, 10, 1.6), 30)
    glare(1.1, 0.3)


def crystal(name, loc, h, r, col, tilt, rz, strength=0.55):
    m = C.mat("Crys" + col, col, rough=0.25, emit=col, strength=strength, spec=0.8)
    o = C.lathe(name, [(0, 0), (r, 0), (r * 1.05, h * 0.8), (0, h)], seg=6, mat=m, smooth=False)
    o.rotation_euler = (math.radians(tilt), 0, math.radians(rz))
    o.location = loc
    return o


def scene_caves():
    rnd = random.Random(6)
    world("2A2046", "241C3E", "140F26", "4A3A7A", 0.25)
    rockm = C.mat("CaveRock", "4A3F6B", rough=0.9)
    rockl = C.mat("CaveRockLight", "6A5C8E", rough=0.9)
    shell = C.ico("cave", (0, 8, 2), r=1, sub=4, mat=rockm)
    C.jitter(shell, 0.12, 2.2, 3)
    shell.data.transform(Matrix.Diagonal((14, 16, 8, 1)))
    shell.data.flip_normals()
    C.paint_faces(shell, rockl, lambda c, n: noise.noise(c * 0.3) > 0.2)
    C.shade(shell, 40)
    floor = C.box("floor", (0, 8, -0.3), (40, 40, 0.6), mat=C.mat("CaveFloor", "3C3360", rough=0.9), bevel=0.0, smooth=False)
    for i in range(14):
        rk = a_island.rock("rk", rnd, rnd.uniform(0.4, 1.4), mats=("CaveRock", "CaveRockLight"), sub=2, jit=0.3)
        rk.location = (rnd.uniform(-10, 10), rnd.uniform(0, 18), 0.0)
    cols = ["F7A8D8", "8FE3F0", "C9A8F7", "A8F0C8", "FFD0A8"]
    clusters = [(-3.2, 3.0, 1.3), (3.4, 4.2, 1.6), (-6.5, 10, 2.2), (6.5, 12, 2.0), (0.6, 14, 2.4), (-1.4, 1.2, 0.6), (2.0, 1.0, 0.5)]
    for ci, (x, y, s) in enumerate(clusters):
        col = cols[ci % len(cols)]
        for k in range(rnd.randint(5, 8)):
            crystal("cr", (x + rnd.uniform(-0.4, 0.4) * s, y + rnd.uniform(-0.4, 0.4) * s, -0.05), s * rnd.uniform(0.6, 1.6),
                    s * rnd.uniform(0.12, 0.2), col, rnd.uniform(-35, 35), rnd.uniform(0, 360))
        C.point_light("cl", (x, y - 0.5, s * 0.8), 120 * s, col, 0.3)
    # stalactites
    for i in range(22):
        x, y = rnd.uniform(-9, 9), rnd.uniform(2, 20)
        st = C.cyl("stal", (x, y, 6.5), r=rnd.uniform(0.15, 0.4), r2=0.0, h=rnd.uniform(1.0, 2.5), rot=(180, 0, 0), mat=rockl, seg=7)
    for i in range(60):
        C.sphere("mote", (rnd.uniform(-6, 6), rnd.uniform(0, 14), rnd.uniform(0.3, 5)), r=0.025, mat=emit_mat("Mote", "FFE9F7", 6), seg=6, rings=4)
    b = balloon_with_sprout((1.2, 8.5, 2.4), 1.2, -15)
    C.point_light("bl", (1.2, 7.0, 3.4), 60, "FFE3C8", 0.4)
    cam((0, -4.5, 1.8), (0.4, 10, 2.5), 28)
    glare(1.0, 0.5)


def mountain(name, loc, r, h, seed, snow=0.62):
    rnd = random.Random(seed)
    prof = [(0, -0.5), (r, -0.5)] + [(r * (1 - (i / 10) ** 0.9), h * i / 10) for i in range(10)] + [(0, h)]
    o = C.lathe(name, prof, seg=40, mat=C.mat("MtnRock", "6D7FA8", rough=0.9), sharp=40)
    C.jitter(o, r * 0.08, 2.0 / r, seed)
    o.location = loc
    C.update()
    C.paint_faces(o, C.mat("Snow", "F3F7FF", rough=0.85), lambda c, n: c.z - loc[2] > h * snow + 0.08 * h * noise.noise(c * 0.8) and n.z > 0.1)
    C.paint_faces(o, C.mat("MtnRockDark", "54628A", rough=0.9), lambda c, n: n.z < 0.35 and c.z - loc[2] < h * snow)
    C.shade(o, 35)
    return o


def scene_peaks():
    rnd = random.Random(7)
    world("2B3F73", "1A2A5A", "070F2A", "3E5596", 0.3)
    sun((35, 0, 150), 0.7, "BFD6FF")
    for (x, y, r, h, sd) in [(-9, 30, 9, 11, 1), (2, 38, 11, 14, 2), (13, 32, 8, 10, 3), (-18, 42, 10, 12, 4), (22, 44, 12, 13, 5),
                            (-4, 20, 6, 6.5, 6), (8, 22, 6.5, 7, 7)]:
        mountain("mt", (x, y, -1), r, h, sd)
    snowg = blob_hill("snowfield", (0, 6, -20), (40, 30, 20), "E8F0FF")
    for i in range(22):
        x, y = rnd.uniform(-12, 12), rnd.uniform(4, 16)
        p = a_nature.build_pine()
        recolor(p, "Pine", C.mat("PineNight", "3F7A66", rough=0.85))
        p.location = (x, y, hill_z([snowg], x, y) - 0.1); p.scale = (rnd.uniform(0.8, 1.5),) * 3
    # aurora curtains
    for k, (x, y, col_a, col_b, amp) in enumerate([(-6, 48, "59F2B5", "B08CFF", 1.0), (4, 52, "63E8D8", "F29CD6", 1.2), (14, 50, "7CF2A0", "8FB5FF", 0.9)]):
        import bmesh
        bm = bmesh.new()
        cols_ = []
        N, M = 40, 6
        vs = []
        for i in range(N + 1):
            t = i / N
            row = []
            for j in range(M + 1):
                u = j / M
                xx = x + (t - 0.5) * 34
                yy = y + 3 * math.sin(t * 7 + k) * amp
                zz = 9 + u * (12 + 6 * math.sin(t * 4 + k)) + 2.5 * math.sin(t * 5 + k * 2)
                row.append(bm.verts.new((xx, yy, zz)))
            vs.append(row)
        for i in range(N):
            for j in range(M):
                bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
        cur = C.mk("aurora", bm, [blended_emission("Aurora%d" % k, col_a, col_b, alpha=0.7, strength=1.6, streaks=True)])
    star = emit_mat("PCStar", "FFFFFF", 6.0)
    for i in range(260):
        C.ico("st", (rnd.uniform(-70, 70), 90, rnd.uniform(5, 60)), r=rnd.uniform(0.06, 0.18), sub=1, mat=star)
    b = balloon_with_sprout((4.5, 14, 6.5), 1.3, -20)
    C.point_light("bl", (4.5, 13, 7.2), 30, "FFD58A", 0.3)
    C.set_emission("GlowBurner", 8.0)
    cam((0, -6, 3.0), (1, 20, 7.5), 28)
    glare(0.85, 0.7)


def scene_moon():
    rnd = random.Random(8)
    world("3A4A86", "243268", "0C1334", "6A7FC0", 0.35, 0.4)
    C.sun((45, 0, 170), 0.9, col="C8D8FF", angle=3, name="Moonlight")
    moon = C.cyl("moon", (1.5, 60, 20), r=13, h=0.2, rot=(90, 0, 0), mat=emit_mat("MoonDisc", "F4EFD2", 0.95), seg=96, smooth=False)
    for (dx, dz, r) in [(-4, 3, 2.2), (3, -4, 1.6), (5, 5, 1.0), (-2, -6, 1.2)]:
        C.cyl("crater", (1.5 + dx, 59.8, 20 + dz), r=r, h=0.1, rot=(90, 0, 0), mat=emit_mat("MoonCrater", "DCD4B4", 0.8), seg=32, smooth=False)
    ground = blob_hill("g", (0, 8, -30), (40, 40, 30), "3E6A7A", seg=96)
    hedge = C.mat("Hedge", "4F7F8A", rough=0.9)
    for (x, y, s) in [(-5, 6, 1.4), (-3, 9, 1.1), (5, 7, 1.5), (3.5, 11, 1.0), (-7, 13, 1.8), (8, 14, 1.8)]:
        h = C.blob("hedge", [((x, y, 0.5 * s), 0.7 * s), ((x + 0.6 * s, y, 0.4 * s), 0.55 * s), ((x - 0.6 * s, y + 0.2, 0.4 * s), 0.55 * s)],
                   mat=hedge, voxel=0.08, smooth_iter=4, target=900, flat_bottom=0.0)
    # stone path
    for k in range(14):
        t = k / 13
        x = math.sin(t * 3) * 0.8
        y = -1 + t * 12
        st = C.cyl("stone", (x, y, 0.0), r=0.32 - 0.1 * t, h=0.06, mat=C.mat("MoonStone", "B8C0D8", rough=0.9), seg=12, bevel=0.02, bseg=1)
        st.scale = (1, 0.75, 1)
    # glowing moon-flowers
    petal = emit_mat("MoonPetal", "D8E8FF", 1.3, base="EAF2FF")
    petal2 = emit_mat("MoonPetalBlue", "9FC0FF", 1.3)
    for i in range(80):
        x, y = rnd.uniform(-4.5, 4.5), rnd.uniform(-1.8, 9)
        if abs(x - math.sin((y + 1) / 12 * 3) * 0.8) < 0.6:
            continue
        h = rnd.uniform(0.3, 0.8)
        C.tube("mst", [(x, y, 0), (x + 0.03, y, h * 0.6), (x, y, h)], r=0.012, mat=C.mat("MoonStem", "6FA59A"), seg=4, res=2)
        fl = C.lathe("mf", [(0, 0), (0.06, 0.03), (0.12, 0.09), (0.1, 0.1), (0, 0.04)], seg=10, mat=petal if i % 3 else petal2,
                     rfun=lambda t, z: 0.75 + 0.25 * abs(math.cos(2.5 * t)))
        fl.location = (x, y, h)
    for i in range(6):
        C.point_light("fg", (rnd.uniform(-4, 4), rnd.uniform(1, 8), 0.6), 15, "C8DCFF", 0.2)
    fly = emit_mat("Firefly", "FFF3A8", 10.0)
    for i in range(40):
        C.sphere("ff", (rnd.uniform(-6, 6), rnd.uniform(0, 12), rnd.uniform(0.4, 3.5)), r=rnd.uniform(0.02, 0.04), mat=fly, seg=6, rings=4)
    lp = a_props.build_lamppost()
    lp.location = (1.6, 3.5, 0)
    C.set_emission("GlowLamp", 6.0)
    C.point_light("lpl", (1.6, 3.5, 1.55), 40, "FFD58A", 0.1)
    star = emit_mat("PCStar", "FFFFFF", 5.0)
    for i in range(160):
        C.ico("st", (rnd.uniform(-60, 60), 70, rnd.uniform(3, 45)), r=rnd.uniform(0.05, 0.15), sub=1, mat=star)
    b = balloon_with_sprout((-0.6, 50, 14.5), 4.5, 0)       # silhouetted against the moon
    cam((0, -5.5, 1.4), (0.5, 12, 4.2), 30)
    glare(0.85, 0.75)


def scene_farm():
    rnd = random.Random(9)
    world("FFC78F", "F7B4C2", "7FB6E8", "F4D9CF", 0.6, 0.42)
    sun((74, 0, -115), 3.2, "FFD2A0", angle=3)
    farm = a_farm.build_farm_island()
    C.update()
    kinds = ["pumpkin", "turnip", "carrot", "sunflower", "corn", "strawberry"]
    for i, kind in enumerate(kinds):
        pe = [o for o in farm.children if o.name.split(".")[0] == "Plot%d" % (i + 1)][0]
        cr = a_crops.build_crop(kind)
        for ch in cr.children:
            ch.hide_render = ch.name.split(".")[0] != "Ripe"
        cr.location = pe.matrix_world.to_translation()
    dock = [o for o in farm.children if o.name.startswith("BalloonDock")][0].matrix_world.to_translation()
    balloon_with_sprout(Vector((-2.8, -1.4, 1.9)), 1.2, 25)
    home = a_island.build_island()
    home.location = (14, 62, -6); home.scale = (0.9,) * 3
    home_cot = a_buildings.build_cottage(); home_cot.location = (14, 62.5, -6); home_cot.scale = (0.9,) * 3
    ht = a_nature.build_tree_round(); ht.location = (11.2, 63, -6); ht.scale = (0.9,) * 3
    sunm = emit_mat("SunDisc", "FFE3A0", 3.0)
    C.cyl("sundisc", (24, 130, -16), r=9, h=0.2, rot=(90, 0, 0), mat=sunm, seg=64, smooth=False)
    for fn, loc, s_ in [(a_nature.build_cloud_a, (15, 40, -14), 3.0), (a_nature.build_cloud_b, (-12, 30, -8), 2.6), (a_nature.build_cloud_a, (-30, 90, 6), 3.5),
                        (a_nature.build_cloud_b, (-4, 70, 16), 3.0), (a_nature.build_cloud_a, (-16, 12, -10), 2.2)]:
        cl = fn(); cl.location = loc; cl.scale = (s_,) * 3
    C.mat("Cloud", "FFFFFF", rough=1.0).node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = C.hex_lin("FFF1EC")
    cam((4.5, -12.5, 5.6), (1.6, 4.0, -0.2), 32)
    glare(1.0, 0.5)


SCENES = {k: globals()["scene_" + k] for k in IDS}


def render(pid, small):
    C.reset()
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    w, h = (600, 400) if small else (1200, 800)
    C.render_setup((w, h), samples=32 if small else 64)
    SCENES[pid]()
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.image_settings.file_format = 'JPEG'
    s.render.image_settings.quality = 85
    s.render.image_settings.color_mode = 'RGB'
    os.makedirs(OUT_DIR, exist_ok=True)
    s.render.filepath = os.path.join(C.PREVIEW_DIR, "pc_%s_small.jpg" % pid) if small else os.path.join(OUT_DIR, "postcard_%s.jpg" % pid)
    bpy.ops.render.render(write_still=True)
    print("@@ rendered", s.render.filepath)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    small = "--small" in args
    ids = [a for a in args if not a.startswith("--")]
    if not ids or ids == ["all"]:
        ids = IDS
    for pid in ids:
        render(pid, small)

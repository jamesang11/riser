"""Riser app icon: sprout peeking over a hill in front of a rising sun.

Blender -b -P Blender/scripts/icon.py -- <variant A|B|C> <out.png> [size]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import common as C
import a_sprout, a_island

VARIANTS = {
    # sprout scale, sun (x, z, radius), hill crest z, sprout x, camera elevation deg
    "A": dict(s=1.4, sun=(0.0, -0.06, 0.3), hill=-0.36, sx=0.0, el=5),
    "B": dict(s=1.4, sun=(0.17, 0.0, 0.27), hill=-0.36, sx=-0.04, el=5),
    "C": dict(s=1.45, sun=(0.0, -0.14, 0.4), hill=-0.38, sx=0.0, el=5),
}


def world_icon():
    w = bpy.data.worlds.new("IconWorld")
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
    stops = [(0.0, "FFB35C"), (0.3, "FF9E7A"), (0.55, "F28FB0"), (0.8, "7C74C9"), (1.0, "33479E")]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], C.hex_lin(stops[0][1])
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], C.hex_lin(stops[-1][1])
    for p, c in stops[1:-1]:
        e = cr.elements.new(p)
        e.color = C.hex_lin(c)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(ramp.outputs[0], bg_cam.inputs[0])
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs[0].default_value = C.hex_lin("F2C6D8")
    bg_light.inputs[1].default_value = 0.55
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_light.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def glare():
    s = bpy.context.scene
    ng = bpy.data.node_groups.new("IconComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    g = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    for attr, val in (("glare_type", 'FOG_GLOW'), ("quality", 'HIGH'), ("size", 8), ("threshold", 0.9), ("mix", 0.0)):
        try:
            setattr(g, attr, val)
        except Exception:
            pass
    for key, val in (("Type", 'Fog Glow'), ("Quality", 'High'), ("Threshold", 1.0), ("Size", 0.5), ("Strength", 0.35)):
        if key in g.inputs:
            try:
                g.inputs[key].default_value = val
            except Exception:
                pass
    ng.links.new(rl.outputs["Image"], g.inputs["Image"])
    ng.links.new(g.outputs["Image"], out.inputs[0])
    s.compositing_node_group = ng


def build(v):
    C.reset()
    rnd = random.Random(5)
    # sprout
    sp = a_sprout.build_sprout()
    for n in ("Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"):
        bpy.data.objects[n].hide_render = True
        bpy.data.objects[n].hide_viewport = True
    sp.location = (v["sx"], 0.12, v["hill"] - 0.07)
    sp.scale = (v["s"],) * 3
    # sun + soft rings behind
    sx, sz, sr = v["sun"]
    rings = [(sr, "000000", "FFC53D", 1.0), (sr * 1.2, "000000", "FFA35A", 1.0), (sr * 1.42, "000000", "FF8A74", 1.0)]
    for i, (r, base, em, st) in enumerate(rings):
        d = C.cyl("sun%d" % i, (sx, 3.0 + i * 0.3, sz), r=r, h=0.02, rot=(90, 0, 0), seg=96,
                  mat=C.mat("IconSun%d" % i, base, rough=1.0, emit=em, strength=st), smooth=False)
    # hill
    hill_m = C.mat("Grass", rough=0.9)
    hill = C.sphere("hill", (0, 0.1, v["hill"] - 0.42), r=1, scale=(0.78, 0.7, 0.42), mat=hill_m, seg=96, rings=48)
    C.paint_faces(hill, C.mat("GrassTuft", rough=0.9), lambda c, n: n.z > 0.93)
    hill2 = C.sphere("hill2", (0.85, 1.2, v["hill"] - 0.62), r=1, scale=(0.7, 0.6, 0.5), mat=C.mat("GrassDark", rough=0.9), seg=64, rings=32)
    hill3 = C.sphere("hill3", (-0.85, 1.2, v["hill"] - 0.66), r=1, scale=(0.7, 0.6, 0.5), mat=C.mat("GrassDark", rough=0.9), seg=64, rings=32)
    # grass tufts + little flowers on the crest
    for (x, y, s) in [(-0.36, -0.12, 1.0), (0.4, -0.1, 0.95), (-0.52, 0.1, 0.9), (0.55, 0.12, 0.9)]:
        ok, loc, n, _ = hill.ray_cast(hill.matrix_world.inverted() @ Vector((x, y, 3)), Vector((0, 0, -1)))
        if ok:
            z = (hill.matrix_world @ loc).z
            t = a_island.grass_tuft("tuft", rnd, s=s * 0.5)
            t.location = (x, y, z - 0.01)
    for (x, y, col) in [(-0.28, -0.2, "White"), (0.3, -0.22, "FlowerYellow"), (-0.46, -0.05, "Blossom"), (0.48, -0.02, "White")]:
        ok, loc, n, _ = hill.ray_cast(hill.matrix_world.inverted() @ Vector((x, y, 3)), Vector((0, 0, -1)))
        if ok:
            f = a_island.tiny_flower(rnd, col)
            f.scale = (1.1,) * 3
            f.location = (x, y, (hill.matrix_world @ loc).z)
    # a few tiny stars in the deep blue
    star = C.mat("IconStar", "FFFFFF", rough=1.0, emit="FFF4D6", strength=2.0)
    for (x, z, r) in [(-0.44, 0.44, 0.014), (0.42, 0.4, 0.011), (-0.24, 0.52, 0.009), (0.27, 0.53, 0.013), (0.5, 0.52, 0.008)]:
        C.ico("star", (x, 2.5, z), r=r, sub=1, mat=star)
    C.update()
    return sp


def render(v, out, size):
    s = bpy.context.scene
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    C.render_setup((size, size), samples=40)
    s.render.image_settings.color_mode = 'RGB'
    s.render.film_transparent = False
    world_icon()
    C.sun((48, 0, -24), 2.6, col="FFF4E6", angle=10.0, name="Key")
    C.sun((-72, 0, 12), 1.3, col="FFB070", angle=5.0, name="Rim")      # back light from the sun side
    el = math.radians(v["el"])
    cam = C.camera((0, 0, 0.0), (0, -math.cos(el), math.sin(el)), 6.0, name="IconCam", ortho=1.2)
    glare()
    s.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    v = VARIANTS[a[0]]
    out = a[1]
    size = int(a[2]) if len(a) > 2 else 1024
    build(v)
    render(v, out, size)

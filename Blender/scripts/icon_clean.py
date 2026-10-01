"""Riser app icon, clean version: the sprout rising from the bottom edge like the sun.

Blender -b -P Blender/scripts/icon_clean.py -- <variant> <out.png> [size]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C
import a_sprout

# top colour, bottom colour, rim light colour
VARIANTS = {
    "sunrise": ("FFC857", "FF7A4D", "FFD9A0"),
    "sky":     ("4F8FF0", "A9D6FF", "FFE3B0"),
    "cream":   ("FFF1D6", "FFD6A5", "FFFFFF"),
}


def world(top, bottom, light):
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
    cr.elements[0].position, cr.elements[0].color = 0.0, C.hex_lin(bottom)
    cr.elements[1].position, cr.elements[1].color = 1.0, C.hex_lin(top)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(ramp.outputs[0], bg_cam.inputs[0])
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs[0].default_value = C.hex_lin(light)
    bg_light.inputs[1].default_value = 0.6
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_light.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def build():
    C.reset()
    sp = a_sprout.build_sprout()
    hide = ("Bud", "Flower", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR",
            "MouthSad", "MouthOpen", "Nightcap", "ArmL", "ArmR")
    for n in hide:
        o = bpy.data.objects.get(n)
        if o:
            o.hide_render = True
            o.hide_viewport = True
    # Without the flower, the two leaves sit at the top of a short stem: a classic sprout.
    for n in ("LeafL", "LeafR"):
        leaf = bpy.data.objects.get(n)
        if leaf:
            leaf.location.z = 0.12
            leaf.scale = tuple(v * 1.35 for v in leaf.scale)
    # A little rounded bud where the leaves meet, so the stem doesn't end in a flat cut.
    stem = bpy.data.objects.get("Stem")
    if stem:
        C.update()
        top = max((stem.matrix_world @ __import__("mathutils").Vector(c)).z for c in stem.bound_box)
        C.sphere("StemCap", (0, 0.005, top - 0.012), r=0.014, mat=C.mat("Stem", rough=0.8), seg=24, rings=12).parent = sp
    # Big and low: the round head rises from the bottom edge like a sun, face fully visible.
    sp.scale = (2.0,) * 3
    sp.location = (0, 0, -0.72)
    C.update()
    return sp


def render(name, out, size):
    top, bottom, light = VARIANTS[name]
    s = bpy.context.scene
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    C.render_setup((size, size), samples=64)
    s.render.image_settings.color_mode = 'RGB'
    s.render.film_transparent = False
    world(top, bottom, light)
    C.sun((52, 0, -28), 2.4, col="FFF6EA", angle=14.0, name="Key")
    C.sun((-70, 0, 20), 1.1, col=light, angle=8.0, name="Rim")
    cam = C.camera((0, 0, 0.0), (0, -1, 0.04), 6.0, name="IconCam", ortho=1.2)
    s.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    size = int(a[2]) if len(a) > 2 else 1024
    build()
    render(a[0], a[1], size)

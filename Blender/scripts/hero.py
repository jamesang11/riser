"""Assemble the hero diorama and render day / night.

Blender -b -P Blender/scripts/hero.py -- [day|night|both] [--small]
Saves Blender/hero_scene.blend (day lighting; call set_night() to switch).
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler
import common as C
import a_island, a_sprout, a_buildings, a_props, a_nature

HERO_BLEND = os.path.join(C.ROOT_DIR, "hero_scene.blend")

# slot -> (builder, (x, y), rotation_z_deg, scale)
LAYOUT = [
    ("home", a_buildings.build_cottage, (0, 0.6), 0, 1),
    ("campfire", a_props.build_campfire, (1.8, -1.6), 10, 1),
    ("lamppost", a_props.build_lamppost, (-1.4, -2.4), 0, 1),
    ("treeA", a_nature.build_tree_round, (-3.2, 1.2), 20, 1),
    ("treeB", a_nature.build_tree_blossom, (3.2, 1.6), -30, 1),
    ("garden", a_nature.build_garden, (-2.6, -0.8), 8, 1),
    ("pond", a_nature.build_pond, (2.6, -0.2), 0, 1),
    ("windmill", a_buildings.build_windmill, (-1.6, 3.2), -18, 1),
    ("bench", a_props.build_bench, (0.2, -2.9), 25, 1),
    ("mailbox", a_props.build_mailbox, (1.2, -3.4), -70, 1),
    ("telescope", a_props.build_telescope, (3.3, -2.3), -40, 1),
    ("flowers", a_nature.build_flowers, (-3.5, -2.1), 0, 1),
    ("lanterns", a_props.build_lanterns, (0.0, 2.9), 0, 1),
    ("pine", a_nature.build_pine, (1.8, 3.4), 0, 1),
]


def place_root(root, xy, rz=0, s=1, z=0.0):
    root.location = (xy[0], xy[1], z)
    root.rotation_euler = (0, 0, math.radians(rz))
    root.scale = (s, s, s)


def extras():
    """Preview-only dressing: flame, chimney smoke puffs."""
    fx = []
    fire = C.lathe("HeroFlame", [(0, 0.0), (0.12, 0.05), (0.13, 0.12), (0.08, 0.26), (0.0, 0.42)], seg=14,
                   mat=C.mat("HeroFlame", "FFB347", rough=0.9, emit="FF9A3C", strength=4.0),
                   rfun=lambda t, z: 1 + 0.12 * math.sin(3 * t) * min(1, z * 4))
    inner = C.lathe("HeroFlameIn", [(0, 0.0), (0.07, 0.04), (0.07, 0.1), (0.03, 0.2), (0, 0.28)], seg=12,
                    mat=C.mat("HeroFlameIn", "FFF1A8", rough=0.9, emit="FFE68A", strength=6.0))
    for o in (fire, inner):
        o.location = (1.8, -1.6, 0.08)
        fx.append(o)
    smoke = C.mat("HeroSmoke", "FFFFFF", rough=1.0)
    for i, (dx, dz, r) in enumerate([(0.0, 0.25, 0.14), (0.12, 0.6, 0.18), (0.3, 1.0, 0.22)]):
        fx.append(C.sphere("HeroSmoke%d" % i, (0.52 + dx, 0.6 + 0.36 + dx * 0.3, 3.18 + dz), r=r, mat=smoke, seg=16, rings=10))
    return fx


def build_scene():
    C.reset()
    island = a_island.build_island()
    roots = {"island": island}
    for slot, fn, xy, rz, s in LAYOUT:
        r = fn()
        place_root(r, xy, rz, s)
        roots[slot] = r
    sp = a_sprout.build_sprout()
    place_root(sp, (0.42, -3.75), 16, 1.6)
    for n in ("Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"):
        bpy.data.objects[n].hide_render = True
        bpy.data.objects[n].hide_viewport = True
    roots["sprout"] = sp
    ca = a_nature.build_cloud_a()
    place_root(ca, (-8.8, 5.5), 10, 1.6, z=0.8)
    cb = a_nature.build_cloud_b()
    place_root(cb, (9.2, 3.0), -15, 1.4, z=-1.2)
    ca2 = a_nature.build_cloud_b()
    place_root(ca2, (-7.5, -6.5), 30, 1.1, z=-5.2)
    cb2 = a_nature.build_cloud_a()
    place_root(cb2, (5.0, 11.0), 0, 2.0, z=2.5)
    extras()
    C.update()
    return roots


def camera_setup(w=1600, h=1100):
    s = bpy.context.scene
    C.render_setup((w, h), samples=96)
    target = Vector((0.2, -0.3, -1.15))
    az, el = math.radians(16), math.radians(27)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam = C.camera(target, d, 26.5, lens=50, name="HeroCam")
    cam.data.dof.use_dof = False
    return cam


def set_day():
    s = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.name.startswith("Night") or o.name.startswith("HeroSun") or o.name.startswith("Star")]:
        bpy.data.objects.remove(o)
    world_screen("FFE2C6", "CDE9F7", "7CC3EE", light_col="CFE3F5", light_strength=0.62)
    C.sun((58, 0, -38), 3.3, col="FFE2B8", angle=4.0, name="HeroSun")
    for m in bpy.data.materials:
        if m.name.startswith("Glow"):
            C.set_emission(m.name, 0.25)
    C.set_emission("GlowEmbers", 1.5)
    s.view_settings.exposure = -0.15
    for n in ("HeroSmoke0", "HeroSmoke1", "HeroSmoke2"):
        bpy.data.objects[n].hide_render = False
    glare(False)


def glare(on, size=7, threshold=1.0, mix=0.0):
    s = bpy.context.scene
    if not on:
        try:
            s.compositing_node_group = None
        except Exception:
            pass
        return
    ng = bpy.data.node_groups.new("HeroComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    g = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    for attr, val in (("glare_type", 'FOG_GLOW'), ("quality", 'HIGH'), ("size", size), ("threshold", threshold), ("mix", mix)):
        try:
            setattr(g, attr, val)
        except Exception:
            pass
    for key, val in (("Type", 'Fog Glow'), ("Quality", 'High'), ("Threshold", threshold), ("Size", 0.7), ("Strength", 0.9)):
        if key in g.inputs:
            try:
                g.inputs[key].default_value = val
            except Exception:
                pass
    ng.links.new(rl.outputs["Image"], g.inputs["Image"])
    ng.links.new(g.outputs["Image"], out.inputs[0])
    s.compositing_node_group = ng


def world_screen(bottom, mid, top, light_col, light_strength, strength=1.0):
    """Camera sees a vertical screen-space gradient; lighting uses a flat sky colour."""
    w = bpy.data.worlds.get("RiserWorld") or bpy.data.worlds.new("RiserWorld")
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
    cr.elements[0].position = 0.0
    cr.elements[0].color = C.hex_lin(bottom)
    cr.elements[1].position = 1.0
    cr.elements[1].color = C.hex_lin(top)
    e = cr.elements.new(0.45)
    e.color = C.hex_lin(mid)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs[1].default_value = strength
    nt.links.new(ramp.outputs[0], bg_cam.inputs[0])
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs[0].default_value = C.hex_lin(light_col)
    bg_light.inputs[1].default_value = light_strength
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_light.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def set_night():
    s = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.name.startswith("HeroSun")]:
        bpy.data.objects.remove(o)
    world_screen("33467E", "182A5A", "070F2A", light_col="4A5FA8", light_strength=0.32)
    C.sun((40, 0, 145), 0.55, col="A9BFFF", angle=2.0, name="NightMoon")
    for m in bpy.data.materials:
        if m.name.startswith("Glow"):
            C.set_emission(m.name, 7.0)
    C.set_emission("GlowEmbers", 6.0)
    C.set_emission("HeroFlame", 9.0)
    C.set_emission("HeroFlameIn", 12.0)
    for n in ("HeroSmoke0", "HeroSmoke1", "HeroSmoke2"):
        bpy.data.objects[n].hide_render = True
    # practical lights
    def wp(name):
        return bpy.data.objects[name].matrix_world.to_translation()
    C.point_light("NightLamp", wp("LightPoint"), 60, "FFC77A", 0.08)
    C.point_light("NightFire", wp("FirePoint") + Vector((0, 0, 0.1)), 140, "FF9A4A", 0.15)
    home = bpy.data.objects["Cottage"].matrix_world
    for p in [(-0.64, -1.3, 1.0), (0.64, -1.3, 1.0), (0, -1.1, 2.0), (1.35, 0.05, 1.0), (-1.35, 0.05, 1.0)]:
        C.point_light("NightWin", home @ Vector(p), 22, "FFCF80", 0.1)
    C.point_light("NightDoor", home @ Vector((0, -1.4, 1.3)), 25, "FFCF80", 0.1)
    lan = bpy.data.objects["Lanterns"].matrix_world
    for x in (-0.7, 0.0, 0.7):
        C.point_light("NightLantern", lan @ Vector((x, -0.1, 1.45)), 14, "FFB870", 0.1)
    wm = bpy.data.objects["Windmill"].matrix_world
    C.point_light("NightMill", wm @ Vector((0, -0.8, 1.55)), 12, "FFCF80", 0.1)
    # stars on a far dome
    rnd = random.Random(9)
    star_m = C.mat("NightStar", "FFFFFF", rough=1.0, emit="FFF6DD", strength=6.0)
    cam = bpy.context.scene.camera
    fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
    cam_q = cam.matrix_world.to_3x3()
    for i in range(260):
        hx = rnd.uniform(-1.0, 1.0); hy = rnd.uniform(-0.75, 0.75)
        dvec = (cam_q @ Vector((hx * 0.62, hy * 0.45, -1.0))).normalized()
        p = cam.location + dvec * 80
        C.ico("Star%d" % i, p, r=rnd.uniform(0.05, 0.2) * (2.2 if rnd.random() < 0.08 else 1.0), sub=1, mat=star_m)
    s.view_settings.exposure = 0.1
    glare(True, size=8, threshold=0.8, mix=0.0)


def render(fname, w, h):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.filepath = os.path.join(C.PREVIEW_DIR, fname)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = args[0] if args else "both"
    small = "--small" in args
    w, h = (800, 550) if small else (1600, 1100)
    build_scene()
    camera_setup(w, h)
    set_day()
    bpy.ops.wm.save_as_mainfile(filepath=HERO_BLEND, compress=True)
    if mode in ("day", "both"):
        render("hero_day.png" if not small else "hero_day_small.png", w, h)
    if mode in ("night", "both"):
        set_night()
        render("hero_night.png" if not small else "hero_night_small.png", w, h)

"""Riser app icon, 3D: the game's floating island (with the sprout) in front of a big glowing sunrise.

Blender -b -P Blender/scripts/icon3d.py -- <variant> <out.png> [size]
Uses the web GLBs (site/assets/3d) so the icon matches the in-game models exactly.
The App Store icon (AppIcon.png, site/assets/icon.png) is variant `sunrise2`; `sunrise` is the original.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import common as C

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GLB = os.path.join(ROOT, "site", "assets", "3d")

# sky stops (bottom→top), sun inner/outer, items kept on the island, sprout spot
DAWN = [(0, "FFC49A"), (0.45, "F59AA8"), (0.8, "8A78D6"), (1, "4C5BC7")]
BASE = dict(sky=DAWN, sun=("FFF1B0", "FF9A45"), items={"Cottage", "TreeRound", "Pine"}, sprout=(1.2, -3.3, 2.8),
            cam=((0, 0, 0.2), (0, -1, 0.3), 23.0, 50), sun_at=((0.0, 34.0, 0.4), 10.2), sun_strength=1.15,
            clouds=[], stars=False, night=False, glass=False, key=3.0, spin=-18,
            # v2 knobs (defaults reproduce the original renders exactly):
            #   float_rocks: keep the little satellite islands around the main one
            #   ground:      uniform scale of the island itself (body + decor); props are moved in by `spread`
            #                (defaults to `ground`) but keep their size times `prop`
            #   strip:       IslandDecor detail to drop: pebbles, tufts, flowers, vines, roots, underrocks, path
            #   tufts_keep:  when "tufts" is not stripped, fraction of grass-tuft clumps to keep
            #   shift:       vertical lens shift (fraction of frame; + moves the whole picture down)
            float_rocks=True, ground=1.0, spread=None, prop=1.0, strip=frozenset(), tufts_keep=1.0, shift=0.0)
def V(**kw):
    d = dict(BASE); d.update(kw); return d
VARIANTS = {
    "cottage": V(),
    "minimal": V(items={"TreeRound"}, sprout=(0.4, -1.6, 2.8)),
    "golden":  V(sky=[(0, "FFD08A"), (0.5, "FFA66B"), (1, "E0657A")], sun=("FFF6C8", "FFB24A")),
    "blue":    V(sky=[(0, "D6ECFF"), (0.55, "7FB6F5"), (1, "3F74E0")], sun=("FFF4B8", "FFB547")),
    # character-first: close on the sprout at the cottage door
    "hero":    V(cam=((0.9, -2.6, 1.3), (0.05, -1, 0.22), 12.0, 50), sprout=(1.0, -3.2, 3.2), sun_at=((0.6, 34.0, 4.5), 9.0)),
    # high diorama view
    "diorama": V(cam=((0, 0, 0.0), (0, -1, 0.75), 24.5, 50), sun_at=((0.0, 40.0, -4.0), 11.0), items={"Cottage", "TreeRound", "Pine", "Windmill", "Pond"}),
    # dawn breaking: dark sky, stars, lit windows, sun just peeking
    "night":   V(sky=[(0, "F6A07A"), (0.3, "7A5CB8"), (0.7, "1E2A6E"), (1, "0B1034")], sun=("FFE9A0", "FF7E3D"),
                 sun_at=((0.0, 34.0, -5.5), 9.5), stars=True, night=True, key=1.2),
    # the original icon (App Store builds 1-5): dawn sky, the sun just rising behind the island
    "sunrise": V(sun_at=((0.0, 34.0, -5.5), 9.5)),
    # sun as a halo framing the island
    "halo":    V(cam=((0, 0, 0.2), (0, -1, 0.3), 27.0, 50), sun_at=((0.0, 40.0, 2.5), 17.0), sun=("FFF7D0", "FFB35A"), items={"Cottage", "TreeRound"}),
    # clouds drifting around the island
    "clouds":  V(clouds=[(-9.5, 6, -3.5, 1.3), (9.0, 4, -2.0, 1.1), (-7.0, -4, 4.5, 0.9), (8.5, 10, 5.0, 1.0)]),
    # "liquid glass" sun: glowing core inside a clear glass orb
    "glass":   V(glass=True, sun_strength=1.4),
    # low hero angle looking up at the floating island
    "below":   V(cam=((0, 0, -0.8), (0, -1, -0.12), 24.0, 50), sun_at=((0.0, 34.0, 7.5), 10.5)),
    # windmill island, golden
    "windmill": V(sky=[(0, "FFD08A"), (0.5, "FFA66B"), (1, "E0657A")], sun=("FFF6C8", "FFB24A"), items={"Windmill", "Cottage", "TreeBlossom"}),
}
# v2 (Sep 2026 feedback on "sunrise"): same sky, sun, cottage, trees and sprout; no satellite islands, a smaller
# and calmer island (no pebbles, thinned grass), recentred with a lens shift.
#   sunrise2        island at 80%, props at full size   <- the shipped App Store icon
#   sunrise2_small  island at 72%, props at 94%
#   sunrise2_clean  sunrise2 with no little flowers and sparser grass
_V2 = dict(sun_at=((0.0, 34.0, -5.5), 9.5), float_rocks=False, tufts_keep=0.35, shift=0.04)
VARIANTS["sunrise2"] = V(**_V2, ground=0.80, spread=0.95, strip=frozenset({"pebbles"}))
VARIANTS["sunrise2_small"] = V(**_V2, ground=0.72, spread=0.88, prop=0.94, strip=frozenset({"pebbles"}))
VARIANTS["sunrise2_clean"] = V(**dict(_V2, tufts_keep=0.2), ground=0.80, spread=0.95, strip=frozenset({"pebbles", "flowers"}))


def world(stops):
    w = bpy.data.worlds.new("IconWorld")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Window"], sep.inputs[0]); nt.links.new(sep.outputs["Y"], ramp.inputs[0])
    cr = ramp.color_ramp; cr.interpolation = 'EASE'
    cr.elements[0].position, cr.elements[0].color = stops[0][0], C.hex_lin(stops[0][1])
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], C.hex_lin(stops[-1][1])
    for p, c in stops[1:-1]:
        e = cr.elements.new(p); e.color = C.hex_lin(c)
    bg_cam = nt.nodes.new("ShaderNodeBackground"); nt.links.new(ramp.outputs[0], bg_cam.inputs[0])
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs[0].default_value = C.hex_lin(stops[len(stops) // 2][1]); bg_light.inputs[1].default_value = 0.7
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_light.outputs[0], mix.inputs[1]); nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def sun_sphere(loc, r, inner, outer, strength=1.15, glass=False):
    """An emissive sun: bright core fading to a warm rim."""
    m = bpy.data.materials.new("IconSunGlow"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = C.hex_lin(inner); ramp.color_ramp.elements[1].color = C.hex_lin(outer)
    nt.links.new(lw.outputs["Facing"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=96, ring_count=48)
    o = bpy.context.active_object; o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if glass:
        # Liquid Glass-style orb: clear in the middle, a bright refracted rim at the edge.
        o.scale = (0.84,) * 3
        g = bpy.data.materials.new("IconSunGlass"); g.use_nodes = True
        try: g.surface_render_method = 'BLENDED'
        except Exception: pass
        nt = g.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = C.hex_lin("FFF8EC"); em.inputs["Strength"].default_value = 2.2
        lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.12
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.55; ramp.color_ramp.elements[1].position = 1.0
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lw.outputs["Facing"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=128, ring_count=64)
        orb = bpy.context.active_object; orb.data.materials.append(g); bpy.ops.object.shade_smooth()
    return o


def glare():
    s = bpy.context.scene
    ng = bpy.data.node_groups.new("IconComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers"); g = ng.nodes.new("CompositorNodeGlare"); out = ng.nodes.new("NodeGroupOutput")
    for attr, val in (("glare_type", 'FOG_GLOW'), ("quality", 'HIGH'), ("size", 9), ("threshold", 0.95)):
        try: setattr(g, attr, val)
        except Exception: pass
    for key, val in (("Type", 'Fog Glow'), ("Quality", 'High'), ("Threshold", 1.0), ("Size", 0.55), ("Strength", 0.3)):
        if key in g.inputs:
            try: g.inputs[key].default_value = val
            except Exception: pass
    ng.links.new(rl.outputs["Image"], g.inputs["Image"]); ng.links.new(g.outputs["Image"], out.inputs[0])
    s.compositing_node_group = ng


def delete_tree(o):
    for c in list(o.children_recursive) + [o]:
        bpy.data.objects.remove(c, do_unlink=True)


DECOR_KINDS = {
    "Pebble": "pebbles", "GrassTuft": "tufts", "GrassLight": "tufts",
    "White": "flowers", "FlowerYellow": "flowers", "Blossom": "flowers", "Purple": "flowers", "BlossomDeep": "flowers",
    "Leaf": "vines", "LeafDark": "vines", "WoodDark": "roots", "Sand": "path",
}


def simplify_decor(o, strip, tufts_keep):
    """Drop whole loose parts of the IslandDecor mesh by kind (see BASE `strip`)."""
    import bmesh
    from collections import Counter
    mats = [m.name if m else "" for m in o.data.materials]
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    seen, doomed = set(), []
    for f in bm.faces:
        if f.index in seen: continue
        comp, stack = [], [f]; seen.add(f.index)
        while stack:
            g = stack.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); stack.append(h)
        name = mats[Counter(g.material_index for g in comp).most_common(1)[0][0]]
        vs = {vv for g in comp for vv in g.verts}
        cx = sum(vv.co.x for vv in vs) / len(vs); cy = sum(vv.co.y for vv in vs) / len(vs); cz = sum(vv.co.z for vv in vs) / len(vs)
        if name in ("Rock", "RockDark"):
            kind = "pebbles" if cz > -0.4 else "underrocks"
        else:
            kind = DECOR_KINDS.get(name)
        if kind in strip:
            doomed += comp
        elif kind == "tufts" and tufts_keep < 1.0:
            # thin whole clumps (a 0.45-unit cell), deterministically, so surviving tufts stay full
            cell = (int(math.floor(cx / 0.45)), int(math.floor(cy / 0.45)))
            if ((cell[0] * 73856093) ^ (cell[1] * 19349663)) % 1000 >= tufts_keep * 1000:
                doomed += comp
    bmesh.ops.delete(bm, geom=list(set(doomed)), context='FACES')
    bm.to_mesh(o.data); bm.free(); o.data.update()


def build(v):
    C.reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, "island.glb"))
    items = bpy.data.objects.get("Items")
    if items:
        for o in list(items.children):
            if o.name not in v["items"]:
                delete_tree(o)
    if not v["float_rocks"]:
        for o in [o for o in bpy.data.objects if o.name.startswith("FloatRock")]:
            delete_tree(o)
    if v["strip"] or v["tufts_keep"] < 1.0:
        simplify_decor(bpy.data.objects["IslandDecor"], v["strip"], v["tufts_keep"])
    g = v["ground"]; spread = v["spread"] if v["spread"] is not None else g
    if g != 1.0 or v["prop"] != 1.0:
        for n in ("IslandBody", "IslandDecor"):
            bpy.data.objects[n].scale = (g,) * 3
        if items:
            for o in items.children:
                o.location.x *= spread; o.location.y *= spread
                o.scale = tuple(c * v["prop"] for c in o.scale)
    island = bpy.data.objects.get("Island")
    island.rotation_euler.z += math.radians(v["spin"])
    if v["night"]:
        for m in bpy.data.materials:
            if m.name.startswith("Glow") and m.node_tree:
                bsdf = m.node_tree.nodes.get("Principled BSDF")
                if bsdf: bsdf.inputs["Emission Strength"].default_value = 8.0
    bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, "sprout.glb"))
    sprout = bpy.data.objects.get("Sprout")
    sx, sy, ss = v["sprout"]
    sprout.scale = (ss * v["prop"],) * 3
    sprout.location = (sx * spread, sy * spread, 0.0)
    sprout.rotation_euler.z = math.radians(8)
    for (x, y, z, sc) in v["clouds"]:
        bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, "cloud.glb"))
        c = bpy.context.selected_objects[0]
        while c.parent: c = c.parent
        c.location = (x, y, z); c.scale = (sc,) * 3
    if v["stars"]:
        star = C.mat("IconStar", "FFFFFF", rough=1.0, emit="FFF4D6", strength=4.0)
        import random
        rnd = random.Random(7)
        for _ in range(40):
            C.ico("star", (rnd.uniform(-22, 22), 60, rnd.uniform(9, 26)), r=rnd.choice([0.07, 0.1, 0.13]), sub=1, mat=star)
    loc, r = v["sun_at"]
    sun_sphere(loc, r, *v["sun"], strength=v["sun_strength"], glass=v["glass"])
    C.update()


def render(v, out, size):
    s = bpy.context.scene
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    C.render_setup((size, size), samples=64)
    s.render.image_settings.color_mode = 'RGB'
    world(v["sky"])
    C.sun((52, 0, -30), v["key"], col="FFF3E2", angle=12.0, name="Key")
    C.sun((-62, 0, 8), 2.6, col="FFB070", angle=6.0, name="Rim")
    target, direction, dist, lens = v["cam"]
    cam = C.camera(target, direction, dist, lens=lens, name="IconCam")
    if v["shift"]:
        cam.data.shift_y = v["shift"]
    glare()
    s.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    v = VARIANTS[a[0]]
    build(v)
    render(v, a[1], int(a[2]) if len(a) > 2 else 1024)

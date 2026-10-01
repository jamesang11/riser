"""Export web-ready glTF (.glb) assets for the Three.js site hero.

Usage:
  /opt/homebrew/bin/blender -b -P Blender/scripts/export_web.py [-- --no-verify]

Writes site/assets/3d/{island,sprout,cloud}.glb (Draco-compressed when available),
then re-imports each file into a fresh scene, prints a report and renders previews
into common.PREVIEW_DIR. Does not touch the app's .usdz models.

island.glb hierarchy (glTF +Y up, Blender -Y front -> glTF +Z):
  Island -> IslandBody, IslandDecor, FloatRock1..3, Items -> <item roots> (Cottage, Windmill -> Blades, ...)
"""
import sys, os, math, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import common as C

OUT_DIR = os.path.join(os.path.dirname(C.ROOT_DIR), "site", "assets", "3d")

# Item placements, copied from Riser/Sources/Model/Buildables.swift:
# id: (module, builder, blender (x, y), yaw radians (about +Z, same sign), scale)
ITEMS = [
    ("cottage",     "a_buildings", "build_cottage",      (0.0, 0.6),   0.0,  1),
    ("campfire",    "a_props",     "build_campfire",     (1.8, -1.6),  0.4,  1),
    ("flowers",     "a_nature",    "build_flowers",      (-3.5, -2.1), 0.0,  1),
    ("lamppost",    "a_props",     "build_lamppost",     (-1.4, -2.4), 0.0,  1),
    ("treeRound",   "a_nature",    "build_tree_round",   (-3.2, 1.2),  0.8,  1),
    ("bench",       "a_props",     "build_bench",        (0.2, -2.9),  0.0,  1),
    ("mailbox",     "a_props",     "build_mailbox",      (1.2, -3.4),  -0.3, 1),
    ("garden",      "a_nature",    "build_garden",       (-2.6, -0.8), 0.3,  1),
    ("pine",        "a_nature",    "build_pine",         (1.8, 3.4),   0.0,  1),
    ("pond",        "a_nature",    "build_pond",         (2.6, -0.2),  0.0,  1),
    ("lanterns",    "a_props",     "build_lanterns",     (0.0, 2.9),   0.0,  1),
    ("treeBlossom", "a_nature",    "build_tree_blossom", (3.2, 1.6),   0.0,  1),
    ("telescope",   "a_props",     "build_telescope",    (3.3, -2.3),  0.6,  1),
    ("windmill",    "a_buildings", "build_windmill",     (-1.6, 3.2),  0.35, 1),
]

# Alternate faces / accessories that are hidden by default in the app.
SPROUT_ALT = ["Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR",
              "MouthSad", "MouthOpen", "Nightcap"]

PRINCIPLED_KEYS = ["Base Color", "Roughness", "Metallic", "Specular IOR Level", "Coat Weight",
                   "Emission Color", "Emission Strength", "Alpha"]


def fn(mod, name):
    return getattr(importlib.import_module(mod), name)


def hierarchy(root):
    return [root] + list(root.children_recursive)


# ---------------------------------------------------------------- material isolation
def mat_vals(m):
    if not m.use_nodes or m.node_tree.nodes.get("Principled BSDF") is None:
        return None
    b = m.node_tree.nodes["Principled BSDF"]
    out = {}
    for k in PRINCIPLED_KEYS:
        i = b.inputs.get(k)
        if i is not None:
            v = i.default_value
            out[k] = tuple(v) if hasattr(v, "__len__") else v
    return out, len(m.node_tree.nodes)


def same_look(a, b):
    """Same colour/emission/coat; roughness within 0.15 (visually identical in a small web render)."""
    va, vb = mat_vals(a), mat_vals(b)
    if va is None or vb is None or va[1] != vb[1]:
        return False
    for k, x in va[0].items():
        y = vb[0].get(k)
        tol = 0.15 if k == "Roughness" else (0.05 if k == "Specular IOR Level" else 1e-3)
        xs, ys = (x, y) if isinstance(x, tuple) else ((x,), (y,))
        if any(abs(p - q) > tol for p, q in zip(xs, ys)):
            return False
    return True


def build_isolated(builder, tag):
    """Run a builder so its get-or-create materials are fresh (as when built alone for the app),
    then merge identical materials back and suffix any that differ from an existing same-named one."""
    stash = {}
    for m in list(bpy.data.materials):
        stash[m.name] = m
        m.name = "__stash__" + m.name
    before = set(bpy.data.objects)
    root = builder()
    new_mats = [m for m in bpy.data.materials if not m.name.startswith("__stash__")]
    for m in new_mats:
        old = stash.get(m.name)
        if old is not None and same_look(old, m):
            m.user_remap(old)
            bpy.data.materials.remove(m)
        elif old is not None:
            print(f"@@ material clash: {m.name} differs in {tag}; renamed")
            m.name = f"{m.name}_{tag}"
    for name, m in stash.items():
        m.name = name
    # drop stray objects the builder left outside its hierarchy (usdz export drops them too)
    keep = set(hierarchy(root))
    for o in set(bpy.data.objects) - before - keep:
        print(f"@@ stray object removed from {tag}: {o.name}")
        bpy.data.objects.remove(o)
    for o in hierarchy(root):
        C.apply_mods(o)
    return root


def dedupe_names(roots):
    """Names that collide across items (Canopy, Trunk, ...) become <base>_<ItemRoot>."""
    from collections import defaultdict
    by_base = defaultdict(list)
    for r in roots:
        for o in hierarchy(r)[1:]:
            base = o.name.split(".")[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
            by_base[base].append((o, r))
    # rename to temp first so final names never collide
    todo = [(base, lst) for base, lst in by_base.items() if len(lst) > 1]
    for base, lst in todo:
        for o, r in lst:
            o.name = "__tmp__" + o.name
    for base, lst in todo:
        for o, r in lst:
            o.name = f"{base}_{r.name}"


# ---------------------------------------------------------------- export
def export_glb(root, fname):
    os.makedirs(OUT_DIR, exist_ok=True)
    keep = set(hierarchy(root))
    for o in list(bpy.context.scene.objects):
        if o not in keep:
            bpy.data.objects.remove(o)
    for o in keep:
        C.apply_mods(o)
        o.hide_set(False)
        o.hide_render = False
        o.hide_viewport = False
    bpy.ops.object.select_all(action='DESELECT')
    for o in keep:
        o.select_set(True)
    path = os.path.join(OUT_DIR, fname)
    kw = dict(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
        export_materials='EXPORT', export_cameras=False, export_lights=False, export_animations=False,
        export_texcoords=False, export_normals=True, export_tangents=False, export_attributes=False,
        export_vertex_color='NONE', export_extras=False, export_morph=False, export_skins=False,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14, export_draco_normal_quantization=10,
        export_image_format='NONE', check_existing=False,
    )
    valid = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    dropped = [k for k in kw if k not in valid]
    if dropped:
        print("@@ glTF export: unsupported args dropped:", dropped)
    try:
        bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in valid})
        draco = kw["export_draco_mesh_compression_enable"] and "export_draco_mesh_compression_enable" in valid
    except Exception as e:
        print("@@ Draco export failed, retrying without:", e)
        kw["export_draco_mesh_compression_enable"] = False
        bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in valid})
        draco = False
    print(f"@@ exported {path}: {os.path.getsize(path) / 1024:.0f} KB draco={draco} tris={C.tri_count(root)}")
    return path


def make_island():
    C.reset()
    I = importlib.import_module("a_island")
    island = build_isolated(I.build_island, "Island")
    items_root = C.empty("Items", parent=island)
    roots = []
    for iid, mod, bfn, (x, y), yaw, s in ITEMS:
        r = build_isolated(fn(mod, bfn), iid)
        r.location = (x, y, 0.0)
        r.rotation_euler = (0, 0, yaw)
        r.scale = (s, s, s)
        C.update()
        C.set_parent(r, items_root)
        roots.append(r)
    dedupe_names(roots)
    return export_glb(island, "island.glb")


def make_sprout():
    C.reset()
    S = importlib.import_module("a_sprout")
    root = build_isolated(S.build_sprout, "Sprout")
    for n in SPROUT_ALT:
        o = bpy.data.objects.get(n)
        if o:
            for c in list(o.children_recursive):
                bpy.data.objects.remove(c)
            bpy.data.objects.remove(o)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    return export_glb(root, "sprout.glb")


def make_cloud():
    C.reset()
    N = importlib.import_module("a_nature")
    root = build_isolated(N.build_cloud_a, "CloudA")
    return export_glb(root, "cloud.glb")


# ---------------------------------------------------------------- verify
def to_gltf(v):
    return Vector((v.x, v.z, -v.y))


def verify(path, preview_name=None, preview_opts=None):
    C.reset()
    bpy.ops.import_scene.gltf(filepath=path)
    C.update()
    objs = list(bpy.context.scene.objects)
    meshes = [o for o in objs if o.type == 'MESH']
    mn, mx = C.world_bbox(meshes)
    gmn, gmx = to_gltf(mn), to_gltf(mx)
    gmin = Vector((min(gmn.x, gmx.x), min(gmn.y, gmx.y), min(gmn.z, gmx.z)))
    gmax = Vector((max(gmn.x, gmx.x), max(gmn.y, gmx.y), max(gmn.z, gmx.z)))
    print(f"@@ VERIFY {os.path.basename(path)}  size={os.path.getsize(path) / 1024:.0f} KB  objects={len(objs)} meshes={len(meshes)} "
          f"tris={sum(C.tris(o) for o in meshes)}")
    print(f"@@   glTF bbox min=({gmin.x:.2f}, {gmin.y:.2f}, {gmin.z:.2f}) max=({gmax.x:.2f}, {gmax.y:.2f}, {gmax.z:.2f}) "
          f"size=({gmax.x - gmin.x:.2f}, {gmax.y - gmin.y:.2f}, {gmax.z - gmin.z:.2f})")
    print("@@   nodes:", ", ".join(sorted(o.name for o in objs)))
    for m in sorted(bpy.data.materials, key=lambda m: m.name):
        b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
        if not b:
            print(f"@@   mat {m.name}: (no principled)")
            continue
        bc = b.inputs["Base Color"].default_value
        em = b.inputs["Emission Color"].default_value
        es = b.inputs["Emission Strength"].default_value
        hexc = "".join("%02X" % round(255 * ((c * 12.92) if c <= 0.0031308 else (1.055 * c ** (1 / 2.4) - 0.055))) for c in bc[:3])
        glow = (es > 0 and max(em[:3]) > 0)
        print(f"@@   mat {m.name}: base #{hexc} rough={b.inputs['Roughness'].default_value:.2f}" + (" EMISSIVE" if glow else ""))
    body = bpy.data.objects.get("IslandBody")
    if body:
        dg = bpy.context.evaluated_depsgraph_get()
        for (x, y) in [(0.0, -2.0), (-1.0, 1.5), (2.0, 1.5)]:
            hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((x, y, 20)), Vector((0, 0, -1)))
            ok, l2, *_ = body.ray_cast(body.matrix_world.inverted() @ Vector((x, y, 20)), Vector((0, 0, -1)))
            print(f"@@   island top at ({x},{y}) blender -> glTF y = {(body.matrix_world @ l2).z if ok else None:.3f}")
        # every item root should sit on the top (base z ~ 0)
        items = bpy.data.objects.get("Items")
        if items:
            for r in items.children:
                imn, imx = C.world_bbox([o for o in hierarchy(r) if o.type == 'MESH'])
                print(f"@@   item {r.name:12s} at ({r.location.x:+.2f},{r.location.y:+.2f}) base z={imn.z:+.3f} top z={imx.z:+.3f}")
    if preview_name:
        roots = [o for o in objs if o.parent is None]
        top = roots[0] if len(roots) == 1 else None
        if top is None:
            top = bpy.data.objects.new("PreviewRoot", None)
            C.link(top)
            for r in roots:
                r.parent = top
        C.preview(top, preview_name, **(preview_opts or {}))
        print("@@   preview", os.path.join(C.PREVIEW_DIR, preview_name))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    paths = [make_island(), make_sprout(), make_cloud()]
    total = sum(os.path.getsize(p) for p in paths)
    print(f"@@ TOTAL {total / 1024:.0f} KB")
    if "--no-verify" not in args:
        verify(paths[0], "web_island.png", dict(ground=False, az=24, el=26, fill=0.68, target_z=-1.2))
        verify(paths[1], "web_sprout.png", dict(az=22, el=14, fill=0.95))
        verify(paths[2], "web_cloud.png", dict(ground=False))

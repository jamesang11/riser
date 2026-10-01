"""Riser procedural asset toolkit (Blender 4.5, headless).

Conventions: Blender Z-up, 1 unit = 1 m, assets face -Y. Every asset is built
under one root Empty at the origin. `export_usdz` bakes a Z-up -> Y-up change
of basis into every object's local frame so that SceneKit node-local axes are
Y-up too (e.g. scaling an eye's Y blinks it vertically).
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler, noise

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = "/Users/jamesangrellera/RIZER/Riser/Resources/Models"
PREVIEW_DIR = "/private/tmp/claude-501/-Users-jamesangrellera-RIZER/0b8b9016-7c85-49c1-b471-4f73b6285a01/scratchpad/previews"
SOURCES_DIR = os.path.join(ROOT_DIR, "sources")

# --------------------------------------------------------------------------- palette
PALETTE = {
    "Grass": "7BC96F", "GrassDark": "5FAF5A", "GrassTuft": "8FD67E",
    "Dirt": "A9774F", "DirtDeep": "8B5E3C", "Rock": "B8B2A7", "RockDark": "8E8A83",
    "Sand": "E8D2A6", "Wood": "B07A4A", "WoodDark": "7A4F2E", "RoofRed": "E0674F",
    "RoofRedDark": "C95440", "RoofTeal": "4FA3A5", "RoofTealDark": "3F8C8E",
    "Cream": "F6E9D2", "TentOrange": "F2B45A", "TentCream": "F7E3B5",
    "Leaf": "6CC265", "LeafLight": "8BD67A", "LeafDark": "4FA85A",
    "Blossom": "F7B7C9", "BlossomDeep": "F59BB6", "BlossomLight": "FBD3DE",
    "SproutBody": "F3F6E4", "SproutCheek": "F7A8A8", "SproutEye": "2B2530",
    "FlowerYellow": "FFD65A", "White": "FFFFFF", "Soil": "6B4630",
    "Iron": "3E4658", "Brass": "E0AE4F", "Navy": "34497A", "WoodLight": "E2BB8A",
    "Apple": "E5533F", "Purple": "B79BE8", "Orange": "F59A4E", "Coral": "F2866B",
    "Pine": "4E9E62", "PineLight": "67B872", "Stem": "7FBF5F", "Carrot": "F28C3A",
    "Cabbage": "A9DB8A", "PondBed": "3E8FA8", "Reed": "74B35E", "Cattail": "8A5A36",
    "Rug": "4FA3A5", "Mail": "5DB3B5", "Interior": "5A3A26", "Pebble": "D8D0C2",
}

def hex_lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)

def mat(name, hexc=None, rough=0.82, emit=None, strength=1.0, spec=0.35, coat=0.0):
    """Get-or-create a flat Principled material."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    hexc = hexc or PALETTE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = hex_lin(hexc)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = hex_lin(emit)
        b.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = hex_lin(hexc)
    return m

def M(name, **kw):
    return mat(name, **kw)

def set_emission(name, strength):
    m = bpy.data.materials.get(name)
    if m:
        m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = strength

# --------------------------------------------------------------------------- scene utils
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o

def update():
    bpy.context.view_layer.update()

def mk(name, bm, mats=(), loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    link(o)
    o.location = loc
    return o

def empty(name, loc=(0, 0, 0), parent=None, size=0.2):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    link(e)
    e.location = loc
    update()
    if parent:
        set_parent(e, parent)
    return e

def set_parent(ch, par):
    update()
    w = ch.matrix_world.copy()
    ch.parent = par
    ch.matrix_parent_inverse = Matrix.Identity(4)
    ch.matrix_world = w
    update()
    return ch

def xform(rot=(0, 0, 0), scale=(1, 1, 1), loc=(0, 0, 0)):
    r = Euler(tuple(math.radians(a) for a in rot), 'XYZ').to_matrix().to_4x4()
    s = Matrix.Diagonal(Vector(scale).to_4d())
    return Matrix.Translation(Vector(loc)) @ r @ s

# --------------------------------------------------------------------------- primitives
def _finish(name, bm, mat_, loc, scale, rot, smooth, sharp):
    o = mk(name, bm, [mat_] if mat_ else [])
    o.data.transform(xform(rot, scale))
    o.location = loc
    if smooth:
        shade(o, sharp)
    return o

def sphere(name, loc=(0, 0, 0), r=0.5, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, seg=24, rings=12, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    return _finish(name, bm, mat, loc, scale, rot, smooth, 180)

def ico(name, loc=(0, 0, 0), r=0.5, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, sub=2, smooth=True, sharp=180):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return _finish(name, bm, mat, loc, scale, rot, smooth, sharp)

def cyl(name, loc=(0, 0, 0), r=0.5, h=1.0, r2=None, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, seg=16,
        base=False, bevel=0.0, bseg=2, smooth=True, sharp=40):
    """Cylinder/cone along local Z. base=True puts origin at the bottom face."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    if base:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    o = mk(name, bm, [mat] if mat else [])
    if bevel:
        add_bevel(o, bevel, bseg)
        apply_mods(o)
    o.data.transform(xform(rot, scale))
    o.location = loc
    if smooth:
        shade(o, sharp)
    return o

def box(name, loc=(0, 0, 0), size=(1, 1, 1), rot=(0, 0, 0), mat=None, bevel=0.04, bseg=3, smooth=True, sharp=40, base=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if base:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, size[2] / 2))
    o = mk(name, bm, [mat] if mat else [])
    if bevel:
        add_bevel(o, bevel, bseg, limit=False)
        apply_mods(o)
    o.data.transform(xform(rot))
    o.location = loc
    if smooth:
        shade(o, sharp)
    return o

def torus(name, loc=(0, 0, 0), R=0.5, r=0.1, rot=(0, 0, 0), scale=(1, 1, 1), mat=None, seg=24, mseg=8, arc=360.0, smooth=True):
    bm = bmesh.new()
    closed = arc >= 359.9
    n = seg if closed else seg + 1
    rings = []
    for i in range(n):
        a = math.radians(arc) * i / seg
        ring = []
        for j in range(mseg):
            b = 2 * math.pi * j / mseg
            rr = R + r * math.cos(b)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(n if closed else n - 1):
        a, b_ = rings[i], rings[(i + 1) % n]
        for j in range(mseg):
            bm.faces.new((a[j], a[(j + 1) % mseg], b_[(j + 1) % mseg], b_[j]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, mat, loc, scale, rot, smooth, 180)

def lathe(name, profile, seg=24, loc=(0, 0, 0), mat=None, rfun=None, rot=(0, 0, 0), scale=(1, 1, 1), smooth=True, sharp=50, mat_idx=None, mats=None, caps=True):
    """Revolve profile [(r, z), ...] (bottom -> top) around Z. r==0 makes a pole.
    rfun(theta, z) -> radius multiplier. mat_idx: per-profile-segment material index."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            ring = []
            for i in range(seg):
                t = 2 * math.pi * i / seg
                k = rfun(t, z) if rfun else 1.0
                ring.append(bm.verts.new((r * k * math.cos(t), r * k * math.sin(t), z)))
            rings.append(ring)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        fs = []
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(seg):
                fs.append(bm.faces.new((a[0], b[i], b[(i + 1) % seg])))
        elif len(b) == 1:
            for i in range(seg):
                fs.append(bm.faces.new((a[i], b[0], a[(i + 1) % seg])))
        else:
            for i in range(seg):
                fs.append(bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i])))
        if mat_idx:
            for f in fs:
                f.material_index = mat_idx[k]
    if caps and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if caps and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ms = mats if mats else ([mat] if mat else [])
    o = mk(name, bm, ms)
    o.data.transform(xform(rot, scale))
    o.location = loc
    if smooth:
        shade(o, sharp)
    return o

def tube(name, pts, r=0.05, mat=None, radii=None, seg=8, caps=True, res=6, smooth=True, sharp=70):
    """Smooth swept tube through points (bezier, auto handles). radii = per-point multipliers."""
    cu = bpy.data.curves.new(name + "_cu", 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = max(0, (seg - 4) // 2)
    cu.use_fill_caps = caps
    cu.resolution_u = res
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for i, (bp, p) in enumerate(zip(sp.bezier_points, pts)):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
        bp.radius = radii[i] if radii else 1.0
    co = link(bpy.data.objects.new(name + "_tmp", cu))
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(co.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(co)
    bpy.data.curves.remove(cu)
    me.name = name
    o = link(bpy.data.objects.new(name, me))
    me.materials.clear()
    if mat:
        me.materials.append(mat)
    if smooth:
        shade(o, sharp)
    return o

def leaf(name, length=0.2, width=0.08, thick=0.015, curl=0.03, mat=None, seg=12, rings=8, fold=0.25):
    """Leaf along +X from origin (attach point), pointed tip, gentle upward curl & midrib fold."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=0.5)
    for v in bm.verts:
        x, y, z = v.co
        t = x + 0.5                       # 0..1 along leaf
        prof = math.sin(math.pi * min(1, max(0, t)) ** 0.85) ** 0.9
        v.co.x = t * length
        v.co.y = y * 2 * width * (0.25 + 0.75 * prof)
        v.co.z = z * 2 * thick * (0.4 + 0.6 * prof) + curl * (t ** 2) * 4 * 0.25 + abs(v.co.y) * fold
    o = mk(name, bm, [mat] if mat else [])
    shade(o, 180)
    return o

# --------------------------------------------------------------------------- mesh ops
def shade(o, angle=40):
    if o.type != 'MESH':
        return
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for f in bm.faces:
        f.smooth = True
    lim = math.radians(angle)
    for e in bm.edges:
        e.smooth = True
        if angle < 179 and len(e.link_faces) == 2:
            try:
                if e.calc_face_angle() > lim:
                    e.smooth = False
            except ValueError:
                pass
    bm.to_mesh(o.data)
    bm.free()

def add_bevel(o, w, seg=3, limit=True, angle=35):
    m = o.modifiers.new("Bevel", 'BEVEL')
    m.width = w
    m.segments = seg
    m.limit_method = 'ANGLE' if limit else 'NONE'
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = True
    return m

def add_subsurf(o, lv=1):
    m = o.modifiers.new("Sub", 'SUBSURF')
    m.levels = lv
    m.render_levels = lv
    return m

def apply_mods(o):
    if o.type != 'MESH' or not o.modifiers:
        return o
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return o

def join(objs, name=None):
    objs = [o for o in objs if o]
    for o in objs:
        apply_mods(o)
    a = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=a, object=a, selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.join()
    if name:
        a.name = name
        a.data.name = name
    return a

def set_origin(o, pt):
    """Move object origin to world point pt without moving geometry or children."""
    update()
    kids = [(c, c.matrix_world.copy()) for c in o.children]
    local = o.matrix_world.inverted() @ Vector(pt)
    if o.type == 'MESH':
        o.data.transform(Matrix.Translation(-local))
    o.matrix_world = o.matrix_world @ Matrix.Translation(local)
    update()
    for c, w in kids:
        c.matrix_world = w
    update()

def bake_transform(o):
    """Apply rotation/scale into mesh data, keep location."""
    update()
    if o.type == 'MESH':
        loc = o.matrix_world.to_translation()
        o.data.transform(Matrix.Translation(-loc) @ o.matrix_world)
        o.matrix_world = Matrix.Translation(loc)

def jitter(o, amp=0.02, freq=3.0, seed=0, axes=(1, 1, 1)):
    off = Vector((seed * 13.7, seed * 7.1, seed * 3.3))
    for v in o.data.vertices:
        n = noise.noise_vector(v.co * freq + off)
        v.co += Vector((n.x * axes[0], n.y * axes[1], n.z * axes[2])) * amp

def blob(name, spheres, mat=None, voxel=0.05, smooth_iter=6, target=2000, flat_bottom=None, seed=0, jit=0.0):
    """Merge ellipsoids [(center, radius, (sx,sy,sz))] into one soft blobby mesh."""
    bm = bmesh.new()
    for s in spheres:
        c, r = s[0], s[1]
        sc = s[2] if len(s) > 2 else (1, 1, 1)
        m = Matrix.Translation(Vector(c)) @ Matrix.Diagonal(Vector(sc).to_4d())
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r, matrix=m)
    o = mk(name, bm, [mat] if mat else [])
    rm = o.modifiers.new("Remesh", 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    apply_mods(o)
    if jit:
        jitter(o, jit, 1.5, seed)
    if flat_bottom is not None:
        for v in o.data.vertices:
            if v.co.z < flat_bottom:
                v.co.z = flat_bottom + (v.co.z - flat_bottom) * 0.15
    sm = o.modifiers.new("Smooth", 'SMOOTH')
    sm.factor = 0.8
    sm.iterations = smooth_iter
    apply_mods(o)
    n = tris(o)
    if n > target:
        d = o.modifiers.new("Dec", 'DECIMATE')
        d.ratio = target / n
        apply_mods(o)
    shade(o, 180)
    return o

def tris(o):
    if o.type != 'MESH':
        return 0
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def tri_count(root):
    return sum(tris(o) for o in [root] + list(root.children_recursive))

def paint_faces(o, mat_, pred):
    """Assign material mat_ to faces where pred(center_world, normal_world) is True."""
    if mat_.name not in [m.name for m in o.data.materials if m]:
        o.data.materials.append(mat_)
    idx = [m.name if m else None for m in o.data.materials].index(mat_.name)
    mw = o.matrix_world
    nm = mw.to_3x3()
    for p in o.data.polygons:
        if pred(mw @ p.center, (nm @ p.normal).normalized()):
            p.material_index = idx

def rng(seed):
    return random.Random(seed)

# --------------------------------------------------------------------------- export
C_YUP = Matrix.Rotation(-math.pi / 2, 4, 'X')   # (x,y,z) -> (x, z, -y)

def bake_yup(root):
    """Re-express every object's local frame + mesh data in Y-up space, keeping the
    Blender-world result identical; root gets C^-1 so the exporter's axis
    conversion (applied on root prims only) yields an identity root."""
    update()
    objs = [root] + list(root.children_recursive)
    Ci = C_YUP.inverted()
    local = {}
    for o in objs:
        local[o] = (o.parent.matrix_world.inverted() @ o.matrix_world) if o.parent else o.matrix_world.copy()
    done = set()
    for o in objs:
        if o.type == 'MESH':
            if o.data.users > 1 or o.data.name in done:
                o.data = o.data.copy()
            o.data.transform(C_YUP)
            done.add(o.data.name)
    for o in objs:
        o.matrix_parent_inverse = Matrix.Identity(4)
        L = C_YUP @ local[o] @ Ci
        o.matrix_basis = (Ci @ L) if o is root else L
    update()

def export_usdz(root, fname):
    os.makedirs(MODELS_DIR, exist_ok=True)
    keep = set([root] + list(root.children_recursive))
    for o in list(bpy.context.scene.objects):
        if o not in keep:
            bpy.data.objects.remove(o)
    for o in keep:
        apply_mods(o)
        o.hide_set(False)
        o.hide_render = False
    bake_yup(root)
    for o in bpy.context.scene.objects:
        o.select_set(o in keep)
    path = os.path.join(MODELS_DIR, fname)
    kw = dict(
        filepath=path, selected_objects_only=True, visible_objects_only=False,
        export_animation=False, export_hair=False, export_uvmaps=False, export_mesh_colors=False,
        export_normals=True, export_materials=True, generate_preview_surface=True,
        generate_materialx_network=False, export_textures=False,
        convert_orientation=True, export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y',
        export_lights=False, export_cameras=False, export_curves=False, export_points=False, export_volumes=False,
        export_armatures=False, export_shapekeys=False, export_custom_properties=False,
        author_blender_name=False, convert_world_material=False, triangulate_meshes=True,
        root_prim_path="", merge_parent_xform=False)
    valid = {p.identifier for p in bpy.ops.wm.usd_export.get_rna_type().properties}
    dropped = [k for k in kw if k not in valid]
    if dropped:
        print("USD export: unsupported args dropped:", dropped)
    bpy.ops.wm.usd_export(**{k: v for k, v in kw.items() if k in valid})
    return path

# --------------------------------------------------------------------------- rendering
def world_gradient(top="7EC8F2", horizon="D9F0FA", bottom=None, strength=1.0, light_col=None, light_strength=1.0):
    w = bpy.data.worlds.get("RiserWorld") or bpy.data.worlds.new("RiserWorld")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = hex_lin(bottom or horizon)
    cr.elements[1].position = 0.55
    cr.elements[1].color = hex_lin(top)
    e = cr.elements.new(0.08)
    e.color = hex_lin(horizon)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs[1].default_value = strength
    nt.links.new(ramp.outputs[0], bg_cam.inputs[0])
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs[0].default_value = hex_lin(light_col or top)
    bg_light.inputs[1].default_value = light_strength
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_light.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])

LOOK = {'view': 'Standard', 'look': 'None', 'exposure': -0.2, 'sun': 3.0, 'ambient': 0.6}

def render_setup(res=(800, 800), samples=64):
    s = bpy.context.scene
    try:
        s.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = False
    s.render.image_settings.file_format = 'PNG'
    e = s.eevee
    e.taa_render_samples = samples
    e.use_shadows = True
    e.shadow_ray_count = 2
    e.shadow_step_count = 8
    e.use_fast_gi = True
    e.fast_gi_distance = 1.5
    e.use_raytracing = True
    s.view_settings.view_transform = LOOK['view']
    try:
        s.view_settings.look = LOOK['look']
    except Exception:
        pass
    s.view_settings.exposure = LOOK['exposure']

def sun(rot=(50, 0, 35), strength=3.2, col="FFF1DC", angle=6.0, name="Sun"):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.color = hex_lin(col)[:3]
    ld.angle = math.radians(angle)
    o = link(bpy.data.objects.new(name, ld))
    o.rotation_euler = Euler(tuple(math.radians(a) for a in rot))
    return o

def point_light(name, loc, energy=50, col="FFC77A", radius=0.1):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = hex_lin(col)[:3]
    ld.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    return o

def world_bbox(objs):
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
    return mn, mx

def camera(target, direction, dist, lens=50, name="Cam", ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 500
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    o = link(bpy.data.objects.new(name, cd))
    d = Vector(direction).normalized()
    o.location = Vector(target) + d * dist
    o.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o

def preview(root, fname, az=32, el=24, ground=True, fill=0.92, size=800, extra=None, sun_rot=(52, 0, 38), target_z=None):
    """3/4 preview render of the asset hierarchy."""
    objs = [root] + list(root.children_recursive)
    mn, mx = world_bbox(objs)
    ctr = (mn + mx) / 2
    if target_z is not None:
        ctr.z = target_z
    rad = (mx - mn).length / 2
    render_setup((size, size))
    world_gradient(top="8FD0F5", horizon="E6F5FB", light_col="D5E8F5", light_strength=LOOK.get('ambient', 0.75))
    sun(sun_rot, LOOK.get('sun', 4.0), col="FFEFD6")
    tmp = []
    if ground:
        g = cyl("PreviewGround", (0, 0, -0.01), r=max(rad * 4, 3), h=0.02, mat=mat("PreviewGround", "D7ECC8", rough=0.95), seg=64, smooth=False)
        tmp.append(g)
    fov = 2 * math.atan(18 / 50)
    dist = rad / math.sin(fov / 2) * fill
    a, e = math.radians(az), math.radians(el)
    cam = camera(ctr, (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)), dist)
    s = bpy.context.scene
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    s.render.filepath = os.path.join(PREVIEW_DIR, fname)
    bpy.ops.render.render(write_still=True)
    return s.render.filepath

def save_blend(fname):
    os.makedirs(SOURCES_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SOURCES_DIR, fname), compress=True)


def prism(name, pts, y0, y1, mat=None, bevel=0.0, bseg=2, sharp=40, smooth=True):
    """Extrude a 2D polygon given in the XZ plane [(x, z), ...] from y0 to y1."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y0, z)) for x, z in pts]
    f = bm.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bm, geom=[f])
    moved = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=(0, y1 - y0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mk(name, bm, [mat] if mat else [])
    if bevel:
        add_bevel(o, bevel, bseg, limit=True, angle=30)
        apply_mods(o)
    if smooth:
        shade(o, sharp)
    return o

def arch_pts(w, h, n=10, z0=0.0):
    """Rectangle with a semicircular top, width w, total height h (XZ)."""
    r = w / 2
    pts = [(-r, z0), (r, z0)]
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((r * math.cos(a), z0 + h - r + r * math.sin(a)))
    return pts

def place(o, rot_z=0.0, loc=(0, 0, 0)):
    """Rotate mesh data about Z (deg) then translate data (object stays at origin)."""
    o.data.transform(Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot_z), 4, 'Z'))
    return o


def slot(name, loc, parent, rz=0.0, ry_after=0.0):
    """Placement slot empty. Items placed with identity rotation face Blender -Y (SceneKit +Z);
    rz rotates that facing about the vertical axis (deg); ry_after tilts it (deg, about world Y) e.g. for sloped walls."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.3
    link(e)
    m = Matrix.Rotation(math.radians(ry_after), 4, 'Y') @ Matrix.Rotation(math.radians(rz), 4, 'Z')
    e.matrix_world = Matrix.Translation(Vector(loc)) @ m
    update()
    set_parent(e, parent)
    return e


def set_color(name, hexc):
    m = bpy.data.materials.get(name)
    if m:
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_lin(hexc)
        m.diffuse_color = hex_lin(hexc)


def harvest(root, loc=(0, 0, 0), rz=0.0, s=1.0):
    """Place a builder's root, bake every mesh into world space, drop the empties; returns the meshes."""
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rz))
    root.scale = (s, s, s)
    update()
    objs = [root] + list(root.children_recursive)
    meshes = []
    for o in objs:
        if o.type == 'MESH':
            apply_mods(o)
            if o.data.users > 1:
                o.data = o.data.copy()
            mw = o.matrix_world.copy()
            o.parent = None
            o.data.transform(mw)
            o.matrix_world = Matrix.Identity(4)
            meshes.append(o)
    for o in objs:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    return meshes

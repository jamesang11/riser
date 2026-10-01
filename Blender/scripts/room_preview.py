import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import importlib
import common as C, a_sprout
allargs = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
args = [a for a in allargs if not a.startswith('--')]
size = int(args[0]) if args else 1000
modname = args[1] if len(args) > 1 else 'a_bedroom'
builder = args[2] if len(args) > 2 else 'build_bedroom'
out = args[3] if len(args) > 3 else 'bedroom.png'
mod = importlib.import_module(modname)
C.reset()
root = getattr(mod, builder)()
sp = a_sprout.build_sprout()
show = {"EyeSleepL", "EyeSleepR", "MouthSad", "Nightcap", "Bud"}
toggle = {"Bud", "Flower", "EyeL", "EyeR", "EyeShineL", "EyeShineR", "Mouth", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR",
          "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"}
for o in sp.children_recursive:
    if o.name in toggle:
        o.hide_render = o.name not in show
bpy.data.materials["SproutBody"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = C.hex_lin("E3EFCB")
C.update()
so = bpy.data.objects["SproutOrigin"].matrix_world.to_translation()
sp.location = so
sp.scale = (mod.SPROUT_SCALE,) * 3
sp.rotation_euler = (mod.RECLINE, 0, 0)
if "--slots" in allargs:
    cols = ["FF5A5A", "5AB0FF", "5AD27A", "FFB84D", "C77DFF"]
    for i, o in enumerate(sorted([o for o in bpy.data.objects if o.name.startswith("Slot")], key=lambda o: o.name)):
        m = C.mat("Marker" + o.name, cols[i % 5], rough=0.5, emit=cols[i % 5], strength=0.3)
        if "Floor" in o.name:
            parts = [C.box("mk", (0, 0, 0), (0.96, 0.96, 0.08), mat=m, bevel=0.01, bseg=1, base=True),
                     C.box("mk2", (0, 0, 0), (0.5, 0.5, 0.5), mat=m, bevel=0.02, bseg=1, base=True),
                     C.cyl("arrow", (0, -0.48, 0.25), r=0.12, r2=0.0, h=0.3, rot=(90, 0, 0), mat=m, seg=10)]
        else:
            parts = [C.box("mk", (0, -0.03, 0), (0.6, 0.06, 0.45), mat=m, bevel=0.01, bseg=1),
                     C.cyl("arrow", (0, -0.2, 0), r=0.08, r2=0.0, h=0.25, rot=(90, 0, 0), mat=m, seg=10)]
        mk = C.join(parts)
        C.set_origin(mk, (0, 0, 0))
        mk.matrix_world = o.matrix_world.copy()
C.LOOK.update(view='Standard', look='None', exposure=0.0)
C.render_setup((size, int(size * 0.8)), samples=48)
C.world_gradient(top="F6D9C8", horizon="FBEADF", light_col="F3E6DA", light_strength=0.7)
C.sun((48, 0, 35), 2.4, col="FFE9CF", angle=8)
lp = bpy.data.objects["LampLight"].matrix_world.to_translation()
C.point_light("lamp", lp, 60, "FFC77A", 0.1)
C.point_light("fill", (0.5, 0.0, 2.3), 120, "FFE7D0", 1.0)
rc = bpy.data.objects["RoomCenter"].matrix_world.to_translation()
d = Vector((0.62, -0.8, 0.62)).normalized()
C.camera(rc, d, 9.3, lens=40, name="Cam")
s = bpy.context.scene
s.render.filepath = os.path.join(C.PREVIEW_DIR, out)
bpy.ops.render.render(write_still=True)
print("@@ tris", C.tri_count(root))

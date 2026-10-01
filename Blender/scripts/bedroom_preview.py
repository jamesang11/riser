import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import common as C, a_bedroom, a_sprout
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
size = int(args[0]) if args else 1000
C.reset()
root = a_bedroom.build_bedroom()
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
sp.scale = (a_bedroom.SPROUT_SCALE,) * 3
sp.rotation_euler = (a_bedroom.RECLINE, 0, 0)
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
s.render.filepath = os.path.join(C.PREVIEW_DIR, "bedroom.png")
bpy.ops.render.render(write_still=True)
print("@@ tris", C.tri_count(root))

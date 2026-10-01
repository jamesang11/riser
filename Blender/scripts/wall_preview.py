"""Preview wall furniture mounted on a little wall: previews/furn_<id>.png"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C, a_furniture as F
for wid in F.WALL:
    C.reset()
    root = getattr(F, "furn_" + wid)()
    root.location = (0, 0, 1.3)
    C.update()
    wall = C.box("wall", (0, 0.05, 0), (2.4, 0.1, 2.4), mat=C.mat("Wallpaper", "F6E9D2", rough=0.9), bevel=0.0, smooth=False, base=True)
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    C.render_setup((800, 800), samples=32)
    C.world_gradient(top="8FD0F5", horizon="E6F5FB", light_col="D5E8F5", light_strength=0.6)
    C.sun((55, 0, 30), 3.0, col="FFEFD6")
    mn, mx = C.world_bbox([root] + list(root.children_recursive))
    ctr = (mn + mx) / 2
    rad = max((mx - mn).length / 2, 0.3)
    C.camera(ctr, (0.35, -1, 0.25), rad * 3.2, lens=50, name="Cam")
    s = bpy.context.scene
    s.render.filepath = os.path.join(C.PREVIEW_DIR, "furn_%s.png" % wid)
    bpy.ops.render.render(write_still=True)

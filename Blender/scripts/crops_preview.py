"""Contact sheet: every crop x 4 stages -> previews/crops.png"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C, a_crops
outs = []
for kind in a_crops.CROPS:
    C.reset()
    root = a_crops.build_crop(kind)
    for i, st in enumerate(["Stage1", "Stage2", "Ripe", "Withered"]):
        o = bpy.data.objects[st]
        o.location = ((i - 1.5) * 1.15, 0, 0)
        C.box("soil", ((i - 1.5) * 1.15, 0, -0.06), (0.95, 0.95, 0.12), mat=C.mat("FarmSoil", "5E3B26", rough=0.95), bevel=0.03, bseg=2)
    C.LOOK.update(view='Standard', look='None', exposure=0.0)
    C.render_setup((1000, 330), samples=32)
    C.world_gradient(top="8FD0F5", horizon="E6F5FB", light_col="D5E8F5", light_strength=0.6)
    C.sun((52, 0, 38), 3.0, col="FFEFD6")
    C.cyl("ground", (0, 0, -0.13), r=12, h=0.02, mat=C.mat("PreviewGround", "D7ECC8", rough=0.95), seg=48, smooth=False)
    C.camera((0, 0, 0.45), (0, -1, 0.42), 5.3, lens=50, name="Cam", ortho=4.8)
    s = bpy.context.scene
    s.render.filepath = os.path.join(C.PREVIEW_DIR, "crop_%s.png" % kind)
    bpy.ops.render.render(write_still=True)
    outs.append(s.render.filepath)
    print("@@ %s tris=%d" % (kind, C.tri_count(root)))

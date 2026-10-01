"""Contact sheet: sprout wearing every hat -> previews/hats.png"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C, a_hats
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ids = args or a_hats.HAT_IDS
outs = []
for hid in ids:
    C.reset()
    root, sp = a_hats.build_hat(hid, keep_sprout=True)
    for n in ("Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"):
        bpy.data.objects[n].hide_render = True
    C.preview(sp, "hat_%s.png" % hid, az=22, el=16, fill=1.25, size=420, target_z=0.27)
    outs.append(os.path.join(C.PREVIEW_DIR, "hat_%s.png" % hid))
print("@@", " ".join(outs))

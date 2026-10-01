"""Render the sprout expression sheet: default / happy wave / sleeping.
Blender -b -P sprout_poses.py -- [size]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C
import a_sprout

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
size = int(args[0]) if args else 600
C.reset()
root = a_sprout.build_sprout()
O = bpy.data.objects
ALL = ["Bud", "Flower", "EyeL", "EyeR", "EyeShineL", "EyeShineR", "Mouth", "EyeHappyL", "EyeHappyR",
       "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"]
POSES = {
    "default": (["Flower", "EyeL", "EyeR", "EyeShineL", "EyeShineR", "Mouth"], 0),
    "happy": (["Flower", "EyeHappyL", "EyeHappyR", "MouthOpen"], 80),
    "sleep": (["Bud", "EyeSleepL", "EyeSleepR", "Mouth", "Nightcap"], -8),
    "sad": (["Bud", "EyeSadL", "EyeSadR", "MouthSad"], -14),
}
outs = []
first = True
for pose, (show, arm) in POSES.items():
    for n in ALL:
        O[n].hide_render = n not in show
    O["ArmR"].rotation_euler = (0, math.radians(-arm), 0)
    O["ArmL"].rotation_euler = (0, math.radians(arm), 0)
    fn = f"sprout_{pose}.png"
    if first:
        C.preview(root, fn, az=18, el=12, fill=1.05, size=size)
        first = False
    else:
        s = bpy.context.scene
        s.render.filepath = os.path.join(C.PREVIEW_DIR, fn)
        bpy.ops.render.render(write_still=True)
    outs.append(os.path.join(C.PREVIEW_DIR, fn))
print("@@", outs)

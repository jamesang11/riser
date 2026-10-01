import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C, a_sickbed
C.reset()
root, sp = a_sickbed.build_sickbed(keep_sprout=True)
show = {"EyeSadL", "EyeSadR", "MouthSad", "Nightcap", "Bud"}
toggle = {"Bud", "Flower", "EyeL", "EyeR", "EyeShineL", "EyeShineR", "Mouth", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR",
          "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"}
for o in sp.children_recursive:
    if o.name in toggle:
        o.hide_render = o.name not in show
C.preview(root, "sickbed.png", az=24, el=48, fill=0.78, size=800)

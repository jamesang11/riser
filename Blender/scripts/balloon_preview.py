import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C, a_balloon, a_sprout
C.reset()
b = a_balloon.build_balloon()
sp = a_sprout.build_sprout()
for n in ("Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "Nightcap", "Mouth", "EyeL", "EyeR", "EyeShineL", "EyeShineR"):
    bpy.data.objects[n].hide_render = n not in ("Mouth", "EyeL", "EyeR", "EyeShineL", "EyeShineR")
bpy.data.objects["MouthOpen"].hide_render = True
C.update()
sp.location = bpy.data.objects["SeatPoint"].matrix_world.to_translation()
sp.scale = (0.8,) * 3
C.preview(b, "balloon_sprout.png", az=20, el=10, fill=0.85, size=700)

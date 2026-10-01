"""Assemble cloud-glyph clock lines and render previews/cloud_clock.png.
Blender -b -P clock_preview.py -- [width]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import common as C
import a_glyphs as G

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
width = int(args[0]) if args else 1600
C.reset()
cache = {}
widths = {}

def glyph(ch):
    root = G.build_glyph(ch)
    mesh = root.children[0]
    mn, mx = C.world_bbox([mesh])
    widths[ch] = (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    return root

def line(text, z):
    items = []
    for ch in text:
        if ch == " ":
            items.append(None)
            continue
        key = "colon" if ch == ":" else ch
        items.append(glyph(key))
    gap, space = 0.05, 0.28
    total = 0
    ws = []
    for it in items:
        w = space if it is None else C.world_bbox([it.children[0]])[1].x * 2
        ws.append(w)
    total = sum(ws) + gap * (len(ws) - 1)
    x = -total / 2
    for it, w in zip(items, ws):
        if it is not None:
            it.location = (x + w / 2, 0, z)
        x += w + gap
    C.update()

line("7:05 AM", 0.75)
line("12:48 PM", -0.75)
line_extra = None
s = bpy.context.scene
C.LOOK.update(view='Standard', look='None', exposure=0.0)
C.render_setup((width, int(width * 0.56)), samples=48)
C.world_gradient(top="6FBDEB", horizon="BFE3F7", light_col="9CC7EC", light_strength=0.75)
C.sun((38, 0, -35), 2.6, col="FFF3E2", angle=10)
cam = C.camera((0, 0, 0.5), (0.12, -1, 0.18), 12, name="Cam", ortho=5.2)
s.render.filepath = os.path.join(C.PREVIEW_DIR, "cloud_clock.png")
bpy.ops.render.render(write_still=True)
for k, v in sorted(widths.items()):
    print("@@ %s w=%.3f d=%.3f h=%.3f" % (k, *v))

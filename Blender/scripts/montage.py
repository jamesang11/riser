"""Blender -b -P montage.py -- out.png cols in1.png in2.png ...  (grid montage, same-size images)"""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
out, cols, ins = a[0], int(a[1]), a[2:]
ims = [bpy.data.images.load(p) for p in ins]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
canvas = np.ones((rows * h, cols * w, 4), dtype=np.float32)
for i, im in enumerate(ims):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    r, c = i // cols, i % cols
    y0 = (rows - 1 - r) * h
    canvas[y0:y0 + im.size[1], c * w:c * w + im.size[0]] = px[:h, :w]
img = bpy.data.images.new("montage", cols * w, rows * h, alpha=True)
img.pixels = canvas.ravel()
img.filepath_raw = out
img.file_format = 'PNG'
img.save()

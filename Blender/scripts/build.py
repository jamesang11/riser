"""Build + preview + export Riser assets.

Usage:
  Blender -b -P Blender/scripts/build.py -- sprout island ...   (or 'all')
  add --no-export to only render previews, --no-preview to skip renders.
"""
import sys, os, importlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import bpy

# name -> (module, builder function, usdz file)
ASSETS = {
    "island":       ("a_island", "build_island", "island.usdz"),
    "sprout":       ("a_sprout", "build_sprout", "sprout.usdz"),
    "tent":         ("a_buildings", "build_tent", "tent.usdz"),
    "cottage":      ("a_buildings", "build_cottage", "cottage.usdz"),
    "windmill":     ("a_buildings", "build_windmill", "windmill.usdz"),
    "campfire":     ("a_props", "build_campfire", "campfire.usdz"),
    "lamppost":     ("a_props", "build_lamppost", "lamppost.usdz"),
    "bench":        ("a_props", "build_bench", "bench.usdz"),
    "mailbox":      ("a_props", "build_mailbox", "mailbox.usdz"),
    "telescope":    ("a_props", "build_telescope", "telescope.usdz"),
    "lanterns":     ("a_props", "build_lanterns", "lanterns.usdz"),
    "tree_round":   ("a_nature", "build_tree_round", "tree_round.usdz"),
    "tree_blossom": ("a_nature", "build_tree_blossom", "tree_blossom.usdz"),
    "pine":         ("a_nature", "build_pine", "pine.usdz"),
    "garden":       ("a_nature", "build_garden", "garden.usdz"),
    "pond":         ("a_nature", "build_pond", "pond.usdz"),
    "flowers":      ("a_nature", "build_flowers", "flowers.usdz"),
    "cloud_a":      ("a_nature", "build_cloud_a", "cloud_a.usdz"),
    "cloud_b":      ("a_nature", "build_cloud_b", "cloud_b.usdz"),
    "butterfly":    ("a_critters", "build_butterfly", "butterfly.usdz"),
    "bird":         ("a_critters", "build_bird", "bird.usdz"),
    "balloon":      ("a_balloon", "build_balloon", "balloon.usdz"),
    "pumpkins":     ("a_harvest", "build_pumpkins", "pumpkins.usdz"),
    "scarecrow":    ("a_harvest", "build_scarecrow", "scarecrow.usdz"),
    "maple":        ("a_harvest", "build_maple", "maple.usdz"),
    "farm_island":  ("a_farm", "build_farm_island", "farm_island.usdz"),
    "food_apple":   ("a_food", "build_food_apple", "food_apple.usdz"),
    "food_soup":    ("a_food", "build_food_soup", "food_soup.usdz"),
    "food_cake":    ("a_food", "build_food_cake", "food_cake.usdz"),
    "sickbed":      ("a_sickbed", "build_sickbed", "sickbed.usdz"),
    "bedroom":      ("a_bedroom", "build_bedroom", "bedroom.usdz"),
    "tent_interior": ("a_tentint", "build_tent_interior", "tent_interior.usdz"),
}

for _g in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "colon", "A", "P", "M", "R", "I", "S", "E"]:
    ASSETS["glyph_" + _g] = ("a_glyphs", "build_glyph_" + _g, "glyph_" + _g + ".usdz")

for _h in ["straw", "flowercrown", "beanie", "frog", "wizard", "crown", "headphones", "bow", "explorer", "party", "pumpkin", "maple"]:
    ASSETS["hat_" + _h] = ("a_hats", "build_hat_" + _h, "hat_" + _h + ".usdz")

for _c in ["turnip", "carrot", "strawberry", "corn", "pumpkin", "sunflower"]:
    ASSETS["crop_" + _c] = ("a_crops", "build_crop_" + _c, "crop_" + _c + ".usdz")

for _f in ["armchair", "beanbag", "aquarium", "recordplayer", "plant", "floorlamp", "teddy", "desk", "toychest", "rocker",
           "poster_sun", "clock", "garland", "shelf"]:
    ASSETS["furn_" + _f] = ("a_furniture", "build_furn_" + _f, "furn_" + _f + ".usdz")
    PREVIEW_EXTRA = None

for _t in ["meadow", "woods", "beach", "mushroom", "harbor", "caves", "peaks", "moon"]:
    ASSETS["trip_" + _t] = ("a_trips", "build_trip_" + _t, "trip_" + _t + ".usdz")

for _d in ["well", "fountain", "gazebo", "beehive", "swing", "lighthouse", "bushes", "boulders", "signpost", "picnic",
           "archway", "hammock", "isle_meadow", "isle_beach", "bridge"]:
    ASSETS[_d] = ("a_decor2", "build_" + _d, _d + ".usdz")

HIDE_IN_PREVIEW = {"sprout": ["Bud", "EyeHappyL", "EyeHappyR", "EyeSleepL", "EyeSleepR", "EyeSadL", "EyeSadR", "MouthSad", "MouthOpen", "Nightcap"]}

PREVIEW_OPTS = {
    **{"trip_" + t: dict(ground=False, az=28, el=30, fill=0.62, target_z=-0.3) for t in ["meadow", "woods", "beach", "mushroom", "harbor", "caves", "peaks", "moon"]},
    **{"furn_" + w: dict(az=18, el=12, fill=1.0) for w in ["poster_sun", "clock", "garland", "shelf"]},
    "island": dict(ground=False, az=24, el=22, fill=0.68, target_z=-1.6),
    "isle_meadow": dict(ground=False, az=24, el=24, fill=0.66, target_z=-0.9),
    "isle_beach": dict(ground=False, az=24, el=24, fill=0.66, target_z=-0.9),
    "bridge": dict(ground=False, az=58, el=26, fill=0.92),
    "farm_island": dict(ground=False, az=20, el=30, fill=0.62, target_z=-0.6),
    "cloud_a": dict(ground=False), "cloud_b": dict(ground=False),
    "sprout": dict(az=22, el=14, fill=0.95),
    "food_apple": dict(az=25, el=22, fill=1.0), "food_soup": dict(az=25, el=35, fill=1.0), "food_cake": dict(az=25, el=28, fill=1.0),
    "butterfly": dict(az=30, el=35, fill=0.9), "bird": dict(az=35, el=15, fill=0.95),
}

def build(name, do_preview=True, do_export=True):
    mod, fn, fname = ASSETS[name]
    m = importlib.import_module(mod)
    C.reset()
    t = time.time()
    root = getattr(m, fn)()
    for o in [root] + list(root.children_recursive):
        C.apply_mods(o)
    tri = C.tri_count(root)
    C.save_blend(name + ".blend")
    if do_preview:
        for hn in HIDE_IN_PREVIEW.get(name, []):
            bpy.data.objects[hn].hide_render = True
        C.preview(root, name + ".png", **PREVIEW_OPTS.get(name, {}))
    if do_export:
        C.export_usdz(root, fname)
    print(f"@@ {name}: tris={tri} time={time.time() - t:.1f}s")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = [a for a in args if a.startswith("--")]
    names = [a for a in args if not a.startswith("--")]
    if not names or names == ["all"]:
        names = list(ASSETS)
    for n in names:
        build(n, "--no-preview" not in flags, "--no-export" not in flags)

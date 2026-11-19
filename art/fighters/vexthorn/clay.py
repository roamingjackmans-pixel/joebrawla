"""Clay check renders of the high-poly parts in the modeling pose (EEVEE).
blender -b --factory-startup --python clay.py -- <outprefix> [views...]   views: front side threeq back face top
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import fblib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
prefix = argv[0] if argv else "clay"
views = argv[1:] or ["front", "side", "threeq", "face"]
L.clear_scene()
cam = L.eevee_studio(res=900, samples=24)
mats = {}
for f in sorted(os.listdir(L.WORK)):
    if f.startswith("high_") and f.endswith(".npz"):
        n = f[5:-4]
        d = np.load(os.path.join(L.WORK, f))
        ob = L.bpy_mesh(n, d["V"], d["Q"])
        ob.data.shade_smooth()
        m = bpy.data.materials.new("clay_" + n)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        col = {"skull": (0.75, 0.70, 0.6), "antler_l": (0.6, 0.5, 0.4), "antler_r": (0.6, 0.5, 0.4),
               "moss": (0.25, 0.45, 0.15), "heart": (1.0, 0.55, 0.15), "lantern": (0.9, 0.6, 0.2)}.get(n, (0.42, 0.33, 0.26))
        b.inputs["Base Color"].default_value = col + (1,)
        b.inputs["Roughness"].default_value = 0.6
        ob.data.materials.append(m)
        print("loaded", n, len(d["V"]))
V = {
    "front": ((0, 0, 1.05), L.el(0, 4), 3.6, 50),
    "side": ((0, 0, 1.05), L.el(90, 4), 3.6, 50),
    "threeq": ((0, 0, 1.05), L.el(-35, 12), 3.7, 50),
    "back": ((0, 0, 1.05), L.el(180, 8), 3.6, 50),
    "face": ((0, -0.08, 1.78), L.el(-28, 8), 1.25, 60),
    "chest": ((0, -0.05, 1.38), L.el(-20, 6), 1.4, 60),
    "top": ((0, 0, 1.5), L.el(-20, 60), 3.0, 50),
    "hand": ((0.52, -0.16, 1.02), L.el(-60, 10), 0.75, 60),
    "foot": ((0.15, -0.05, 0.25), L.el(-60, 10), 1.1, 60),
}
for v in views:
    t, d, dist, lens = V[v]
    L.aim(cam, t, d, dist, lens)
    L.render(os.path.join(L.WORK, "%s_%s.jpg" % (prefix, v)))

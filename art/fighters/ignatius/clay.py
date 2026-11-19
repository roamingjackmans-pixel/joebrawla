"""Quick clay renders of the high-poly parts in the modeling pose (EEVEE) -> _work/clay_<view>.png
blender -b --factory-startup --python clay.py -- [tag] [views...]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler
import jb_lib as L
import f_sets, f_rig

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAG = argv[0] if argv else "clay"
VIEWS = argv[1:] or ["front", "side", "threeq", "back", "face"]
J = L.load_json(os.path.join(L.WORK, "joints.json"))
import f_parts as CP
CP.setJ(J)
L.clear_scene()
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = sc.render.resolution_y = 900
cols = [(0.62, 0.6, 0.57), (0.55, 0.42, 0.3), (0.45, 0.47, 0.5), (0.7, 0.55, 0.25), (0.35, 0.3, 0.27)]
ONLY = [s for s in os.environ.get("CLAY_ONLY", "").split(",") if s]
for i, p in enumerate(f_sets.all_parts()):
    if ONLY and p.name not in ONLY:
        continue
    f = os.path.join(L.WORK, "high_%s.npz" % p.name)
    if not os.path.exists(f):
        continue
    d = np.load(f)
    V = d["V"]
    if p.name == "hammer":
        M = f_rig.prop_to_armature(J, "r", True)
        V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3].astype(np.float32)
    ob = L.bpy_mesh(p.name, V, d["Q"])
    ob.data.shade_smooth()
    m = bpy.data.materials.new(p.name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    c = cols[i % len(cols)]
    b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1)
    b.inputs["Roughness"].default_value = 0.6
    ob.data.materials.append(m)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.26, 0.28, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for nm, en, rot, col in (("key", 4.0, (50, 0, -35), (1, 0.9, 0.8)), ("rim", 3.0, (-60, 0, 150), (0.7, 0.8, 1.0))):
    l = bpy.data.objects.new(nm, bpy.data.lights.new(nm, 'SUN')); sc.collection.objects.link(l)
    l.data.energy = en; l.data.color = col; l.rotation_euler = Euler([math.radians(a) for a in rot])
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
V = {"front": ((0, 0.0, 0.95), (0, -1, 0.08), 5.2, 50), "side": ((0, 0, 0.95), (1, 0, 0.05), 5.2, 50),
     "threeq": ((0, 0, 0.95), (0.6, -0.8, 0.25), 5.2, 50), "back": ((0, 0, 0.95), (-0.3, 1, 0.15), 5.2, 50),
     "face": ((0, -0.1, 1.60), (0.25, -1, 0.05), 1.6, 50), "hand": ((0.55, -0.2, 1.0), (0.5, -1, 0.3), 1.3, 50),
     "handr": ((-0.55, -0.2, 1.0), (-0.5, -1, 0.3), 1.3, 50), "feet": ((0, -0.1, 0.25), (0.4, -1, 0.3), 1.8, 50)}
for v in VIEWS:
    t, d, dist, lens = V[v]
    d = Vector(d).normalized()
    cam.location = Vector(t) + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.filepath = os.path.join(L.WORK, "%s_%s.png" % (TAG, v))
    bpy.ops.render.render(write_still=True)
    print("RENDER", sc.render.filepath)

"""Stage 2: decimate each high-poly part of an atlas set to its budget, chart + unwrap, and pack all parts of the
set into one shared atlas (texel density weighted per part).  -> _work/<id>/low_<set>.blend
blender -b --factory-startup --python s2_low.py -- <set>
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import fblib as L
L.load_joints()
import parts as PT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SET = argv[0] if argv else "bark"
L.clear_scene()
parts = PT.parts(SET)
PT_BY = {p.name: p for p in parts}
lows = []
for p in parts:
    d = np.load(os.path.join(L.WORK, "high_%s.npz" % p.name))
    ob = L.bpy_mesh(p.name + "_low", d["V"], d["Q"])
    nt = L.decimate(ob, p.tris)
    ob["texel"] = p.texel
    lows.append(ob)
    print("LOW %-10s tris=%d" % (p.name, nt))
for ob in lows:
    nf = len(ob.data.polygons)
    bins = getattr(PT_BY[ob.name[:-4]], "chart_bins", None)
    nch = L.chart_seams(ob, min_faces=90 if nf > 3000 else (45 if nf > 800 else 25), smooth_iters=12,
                        bins=bins() if callable(bins) else bins)
    print("CHARTS %-12s %d" % (ob.name, nch))
bpy.ops.object.select_all(action='DESELECT')
for ob in lows:
    ob.select_set(True)
bpy.context.view_layer.objects.active = lows[0]
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.0)
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
for ob in lows:
    me = ob.data
    uv = me.uv_layers.active.data
    a = np.zeros(len(uv) * 2, np.float32); uv.foreach_get("uv", a); a = a.reshape(-1, 3, 2)
    uva = 0.5 * np.abs((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1]) - (a[:, 2, 0] - a[:, 0, 0]) * (a[:, 1, 1] - a[:, 0, 1]))
    ar = np.array([p.area for p in me.polygons], np.float32)
    k = np.median(uva / np.maximum(ar, 1e-12))
    bad = uva > 8 * k * ar + 1e-9
    if bad.any():
        c = a[bad].mean(1, keepdims=True)
        a[bad] = c + (a[bad] - c) * 0.01
        uv.foreach_set("uv", a.ravel())
        print("SHRUNK", ob.name, int(bad.sum()))
for ob in lows:
    uv = ob.data.uv_layers.active.data
    a = np.zeros(len(uv) * 2, np.float32)
    uv.foreach_get("uv", a)
    a *= math.sqrt(ob["texel"])
    uv.foreach_set("uv", a)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, scale=True, margin_method='FRACTION', margin=0.003,
                        shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
tot = 0.0
for ob in lows:
    me = ob.data
    uv = me.uv_layers.active.data
    a = np.zeros(len(uv) * 2, np.float32); uv.foreach_get("uv", a); a = a.reshape(-1, 3, 2)
    ar = 0.5 * np.abs((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1]) - (a[:, 2, 0] - a[:, 0, 0]) * (a[:, 1, 1] - a[:, 0, 1]))
    tot += ar.sum()
    print("UV %-12s area=%.3f" % (ob.name, ar.sum()))
print("UV utilisation %.2f" % tot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "low_%s.blend" % SET))

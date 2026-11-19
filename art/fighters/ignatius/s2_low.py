"""Stage 2: decimate each high-poly part to its budget, triangulate, smart-UV and pack all body parts into
one shared 2048 atlas (texel density weighted per part).  -> _work/low.blend
blender -b --factory-startup --python s2_lowpoly.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
import jb_lib as L
import f_parts as CP
import f_sets

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SET = argv[0] if argv else "body"

CP.setJ(L.load_json(os.path.join(L.WORK, "joints.json")))
L.clear_scene()
parts = f_sets.parts(SET)


def decimate(ob, target_tris):
    me = ob.data
    ntri = sum(len(p.vertices) - 2 for p in me.polygons)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = min(1.0, target_tris / ntri)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-4, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bad = [f for f in bm.faces if f.calc_area() < 2e-8]
    bmesh.ops.delete(bm, geom=bad, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    ob.select_set(False)
    return len(ob.data.polygons)


def drop_small(ob, min_verts=60):
    """remove tiny disconnected islands (sub-voxel blobs)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    kill = []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp = [v]
        seen.add(v.index)
        i = 0
        while i < len(comp):
            for e in comp[i].link_edges:
                o = e.other_vert(comp[i])
                if o.index not in seen:
                    seen.add(o.index)
                    comp.append(o)
            i += 1
        if len(comp) < min_verts:
            kill += comp
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()


def remesh(ob, h):
    mod = ob.modifiers.new("rm", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = h
    mod.adaptivity = 0.0
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.select_set(False)


lows = []
for p in parts:
    d = np.load(os.path.join(L.WORK, "high_%s.npz" % p.name))
    ob = L.bpy_mesh(p.name + "_low", d["V"], d["Q"])
    drop_small(ob)
    nt = decimate(ob, p.tris)
    if nt > p.tris * 1.25:
        print("LOW %-8s decimation stalled at %d tris: voxel remesh + retry" % (p.name, nt))
        bpy.data.objects.remove(ob, do_unlink=True)
        ob = L.bpy_mesh(p.name + "_low", d["V"], d["Q"])
        drop_small(ob)
        remesh(ob, p.h * 1.1)
        nt = decimate(ob, p.tris)
    ob["texel"] = p.texel
    lows.append(ob)
    print("LOW %-8s tris=%d" % (p.name, nt))

# ---- UVs: smart project each, equalise texel density, weight per part, pack all together
for ob in lows:
    nch = L.chart_seams(ob, min_faces=90 if len(ob.data.polygons) > 3000 else 45, smooth_iters=12)
    print("CHARTS %-10s %d" % (ob.name, nch))
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
# safety: any face whose uv/3d area ratio is wildly off (degenerate single-face islands) gets shrunk
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
bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, scale=True, margin_method='FRACTION', margin=0.004,
                        shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')

# utilisation report
tot = 0.0
for ob in lows:
    me = ob.data
    uv = me.uv_layers.active.data
    a = np.zeros(len(uv) * 2, np.float32); uv.foreach_get("uv", a); a = a.reshape(-1, 3, 2)
    ar = 0.5 * np.abs((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1]) - (a[:, 2, 0] - a[:, 0, 0]) * (a[:, 1, 1] - a[:, 0, 1]))
    tot += ar.sum()
    print("UV %-10s area=%.3f" % (ob.name, ar.sum()))
print("UV utilisation %.2f" % tot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "low_%s.blend" % SET))

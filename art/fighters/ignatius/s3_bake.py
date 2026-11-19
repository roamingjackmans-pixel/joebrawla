"""Stage 3: bake high -> low for every body part into one atlas.
  1. per-vertex ambient occlusion on all high-poly parts together (Cycles bake to colour attribute)
  2. per part, selected-to-active bakes: object-space normal, high surface position, (AO, curvature)
  3. composite into atlas arrays -> _work/atlas_<name>.npz
blender -b --factory-startup --python s3_bake.py -- [atlas_name=body] [lowblend] [part names...]
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import jb_lib as L
import f_sets
import f_parts as CP
CP.setJ(L.load_json(os.path.join(L.WORK, "joints.json")))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ATLAS = argv[0] if argv else "body"
LOWBLEND = os.path.join(L.WORK, "low_%s.blend" % ATLAS)
SIZE = f_sets.size(ATLAS)
EXTRUDE = float(os.environ.get("CT_EXTRUDE", "0.02"))
MAXRAY = float(os.environ.get("CT_MAXRAY", "0.05"))

bpy.ops.wm.open_mainfile(filepath=LOWBLEND)
sc = L.setup_cycles(samples=1)
lows = sorted([o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith("_low")], key=lambda o: o.name)
names = [o.name[:-4] for o in lows]
print("PARTS", names)

# ---- highs
highs = {}
for n in names:
    d = np.load(os.path.join(L.WORK, "high_%s.npz" % n))
    ob = L.bpy_mesh(n + "_high", d["V"], d["Q"])
    ob.data.shade_smooth()
    L.set_attr(ob, "curv", d["C"])
    a = ob.data.color_attributes.new("ao", 'FLOAT_COLOR', 'POINT')
    ob.data.color_attributes.active_color = a
    highs[n] = ob

# occluders for AO: the high parts of the other body atlases (not the separately framed props)
occl = []
if ATLAS in ("body", "gear"):
    for p in f_sets.all_parts():
        if p.aset in ("body", "gear") and p.name not in names:
            f = os.path.join(L.WORK, "high_%s.npz" % p.name)
            if os.path.exists(f):
                d = np.load(f)
                oc = L.bpy_mesh(p.name + "_occl", d["V"], d["Q"])
                occl.append(oc)
print("OCCLUDERS", [o.name for o in occl])

# ---- world for AO
w = bpy.data.worlds.new("bakeworld")
sc.world = w
w.light_settings.distance = 0.22
for o in lows:
    o.hide_render = True
sc.cycles.samples = 96
t0 = time.time()
for n, ob in highs.items():
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
    ao = L.get_attr(ob, "ao")[:, 0]
    print("AO %-8s mean=%.3f  (%.1fs)" % (n, ao.mean(), time.time() - t0))
for o in lows:
    o.hide_render = False
for o in occl:
    bpy.data.objects.remove(o, do_unlink=True)

# ---- emission material for the highs (link switched per pass)
hm = bpy.data.materials.new("HighEmit")
hm.use_nodes = True
nt = hm.node_tree
for nd in list(nt.nodes):
    nt.nodes.remove(nd)
out = nt.nodes.new("ShaderNodeOutputMaterial")
em = nt.nodes.new("ShaderNodeEmission")
geo = nt.nodes.new("ShaderNodeNewGeometry")
at_ao = nt.nodes.new("ShaderNodeAttribute"); at_ao.attribute_name = "ao"
at_cv = nt.nodes.new("ShaderNodeAttribute"); at_cv.attribute_name = "curv"
comb = nt.nodes.new("ShaderNodeCombineColor")
nt.links.new(at_ao.outputs["Fac"], comb.inputs[0])
nt.links.new(at_cv.outputs["Fac"], comb.inputs[1])
nt.links.new(em.outputs[0], out.inputs[0])
for ob in highs.values():
    ob.data.materials.clear()
    ob.data.materials.append(hm)

img = L.new_image("bake_tmp", SIZE, float_buffer=True)
for ob in lows:
    m = bpy.data.materials.new(ob.name + "_bake")
    m.use_nodes = True
    tn = m.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    m.node_tree.nodes.active = tn
    ob.data.materials.clear()
    ob.data.materials.append(m)

pos = np.zeros((SIZE, SIZE, 3), np.float32)
nrm = np.zeros((SIZE, SIZE, 3), np.float32)
aoc = np.zeros((SIZE, SIZE, 2), np.float32)
pid = np.full((SIZE, SIZE), -1, np.int8)
zero = np.zeros(SIZE * SIZE * 4, np.float32)


def bake(low, high, kind):
    img.pixels.foreach_set(zero)
    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    kw = dict(use_selected_to_active=True, cage_extrusion=EXTRUDE, max_ray_distance=MAXRAY, margin=0,
              use_clear=False, target='IMAGE_TEXTURES')
    if kind == "nrm":
        bpy.ops.object.bake(type='NORMAL', normal_space='OBJECT', **kw)
    else:
        if kind == "pos":
            nt.links.new(geo.outputs["Position"], em.inputs["Color"])
        else:
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        bpy.ops.object.bake(type='EMIT', **kw)
    return L.img_np(img)


for i, (low, n) in enumerate(zip(lows, names)):
    t1 = time.time()
    a = bake(low, highs[n], "pos")
    cov = a[..., 3] > 0.5
    pid[cov] = i
    pos[cov] = a[..., :3][cov]
    a = bake(low, highs[n], "nrm")
    nrm[cov] = a[..., :3][cov]
    a = bake(low, highs[n], "aoc")
    aoc[cov] = a[..., :2][cov]
    print("BAKED %-8s texels=%d  %.1fs" % (n, cov.sum(), time.time() - t1))

np.savez_compressed(os.path.join(L.WORK, "atlas_%s.npz" % ATLAS), pos=pos, nrm=nrm, aoc=aoc, pid=pid,
                    names=np.array(names))
print("SAVED atlas", ATLAS, "coverage %.2f" % (pid >= 0).mean())

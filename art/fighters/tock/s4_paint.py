"""Stage 4: paint an atlas set in texture space and convert normals to tangent space.
  _work/<id>/atlas_<set>.npz -> _work/<id>/tex/<set>_albedo.png, _orm.png, _emission.png, _normal.png
blender -b --factory-startup --python s4_paint.py -- <set>
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import fblib as L
L.load_joints()
import parts as PT
import paint as PN

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SET = argv[0] if argv else "bark"
TEX = L.TEX
A = np.load(os.path.join(L.WORK, "atlas_%s.npz" % SET))
pos, nrm, aoc, pid, names = A["pos"], A["nrm"], A["aoc"], A["pid"], list(A["names"])
S = pid.shape[0]
parts = {p.name: p for p in PT.parts(SET)}

alb = np.zeros((S, S, 3), np.float32)
orm = np.zeros((S, S, 3), np.float32)
emi = np.zeros((S, S, 3), np.float32)
nob = np.zeros((S, S, 3), np.float32)
for i, n in enumerate(names):
    t0 = time.time()
    idx = np.nonzero(pid == i)
    P = pos[idx]
    N = nrm[idx] * 2.0 - 1.0
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
    ao = aoc[idx][:, 0]
    ao = np.clip((ao - 0.05) / 0.85, 0, 1)
    cv = aoc[idx][:, 1]
    cv = cv / max(1e-6, np.percentile(np.abs(cv), 96))
    col, rough, metal, em = PN.PAINTERS[n](P, N, ao, cv, parts[n])
    alb[idx] = np.clip(col, 0, 1)
    orm[idx] = np.stack([0.35 + 0.65 * ao ** 0.7, np.clip(rough, 0.04, 1),
                         metal if metal is not None else np.zeros(len(P))], 1)
    if em is not None:
        emi[idx] = em
    nob[idx] = PN.detail_normals(parts[n], P, N)
    print("PAINT %-10s texels=%d %.1fs" % (n, len(P), time.time() - t0))

mask = pid >= 0
DI = L.dilate_index(mask, 24)
alb = L.dilate_fast(alb, DI, (0.5, 0.5, 0.5))
orm = L.dilate_fast(orm, DI, (1.0, 0.9, 0.0))
emi = L.dilate_fast(emi, DI, (0, 0, 0))
nob = L.dilate_fast(nob, DI, (0, 0, 1))
L.save_np_png(alb, os.path.join(TEX, SET + "_albedo.png"))
L.save_np_png(orm, os.path.join(TEX, SET + "_orm.png"), 'Non-Color')
L.save_np_png(emi, os.path.join(TEX, SET + "_emission.png"))
print("EMISSION max %.3f" % emi.max())

# ---- object-space -> tangent-space normal via Cycles bake on the low-poly
bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "low_%s.blend" % SET))
L.setup_cycles(samples=1)
nimg = L.np_img("nrm_obj", np.concatenate([nob * 0.5 + 0.5, np.ones((S, S, 1), np.float32)], 2), 'Non-Color', True)
target = L.new_image("nrm_tan", S, float_buffer=True)
lows = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith("_low")]
for ob in lows:
    m = bpy.data.materials.new(ob.name + "_nconv")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    it = nt.nodes.new("ShaderNodeTexImage"); it.image = nimg; it.interpolation = 'Closest'
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.space = 'OBJECT'
    nt.links.new(it.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = target
    nt.nodes.active = tn
    ob.data.materials.clear()
    ob.data.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
for ob in lows:
    ob.select_set(True)
bpy.context.view_layer.objects.active = lows[0]
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=False, margin=0, use_clear=False,
                    target='IMAGE_TEXTURES')
tan = L.img_np(target)[..., :3]
tan = L.dilate_fast(tan, DI, (0.5, 0.5, 1.0))
L.save_np_png(tan, os.path.join(TEX, SET + "_normal.png"), 'Non-Color')
print("SAVED textures to", TEX)

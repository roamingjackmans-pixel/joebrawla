"""Stage 6: assemble the rigged fighter on its rest skeleton (rig.blend).
  * per-part skin weights in the modeling pose (parts.py weights(), smoothed, max 4 influences)
  * un-poses every vertex with the inverse of its blended skinning matrix -> mesh rests on the bind pose
  * bark parts -> Vexthorn_Body (tint2_bark), bone parts -> Vexthorn_Bone (vex_bone), leaf cards -> Vexthorn_Leaves
    (tint1_leaves, alpha mask); tiny lanterns instanced under the antlers, rigid on Head
  -> _work/<id>/final.blend
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Matrix
import fblib as L
L.load_joints()
import parts as PT
import paint as PN

F32 = np.float32
TEX = L.TEX
BARK_FACTOR = L.srgb_to_lin(L.hexc(PN.BARK_FACTOR_SRGB))
LEAF_FACTOR = L.srgb_to_lin(L.hexc("#d2561c"))

bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "rig.blend"))
arm = bpy.data.objects["Armature"]
for o in list(bpy.data.objects):
    if o.name == "REF_UBC":
        bpy.data.objects.remove(o, do_unlink=True)
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
BONES = [b.name for b in arm.data.bones]
print("RIG bones", len(BONES))

parts = {p.name: p for p in PT.all_parts()}
lows = L.append_objects(os.path.join(L.WORK, "low_bark.blend")) + L.append_objects(os.path.join(L.WORK, "low_bone.blend"))
cache = {}
for ob in lows:
    name = ob.name[:-4]
    p = parts[name]
    if name == "lantern":
        continue
    V = L.mesh_verts(ob)
    M = L.to_matrix(p.weights(V), BONES, len(V))
    M = L.limit_norm(M, 4)
    if M.max(1).min() < 0.999 or name in ("torso",):
        M = L.smooth_weights(M, ob, iters=2 if name.startswith("hand") else 4)
        M = L.limit_norm(M, 4)
    cache[name] = (V, M)
    Vr = L.unpose(V, M, BONES)
    ob.data.vertices.foreach_set("co", Vr.ravel())
    ob.data.update()
    L.assign_groups(ob, M, BONES)
    print("RIG %-10s verts=%d tris=%d" % (name, len(V), L.tri_count(ob)))

# ---- round-trip check: pose the armature into the modeling pose -> torso must match the sculpt
import cfg
torso = [o for o in lows if o.name == "torso_low"][0]
mchk = torso.modifiers.new("chk", 'ARMATURE')
mchk.object = arm
for pb in arm.pose.bones:
    e = cfg.modeling_pose().get(pb.name)
    pb.rotation_quaternion = (1, 0, 0, 0) if e is None else L.rest_axes_to_local(pb, L.rq(*e))
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = torso.evaluated_get(dg)
me = ev.to_mesh()
Ve = np.zeros(len(me.vertices) * 3, F32); me.vertices.foreach_get("co", Ve)
ev.to_mesh_clear()
print("RIG modeling-pose round trip max error %.5f m" % np.abs(Ve.reshape(-1, 3) - cache["torso"][0]).max())
torso.modifiers.remove(mchk)
for pb in arm.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()

# ---- tiny lanterns: instances of the lantern part hung under the antlers (rigid on Head; Head is not posed in the
#      modeling pose, so modeling space == rest space here)
lan = [o for o in lows if o.name == "lantern_low"][0]
hangs = L.load_json(os.path.join(L.WORK, "lantern_hangs.json"))
V0 = L.mesh_verts(lan) - PT.Lantern.off
inst = []
rng = np.random.default_rng(5)
for i, hp in enumerate(hangs):
    o = lan.copy()
    o.data = lan.data.copy()
    bpy.context.scene.collection.objects.link(o)
    yaw = rng.uniform(0, math.pi / 2)
    c, s_ = math.cos(yaw), math.sin(yaw)
    R = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]], F32)
    sc = 1.0 if i % 2 == 0 else 0.85
    Vi = (V0 * sc) @ R.T + np.array(hp, F32)
    o.data.vertices.foreach_set("co", Vi.ravel())
    o.data.update()
    L.assign_groups(o, L.to_matrix({"Head": np.ones(len(Vi), F32)}, BONES, len(Vi)), BONES)
    inst.append(o)
lows = [o for o in lows if o is not lan]
bpy.data.objects.remove(lan, do_unlink=True)
print("RIG lanterns", len(inst))

# ---- leaves
lv = L.append_objects(os.path.join(L.WORK, "leaves.blend"), "_fol")[0]
V = L.mesh_verts(lv)
anc = L.get_attr(lv, "anchor")[:, :3]
ga = lv.data.attributes["lgroup"]
grp = np.zeros(len(V), np.int32)
ga.data.foreach_get("value", grp)
W = np.zeros((len(V), len(BONES)), F32)
for gi, gname in enumerate(["shoulder_l", "shoulder_r", "head", "torso", "moss"]):
    idx = np.nonzero(grp == gi)[0]
    if len(idx) == 0:
        continue
    if gname == "head":
        W[idx, BONES.index("Head")] = 1.0
        continue
    src = parts[gname] if gname in parts else parts["moss"]
    W[idx] = L.to_matrix(src.weights(anc[idx]), BONES, len(idx))
W = L.limit_norm(W, 4)
Vr = L.unpose(V, W, BONES)
lv.data.vertices.foreach_set("co", Vr.ravel())
lv.data.update()
L.assign_groups(lv, W, BONES)
for nm in ("anchor", "lgroup"):
    if nm in lv.data.attributes:
        lv.data.attributes.remove(lv.data.attributes[nm])

# ---- materials
bark_mat = L.pbr_material("tint2_bark", os.path.join(TEX, "bark_albedo.png"), os.path.join(TEX, "bark_normal.png"),
                          os.path.join(TEX, "bark_orm.png"), os.path.join(TEX, "bark_emission.png"), 3.0,
                          factor=BARK_FACTOR)
bone_mat = L.pbr_material("vex_bone", os.path.join(TEX, "bone_albedo.png"), os.path.join(TEX, "bone_normal.png"),
                          os.path.join(TEX, "bone_orm.png"), os.path.join(TEX, "bone_emission.png"), 5.0)
leaf_mat = L.pbr_material("tint1_leaves", os.path.join(TEX, "leaves_albedo.png"), os.path.join(TEX, "leaves_normal.png"),
                          os.path.join(TEX, "leaves_orm.png"), alpha_clip=0.5, factor=LEAF_FACTOR)


def join(obs, name, mat):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
        o.data.materials.clear()
        o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = obs[0]
    ob.name = name
    ob.data.name = name
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    m = ob.modifiers.new("Armature", 'ARMATURE')
    m.object = arm
    return ob


bark = [o for o in lows if parts[o.name[:-4]].atlas == "bark"]
bone = [o for o in lows if parts[o.name[:-4]].atlas == "bone"] + inst
body = join(bark, "Vexthorn_Body", bark_mat)
bon = join(bone, "Vexthorn_Bone", bone_mat)
lea = join([lv], "Vexthorn_Leaves", leaf_mat)
tot = 0
for o in (body, bon, lea):
    t = L.tri_count(o)
    tot += t
    print("FINAL %-16s tris=%d groups=%d" % (o.name, t, len(o.vertex_groups)))
print("TRIS total %d" % tot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "final.blend"))

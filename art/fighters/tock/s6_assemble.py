"""Stage 6: assemble Archmagister Tock on his rest skeleton (rig.blend).
  * per-part skin weights in the modeling pose, smoothed, max 4 influences; un-posed onto the bind pose
  * extra bone `staff_pendulum` (child of hand_r, head at the pendulum pivot): the pendulum is 100 % on it
  * meshes: Tock_Body, Tock_GearCrown (Head), Tock_ClockHour + Tock_ClockMinute (spine_03, separate so the game can
    spin them about the clock axis), Tock_Robe (tint1_robe), Tock_Trim (tint2_trim), Tock_Staff (staff 100 % hand_r
    + pendulum on staff_pendulum)
  -> _work/<id>/final.blend, _work/<id>/clock_info.json
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Matrix, Vector
import fblib as L
L.load_joints()
import parts as PT
import paint as PN
import cfg

F32 = np.float32
TEX = L.TEX
ROBE_FACTOR = L.srgb_to_lin(L.hexc(PN.ROBE_FACTOR_SRGB))
TRIM_FACTOR = L.srgb_to_lin(L.hexc(PN.TRIM_FACTOR_SRGB))

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
lows = []
for S in ("body", "robe", "trim", "staff"):
    lows += L.append_objects(os.path.join(L.WORK, "low_%s.blend" % S))
cache = {}
for ob in lows:
    name = ob.name[:-4]
    p = parts[name]
    V = L.mesh_verts(ob)
    M = L.to_matrix(p.weights(V), BONES, len(V))
    M = L.limit_norm(M, 4)
    if M.max(1).min() < 0.999:
        M = L.smooth_weights(M, ob, iters=2 if name.startswith("hand") else 4)
        M = L.limit_norm(M, 4)
    cache[name] = (V, M)
    Vr = L.unpose(V, M, BONES)
    ob.data.vertices.foreach_set("co", Vr.ravel())
    ob.data.update()
    L.assign_groups(ob, M, BONES)
    print("RIG %-10s verts=%d tris=%d" % (name, len(V), L.tri_count(ob)))

# ---- round trip check on the robe
robe = [o for o in lows if o.name == "robe_low"][0]
mchk = robe.modifiers.new("chk", 'ARMATURE')
mchk.object = arm
for pb in arm.pose.bones:
    e = cfg.modeling_pose().get(pb.name)
    pb.rotation_quaternion = (1, 0, 0, 0) if e is None else L.rest_axes_to_local(pb, L.rq(*e))
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = robe.evaluated_get(dg)
me = ev.to_mesh()
Ve = np.zeros(len(me.vertices) * 3, F32); me.vertices.foreach_get("co", Ve)
ev.to_mesh_clear()
print("RIG modeling-pose round trip max error %.5f m" % np.abs(Ve.reshape(-1, 3) - cache["robe"][0]).max())
robe.modifiers.remove(mchk)
for pb in arm.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()

# ---- extra bone for the pendulum (rest = modeling pose un-posed with hand_r's skin matrix)
pv, ad = PT.pendulum_pivot()
g, ax, sd, top, bot = PT.staff_pts()
Mh = np.zeros((2, len(BONES)), F32)
Mh[:, BONES.index("hand_r")] = 1
ends = L.unpose(np.array([pv, pv - ax * 0.29], F32), Mh, BONES)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones.new("staff_pendulum")
eb.head = Vector(ends[0].tolist())
eb.tail = Vector(ends[1].tolist())
eb.parent = arm.data.edit_bones["hand_r"]
eb.use_connect = False
eb.use_deform = True
bpy.ops.object.mode_set(mode='OBJECT')
pen = [o for o in lows if o.name == "pendulum_low"][0]
pen.vertex_groups.clear()
vg = pen.vertex_groups.new(name="staff_pendulum")
vg.add(list(range(len(pen.data.vertices))), 1.0, 'REPLACE')
print("RIG extra bone staff_pendulum head", tuple(round(x, 4) for x in ends[0]))

# ---- clock info for the game (rest pose, Blender Z-up and glTF Y-up)
Ms = np.zeros((2, len(BONES)), F32)
Ms[:, BONES.index("spine_03")] = 1
cc = L.unpose(np.array([PT.CLOCK_C, PT.CLOCK_C + PT.CLOCK_N * 0.1], F32), Ms, BONES)
cn = (cc[1] - cc[0]) / 0.1
b3 = arm.data.bones["spine_03"]
loc = np.array(b3.matrix_local.inverted() @ Vector(cc[0].tolist()), F32)
axl = np.array(b3.matrix_local.inverted().to_3x3() @ Vector(cn.tolist()), F32)
info = {"centre_rest_blender": cc[0].tolist(), "axis_rest_blender": cn.tolist(),
        "centre_rest_gltf": [float(cc[0][0]), float(cc[0][2]), float(-cc[0][1])],
        "axis_rest_gltf": [float(cn[0]), float(cn[2]), float(-cn[1])],
        "centre_in_spine_03": loc.tolist(), "axis_in_spine_03": axl.tolist(),
        "rest_time": "10:10 (hour hand 305 deg, minute hand 60 deg clockwise from 12)"}
L.save_json(os.path.join(L.WORK, "clock_info.json"), info)
print("RIG clock", info["centre_rest_gltf"], info["axis_rest_gltf"])

# ---- materials
body_mat = L.pbr_material("tock_body", os.path.join(TEX, "body_albedo.png"), os.path.join(TEX, "body_normal.png"),
                          os.path.join(TEX, "body_orm.png"), os.path.join(TEX, "body_emission.png"), 4.0)
robe_mat = L.pbr_material("tint1_robe", os.path.join(TEX, "robe_albedo.png"), os.path.join(TEX, "robe_normal.png"),
                          os.path.join(TEX, "robe_orm.png"), factor=ROBE_FACTOR)
trim_mat = L.pbr_material("tint2_trim", os.path.join(TEX, "trim_albedo.png"), os.path.join(TEX, "trim_normal.png"),
                          os.path.join(TEX, "trim_orm.png"), factor=TRIM_FACTOR)
staff_mat = L.pbr_material("tock_staff", os.path.join(TEX, "staff_albedo.png"), os.path.join(TEX, "staff_normal.png"),
                           os.path.join(TEX, "staff_orm.png"), os.path.join(TEX, "staff_emission.png"), 4.0)


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


by = {o.name[:-4]: o for o in lows}
special = {"crown", "clock_hour", "clock_min"}
body_parts = [o for n, o in by.items() if parts[n].atlas == "body" and n not in special]
out = [join(body_parts, "Tock_Body", body_mat),
       join([by["crown"]], "Tock_GearCrown", body_mat),
       join([by["clock_hour"]], "Tock_ClockHour", body_mat),
       join([by["clock_min"]], "Tock_ClockMinute", body_mat),
       join([by["robe"], by["hat"]], "Tock_Robe", robe_mat),
       join([by["trim"], by["tassel"]], "Tock_Trim", trim_mat),
       join([by["staff"], by["pendulum"]], "Tock_Staff", staff_mat)]
tot = 0
for o in out:
    t = L.tri_count(o)
    tot += t
    print("FINAL %-16s tris=%d groups=%d" % (o.name, t, len(o.vertex_groups)))
print("TRIS total %d" % tot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "final.blend"))

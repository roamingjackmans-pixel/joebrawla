"""Stage 0: rig.  Imports the Quaternius UBC Superhero_Male skeleton (its rest = the bind pose), rescales bone
lengths to the fighter's proportions (cfg.OWN / cfg.KIDS, orientations untouched), puts the feet back on the
ground, saves _work/<id>/rig.blend (armature only + the UBC body as a hidden scale reference), then applies the
modeling pose and dumps _work/<id>/joints.json (pose/rest matrices, heads/tails).
blender -b --factory-startup --python s0_rig.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
import fblib as L
import cfg

L.clear_scene()
objs = L.import_gltf(L.UBC_MALE)
arm = [o for o in objs if o.type == 'ARMATURE'][0]
for o in objs:
    if o.type == 'MESH':
        if o.name.startswith("SuperHero"):
            o.name = "REF_UBC"
            o.hide_render = True
            o.modifiers.clear()
            o.parent = None
        else:
            bpy.data.objects.remove(o, do_unlink=True)
arm.name = "Armature"
arm.data.name = "Armature"
if arm.animation_data:
    arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

old_local = {b.name: L.rest_local(b).to_quaternion() for b in arm.data.bones}
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
old = {b.name: (b.head.copy(), b.tail.copy(), b.roll) for b in eb}
newh, newt = {}, {}


def kids_scale(n):
    if n in cfg.KIDS:
        return Vector(cfg.KIDS[n])
    s = cfg.OWN.get(n, 1.0)
    return Vector((s, s, s))


order = []
def walk(b):
    order.append(b.name)
    for c in b.children:
        walk(c)
for b in eb:
    if b.parent is None:
        walk(b)
for n in order:
    b = eb[n]
    oh, ot, _ = old[n]
    if b.parent is None:
        h = oh.copy()
    else:
        p = b.parent.name
        ks = kids_scale(p)
        h = newh[p] + (oh - old[p][0]) * ks
    s = cfg.OWN.get(n, 1.0)
    newh[n] = h
    newt[n] = h + (ot - oh) * s
# feet back on the ground: the ball joints keep their UBC height
dz = old["ball_l"][0].z - newh["ball_l"].z
for n in order:
    if eb[n].parent is not None:
        newh[n] = newh[n] + Vector((0, 0, dz))
        newt[n] = newt[n] + Vector((0, 0, dz))
for n in order:
    b = eb[n]
    b.use_connect = False
for n in order:
    b = eb[n]
    roll = old[n][2]
    b.head = newh[n]
    b.tail = newt[n]
    b.roll = roll
bpy.ops.object.mode_set(mode='OBJECT')
err = max((L.rest_local(b).to_quaternion().rotation_difference(old_local[b.name]).angle) for b in arm.data.bones)
print("RIG max local-rest rotation change %.6f rad (must be ~0)" % err)
for n in ("pelvis", "spine_03", "neck_01", "Head", "upperarm_l", "hand_l", "thigh_l", "calf_l", "foot_l", "ball_l"):
    b = arm.data.bones[n]
    print("RIG %-12s head=(%.3f %.3f %.3f) tail=(%.3f %.3f %.3f)" % ((n,) + tuple(b.head_local) + tuple(b.tail_local)))
print("RIG pelvis rest height %.4f  -> clip pelvis translation scale k = %.4f" % (
    arm.data.bones["pelvis"].head_local.z, arm.data.bones["pelvis"].head_local.z / L.UAL_PELVIS_Z))
L.save_json(os.path.join(L.WORK, "rig_info.json"), {"pelvis_z": arm.data.bones["pelvis"].head_local.z,
                                                    "k": arm.data.bones["pelvis"].head_local.z / L.UAL_PELVIS_Z})
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "rig.blend"))

# ---- modeling pose -> joints.json
def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
        e = pose.get(pb.name)
        pb.rotation_quaternion = (1, 0, 0, 0) if e is None else L.rest_axes_to_local(pb, L.rq(*e))
    bpy.context.view_layer.update()


apply_pose(arm, cfg.modeling_pose())
J = {}
for pb in arm.pose.bones:
    J[pb.name] = {"head": list(pb.head), "tail": list(pb.tail), "pose": [list(r) for r in pb.matrix],
                  "rest": [list(r) for r in pb.bone.matrix_local], "parent": pb.parent.name if pb.parent else None}
L.save_json(os.path.join(L.WORK, "joints.json"), J)
for b in ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "Head", "clavicle_l", "upperarm_l", "lowerarm_l",
          "hand_l", "index_01_l", "middle_01_l", "middle_04_leaf_l", "pinky_01_l", "thumb_01_l", "thumb_04_leaf_l",
          "thigh_l", "calf_l", "foot_l", "ball_l", "ball_leaf_l"):
    print("J %-16s head=(%.3f %.3f %.3f) tail=(%.3f %.3f %.3f)" % ((b,) + tuple(J[b]["head"]) + tuple(J[b]["tail"])))

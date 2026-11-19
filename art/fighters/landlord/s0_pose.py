"""Stage 0: build the edited UAL1 skeleton, measure the standard UAL fist (grip line for held props), apply the
modeling pose and dump joint data -> _work/joints.json.
blender -b --factory-startup --python s0_pose.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import jb_lib as L
import f_rig as R

arm = R.make_armature()
clips = R.load_clips([L.UAL1])
act = clips[R.REF_CLIP[0]]
arm.animation_data_create()
arm.animation_data.action = act
if act.slots:
    arm.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(R.REF_CLIP[1])
bpy.context.view_layer.update()
grips = {}
for s in ("l", "r"):
    c, ax, r = R.fist_grip(arm, s)
    grips[s] = {"centre": c, "axis": ax, "loop_r": r}
    print("GRIP hand_%s centre (%.4f %.4f %.4f) axis (%.3f %.3f %.3f) finger-loop r %.4f" % ((s,) + tuple(c) + tuple(ax) + (r,)))
arm.animation_data.action = None
R.apply_pose(arm, R.modeling_pose())
J = R.joints_dict(arm)
J["_grip"] = grips
L.save_json(os.path.join(L.WORK, "joints.json"), J)
for b in ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "Head", "clavicle_l", "upperarm_l", "lowerarm_l",
          "hand_l", "middle_01_l", "middle_04_leaf_l", "thumb_04_leaf_l", "thigh_l", "calf_l", "foot_l", "ball_l", "ball_leaf_l"):
    print("J %-16s head=(%.3f %.3f %.3f) tail=(%.3f %.3f %.3f)" % ((b,) + tuple(J[b]["head"]) + tuple(J[b]["tail"])))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "pose_check.blend"))

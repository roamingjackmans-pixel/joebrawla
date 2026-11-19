"""Foreman Ignatius: skeleton, proportions and modeling pose.

Skeleton = Quaternius UAL1 (65 joints, exact names, exact joint ORIENTATIONS and leg chain) with a few
translation-only edits for a big body (wider shoulders, bigger hands, lower bull-neck head, wider hips).
Only joints whose translation the game strips from clips are moved (everything except root/pelvis), and the leg
chain is untouched, so UAL pelvis tracks keep the boots on the floor.  The finished armature object is scaled
uniformly (glTF node scale on `Armature`) to the 2.15 m height; clip translations are then scaled with it.

Rotations below are XYZ euler degrees in ARMATURE rest axes (character faces -Y, its left side is +X).
"""
import numpy as np
import jb_lib as L

FINGERS = ("index", "middle", "ring", "pinky")
HEIGHT = 2.15                       # top of the hardhat, metres in game

# translation-only proportion edits (UAL1 armature space, metres)
SHOULDER_SHIFT = (0.050, 0.0, -0.012)    # upperarm subtree, mirrored in x
HEAD_SHIFT = (0.0, -0.012, -0.030)       # Head subtree: sunk into the traps, a touch forward
HIP_SHIFT = 0.020                        # thigh subtree outwards
HAND_SCALE = 1.12                        # finger joints scaled about the wrist (big hands; fist hole scales too)
REF_CLIP = ("Idle_Loop", 10)             # a UAL clip frame with the standard closed fist (same fist in every clip)


def _desc(b):
    out = [b]
    for c in b.children:
        out += _desc(c)
    return out


def edit_skeleton(arm):
    import bpy
    from mathutils import Vector
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for b in eb:
        b.use_connect = False

    def shift(name, d):
        for b in _desc(eb[name]):
            b.head += d
            b.tail += d

    def scale_sub(name, s, include_self_tail=True):
        c = eb[name].head.copy()
        for i, b in enumerate(_desc(eb[name])):
            if i == 0:
                if include_self_tail:
                    b.tail = c + (b.tail - c) * s
                continue
            h, t = b.head.copy(), b.tail.copy()
            b.head = c + (h - c) * s
            b.tail = c + (t - c) * s

    sx, sy, sz = SHOULDER_SHIFT
    shift("upperarm_l", Vector((sx, sy, sz)))
    shift("upperarm_r", Vector((-sx, sy, sz)))
    shift("Head", Vector(HEAD_SHIFT))
    shift("thigh_l", Vector((HIP_SHIFT, 0, 0)))
    shift("thigh_r", Vector((-HIP_SHIFT, 0, 0)))
    for s in ("l", "r"):
        scale_sub("hand_" + s, HAND_SCALE)
    bpy.ops.object.mode_set(mode='OBJECT')


def make_armature():
    """fresh scene with the edited UAL1 armature (named Armature, no meshes / actions)."""
    import bpy
    L.clear_scene()
    bpy.ops.import_scene.gltf(filepath=L.UAL1, bone_heuristic='BLENDER', disable_bone_shape=True)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    for o in list(bpy.data.objects):
        if o.type != 'ARMATURE':
            bpy.data.objects.remove(o, do_unlink=True)
    arm.animation_data_clear()
    arm.name = "Armature"
    arm.data.name = "Armature"
    edit_skeleton(arm)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    return arm


def load_clips(paths=None):
    """import UAL clip libraries (actions only); returns {name: action}."""
    import bpy
    paths = paths or [L.UAL1, L.UAL2]
    keep = set(bpy.data.objects)
    for p in paths:
        before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=p, bone_heuristic='BLENDER', disable_bone_shape=True)
        for a in bpy.data.actions:
            if a not in before:
                a.use_fake_user = True
        for o in list(bpy.data.objects):
            if o not in keep:
                bpy.data.objects.remove(o, do_unlink=True)
    out = {}
    for a in bpy.data.actions:
        nm = a.name
        if nm.endswith(".001") or nm.endswith(".002"):
            continue
        out[nm] = a
    return out


def modeling_pose():
    P = {}
    P["upperarm_l"] = (0, 44, -12)
    P["upperarm_r"] = (0, -44, 12)
    P["lowerarm_l"] = (0, 0, -22)
    P["lowerarm_r"] = (0, 0, 22)
    P["hand_l"] = (8, 0, 0)
    P["hand_r"] = (8, 0, 0)
    curl = {"01": 16, "02": 22, "03": 14}
    spread = {"index": 4, "middle": 0, "ring": -4, "pinky": -8}
    for f in FINGERS:
        for seg, c in curl.items():
            P["%s_%s_l" % (f, seg)] = (0, c, -spread[f] if seg == "01" else 0)
            P["%s_%s_r" % (f, seg)] = (0, -c, spread[f] if seg == "01" else 0)
    P["thumb_01_l"] = (0, 6, 8)
    P["thumb_02_l"] = (0, 10, 0)
    P["thumb_03_l"] = (0, 10, 0)
    P["thumb_01_r"] = (0, -6, -8)
    P["thumb_02_r"] = (0, -10, 0)
    P["thumb_03_r"] = (0, -10, 0)
    P["thigh_l"] = (0, -5, 0)
    P["thigh_r"] = (0, 5, 0)
    P["calf_l"] = (0, 4, 0)
    P["calf_r"] = (0, -4, 0)
    return P


def apply_pose(arm, pose):
    import bpy
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
        e = pose.get(pb.name)
        pb.rotation_quaternion = (1, 0, 0, 0) if e is None else L.rest_axes_to_local(pb, L.rq(*e))
    bpy.context.view_layer.update()


def joints_dict(arm):
    J = {}
    for pb in arm.pose.bones:
        J[pb.name] = {
            "head": list(pb.head), "tail": list(pb.tail),
            "pose": [list(r) for r in pb.matrix],
            "rest": [list(r) for r in pb.bone.matrix_local],
            "parent": pb.parent.name if pb.parent else None,
        }
    return J


def fist_grip(arm, side):
    """grip line of the standard UAL closed fist in hand-bone local space: (centre, axis toward the index side)."""
    pb = arm.pose.bones
    Minv = pb["hand_" + side].matrix.inverted()
    cents = []
    zs = []
    for f in FINGERS:
        pts = [Minv @ pb["%s_0%d_%s" % (f, i, side)].head for i in (1, 2, 3)] + [Minv @ pb["%s_04_leaf_%s" % (f, side)].head]
        P = np.array([list(p) for p in pts])
        # circle through the curled finger joints (fit in the hand XY plane)
        A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
        bvec = (P[:, :2] ** 2).sum(1)
        cx, cy, c = np.linalg.lstsq(A, bvec, rcond=None)[0]
        r = float(np.sqrt(c + cx * cx + cy * cy))
        cents.append((cx, cy, P[:, 2].mean(), r))
    C = np.array([c[:3] for c in cents])
    ctr = C.mean(0)
    u, s, vt = np.linalg.svd(C - ctr)
    ax = vt[0]
    idx_side = C[0] - C[-1]
    if ax @ idx_side < 0:
        ax = -ax
    return ctr.tolist(), (ax / np.linalg.norm(ax)).tolist(), float(np.mean([c[3] for c in cents]))

"""Preview renders of an exported fighter GLB (re-imported fresh, so the export itself is what is shown).

  blender -b --factory-startup --python fb_previews.py -- <src.glb> <out_dir> [--sheet <work_dir>] [--idle Clip:frame]
Writes front/side/threeq/face.jpg (idle pose) and pose_punch/pose_combo/pose_crouch.jpg (UAL clips, three.js
semantics: local bone rotations only, pelvis translation scaled to this body). --sheet also renders the brief's
six test clips at three frames each into <work_dir>/clipcheck/ (for checking pierce-through).
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import fblib as F
import fbview as FV

a = F.args()
GLB, OUT = a[0], a[1]
os.makedirs(OUT, exist_ok=True)


def opt(k, d=None):
    return a[a.index(k) + 1] if k in a else d


SHEET = opt('--sheet')
IDLE = opt('--idle', 'Sword_Idle:12')
FACE_UP = float(opt('--face-up', '0.0'))
ONLY = opt('--only')
STAFF_UP = opt('--staff-up')          # bone name of a socket at the staff tip: stand the staff upright (static views)

F.reset()
bpy.context.scene.render.fps = 30
objs = F.import_gltf(GLB)
arm = next(o for o in objs if o.type == 'ARMATURE')
meshes = [o for o in objs if o.type == 'MESH']
cam, ground = FV.studio(1024, samples=64)
pelvis_z = arm.data.bones['pelvis'].head_local.z


def clip_pose(clip, frame):
    src, act = F.load_clip_source(clip)
    ps = pelvis_z / max(0.3, src.data.bones['pelvis'].head_local.z)
    F.pose_from(src, [arm], frame, ps)
    return src, act


def staff_upright(sock, hand='hand_r', lean=0.24):
    """turn the wrist so the held staff stands upright, leaning a little away from the body (presentation)."""
    pb = arm.pose.bones[hand]
    h = pb.head.copy()
    a = (arm.pose.bones[sock].head - h).normalized()
    side = 1.0 if h.x > 0 else -1.0
    q = a.rotation_difference(Vector((side * lean, 0.03, 1.0)).normalized())
    R = q.to_matrix().to_4x4()
    from mathutils import Matrix
    pb.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def drop_src(src):
    F.delete([src])
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)


BODY = [m for m in meshes if m.name.endswith('_Body')] or meshes


def ground_to_feet():
    """the floor goes under the lowest point of the body (clips are played in place; props may dip)."""
    pts = FV.eval_points(BODY)
    return min(p.z for p in pts)


def best_frame(clip, bone, axis_fn, frames):
    src, act = F.load_clip_source(clip)
    ps = pelvis_z / max(0.3, src.data.bones['pelvis'].head_local.z)
    best, bf = -1e9, frames[0]
    for f in frames:
        F.pose_from(src, [arm], f, ps)
        p = arm.matrix_world @ arm.pose.bones[bone].head
        v = axis_fn(p)
        if v > best:
            best, bf = v, f
    return src, bf


def shot(name, view, focus=None, lens=70, pad=1.07):
    FV.frame(cam, meshes, view, pad=pad, focus=focus, lens=lens)
    FV.render(os.path.join(OUT, name + '.jpg'))


def head_focus():
    hb = arm.pose.bones['Head']
    M = arm.matrix_world @ hb.matrix
    c = M @ Vector((0, 0.10 + FACE_UP, 0.0))          # bone +Y runs up the head
    return (c + Vector((0, -0.03, 0)), 0.17)


# ---- static views in the idle pose
clip, fr = IDLE.split(':')
if not ONLY or 'static' in ONLY:
    src, act = clip_pose(clip, float(fr))
    if STAFF_UP:
        staff_upright(STAFF_UP)
    gz = ground_to_feet()
    ground.location.z = gz
    shot('front', 'front')
    shot('side', 'side')
    shot('threeq', 'threeq')
    drop_src(src)
    F.rest_pose(arm)
    shot('face', (-20, -5), focus=head_focus(), lens=85, pad=1.0)

# ---- posed frames
POSES = [('pose_punch', 'Punch_Cross', 'hand_r', lambda p: -p.y, range(0, 30), (-58, 8)),
         ('pose_combo', 'Sword_Regular_Combo', 'hand_r', lambda p: -p.y + 0.4 * p.z, range(8, 60), (-40, 10)),
         ('pose_crouch', 'Crouch_Idle_Loop', 'pelvis', lambda p: 0.0, [12], (-35, 12))]
if not ONLY or 'poses' in ONLY:
    for name, clip, bone, fn, frames, view in POSES:
        src, bf = best_frame(clip, bone, fn, list(frames))
        ps = pelvis_z / max(0.3, src.data.bones['pelvis'].head_local.z)
        F.pose_from(src, [arm], bf, ps)
        ground.location.z = ground_to_feet()
        F.log('pose', name, clip, 'frame', bf)
        shot(name, view)
        drop_src(src)

# ---- clip check sheet (the six clips of the brief)
if SHEET:
    d = os.path.join(SHEET, 'clipcheck')
    os.makedirs(d, exist_ok=True)
    bpy.context.scene.render.resolution_x = 640
    bpy.context.scene.render.resolution_y = 640
    for clip in ('Punch_Cross', 'Sword_Regular_Combo', 'Jump_Loop', 'Crouch_Idle_Loop', 'Hit_Knockback',
                 'Spell_Simple_Shoot'):
        src, act = F.load_clip_source(clip)
        f0, f1 = act.frame_range
        ps = pelvis_z / max(0.3, src.data.bones['pelvis'].head_local.z)
        for k, t in enumerate((0.2, 0.5, 0.8)):
            f = round(f0 + (f1 - f0) * t)
            F.pose_from(src, [arm], f, ps)
            ground.location.z = ground_to_feet()
            for vn, view in (('a', (-50, 10)), ('b', (130, 10))):
                FV.frame(cam, meshes, view)
                FV.render(os.path.join(d, '%s_%d%s.jpg' % (clip, k, vn)))
        drop_src(src)

"""Stage 8: preview renders (EEVEE, neutral grey studio, warm key + cool rim, bloom), 1024 px JPG.
  final mode -> art/fighters/<id>/previews/: front, side, threeq, face (idle pose) and pose_punch (Punch_Cross
               mid-strike), pose_combo (Sword_Regular_Combo), pose_crouch (Crouch_Idle_Loop)
  sheet mode -> art/_work/<id>/sheet_<clip>.jpg: 5 frames of each big clip (clipping review)
UAL clips are retargeted the way the game plays them: absolute local rotations, translation only on root/pelvis,
pelvis translation scaled by k = rest pelvis height / UAL pelvis height (rig_info.json).
blender -b --factory-startup --python s8_previews.py -- [final|sheet] [shot names...]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
import fblib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "final"
ONLY = argv[1:]
bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "final.blend"))
arm = bpy.data.objects["Armature"]
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent is arm]
K = L.load_json(os.path.join(L.WORK, "rig_info.json"))["k"]
cam = L.eevee_studio(res=1024 if MODE == "final" else 512, samples=64 if MODE == "final" else 24)
stage = bpy.data.objects.new("STAGE", None)
bpy.context.scene.collection.objects.link(stage)
for n in ("CYC", "Key", "Rim", "Rim2", "Fill"):
    bpy.data.objects[n].parent = stage
SRC = L.load_clip_sources()
print("CLIPS", sorted(SRC))


def pose(clip, frame):
    src, act = SRC[clip]
    L.pose_from_clip(src, act, frame, arm, K)


def bounds():
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        a = np.zeros(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", a)
        M = np.array(ev.matrix_world)
        a = a.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        pts.append(a[::7])
        ev.to_mesh_clear()
    P = np.concatenate(pts)
    return P


def shot(path, az, elev, lens=50, target=None, dist=None, pad=1.12):
    stage.rotation_euler = (0, 0, math.radians(az))
    d = Vector(L.el(az, elev))
    if target is None or dist is None:
        P = bounds()
        right = Vector((math.cos(math.radians(az)), math.sin(math.radians(az)), 0))
        up = d.cross(right).normalized() if False else Vector((0, 0, 1))
        lo, hi = P.min(0), P.max(0)
        c = Vector(((lo + hi) * 0.5).tolist())
        xs = P @ np.array(right, np.float32)
        h = (hi[2] - lo[2])
        w = xs.max() - xs.min()
        c = Vector((c.x, c.y, (lo[2] + hi[2]) * 0.5))
        fov = 2 * math.atan(18.0 / lens)
        dist = max(h, w) * 0.5 * pad / math.tan(fov / 2) + 0.4
        target = c
    L.aim(cam, target, d, dist, lens)
    L.render(path)


def clip_range(clip):
    a = SRC[clip][1]
    return int(a.frame_range[0]), int(a.frame_range[1])


def best_frame(clip, score, lo=0.0, hi=1.0, step=1):
    f0, f1 = clip_range(clip)
    best, bf = -1e9, f0
    for f in range(int(f0 + (f1 - f0) * lo), int(f0 + (f1 - f0) * hi) + 1, step):
        pose(clip, f)
        s = score()
        if s > best:
            best, bf = s, f
    return bf


def hand(n):
    return arm.matrix_world @ arm.pose.bones[n].head


if MODE == "final":
    out = L.PREV_DIR
    want = lambda n: (not ONLY) or n in ONLY
    pose("Idle_Loop", 0)
    if want("front"):
        shot(os.path.join(out, "front.jpg"), 0, 4)
    if want("side"):
        shot(os.path.join(out, "side.jpg"), 90, 4)
    if want("threeq"):
        shot(os.path.join(out, "threeq.jpg"), -38, 12)
    if want("face"):
        hd = arm.matrix_world @ arm.pose.bones["Head"].head
        shot(os.path.join(out, "face.jpg"), -30, 6, 55, hd + Vector((0.0, -0.08, 0.04)), 1.05)
    if want("pose_punch"):
        f = best_frame("Punch_Cross", lambda: -hand("hand_r").y, 0.1, 0.8)
        pose("Punch_Cross", f)
        print("POSE Punch_Cross frame", f)
        shot(os.path.join(out, "pose_punch.jpg"), 62, 8)
    if want("pose_combo"):
        f0, f1 = clip_range("Sword_Regular_Combo")
        f = int(f0 + (f1 - f0) * 0.29)
        pose("Sword_Regular_Combo", f)
        print("POSE Sword_Regular_Combo frame", f, (f0, f1))
        shot(os.path.join(out, "pose_combo.jpg"), -58, 10)
    if want("pose_crouch"):
        f0, f1 = clip_range("Crouch_Idle_Loop")
        pose("Crouch_Idle_Loop", (f0 + f1) // 2)
        shot(os.path.join(out, "pose_crouch.jpg"), 55, 10)
else:
    clips = ONLY or ["Punch_Cross", "Sword_Regular_Combo", "Jump_Loop", "Crouch_Idle_Loop", "Hit_Knockback",
                     "Spell_Simple_Shoot"]
    tmp = os.path.join(L.WORK, "_sheet_tmp.jpg")
    for clip in clips:
        f0, f1 = clip_range(clip)
        tiles = []
        for i, t in enumerate((0.1, 0.3, 0.5, 0.7, 0.9)):
            f = int(f0 + (f1 - f0) * t)
            pose(clip, f)
            shot(tmp, 50 if i % 2 else -40, 8)
            img = bpy.data.images.load(tmp, check_existing=False)
            a = np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], 4)
            bpy.data.images.remove(img)
            tiles.append(a)
        sheet = np.concatenate(tiles, 1)
        im = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0])
        im.pixels.foreach_set(sheet.ravel())
        im.filepath_raw = os.path.join(L.WORK, "sheet_%s.jpg" % clip)
        im.file_format = 'JPEG'
        im.save()
        bpy.data.images.remove(im)
        print("SHEET", clip, (f0, f1))

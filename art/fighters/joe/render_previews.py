"""Preview renders for a JoeBrawla fighter (art/BRIEF.md): EEVEE, neutral grey studio, warm key + cool rim.

blender -b --factory-startup --python render_previews.py -- <id> [--no-sheet]

Copies UAL clips onto the fighter's joints (tools/posed.mjs, the same channels the game plays) and renders
art/fighters/<id>/previews/: front, side, threeq, face, pose_punch (Punch_Cross mid-strike), pose_combo
(Sword_Regular_Combo), pose_crouch (Crouch_Idle_Loop); plus a clip-check contact sheet in art/_work/<id>/.
"""
import os, sys, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import bpy
import numpy as np
from mathutils import Vector
import fpreview as P

JB = r"C:\dev\JoeBrawla"
NODE = r"C:\Program Files\nodejs\node.exe"
ANIM = r"C:\dev\AverageJoe\DungeonJoe3D\assets\thirdparty\quaternius\anim"
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FID = args[0]
WORK = os.path.join(JB, 'art', '_work', FID)
OUT = os.path.join(JB, 'art', 'fighters', FID, 'previews')
os.makedirs(OUT, exist_ok=True)
SRC = os.path.join(WORK, FID + '_src.glb')
POSED = os.path.join(WORK, FID + '_posed.glb')
CHECK = ['Punch_Cross', 'Sword_Regular_Combo', 'Jump', 'Crouch_Idle', 'Hit_Knockback', 'Spell_Simple_Shoot']

r = subprocess.run([NODE, os.path.join(HERE, 'tools', 'posed.mjs'), SRC, POSED,
                    ANIM + r"\UAL1_Standard.glb:Idle_Loop,Punch_Cross,Crouch_Idle_Loop,Jump_Loop,Spell_Simple_Shoot",
                    ANIM + r"\UAL2_Standard.glb:Sword_Regular_Combo,Hit_Knockback"], capture_output=True, text=True, cwd=JB)
print(r.stdout, r.stderr[-2000:])

P.reset()
arm, meshes, objs = P.import_glb(POSED)
cam = P.studio(1024)
sc = bpy.context.scene


def bone(name):
    return arm.matrix_world @ arm.pose.bones[name].head


def frames_of(clip):
    act, (f0, f1) = P.set_clip(arm, clip, frac=0.0)
    return f0, f1


def best_frame(clip, score, n=48):
    f0, f1 = frames_of(clip)
    best, bf = -1e9, f0
    for i in range(n + 1):
        f = f0 + (f1 - f0) * i / n
        sc.frame_set(int(f), subframe=f - int(f))
        s = score()
        if s > best:
            best, bf = s, f
    sc.frame_set(int(bf), subframe=bf - int(bf))
    return bf


# ---------------------------------------------------------------- idle views
P.set_clip(arm, 'Idle', frac=0.0)
pts = P.eval_points(meshes, 2)
h = float(pts[:, 2].max() - pts[:, 2].min())
print('HEIGHT idle %.3f m' % h)
for view, az, el, lens in (('front', 0, 4, 55), ('side', 90, 3, 55), ('threeq', -35, 10, 55)):
    P.frame(cam, pts, az, el, lens=lens, pad=1.06)
    P.render(os.path.join(OUT, view + '.jpg'))
hp = bone('Head')
fp = pts[np.linalg.norm(pts - np.array(hp + Vector((0, 0, 0.06))), axis=1) < 0.17]
P.frame(cam, fp, -18, 4, lens=85, pad=1.08)
P.render(os.path.join(OUT, 'face.jpg'))

# ---------------------------------------------------------------- posed frames
best_frame('Punch_Cross', lambda: -(bone('hand_r').y - bone('pelvis').y))
pts = P.eval_points(meshes, 2)
P.frame(cam, pts, -55, 8, lens=55, pad=1.08)
P.render(os.path.join(OUT, 'pose_punch.jpg'))
f0, f1 = frames_of('Sword_Regular_Combo')
best_frame('Sword_Regular_Combo', lambda: (bone('hand_r') - bone('spine_03')).length * (1 if bone('hand_r').z > 1.0 else 0.6))
pts = P.eval_points(meshes, 2)
P.frame(cam, pts, -40, 10, lens=55, pad=1.08)
P.render(os.path.join(OUT, 'pose_combo.jpg'))
P.set_clip(arm, 'Crouch_Idle', frac=0.3)
pts = P.eval_points(meshes, 2)
P.frame(cam, pts, -35, 12, lens=55, pad=1.1)
P.render(os.path.join(OUT, 'pose_crouch.jpg'))

# ---------------------------------------------------------------- clip-check contact sheet (4 frames per clip)
if '--no-sheet' not in args:
    sc.render.resolution_x = 360
    sc.render.resolution_y = 360
    sc.eevee.taa_render_samples = 32
    tiles = []
    for clip in CHECK:
        row = []
        for k, frac in enumerate((0.15, 0.4, 0.62, 0.85)):
            P.set_clip(arm, clip, frac=frac)
            pts = P.eval_points(meshes, 4)
            P.frame(cam, pts, -60 if k % 2 else 30, 8, lens=50, pad=1.05)
            pth = os.path.join(WORK, '_sheet_%s_%d.jpg' % (clip, k))
            P.render(pth, quality=85)
            row.append(pth)
        tiles.append(row)
    rows = []
    for row in tiles:
        ims = []
        for pth in row:
            im = bpy.data.images.load(pth)
            a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)
            ims.append(a)
            bpy.data.images.remove(im)
        rows.append(np.concatenate(ims, 1))
    full = np.concatenate(rows[::-1], 0)
    out = bpy.data.images.new('sheet', full.shape[1], full.shape[0])
    out.pixels.foreach_set(full.ravel())
    out.filepath_raw = os.path.join(WORK, FID + '_clipcheck.png')
    out.file_format = 'PNG'
    out.save()
    for row in tiles:
        for pth in row:
            os.remove(pth)
    print('SHEET', out.filepath_raw)

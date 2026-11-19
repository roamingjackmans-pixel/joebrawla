"""Stage 0b: take the Quaternius UBC male head (face, ears, neck + eyebrows), move it onto the Landlord's Head
joint (x1.06, fighting-game head size), subdivide it twice and save it with its UVs -> _work/ubc_head.npz.
Also measures the eyeball centres/radius and fits the cranium ellipsoid used to sculpt the slicked hair.
blender -b --factory-startup --python s0b_head.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
import jb_lib as L

HEAD_SCALE = 1.06
J = L.load_json(os.path.join(L.WORK, "joints.json"))
L.clear_scene()
bpy.ops.import_scene.gltf(filepath=L.UBC_MALE, bone_heuristic='BLENDER', disable_bone_shape=True)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SuperHero')][0]
brows = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Eyebrows')][0]
eyes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Eyes')][0]
src_head = arm.data.bones["Head"].head_local.copy()
dst_head = Vector(J["Head"]["head"])


def xf(co):
    return dst_head + (co - src_head) * HEAD_SCALE


# --- keep the head + neck faces of the body
gi = {g.index: g.name for g in body.vertex_groups}
keep_v = set()
for v in body.data.vertices:
    ws = {gi[g.group]: g.weight for g in v.groups}
    if ws.get("Head", 0) + ws.get("neck_01", 0) > 0.5 and v.co.z > 1.47:
        keep_v.add(v.index)
bm = bmesh.new()
bm.from_mesh(body.data)
kill = [f for f in bm.faces if not all(v.index in keep_v for v in f.verts)]
bmesh.ops.delete(bm, geom=kill, context='FACES')
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
for v in bm.verts:
    v.co = xf(v.co)
bm.to_mesh(body.data)
bm.free()
# brows: joined (separate shells), flagged by a face attribute
for v in brows.data.vertices:
    v.co = xf(brows.matrix_world @ v.co)
brows.matrix_world.identity()
fa = body.data.attributes.new("brow", 'INT', 'FACE')
fb = brows.data.attributes.new("brow", 'INT', 'FACE')
fb.data.foreach_set("value", [1] * len(brows.data.polygons))
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
brows.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
head = body
for m in list(head.modifiers):
    head.modifiers.remove(m)
head.parent = None
head.matrix_world.identity()
# subdivide x2 (keeps UVs)
mod = head.modifiers.new("ss", 'SUBSURF')
mod.levels = 2
mod.render_levels = 2
mod.uv_smooth = 'PRESERVE_BOUNDARIES'
bpy.context.view_layer.objects.active = head
bpy.ops.object.modifier_apply(modifier=mod.name)
bm = bmesh.new()
bm.from_mesh(head.data)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.to_mesh(head.data)
bm.free()
me = head.data
V = np.zeros(len(me.vertices) * 3, np.float32)
me.vertices.foreach_get("co", V)
V = V.reshape(-1, 3)
F = np.zeros(len(me.polygons) * 3, np.int32)
me.polygons.foreach_get("vertices", F)
F = F.reshape(-1, 3)
uvl = me.uv_layers.active.data
UV = np.zeros(len(uvl) * 2, np.float32)
uvl.foreach_get("uv", UV)
UV = UV.reshape(-1, 3, 2)
brow = np.zeros(len(me.polygons), np.int32)
me.attributes["brow"].data.foreach_get("value", brow)
# eyes: fit centre + radius per eyeball from the UBC eye mesh
E = np.array([list(xf(eyes.matrix_world @ v.co)) for v in eyes.data.vertices], np.float32)
eye = []
for s in (1, -1):
    P = E[(E[:, 0] * s) > 0]
    A = np.c_[2 * P, np.ones(len(P))]
    bvec = (P ** 2).sum(1)
    cx, cy, cz, c = np.linalg.lstsq(A, bvec, rcond=None)[0]
    r = float(np.sqrt(c + cx * cx + cy * cy + cz * cz))
    eye.append([float(cx), float(cy), float(cz), r])
    print("EYE", s, np.round([cx, cy, cz], 4), "r %.4f" % r)
# cranium ellipsoid: bounding fit of the skull above the brows
sk = V[(V[:, 2] > eye[0][2] + 0.02) & (brow[np.arange(len(V)) % len(brow)] >= 0)]
c = np.array([0.0, float(sk[:, 1].mean()), float(sk[:, 2].min() + 0.02)], np.float32)
q = sk - c
ax = np.array([np.abs(q[:, 0]).max(), np.abs(q[:, 1]).max(), np.abs(q[:, 2]).max()], np.float32)
k = float(np.sqrt(((q / ax) ** 2).sum(1)).max())
ax = ax * k
print("CRANIUM centre", np.round(c, 4), "radii", np.round(ax, 4), "top z %.4f" % V[:, 2].max())
np.savez(os.path.join(L.WORK, "ubc_head.npz"), V=V, F=F, UV=UV, brow=brow, eye=np.array(eye, np.float32),
         cranium=np.concatenate([c, ax]).astype(np.float32))
print("HEAD verts %d tris %d" % (len(V), len(F)))

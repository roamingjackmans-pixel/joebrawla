"""Probe the UBC Superhero_Male body: meshes, tris, materials, landmarks; export round-trip test.
blender -b --factory-startup --python probe_body.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import bpy
import djlib as dj
import agcore as C
dj.reset()
body = C.Body('m')
for o in body.meshes:
    print('MESH', o.name, 'tris', dj.tri_count(o), 'mats', [s.material.name for s in o.material_slots],
          'uv', [u.name for u in o.data.uv_layers], 'verts', len(o.data.vertices))
    for s in o.material_slots:
        for n in s.material.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                print('   img', n.image.name, n.image.size[:], n.image.filepath)
body.report()
print('ARM bones', len(body.arm.data.bones), 'arm scale', body.arm.scale[:], 'loc', body.arm.location[:], 'rot', body.arm.rotation_euler[:])
for b in ('root', 'pelvis', 'Head', 'neck_01', 'hand_r', 'middle_01_r', 'foot_l', 'ball_l'):
    print('BONE', b, tuple(round(x, 4) for x in body.h(b)), tuple(round(x, 4) for x in body.t(b)))
out = os.path.join(os.environ.get('FIGHTER_WORK', 'C:/dev/JoeBrawla/art/_work/joe'), 'probe_rt.glb')
dj.export_glb(out, [body.mesh, body.arm], skinned=True)

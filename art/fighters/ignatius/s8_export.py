"""Stage 8: export the uncompressed source GLB (armature + skinned meshes, embedded PNG textures, no clips)
-> art/_work/<id>/<id>_src.glb.   The game ships it through `node tools/assets.mjs fighter ...` (1024 WebP + meshopt).
blender -b --factory-startup --python s8_export.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import jb_lib as L

bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "rig.blend"))
arm = bpy.data.objects["Armature"]
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for o in list(bpy.data.objects):
    if o.type not in ('ARMATURE', 'MESH') or (o.type == 'MESH' and o.parent != arm):
        bpy.data.objects.remove(o, do_unlink=True)
out = L.SRC_GLB
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB', use_selection=False, use_visible=False, export_yup=True, export_apply=False,
    export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
    export_image_format='AUTO', export_skins=True, export_influence_nb=4, export_all_influences=False,
    export_def_bones=False, export_leaf_bone=False, export_rest_position_armature=True, export_animations=False,
    export_morph=False, export_cameras=False, export_lights=False, export_extras=False)
print("EXPORT", out, os.path.getsize(out) // 1024, "KB")

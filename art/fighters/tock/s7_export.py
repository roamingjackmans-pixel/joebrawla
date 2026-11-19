"""Stage 7: export the source GLB (armature + skinned meshes, rest pose, no clips, PNG textures)
  -> art/_work/<id>/<id>_src.glb   (then: node tools/assets.mjs fighter art/_work/<id>/<id>_src.glb <id>)
blender -b --factory-startup --python s7_export.py
"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import fblib as L

bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "final.blend"))
arm = bpy.data.objects["Armature"]
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for pb in arm.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('ARMATURE', 'MESH') and (o is arm or o.parent is arm):
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
out = os.path.join(L.WORK, L.FID + "_src.glb")
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
    export_texcoords=True, export_normals=True, export_tangents=True, export_materials='EXPORT',
    export_image_format='AUTO', export_skins=True, export_influence_nb=4, export_all_influences=False,
    export_def_bones=False, export_leaf_bone=False, export_rest_position_armature=True, export_reset_pose_bones=True,
    export_animations=False, export_morph=False, export_cameras=False, export_lights=False, export_extras=False)
print("EXPORT", out, "%.2f MB" % (os.path.getsize(out) / 1e6))

# quick JSON sanity check
data = open(out, 'rb').read()
clen, ctype = struct.unpack_from('<II', data, 12)
js = json.loads(data[20:20 + clen].decode('utf8'))
for m in js["materials"]:
    pbr = m.get("pbrMetallicRoughness", {})
    print("CHECK material %-14s factor=%s alpha=%s emissive=%s ext=%s" % (
        m["name"], [round(x, 3) for x in pbr.get("baseColorFactor", [1, 1, 1, 1])], m.get("alphaMode", "OPAQUE"),
        m.get("emissiveFactor"), list(m.get("extensions", {}).keys())))
sk = js["skins"][0]
names = [js["nodes"][j]["name"] for j in sk["joints"]]
print("CHECK joints", len(names), "anim", len(js.get("animations", [])), "meshes", [m["name"] for m in js["meshes"]])

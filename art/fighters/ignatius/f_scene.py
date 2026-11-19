"""glTF-friendly materials + the EEVEE preview studio (neutral grey, warm key, cool rim)."""
import math, os
import bpy
from mathutils import Vector, Euler
import jb_lib as L


# ------------------------------------------------------------------------------------------ materials
def gltf_output_group():
    name = "glTF Material Output"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    g.interface.new_socket("Thickness", in_out='INPUT', socket_type='NodeSocketFloat')
    g.nodes.new("NodeGroupInput")
    return g


def load_img(path, colorspace):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def pbr_material(name, albedo, normal=None, orm=None, emission=None, emission_strength=1.0, alpha_clip=None,
                 normal_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    ia = nt.nodes.new("ShaderNodeTexImage"); ia.image = load_img(albedo, 'sRGB'); ia.location = (-600, 300)
    nt.links.new(ia.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_clip is not None:
        nt.links.new(ia.outputs["Alpha"], bsdf.inputs["Alpha"])
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        m["gltf_alpha_cutoff"] = alpha_clip
        m.use_backface_culling = False
    if normal:
        inn = nt.nodes.new("ShaderNodeTexImage"); inn.image = load_img(normal, 'Non-Color'); inn.location = (-600, -300)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -300)
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(inn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if orm:
        io = nt.nodes.new("ShaderNodeTexImage"); io.image = load_img(orm, 'Non-Color'); io.location = (-600, 0)
        sp = nt.nodes.new("ShaderNodeSeparateColor"); sp.location = (-300, 0)
        nt.links.new(io.outputs["Color"], sp.inputs["Color"])
        nt.links.new(sp.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sp.outputs["Blue"], bsdf.inputs["Metallic"])
        grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = gltf_output_group(); grp.location = (0, -500)
        nt.links.new(sp.outputs["Red"], grp.inputs["Occlusion"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.8
    if emission:
        ie = nt.nodes.new("ShaderNodeTexImage"); ie.image = load_img(emission, 'sRGB'); ie.location = (-600, -650)
        nt.links.new(ie.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    m.use_backface_culling = alpha_clip is None
    return m


def foliage_material(name, albedo):
    """alpha-cutout, double sided (glTF alphaMode MASK via Math Round)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    ia = nt.nodes.new("ShaderNodeTexImage"); ia.image = load_img(albedo, 'sRGB')
    ia.image.alpha_mode = 'STRAIGHT'
    nt.links.new(ia.outputs["Color"], bsdf.inputs["Base Color"])
    rnd = nt.nodes.new("ShaderNodeMath"); rnd.operation = 'ROUND'
    nt.links.new(ia.outputs["Alpha"], rnd.inputs[0])
    nt.links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.75
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
    m.use_backface_culling = False
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m



def set_base_factor(m, fac_lin):
    """base colour = texture x factor (exported as glTF baseColorFactor)."""
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    lk = bsdf.inputs["Base Color"].links[0]
    src = lk.from_socket
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(src, mx.inputs[6])
    mx.inputs[7].default_value = (fac_lin[0], fac_lin[1], fac_lin[2], 1.0)
    nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
    return m


# ------------------------------------------------------------------------------------------ EEVEE studio
def studio(res=1024, samples=64, floor=True):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass
    for attr, val in (("use_shadows", True), ("use_raytracing", True), ("use_gtao", True)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.20, 0.205, 0.215, 1)
    bg.inputs["Strength"].default_value = 0.35
    lights = {}
    for nm, kind, en, col, rot, size in (("key", 'AREA', 360.0, (1.0, 0.84, 0.66), (52, 0, -40), 2.5),
                                          ("rim", 'AREA', 520.0, (0.55, 0.72, 1.0), (-62, 0, 152), 1.8),
                                          ("fill", 'AREA', 70.0, (0.85, 0.88, 1.0), (75, 0, 70), 4.0)):
        ld = bpy.data.lights.new(nm, kind)
        ld.energy = en
        ld.color = col
        ld.size = size
        ob = bpy.data.objects.new(nm, ld)
        sc.collection.objects.link(ob)
        r = [math.radians(a) for a in rot]
        ob.rotation_euler = Euler(r, 'XYZ')
        d = ob.rotation_euler.to_matrix() @ Vector((0, 0, 1))
        ob.location = Vector((0, 0, 1.1)) + d * 5.0
        lights[nm] = ob
    if floor:
        bpy.ops.mesh.primitive_circle_add(vertices=96, radius=12, fill_type='NGON', location=(0, 0, 0))
        g = bpy.context.active_object
        g.name = "floor"
        gm = bpy.data.materials.new("floor")
        gm.use_nodes = True
        p = gm.node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value = (0.20, 0.205, 0.215, 1)
        p.inputs["Roughness"].default_value = 0.85
        g.data.materials.append(gm)
    return lights


def camera(name="cam", lens=50):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_end = 200
    cam.data.clip_start = 0.02
    bpy.context.scene.camera = cam
    return cam


def aim(cam, target, direction, dist):
    d = Vector(direction).normalized()
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path)

"""EEVEE preview renders for JoeBrawla fighters (art/BRIEF.md): neutral grey studio, warm key + cool rim light.

Views: front, side, threeq, face; posed frames come from a GLB whose clips were copied onto the fighter's joints by
tools/posed.mjs (the same channels the game plays), so the poses match three.js exactly.
"""
import bpy, math, os
import numpy as np
from mathutils import Vector, Euler, Matrix


def srgb_lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in objs if o.type == 'ARMATURE'), None)
    meshes = [o for o in objs if o.type == 'MESH']
    return arm, meshes, objs


def _area(name, color, energy, size, loc, target, shape='DISK', spread=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.color = srgb_lin(color)
    ld.energy = energy
    ld.shape = shape
    ld.size = size
    if spread is not None:
        ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    d = (Vector(target) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def studio(res=1024, bg='#5a5c60', floor='#64666a'):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    ee = sc.eevee
    for k, v in (('taa_render_samples', 96), ('use_shadows', True), ('shadow_ray_count', 2), ('shadow_step_count', 8),
                 ('use_raytracing', True), ('fast_gi_distance', 0.6), ('use_fast_gi', True)):
        try:
            setattr(ee, k, v)
        except Exception:
            pass
    try:
        ee.ray_tracing_options.resolution_scale = '1'
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    # world: soft neutral grey ambient
    w = bpy.data.worlds.new('Studio')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bgn = nt.nodes.new('ShaderNodeBackground')
    bgn.inputs['Color'].default_value = (*srgb_lin(bg), 1)
    bgn.inputs['Strength'].default_value = 0.55
    nt.links.new(bgn.outputs[0], out.inputs[0])
    # seamless cyclorama: floor curving up into a back wall (+Y is behind the fighter, who faces -Y)
    import bmesh
    bm = bmesh.new()
    prof = []
    for i in range(10):
        prof.append((-2.0 + 6.0 * i / 9, 0.0))
    R = 1.6
    for i in range(1, 12):
        a = (math.pi / 2) * i / 11
        prof.append((4.0 + R * math.sin(a), R * (1 - math.cos(a))))
    prof.append((4.0 + R, 8.0))
    W = 9.0
    rows = []
    for (y, z) in prof:
        rows.append([bm.verts.new((x, y, z)) for x in np.linspace(-W, W, 12)])
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(len(a) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    me = bpy.data.meshes.new('cyc')
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    cyc = bpy.data.objects.new('cyclorama', me)
    sc.collection.objects.link(cyc)
    gm = bpy.data.materials.new('cyc')
    gm.use_nodes = True
    p = gm.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*srgb_lin(floor), 1)
    p.inputs['Roughness'].default_value = 0.85
    me.materials.append(gm)
    # lights: warm key front-left-high, cool rim back-right, faint neutral fill front-right, cool kicker back-left
    _area('Key', '#ffd2a3', 900.0, 1.6, (-2.6, -3.2, 3.6), (0, 0, 1.15))
    _area('Rim', '#8fb8ff', 1100.0, 1.2, (2.6, 2.4, 2.9), (0, 0, 1.25))
    _area('Kick', '#a9c6ff', 380.0, 1.0, (-2.8, 2.2, 1.6), (0, 0, 1.0))
    _area('Fill', '#e8ecf2', 160.0, 3.0, (3.0, -3.4, 1.4), (0, 0, 1.0))
    cd = bpy.data.cameras.new('Cam')
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    _glare()
    return cam


def _glare():
    """bloom on emissive accents (compositor fog glow); skipped quietly if the node API differs."""
    sc = bpy.context.scene
    try:
        sc.use_nodes = True
        nt = sc.node_tree
    except Exception:
        nt = None
    if nt is None:
        try:
            ng = bpy.data.node_groups.new('Comp', 'CompositorNodeTree')
            sc.compositing_node_group = ng
            nt = ng
            rl = nt.nodes.new('CompositorNodeRLayers')
            gl = nt.nodes.new('CompositorNodeGlare')
            out = nt.nodes.new('NodeGroupOutput')
            nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
            _glare_cfg(gl)
            nt.links.new(rl.outputs['Image'], gl.inputs[0])
            nt.links.new(gl.outputs[0], out.inputs[0])
            return
        except Exception as e:
            print('glare skipped', e)
            return
    try:
        nt.nodes.clear()
        rl = nt.nodes.new('CompositorNodeRLayers')
        gl = nt.nodes.new('CompositorNodeGlare')
        comp = nt.nodes.new('CompositorNodeComposite')
        _glare_cfg(gl)
        nt.links.new(rl.outputs['Image'], gl.inputs[0])
        nt.links.new(gl.outputs[0], comp.inputs[0])
    except Exception as e:
        print('glare skipped', e)


def _glare_cfg(gl):
    for k, v in (('glare_type', 'BLOOM'), ('quality', 'HIGH'), ('threshold', 1.2), ('size', 7), ('mix', -0.55)):
        try:
            setattr(gl, k, v)
        except Exception:
            pass
    for k, v in (('Threshold', 1.2), ('Strength', 0.45), ('Size', 0.55)):
        try:
            gl.inputs[k].default_value = v
        except Exception:
            pass
    try:
        gl.inputs['Type'].default_value = 'Bloom'
    except Exception:
        pass


def eval_points(meshes, step=1):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)[::step]
        M = np.array(mw)
        co = co @ M[:3, :3].T + M[:3, 3]
        pts.append(co)
        ev.to_mesh_clear()
    return np.concatenate(pts, 0) if pts else np.zeros((0, 3))


def frame(cam, pts, az, el, lens=60, pad=1.08, center=None, aspect=1.0):
    """point the camera from azimuth az (0 = in front of the fighter, who faces -Y; +90 = his left) and elevation
    el (deg) so all pts fit."""
    cam.data.lens = lens
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.sensor_width = 36
    azr, elr = math.radians(az), math.radians(el)
    d = Vector((math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)))
    mn, mx = pts.min(0), pts.max(0)
    c = Vector(((mn + mx) * 0.5).tolist()) if center is None else Vector(center)
    q = (-d).to_track_quat('-Z', 'Y')
    R = np.array(q.to_matrix())
    right, up = R[:, 0], R[:, 1]
    v = pts - np.array(c)
    x, y, z = v @ right, v @ up, v @ np.array(d)
    th = math.tan(math.atan(18 / lens))
    tv = th / aspect
    dist = float(np.max(np.maximum(np.abs(x) / th, np.abs(y) / tv) + z)) * pad
    cam.location = c + d * dist
    cam.rotation_euler = q.to_euler()
    cam.data.clip_start = 0.02
    cam.data.clip_end = dist * 10
    return dist


def render(path, quality=92):
    sc = bpy.context.scene
    s = sc.render.image_settings
    s.file_format = 'JPEG'
    s.quality = quality
    s.color_mode = 'RGB'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)


def set_clip(arm, name, t=None, frac=None):
    """assign the imported action `name` (glTF clip) and go to time t (s) or fraction of its length."""
    act = None
    for a in bpy.data.actions:
        if a.name == name or a.name.startswith(name + '_') or a.name.split('|')[-1] == name:
            act = a
            break
    if act is None:
        raise KeyError(name + ' in ' + ', '.join(a.name for a in bpy.data.actions))
    if arm.animation_data is None:
        arm.animation_data_create()
    ad = arm.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    ad.action = act
    try:
        if act.slots:
            ad.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = act.frame_range
    sc = bpy.context.scene
    fps = sc.render.fps / sc.render.fps_base
    if frac is not None:
        f = f0 + (f1 - f0) * frac
    else:
        f = f0 + (t or 0.0) * fps
    sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    return act, (f0, f1)

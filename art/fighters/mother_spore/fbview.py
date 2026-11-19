"""Preview studio for fighter renders: EEVEE, neutral grey studio, warm key + cool rim + soft fill, bloom."""
import bpy, math, os
from mathutils import Vector, Euler
import fblib as F

VIEWS = {  # azimuth (0 = front, camera on -Y), elevation (deg)
    'front': (0, 2), 'side': (90, 4), 'threeq': (-38, 4), 'back': (180, 8), 'face': (-18, 6), 'sideL': (-90, 4),
}


def studio(res=1024, engine='EEVEE', samples=64, ground=True):
    sc = bpy.context.scene
    if engine == 'EEVEE':
        sc.render.engine = 'BLENDER_EEVEE'
        ee = sc.eevee
        ee.taa_render_samples = samples
        for k, v in (('use_shadows', True), ('use_raytracing', True), ('shadow_ray_count', 2), ('shadow_step_count', 8),
                     ('use_fast_gi', True)):
            try:
                setattr(ee, k, v)
            except Exception:
                pass
    else:
        F.gpu_setup(samples)
        sc.cycles.use_denoising = True
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception as e:
        F.log('colour management', e)
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92
    # world: neutral grey, soft
    w = bpy.data.worlds.new('Studio')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.16, 0.16, 0.165, 1)
    bg.inputs['Strength'].default_value = 0.55
    nt.links.new(bg.outputs[0], out.inputs[0])
    lights = []

    def sun(name, col, energy, rx, rz, angle=4.0):
        d = bpy.data.lights.new(name, 'SUN')
        d.energy = energy
        d.color = col
        d.angle = math.radians(angle)
        o = bpy.data.objects.new(name, d)
        F.link(o)
        o.rotation_euler = Euler((math.radians(rx), 0, math.radians(rz)), 'XYZ')
        lights.append(o)
        return o
    sun('Key', (1.0, 0.84, 0.66), 3.6, 48, -36, 3.0)        # warm key from front-left, above
    sun('Rim', (0.55, 0.72, 1.0), 4.2, -62, 152, 2.0)       # cool rim from behind-right
    sun('Fill', (0.85, 0.88, 1.0), 0.7, 70, 60, 10.0)       # soft fill from the right
    g = None
    if ground:
        gm = bpy.data.materials.new('ground')
        gm.use_nodes = True
        gp = gm.node_tree.nodes.get('Principled BSDF')
        gp.inputs['Base Color'].default_value = (0.19, 0.19, 0.195, 1)
        gp.inputs['Roughness'].default_value = 0.85
        me = bpy.data.meshes.new('ground')
        s = 30
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new('GROUND', me)
        F.link(g)
        me.materials.append(gm)
    # bloom (compositor glare), so emissive accents read like they will in the game
    try:
        ng = bpy.data.node_groups.new('Bloom', 'CompositorNodeTree')
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        rl = ng.nodes.new('CompositorNodeRLayers')
        gl = ng.nodes.new('CompositorNodeGlare')
        go = ng.nodes.new('NodeGroupOutput')
        for nm, v in (('Type', 'Bloom'), ('Quality', 'High'), ('Threshold', 1.0), ('Strength', 0.35), ('Size', 0.55),
                      ('Saturation', 1.0)):
            try:
                gl.inputs[nm].default_value = v
            except Exception as e:
                F.log('glare', nm, e)
        ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
        ng.links.new(gl.outputs['Image'], go.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
    except Exception as e:
        F.log('no bloom', e)
    cd = bpy.data.cameras.new('Cam')
    cd.lens = 70
    cam = bpy.data.objects.new('Cam', cd)
    F.link(cam)
    sc.camera = cam
    return cam, g


def eval_points(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        if o.hide_render:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        pts += [mw @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return pts


def frame(cam, meshes, view, pad=1.07, focus=None, lens=70, aim_y=0.0):
    """Place the camera to fit `meshes` (or focus=((x,y,z), radius)) from a view (name or (az, el))."""
    cam.data.lens = lens
    pts = eval_points(meshes)
    az, el = VIEWS[view] if isinstance(view, str) else view
    azr, elr = math.radians(az), math.radians(el)
    d = Vector((math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)))
    if focus is not None:
        c = Vector(focus[0])
        pts = [p for p in pts if (p - c).length < focus[1]]
    else:
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        c = (mn + mx) * 0.5
        c.z += aim_y
    q = (-d).to_track_quat('-Z', 'Y')
    R = q.to_matrix()
    right, up = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0))
    fov = 2 * math.atan(18 / cam.data.lens)
    best = 0.01
    step = max(1, len(pts) // 30000)
    for p in pts[::step]:
        v = p - c
        x, y, z = v.dot(right), v.dot(up), v.dot(d)
        best = max(best, max(abs(x), abs(y)) / math.tan(fov / 2) + z)
    dist = best * pad
    cam.location = c + d * dist
    cam.rotation_euler = q.to_euler()
    cam.data.clip_end = dist * 8
    cam.data.clip_start = 0.02
    return c, dist


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    F.log('rendered', path)

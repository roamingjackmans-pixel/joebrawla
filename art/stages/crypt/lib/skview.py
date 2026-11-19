"""Stage previews that mimic the game's three.js frame (public/js/render/scene.js + stages.js).

EEVEE renders the GLB lit by stage.json (sun, hemisphere + sky environment as world light, two rims, a front
fill) into linear EXR passes (premultiplied colour on a transparent film + view depth). numpy then does what the
game does after that: linear smoothstep fog on surfaces (THREE.Fog), the gradient sky dome with its sun glow behind
everything (not fogged), UnrealBloomPass (5 mips, radius 0.55), ACESFilmicToneMapping (exposure / 0.6), sRGB, and the
GradeShader (saturation 1.08, contrast 1.06, vignette 0.32).

blender -b --factory-startup --python skview.py -- <stage id> [--glb path] [--extra] [--res 1280x720]
  -> art/stages/<id>/previews/game.jpg (camera (0,1.5,9.5) -> (0,1,0), vFOV 30, two 1.8 m capsules at x = +-1.5)
     art/stages/<id>/previews/wide.jpg (camera (0,2.5,16) -> (0,2,-10))
  --extra also renders art/_work/stages/<id>/view_*.jpg: the camera pulled back/up and slid to the walls.
Coordinates: glTF (x, y up, z toward the camera) == Blender (x, -z, y).
"""
import bpy, os, sys, math, json, time
import numpy as np
from mathutils import Vector

JB = r"C:\dev\JoeBrawla"


def g2b(x, y, z):
    """glTF (Y-up, +Z toward camera) -> Blender (Z-up, +Y away from camera)."""
    return Vector((x, -z, y))


def hexlin(h):
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _defaults(S):
    S = dict(S)
    S.setdefault('envIntensity', 0.75)
    S.setdefault('rimIntensity', [2.0, 1.6])
    S.setdefault('exposure', 1.0)
    S.setdefault('bloom', [0.42, 0.82])
    S.setdefault('fill', 0.35)
    return S


# ----------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def _sun(name, dir_gl, color, strength, shadow=True, angle=1.5):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.color = tuple(hexlin(color))
    ld.energy = strength
    ld.angle = math.radians(angle)
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    d = g2b(*dir_gl).normalized()          # direction toward the light
    ob.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    return ob


def world(S):
    """World = what lights the surfaces: env (the sky dome as scene.environment) + hemisphere light / pi."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('StageWorld')
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links.new
    out = N.new('ShaderNodeOutputWorld')
    bg = N.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 1.0
    L(bg.outputs[0], out.inputs['Surface'])
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    L(tc.outputs['Generated'], sep.inputs[0])       # world generated == view direction (Blender Z up)
    z = sep.outputs['Z']
    top, mid, bot = (hexlin(S['sky'][k]) for k in ('top', 'mid', 'bottom'))
    env = S['envIntensity']
    hs, hg = hexlin(S['hemi']['sky']), hexlin(S['hemi']['ground'])
    hk = S['hemi']['intensity'] / math.pi

    def rgb(c):
        n = N.new('ShaderNodeRGB')
        n.outputs[0].default_value = (*c, 1.0)
        return n.outputs[0]

    def mixc(f, a, b):
        n = N.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.clamp_factor = True
        ins = {s.identifier: s for s in n.inputs}
        L(f, ins['Factor_Float']) if not isinstance(f, float) else None
        if isinstance(f, float):
            ins['Factor_Float'].default_value = f
        L(a, ins['A_Color'])
        L(b, ins['B_Color'])
        return [s for s in n.outputs if s.identifier == 'Result_Color'][0]

    def m(op, a, b=None):
        n = N.new('ShaderNodeMath')
        n.operation = op
        n.use_clamp = False
        if isinstance(a, float):
            n.inputs[0].default_value = a
        else:
            L(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float):
                n.inputs[1].default_value = b
            else:
                L(b, n.inputs[1])
        return n.outputs[0]

    up = m('POWER', m('MAXIMUM', z, 0.0), 0.6)
    dn = m('POWER', m('MAXIMUM', m('MULTIPLY', z, -1.0), 0.0), 0.5)
    pos = m('GREATER_THAN', z, 0.0)
    skyc = mixc(pos, mixc(dn, rgb(mid), rgb(bot)), mixc(up, rgb(mid), rgb(top)))
    hemi = mixc(m('ADD', m('MULTIPLY', z, 0.5), 0.5), rgb(hg * hk), rgb(hs * hk))
    envc = N.new('ShaderNodeVectorMath')
    envc.operation = 'SCALE'
    L(skyc, envc.inputs[0])
    envc.inputs['Scale'].default_value = env
    tot = N.new('ShaderNodeVectorMath')
    tot.operation = 'ADD'
    L(envc.outputs[0], tot.inputs[0])
    L(hemi, tot.inputs[1])
    L(tot.outputs[0], bg.inputs['Color'])
    return w


def lights(S):
    sun = S['sun']
    _sun('Sun', sun['dir'], sun['color'], sun['intensity'], shadow=True, angle=S.get('sunAngle', 1.2))
    ra, rb = S['rim']
    ia, ib = S['rimIntensity']
    _sun('RimA', (-7, 4, -6), ra, ia, shadow=False)
    _sun('RimB', (7, 3, -6), rb, ib, shadow=False)
    _sun('Fill', (0, 2, 10), '#ffffff', S['fill'], shadow=False)


def capsules():
    mt = bpy.data.materials.new('capsule_grey')
    p = mt.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (0.32, 0.32, 0.33, 1)
    p.inputs['Roughness'].default_value = 0.6
    obs = []
    for x in (-1.5, 1.5):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.28, location=(x, 0, 0.28))
        a = bpy.context.object
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.28, depth=1.8 - 0.56, location=(x, 0, 0.9))
        b = bpy.context.object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.28, location=(x, 0, 1.8 - 0.28))
        c = bpy.context.object
        for o in (a, b, c):
            o.data.materials.append(mt)
            o.data.shade_smooth()
            o.name = 'capsule'
            obs.append(o)
    return obs


def camera(pos_gl, look_gl, fov_v=30.0):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('Cam')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov_v)
    cd.clip_start = 0.1
    cd.clip_end = 400.0
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    place_camera(cam, pos_gl, look_gl)
    return cam


def place_camera(cam, pos_gl, look_gl):
    p, t = g2b(*pos_gl), g2b(*look_gl)
    cam.location = p
    cam.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()


def setup_render(res=(1280, 720), samples=64):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    ee = sc.eevee
    for k, v in (('taa_render_samples', samples), ('use_shadows', True), ('shadow_ray_count', 2),
                 ('shadow_step_count', 8), ('use_raytracing', False), ('use_fast_gi', False),
                 ('shadow_resolution_scale', 1.0)):
        try:
            setattr(ee, k, v)
        except Exception:
            pass
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    work = os.path.join(bpy.app.tempdir or '.', 'skview_passes')
    os.makedirs(work, exist_ok=True)
    ng = bpy.data.node_groups.new('SKComp', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    rl = ng.nodes.new('CompositorNodeRLayers')
    fo = ng.nodes.new('CompositorNodeOutputFile')
    fo.directory = work + os.sep
    fo.file_name = 'p_'
    fo.format.file_format = 'OPEN_EXR'
    fo.format.color_depth = '32'
    fo.file_output_items.new('RGBA', 'rgba')
    fo.file_output_items.new('FLOAT', 'depth')
    ng.links.new(rl.outputs['Image'], fo.inputs['rgba'])
    ng.links.new(rl.outputs['Depth'], fo.inputs['depth'])
    out = ng.nodes.new('NodeGroupOutput')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.links.new(rl.outputs['Image'], out.inputs[0])
    sc.render.filepath = os.path.join(work, 'beauty.png')
    return work


def _load(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)


# ----------------------------------------------------------------------------- post (numpy, three.js maths)
def _blur1(a, r, axis):
    sig = float(r)
    w = np.array([0.39894 * math.exp(-0.5 * i * i / (sig * sig)) / sig for i in range(r)], np.float32)
    acc = a * w[0]
    tot = w[0]
    n = a.shape[axis]
    for i in range(1, r):
        s1 = np.take(a, np.clip(np.arange(n) + i, 0, n - 1), axis=axis)
        s2 = np.take(a, np.clip(np.arange(n) - i, 0, n - 1), axis=axis)
        acc = acc + (s1 + s2) * w[i]
        tot += 2 * w[i]
    return acc / tot


def _down(a):
    h, w = a.shape[:2]
    h2, w2 = max(1, h // 2), max(1, w // 2)
    a = a[:h2 * 2, :w2 * 2]
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def _up(a, h, w):
    ys = (np.arange(h) + 0.5) * a.shape[0] / h - 0.5
    xs = (np.arange(w) + 0.5) * a.shape[1] / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, a.shape[0] - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, a.shape[1] - 1)
    y1 = np.clip(y0 + 1, 0, a.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, a.shape[1] - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    r0 = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    r1 = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return r0 * (1 - fy) + r1 * fy


def bloom(c, strength, threshold, radius=0.55):
    lum = c @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    al = np.clip((lum - threshold) / 0.01, 0, 1)
    al = al * al * (3 - 2 * al)
    hi = c * al[..., None]
    h, w = c.shape[:2]
    cur = _down(hi)
    facs = [1.0, 0.8, 0.6, 0.4, 0.2]
    comp = np.zeros_like(cur)
    H0, W0 = cur.shape[:2]
    for i, r in enumerate((3, 5, 7, 9, 11)):
        if i > 0:
            cur = _down(cur)
        cur = _blur1(_blur1(cur, r, 1), r, 0)
        f = facs[i] * (1 - radius) + (1.2 - facs[i]) * radius
        comp += f * _up(cur, H0, W0)
    return c + strength * _up(comp, h, w)


def aces_three(c, exposure):
    c = c * (exposure / 0.6)
    Mi = np.array([[0.59719, 0.35458, 0.04823], [0.07600, 0.90834, 0.01566], [0.02840, 0.13383, 0.83777]], np.float32)
    Mo = np.array([[1.60475, -0.53108, -0.07367], [-0.10208, 1.10813, -0.00605], [-0.00327, -0.07276, 1.07602]], np.float32)
    v = c @ Mi.T
    a = v * (v + 0.0245786) - 0.000090537
    b = v * (0.983729 * v + 0.4329510) + 0.238081
    v = (a / b) @ Mo.T
    return np.clip(v, 0, 1)


def srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055)


def grade(c, sat=1.08, contrast=1.06, vignette=0.32):
    h, w = c.shape[:2]
    l = c @ np.array([0.299, 0.587, 0.114], np.float32)
    c = l[..., None] + (c - l[..., None]) * sat
    c = (c - 0.5) * contrast + 0.5
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5) / w - 0.5
    v = (yy + 0.5) / h - 0.5
    d = np.sqrt((u * 1.25) ** 2 + v ** 2)
    t = np.clip((d - 0.85) / (0.2 - 0.85), 0, 1)
    t = t * t * (3 - 2 * t)
    c = c * ((1 - vignette) + vignette * t)[..., None]
    return np.clip(c, 0, 1)


def sky_image(S, cam, w, h):
    """The game's gradient sky dome (radius 180 at the origin, fog off) as seen through cam (linear RGB)."""
    top, mid, bot = (hexlin(S['sky'][k]) for k in ('top', 'mid', 'bottom'))
    sd = np.array(S['sun']['dir'], np.float64)
    sd = sd / np.linalg.norm(sd)
    scol = hexlin(S['sun']['color'])
    cd = cam.data
    fy = math.tan(cd.angle_y / 2)
    fx = fy * w / h
    yy, xx = np.mgrid[0:h, 0:w]
    px = ((xx + 0.5) / w * 2 - 1) * fx
    py = (1 - (yy + 0.5) / h * 2) * fy
    R = np.array(cam.matrix_world.to_3x3())
    dirs = np.stack([px, py, -np.ones_like(px)], -1) @ R.T          # Blender world
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    C = np.array(cam.matrix_world.translation)
    b = (dirs * C).sum(-1)
    cc = (C * C).sum() - 180.0 ** 2
    t = -b + np.sqrt(np.maximum(b * b - cc, 0))
    P = C + dirs * t[..., None]
    vD = P / np.linalg.norm(P, axis=-1, keepdims=True)
    vg = np.stack([vD[..., 0], vD[..., 2], -vD[..., 1]], -1)       # -> glTF axes
    y = vg[..., 1]
    upc = mid + (top - mid) * (np.maximum(y, 0) ** 0.6)[..., None]
    dnc = mid + (bot - mid) * (np.maximum(-y, 0) ** 0.5)[..., None]
    c = np.where((y > 0)[..., None], upc, dnc)
    s = np.maximum((vg * sd).sum(-1), 0)
    c = c + scol * (np.power(s, 400) * 3 + np.power(s, 12) * 0.35)[..., None]
    return c.astype(np.float32)


def finish_frame(S, cam, work, out_path, quality=92):
    rgba = _load(os.path.join(work, 'p_rgba.exr'))[::-1]
    depth = _load(os.path.join(work, 'p_depth.exr'))[::-1, :, 0]
    h, w = depth.shape
    a = np.clip(rgba[..., 3:4], 0, 1)
    col = rgba[..., :3]
    fog = S['fog']
    fc = hexlin(fog['color']).astype(np.float32)
    f = np.clip((depth - fog['near']) / (fog['far'] - fog['near']), 0, 1)
    f = (f * f * (3 - 2 * f))[..., None]
    surf = col * (1 - f) + fc * f * a
    sky = sky_image(S, cam, w, h)
    img = surf + sky * (1 - a)
    b = S['bloom']
    img = bloom(img, b[0], b[1])
    img = srgb(aces_three(img, S['exposure']))
    gr = S.get('grade', {})
    img = grade(img, sat=gr.get('sat', 1.08))
    out = bpy.data.images.new('out', w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = img[::-1]
    out.pixels.foreach_set(px.ravel())
    sc = bpy.context.scene
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = quality
    out.filepath_raw = out_path
    out.file_format = 'JPEG'
    # pixels are display-referred already: save without another transform
    out.colorspace_settings.name = 'Non-Color'
    out.save()
    bpy.data.images.remove(out)
    print('PREVIEW', out_path)


def render_view(S, cam, work, out_path, pos_gl, look_gl):
    place_camera(cam, pos_gl, look_gl)
    t0 = time.time()
    bpy.ops.render.render(write_still=False)
    finish_frame(S, cam, work, out_path)
    print('  %.1fs' % (time.time() - t0))


def run(sid, glb=None, extra=False, res=(1280, 720), samples=64, stage_json=None, out_dir=None):
    sdir = os.path.join(JB, 'art', 'stages', sid)
    S = _defaults(json.load(open(stage_json or os.path.join(sdir, 'stage.json'))))
    glb = glb or os.path.join(JB, 'art', '_work', 'stages', sid, sid + '_src.glb')
    reset()
    work = setup_render(res, samples)
    objs = import_glb(glb)
    for o in objs:
        if o.type == 'MESH' and 'noshadow' in o.name:
            o.visible_shadow = False
    world(S)
    lights(S)
    capsules()
    cam = camera((0, 1.5, 9.5), (0, 1.0, 0))
    prev = out_dir or os.path.join(sdir, 'previews')
    os.makedirs(prev, exist_ok=True)
    render_view(S, cam, work, os.path.join(prev, 'game.jpg'), (0, 1.5, 9.5), (0, 1.0, 0))
    render_view(S, cam, work, os.path.join(prev, 'wide.jpg'), (0, 2.5, 16), (0, 2, -10))
    if extra:
        wk = os.path.join(JB, 'art', '_work', 'stages', sid)
        for name, p, l in (('far_left', (-2.4, 2.4, 11.5), (-2.4, 1.6, 0)),
                           ('near_right', (4.3, 1.3, 7.4), (4.3, 1.05, 0)),
                           ('near_left', (-4.3, 1.3, 7.4), (-4.3, 1.05, 0))):
            render_view(S, cam, work, os.path.join(wk, 'view_%s.jpg' % name), p, l)


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    sid = a[0]
    glb = a[a.index('--glb') + 1] if '--glb' in a else None
    res = tuple(int(v) for v in a[a.index('--res') + 1].split('x')) if '--res' in a else (1280, 720)
    out = a[a.index('--out') + 1] if '--out' in a else None
    run(sid, glb, extra='--extra' in a, res=res, out_dir=out)

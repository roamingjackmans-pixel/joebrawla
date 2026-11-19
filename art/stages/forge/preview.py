"""Stage previews: EEVEE render of <id>_src.glb lit from stage.json, then a three.js-like post in numpy
(gradient sky dome behind, linear fog with smoothstep, UnrealBloom-style bloom, exposure, ACES filmic as in
three.js, sRGB). Writes art/stages/<id>/previews/game.jpg (game camera + two 1.8 m grey capsules) and wide.jpg.

blender -b --factory-startup --python preview.py -- <id> [--extra]
"""
import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import texgen as tg  # noqa: E402

JB = r"C:\dev\JoeBrawla"
W, H = 1280, 720


def t2b(v):
    """three.js / glTF (x, y, z) -> Blender (x, -z, y)."""
    return Vector((v[0], -v[2], v[1]))


def lin(hx):
    return tg.s2l(tg.hexrgb(hx))


def setup_world(cfg):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('PreviewWorld')
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs[1].default_value = -0.08
    mr.inputs[2].default_value = 0.08
    nt.links.new(sep.outputs['Z'], mr.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    hemi = cfg['hemi']
    k = hemi['intensity'] / math.pi
    sky = lin(hemi['sky']) * k
    gnd = lin(hemi['ground']) * k
    ins = {s.identifier: s for s in mix.inputs}
    nt.links.new(mr.outputs[0], ins['Factor_Float'])
    ins['A_Color'].default_value = (*gnd, 1)
    ins['B_Color'].default_value = (*sky, 1)
    res = [s for s in mix.outputs if s.identifier == 'Result_Color'][0]
    nt.links.new(res, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs[0])


def sun_lamp(name, direction_three, color, strength, shadow=True, angle=2.0):
    sc = bpy.context.scene
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.color = tuple(lin(color))
    ld.angle = math.radians(angle)
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    d = t2b(direction_three).normalized()
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return ob


def camera(pos_three, look_three, fov=30.0):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get('PCam') or bpy.data.cameras.new('PCam')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov)
    cd.clip_start = 0.1
    cd.clip_end = 600
    co = bpy.data.objects.get('PCam') or bpy.data.objects.new('PCam', cd)
    if co.name not in sc.collection.objects:
        sc.collection.objects.link(co)
    sc.camera = co
    p = t2b(pos_three)
    t = t2b(look_three)
    co.location = p
    co.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
    return co


def capsules():
    m = bpy.data.materials.new('capsule')
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.32, 0.32, 0.33, 1)
    b.inputs['Roughness'].default_value = 0.55
    obs = []
    for x in (-1.5, 1.5):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.26, segments=24, ring_count=12, location=(x, 0, 0.26))
        a = bpy.context.active_object
        bpy.ops.mesh.primitive_cylinder_add(radius=0.26, depth=1.8 - 0.52, vertices=24, location=(x, 0, 0.9))
        c = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.26, segments=24, ring_count=12, location=(x, 0, 1.8 - 0.26))
        t = bpy.context.active_object
        for o in (a, c, t):
            o.data.materials.append(m)
            o.data.shade_smooth()
            obs.append(o)
    return obs


def render_exr(path):
    sc = bpy.context.scene
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    a = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(H, W, 4)


def depth_override():
    m = bpy.data.materials.new('depth')
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    cam = nt.nodes.new('ShaderNodeCameraData')
    nt.links.new(cam.outputs['View Z Depth'], em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def view_dirs(cam):
    """Per-pixel world view directions (three.js coords) for the sky dome."""
    cd = cam.data
    th = math.tan(cd.angle_y / 2)
    tw = th * W / H
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    px = ((xs + 0.5) / W * 2 - 1) * tw
    py = ((ys + 0.5) / H * 2 - 1) * th  # image rows from the bottom (Blender pixel order)
    R = np.array(cam.matrix_world.to_3x3(), np.float32)
    d = np.stack([px, py, -np.ones_like(px)], -1) @ R.T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    # Blender -> three: (x, z, -y)
    return np.stack([d[..., 0], d[..., 2], -d[..., 1]], -1)


def sky_dome(cfg, dirs):
    sk = cfg['sky']
    top, mid, bot = lin(sk['top']), lin(sk['mid']), lin(sk['bottom'])
    y = dirs[..., 1:2]
    up = mid + (top - mid) * np.power(np.clip(y, 0, 1), 0.6)
    dn = mid + (bot - mid) * np.power(np.clip(-y, 0, 1), 0.5)
    c = np.where(y > 0, up, dn)
    sd = np.array(cfg['sun']['dir'], np.float32)
    sd /= np.linalg.norm(sd)
    s = np.clip((dirs * sd).sum(-1, keepdims=True), 0, 1)
    sc = lin(cfg['sun']['color'])
    c = c + sc * (np.power(s, 400.0) * 3.0 + np.power(s, 12.0) * 0.35) * float(cfg.get('sky_sun', 1.0))
    return c.astype(np.float32)


def _blur_axis(a, sigma, axis):
    if sigma <= 0:
        return a
    r = max(1, int(sigma * 3))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    ap = np.pad(a, pad, mode='edge')
    out = np.zeros_like(a)
    n = a.shape[axis]
    for i, kv in enumerate(k):
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(i, i + n)
        out += ap[tuple(sl)] * kv
    return out


def gblur(a, sigma):
    return _blur_axis(_blur_axis(a, sigma, 0), sigma, 1)


def down2(a):
    h, w = a.shape[:2]
    h2, w2 = h // 2 * 2, w // 2 * 2
    a = a[:h2, :w2]
    return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) * 0.25


def up_to(a, h, w):
    ys = (np.arange(h) + 0.5) / h * a.shape[0] - 0.5
    xs = (np.arange(w) + 0.5) / w * a.shape[1] - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, a.shape[0] - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, a.shape[1] - 1)
    y1 = np.clip(y0 + 1, 0, a.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, a.shape[1] - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    A = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    B = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return A * (1 - fy) + B * fy


def bloom(img, strength, threshold, radius=0.4):
    """three.js UnrealBloomPass approximation (5 mips at half res, kernels 3,5,7,9,11)."""
    L = img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114
    a = tg.smooth(threshold, threshold + 0.01, L)[..., None]
    hp = img * a
    lvl = down2(hp)
    acc = np.zeros_like(img)
    factors = [1.0, 0.8, 0.6, 0.4, 0.2]
    for i, ks in enumerate((3, 5, 7, 9, 11)):
        b = gblur(lvl, ks / 2.0)
        f = factors[i] * (1 - radius) + (1.2 - factors[i]) * radius
        acc += up_to(b, img.shape[0], img.shape[1]) * f
        lvl = down2(b)
    return img + acc * strength


def aces_three(c, exposure):
    c = c * exposure / 0.6
    Min = np.array([[0.59719, 0.35458, 0.04823], [0.07600, 0.90834, 0.01566], [0.02840, 0.13383, 0.83777]], np.float32)
    Mout = np.array([[1.60475, -0.53108, -0.07367], [-0.10208, 1.10813, -0.00605], [-0.00327, -0.07276, 1.07602]], np.float32)
    c = c @ Min.T
    a = c * (c + 0.0245786) - 0.000090537
    b = c * (0.983729 * c + 0.4329510) + 0.238081
    c = a / b
    c = c @ Mout.T
    return np.clip(c, 0, 1)


def post(cfg, rgba, depth, cam):
    rgb = rgba[..., :3]
    al = np.clip(rgba[..., 3:4], 0, 1)
    fog = cfg['fog']
    z = depth[..., 0:1]
    f = tg.smooth(fog['near'], fog['far'], z)
    fc = lin(fog['color'])
    rgb = rgb * (1 - f) + fc * f * al
    sky = sky_dome(cfg, view_dirs(cam))
    img = rgb + sky * (1 - al)
    bl = cfg.get('bloom', [0.6, 0.85])
    img = bloom(img, bl[0], bl[1], bl[2] if len(bl) > 2 else 0.4)
    img = aces_three(img, cfg.get('exposure', 1.0))
    return tg.l2s(img)


def save_jpg(rgb, path):
    a = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,), np.float32)], -1)
    im = bpy.data.images.new('out', W, H, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'sRGB'
    im.pixels.foreach_set(np.clip(a, 0, 1).ravel())
    im.filepath_raw = path
    im.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 92
    im.save(quality=92) if 'quality' in im.save.__doc__ else im.save()
    bpy.data.images.remove(im)


def save_jpg2(rgb, path):
    """Save through the render pipeline settings (reliable JPEG quality)."""
    sc = bpy.context.scene
    a = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,), np.float32)], -1)
    im = bpy.data.images.new('out', W, H, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'sRGB'
    im.pixels.foreach_set(np.clip(a, 0, 1).ravel())
    s = sc.render.image_settings
    s.file_format = 'JPEG'
    s.color_mode = 'RGB'
    s.quality = 92
    im.save_render(path, scene=sc)
    bpy.data.images.remove(im)


def render(sid, extra=False, src=None, shots=None):
    sdir = os.path.join(JB, 'art', 'stages', sid)
    work = os.path.join(JB, 'art', '_work', 'stages', sid)
    cfg = json.load(open(os.path.join(sdir, 'stage.json')))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=src or os.path.join(work, f'{sid}_src.glb'))
    for o in sc.objects:
        if o.type == 'MESH' and 'noshadow' in o.name:
            o.visible_shadow = False
    sc.render.engine = 'BLENDER_EEVEE'
    ee = sc.eevee
    ee.taa_render_samples = 48
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 8
    ee.use_raytracing = False
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    setup_world(cfg)
    s = cfg['sun']
    sun_lamp('Sun', s['dir'], s['color'], s['intensity'], True, angle=1.5)
    rim = cfg['rim']
    ri = cfg.get('rim_intensity', [2.0, 1.6])
    # the game's rim lights sit behind the fighters at (-7, 4, -6) and (7, 3, -6), shining toward the origin
    sun_lamp('RimA', (-7, 4, -6), rim[0], ri[0], False)
    sun_lamp('RimB', (7, 3, -6), rim[1], ri[1], False)
    caps = capsules()
    shots = shots or [('game', (0, 1.5, 9.5), (0, 1.0, 0), True), ('wide', (0, 2.5, 16), (0, 2, -10), False)]
    if extra:
        shots += [('game_left', (-6.0, 1.5, 9.5), (-6.0, 1.0, 0), True), ('game_right', (6.0, 1.5, 9.5), (6.0, 1.0, 0), True),
                  ('game_high', (0, 2.5, 11.5), (0, 1.0, 0), True)]
    dm = depth_override()
    outs = []
    for name, pos, look, show_caps in shots:
        for c in caps:
            c.hide_render = not show_caps
        cam = camera(pos, look)
        sc.view_layers[0].material_override = None
        rgba = render_exr(os.path.join(work, f'_prev_{name}_rgba.exr'))
        sc.view_layers[0].material_override = dm
        dep = render_exr(os.path.join(work, f'_prev_{name}_depth.exr'))
        sc.view_layers[0].material_override = None
        img = post(cfg, rgba, dep, cam)
        d = os.path.join(sdir, 'previews') if name in ('game', 'wide') else os.path.join(work, 'previews')
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f'{name}.jpg')
        save_jpg2(img, p)
        outs.append(p)
        print('PREVIEW', p, flush=True)
    return outs


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    render(a[0], extra='--extra' in a)

"""Class face / skin textures for the UBC bodies (and eye colours).

blender -b --factory-startup --python build_faces.py -- [--classes knight,brute] [--size 2048] [--look]

Each class gets a full body base-colour texture: the stock texture's detail re-toned to the class skin colour,
plus face character painted with 3D masks placed from the body's face landmarks (stubble, freckles, wrinkles,
eye bags, scars, war paint, kohl, lip tint ...), baked into the body's own UVs. Output (JPEG q92):
  assets/custom/characters/faces/skin_<class>.jpg      assets/custom/characters/eyes/T_Eye_<colour>.png
"""
import bpy, sys, os, math, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agcore as C
import djlib as dj
from djlib import NB, srgb
from mathutils import Vector

TEX = r"C:\dev\AverageJoe\_downloads\quaternius-universal-base-characters\x\Universal Base Characters[Standard]\Base Characters\Textures"
BASE = {'m': TEX + r"\T_Superhero_Male_Dark.png", 'f': TEX + r"\T_Superhero_Female_Dark_BaseColor.png"}
MEAN = {'m': (0.648, 0.451, 0.315), 'f': (0.66, 0.463, 0.321)}       # mean skin sRGB of the stock textures
OUT_FACES = os.path.join(C.OUT_CHAR, 'faces')
OUT_EYES = os.path.join(C.OUT_CHAR, 'eyes')
os.makedirs(OUT_FACES, exist_ok=True)
os.makedirs(OUT_EYES, exist_ok=True)

# class -> sex, skin (sRGB of the average skin), features
FACES = {
    'knight':    dict(sex='m', skin='#b27c58', feats=[('stubble', '#3a2414', 0.55), ('scar', 'chin', 0.7), ('rosy', 0.12)]),
    'brute':     dict(sex='m', skin='#6e4029', feats=[('stubble', '#120a06', 0.8), ('broken_nose', 0.8), ('scar', 'brow_l', 1.0),
                                                      ('eyebags', 0.35)]),
    'duelist':   dict(sex='f', skin='#c48c6a', feats=[('kohl', '#160c10', 0.85), ('lips', '#8e2836', 0.6), ('mole', 'cheek_r', 1.0),
                                                      ('rosy', 0.15)]),
    'scholar':   dict(sex='f', skin='#d6a585', feats=[('freckles', '#8a4a2a', 0.65), ('eyebags', 0.3), ('ink', 0.8),
                                                      ('rosy', 0.22)]),
    'cleric':    dict(sex='m', skin='#a8704c', feats=[('wrinkles', 0.85), ('stubble', '#d8d4cc', 0.5), ('rosy', 0.35),
                                                      ('agespots', 0.6), ('eyebags', 0.45)]),
    'spearman':  dict(sex='f', skin='#86563a', feats=[('scar', 'nose', 0.8), ('lips', '#5e2a22', 0.35), ('rosy', 0.08)]),
    'hunter':    dict(sex='f', skin='#c99470', feats=[('freckles', '#7a3c1e', 0.8), ('mud', '#3e4426', 0.75), ('sunburn', 0.25)]),
    'nobody':    dict(sex='m', skin='#b98864', feats=[('stubble', '#2e1e12', 0.6), ('eyebags', 0.65), ('sunburn', 0.3)]),
    'berserker': dict(sex='m', skin='#d4a282', feats=[('woad', '#1f3f86', 0.85), ('stubble', '#8a3a14', 0.55), ('rosy', 0.3),
                                                      ('scar', 'cheek_l', 0.8)]),
    'occultist': dict(sex='m', skin='#b4a08e', feats=[('eyebags', 0.9), ('runes', '#5a1f9a', 0.85), ('sunken', 0.6),
                                                      ('lips', '#6a4a52', 0.4), ('stubble', '#1a0e18', 0.3)]),
}
EYES = {'brown': None, 'blue': (0.58, 1.1), 'green': (0.33, 0.9), 'grey': (0.58, 0.15), 'amber': (0.09, 1.15),
        'violet': (0.76, 1.0), 'hazel': (0.15, 0.8)}


def lin(c):
    return srgb(c)[:3]


def build_material(body, info, base_img):
    L = body.L
    m = bpy.data.materials.new('FACE')
    nb = NB(m)
    tex = nb.node('ShaderNodeTexImage')
    tex.image = base_img
    uvn = nb.node('ShaderNodeUVMap')
    uvn.uv_map = body.mesh.data.uv_layers[0].name
    nb.link(uvn.outputs[0], tex.inputs[0])
    mean = srgb(MEAN[info['sex']])
    tgt = srgb(info['skin'])
    gain = tuple(min(3.0, t / max(mv, 1e-3)) for t, mv in zip(tgt[:3], mean[:3]))
    bw = nb.node('ShaderNodeRGBToBW')
    nb.link(tex.outputs['Color'], bw.inputs[0])
    skin_k = nb.mr(bw.outputs[0], 0.06, 0.16, 0.0, 1.0)
    c = nb.mix(skin_k, tex.outputs['Color'], nb.mix(1.0, tex.outputs['Color'], (gain[0], gain[1], gain[2], 1.0), 'MULTIPLY'))
    co = nb.coord('Object')
    el, er = L['eye_l'], L['eye_r']
    nose, chin = L['nose'], L['chin']
    mouth = Vector((0, nose.y + 0.028, (nose.z + chin.z) * 0.5 + 0.006))
    eye_z = (el.z + er.z) * 0.5

    def ell(cen, r, rot=(0, 0, 0), soft=0.4):
        d = nb.vmath('SUBTRACT', co, tuple(cen))
        if any(rot):
            d = nb.mapping(d, rot=rot)
        d = nb.mapping(d, scale=(1 / r[0], 1 / r[1], 1 / r[2]))
        ln = nb.vmath('LENGTH', d)
        return nb.mr(ln, 1.0 - soft, 1.0, 1.0, 0.0)

    def union(*ms):
        out = ms[0]
        for x in ms[1:]:
            out = nb.mx(out, x)
        return out

    def front(margin=0.0):
        # only the face side (y in front of the ears)
        y = nb.sep(co)[1]
        return nb.mr(y, L['eye_l'].y + 0.045 + margin, L['eye_l'].y + 0.02 + margin, 0.0, 1.0)

    def paint(c, mask, col, alpha=1.0, blend='MIX'):
        return nb.mix(nb.mul(mask, alpha), c, srgb(col) if isinstance(col, str) else col, blend)

    rough_add = None
    for f in info['feats']:
        k = f[0]
        if k == 'stubble':
            col, a = f[1], f[2]
            reg = union(ell((0, chin.y + 0.012, chin.z + 0.01), (0.04, 0.034, 0.032)),
                        ell((0.052, chin.y + 0.05, chin.z + 0.035), (0.026, 0.05, 0.05)),
                        ell((-0.052, chin.y + 0.05, chin.z + 0.035), (0.026, 0.05, 0.05)),
                        ell((0, nose.y + 0.024, nose.z - 0.021), (0.03, 0.02, 0.011)),
                        ell((0.04, nose.y + 0.045, nose.z - 0.024), (0.022, 0.03, 0.026)),
                        ell((-0.04, nose.y + 0.045, nose.z - 0.024), (0.022, 0.03, 0.026)),
                        ell((0, chin.y + 0.05, chin.z - 0.02), (0.045, 0.04, 0.03)))
            lips = ell(tuple(mouth), (0.021, 0.02, 0.0075), soft=0.3)
            reg = nb.mul(reg, nb.inv(lips))
            dots = nb.mr(nb.voronoi(co, 1400.0, 'F1', out='Distance'), 0.32, 0.18, 0.0, 1.0)
            st = nb.add(nb.mul(dots, 0.6), 0.4)
            c = paint(c, nb.mul(reg, st), col, a)
        elif k == 'freckles':
            col, a = f[1], f[2]
            reg = union(ell((0, nose.y + 0.02, nose.z + 0.012), (0.03, 0.03, 0.022)),
                        ell((0.04, el.y + 0.004, eye_z - 0.028), (0.026, 0.03, 0.02)),
                        ell((-0.04, er.y + 0.004, eye_z - 0.028), (0.026, 0.03, 0.02)))
            v = nb.voronoi(co, 520.0, 'F1', out='Distance')
            rnd = nb.voronoi(co, 520.0, 'F1', out='Color')
            sel = nb.mr(nb.sep(rnd)[0], 0.45, 0.55, 0.0, 1.0)
            dots = nb.mul(nb.mr(v, 0.3, 0.15, 0.0, 1.0), sel)
            c = paint(c, nb.mul(reg, dots), col, a)
        elif k == 'wrinkles':
            a = f[1]
            fh = ell((0, el.y + 0.012, eye_z + 0.05), (0.05, 0.04, 0.022))
            lines = nb.mr(nb.wave(co, 170.0, 1.5, 2.0, 'BANDS', 'Z'), 0.82, 1.0, 0.0, 1.0)
            c = paint(c, nb.mul(fh, lines), '#5a3424', 0.45 * a)
            for sx in (1, -1):
                cf = ell((sx * 0.062, el.y + 0.03, eye_z - 0.002), (0.016, 0.03, 0.014))
                rays = nb.mr(nb.wave(nb.mapping(co, rot=(0, 1.2 * sx, 0)), 260.0, 2.0, 2.0, 'BANDS', 'X'), 0.8, 1.0, 0.0, 1.0)
                c = paint(c, nb.mul(cf, rays), '#5a3424', 0.4 * a)
                nl = ell((sx * 0.03, nose.y + 0.03, (nose.z + mouth.z) * 0.5 - 0.004), (0.006, 0.03, 0.026),
                         rot=(0, 0.35 * sx, 0))
                c = paint(c, nl, '#4a2a1a', 0.45 * a)
        elif k == 'eyebags':
            a = f[1]
            for e in (el, er):
                bag = ell((e.x, e.y + 0.004, e.z - 0.017), (0.017, 0.02, 0.0085))
                c = paint(c, bag, '#5a3a40', 0.45 * a)
        elif k == 'kohl':
            col, a = f[1], f[2]
            for e, sx in ((el, 1), (er, -1)):
                ring = nb.mul(ell((e.x, e.y + 0.002, e.z), (0.019, 0.022, 0.0115), soft=0.25),
                              nb.inv(ell((e.x, e.y + 0.002, e.z), (0.0155, 0.022, 0.0085), soft=0.3)))
                wing = ell((e.x + sx * 0.019, e.y + 0.008, e.z + 0.004), (0.008, 0.02, 0.0025), rot=(0, -0.4 * sx, 0))
                c = paint(c, nb.mx(ring, wing), col, a)
        elif k == 'lips':
            col, a = f[1], f[2]
            c = paint(c, ell(tuple(mouth), (0.02, 0.02, 0.0075), soft=0.45), col, a)
        elif k == 'mole':
            pos = (-0.035, nose.y + 0.04, nose.z - 0.028) if f[1] == 'cheek_r' else (0.035, nose.y + 0.04, nose.z - 0.028)
            c = paint(c, ell(pos, (0.0022, 0.01, 0.0022), soft=0.4), '#2a1610', f[2])
        elif k == 'rosy':
            a = f[1]
            for sx in (1, -1):
                c = paint(c, ell((sx * 0.042, el.y + 0.01, eye_z - 0.034), (0.024, 0.03, 0.02), soft=0.9), '#c0504a', a)
            c = paint(c, ell((0, nose.y + 0.005, nose.z + 0.002), (0.012, 0.02, 0.012), soft=0.8), '#c0504a', a)
        elif k == 'sunburn':
            a = f[1]
            c = paint(c, ell((0, nose.y + 0.01, nose.z + 0.01), (0.04, 0.03, 0.018), soft=0.9), '#c8503c', a)
        elif k == 'agespots':
            a = f[1]
            reg = union(ell((0.045, el.y + 0.02, eye_z + 0.04), (0.03, 0.04, 0.025)),
                        ell((-0.05, er.y + 0.03, eye_z - 0.03), (0.02, 0.04, 0.02)))
            sp = nb.mr(nb.voronoi(co, 140.0, 'F1', out='Distance'), 0.25, 0.1, 0.0, 1.0)
            c = paint(c, nb.mul(reg, sp), '#6a4026', 0.5 * a)
        elif k == 'scar':
            where, a = f[1], f[2]
            if where == 'chin':
                cen, r, rot = (0.012, chin.y + 0.006, chin.z + 0.008), (0.0025, 0.03, 0.014), (0, 0.4, 0)
            elif where == 'brow_l':
                cen, r, rot = (el.x + 0.004, el.y - 0.004, el.z + 0.017), (0.003, 0.03, 0.02), (0, 0.25, 0)
            elif where == 'nose':
                cen, r, rot = (0.0, nose.y + 0.018, nose.z + 0.02), (0.035, 0.03, 0.0028), (0, 0.25, 0)
            else:
                cen, r, rot = (el.x + 0.006, el.y + 0.02, el.z - 0.03), (0.0028, 0.03, 0.022), (0, -0.5, 0)
            core = ell(cen, r, rot, soft=0.5)
            halo = ell(cen, (r[0] * 2.6, r[1], r[2] * 1.15), rot, soft=0.6)
            c = paint(c, halo, '#8a4a3a', 0.35 * a)
            c = paint(c, core, '#e0b0a0', 0.75 * a)
        elif k == 'broken_nose':
            a = f[1]
            c = paint(c, ell((0.004, nose.y + 0.016, nose.z + 0.024), (0.009, 0.02, 0.012), soft=0.7), '#7a3a2a', 0.5 * a)
        elif k == 'woad':
            col, a = f[1], f[2]
            z = nb.sep(co)[2]
            band = nb.mul(nb.mr(z, eye_z - 0.02, eye_z - 0.012, 0.0, 1.0), nb.mr(z, eye_z + 0.016, eye_z + 0.024, 1.0, 0.0))
            band = nb.mul(band, front(-0.01))
            edge = nb.mr(nb.noise(co, 90.0, 4, 0.6), 0.35, 0.55, 0.0, 1.0)
            c = paint(c, nb.mul(band, nb.add(0.55, nb.mul(edge, 0.45))), col, a)
            for sx in (-0.016, 0.0, 0.016):
                st = ell((sx, chin.y + 0.006, chin.z + 0.004), (0.0035, 0.03, 0.02), soft=0.4)
                c = paint(c, st, col, a)
        elif k == 'mud':
            col, a = f[1], f[2]
            z = nb.sep(co)[2]
            zc = eye_z - 0.026
            band = nb.mul(nb.mr(z, zc - 0.012, zc - 0.004, 0.0, 1.0), nb.mr(z, zc + 0.004, zc + 0.012, 1.0, 0.0))
            band = nb.mul(band, nb.mul(front(), nb.inv(ell((0, nose.y + 0.01, nose.z + 0.01), (0.012, 0.03, 0.03)))))
            n = nb.mr(nb.noise(co, 60.0, 5, 0.7), 0.4, 0.6, 0.3, 1.0)
            c = paint(c, nb.mul(band, n), col, a)
        elif k == 'ink':
            a = f[1]
            c = paint(c, ell((0.045, el.y + 0.02, eye_z - 0.045), (0.008, 0.03, 0.004), (0, -0.3, 0), soft=0.7), '#1a2040', 0.6 * a)
        elif k == 'runes':
            col, a = f[1], f[2]
            for e in (el, er):
                m1 = ell((e.x, e.y + 0.004, e.z - 0.026), (0.0016, 0.02, 0.009), soft=0.3)
                m2 = ell((e.x - 0.006, e.y + 0.004, e.z - 0.022), (0.002, 0.02, 0.002), soft=0.3)
                m3 = ell((e.x + 0.006, e.y + 0.004, e.z - 0.022), (0.002, 0.02, 0.002), soft=0.3)
                c = paint(c, union(m1, m2, m3), col, a)
        elif k == 'sunken':
            a = f[1]
            for sx in (1, -1):
                c = paint(c, ell((sx * 0.048, nose.y + 0.05, nose.z - 0.02), (0.016, 0.03, 0.026), soft=0.9), '#5a4446', 0.4 * a)
    nb.finish(c, 0.55, 0.0, None)
    return m


def bake(body, mat, size, name):
    me = body.mesh.data
    me.uv_layers.active_index = 0
    orig = list(me.materials)
    me.materials.clear()
    me.materials.append(mat)
    img = dj.new_image(name, size, False)
    t = mat.node_tree.nodes.new('ShaderNodeTexImage')
    t.image = img
    mat.node_tree.nodes.active = t
    dj.set_channel([mat], 'color')
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = o is not body.mesh
    dj.deselect_all()
    body.mesh.select_set(True)
    bpy.context.view_layer.objects.active = body.mesh
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    dj.gpu_setup(4)
    sc.render.bake.margin = 8
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=False, margin=8, use_clear=True, target='IMAGE_TEXTURES')
    dj.set_channel([mat], 'bsdf')
    mat.node_tree.nodes.remove(t)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = False
    return img


def save_jpg(img, path, q=92):
    img.file_format = 'JPEG'
    try:
        img.save(filepath=path, quality=q)
    except TypeError:
        img.filepath_raw = path
        img.save()


def eye_textures():
    src = bpy.data.images.load(os.path.join(C.UBC, 'bodies', 'T_Eye_Brown.png'))
    w, h = src.size
    px = np.array(src.pixels[:], dtype=np.float32).reshape(h, w, 4)
    import colorsys
    for name, hs in EYES.items():
        out = px.copy()
        if hs:
            hue, sat = hs
            rgb = out[..., :3]
            mx = rgb.max(-1)
            mn = rgb.min(-1)
            s = (mx - mn) / np.maximum(mx, 1e-4)
            iris = (s > 0.25) & (mx < 0.85)
            for (y, x) in zip(*np.nonzero(iris)):
                r, g, b = rgb[y, x]
                H, S, V = colorsys.rgb_to_hsv(r, g, b)
                r2, g2, b2 = colorsys.hsv_to_rgb(hue, min(1.0, S * sat), min(1.0, V * 1.15))
                rgb[y, x] = (r2, g2, b2)
        img = bpy.data.images.new('eye_' + name, w, h, alpha=True)
        img.pixels = out.ravel()
        img.filepath_raw = os.path.join(OUT_EYES, 'T_Eye_%s.png' % name.capitalize())
        img.file_format = 'PNG'
        img.save()
    dj.log('eyes written')


if __name__ == '__main__':
    a = C.args()
    classes = C.opt(a, '--classes', ','.join(FACES)).split(',')
    size = int(C.opt(a, '--size', '2048'))
    if '--eyes' in a:
        dj.reset()
        eye_textures()
    for cid in classes:
        info = FACES[cid]
        dj.reset()
        body = C.Body(info['sex'])
        base = bpy.data.images.load(BASE[info['sex']])
        mat = build_material(body, info, base)
        img = bake(body, mat, size, 'skin_' + cid)
        out = os.path.join(OUT_FACES, 'skin_%s.jpg' % cid)
        save_jpg(img, out)
        dj.log('face', cid, out, '%.2f MB' % (os.path.getsize(out) / 1e6))

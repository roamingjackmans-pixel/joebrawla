"""The Mossy Crypt (B1) - JoeBrawla stage. Graveyard valley in morning sun.

blender -b --factory-startup --python art/stages/crypt/build_crypt.py [-- --no-export]
  -> art/_work/stages/crypt/crypt_src.glb -> (tools/assets.mjs) public/assets/stages/crypt.glb
Then: blender -b --factory-startup --python art/stages/crypt/lib/skview.py -- crypt   (previews)

Layout (glTF coords; Blender Y = -glTF z): fighters on a dirt path along z = 0 in a grassy valley floor; low graves,
wildflowers and the Caretaker's open grave in the midground (z -4 .. -20); iron fences, a mausoleum, twisted trees
with eviction notices; the path climbs through a gate and up the hill to the ruined chapel (landmark, z ~ -96).
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, noise as mnoise
import sk
import sk_tiles as T
import dj_common as dj
import dj_mats as mats

SID = 'crypt'
ARGS = dj.script_args()
sk.reset(SID)
R = random.Random(11)
S = sk.smoothstep


# ============================================================================ terrain
CH_X, CH_Y = 7.0, 96.0           # chapel centre (Blender XY)


def H(X, Y):
    X = np.asarray(X, np.float64)
    Y = np.asarray(Y, np.float64)
    ax = np.abs(X)
    flat = (1 - S(10.5, 15.0, ax)) * (1 - S(2.5, 6.5, Y))
    rise = 1.1 * S(3.0, 30.0, Y) + 1.4 * S(22.0, 60.0, Y)
    wob = np.sin(X * 0.045 + 1.3) * np.cos(Y * 0.037) * 0.5 + np.sin(X * 0.11 + Y * 0.07) * 0.25
    side = (6.5 + 3.0 * np.sin(Y * 0.031 + X * 0.01)) * S(15.0, 52.0, ax) * S(-30.0, 12.0, Y)
    side += 2.0 * S(26.0, 60.0, ax)
    hill = 8.6 * np.exp(-(((X - CH_X) / 34.0) ** 2 + ((Y - CH_Y) / 24.0) ** 2))
    shoulder = 3.0 * np.exp(-(((X + 30.0) / 30.0) ** 2 + ((Y - 80.0) / 26.0) ** 2))
    far = S(120.0, 175.0, Y) * (15.0 + 9.0 * np.sin(X * 0.021 + 0.7) + 4.0 * np.sin(X * 0.057))
    z = rise + side + hill + shoulder + far + wob * S(4.0, 14.0, Y + ax * 0.3)
    # chapel pad
    pad = 1 - S(9.0, 15.0, np.hypot((X - CH_X) / 1.4, Y - CH_Y))
    ztop = 8.6 + 1.1 * S(3.0, 30.0, CH_Y) + 1.4 + 0.3
    z = z * (1 - pad) + ztop * pad
    return z * (1 - flat)


def h_at(x, y):
    return float(H(np.array([x]), np.array([y]))[0])


# ============================================================================ materials
def tile(m, key, size=1024):
    p = os.path.join(sk.work_dir(SID), 'bake', key + '_BaseColor.png')
    if os.path.exists(p) and '--rebake-tiles' not in ARGS:
        imgs = {}
        for k, suf in (('base', 'BaseColor'), ('orm', 'ORM'), ('normal', 'Normal')):
            im = bpy.data.images.load(os.path.join(sk.work_dir(SID), 'bake', f'{key}_{suf}.png'))
            im.colorspace_settings.name = 'sRGB' if k == 'base' else 'Non-Color'
            imgs[k] = im
        return imgs
    return sk.bake_tile(m, key, size)


g_imgs = tile(T.grass('t_grass', L=3.0, seed=1.0), 'crypt_grass')
d_imgs = tile(T.dirt('t_dirt', L=2.5, grass_amt=0.35, seed=2.0), 'crypt_dirt')
M_GRASS = sk.image_material('M_grass', g_imgs, vcol='Col')
M_DIRT = sk.image_material('M_dirt', d_imgs, vcol='Col')
M_FOL = sk.color_material('M_foliage', '#ffffff', rough=0.8, vcol='Col', double_sided=True)
M_GLOW = sk.color_material('M_glow', '#ffd9a0', rough=0.5, vcol=None, emit='#ffb860', emit_strength=6.0)


# ============================================================================ ground
def build_ground():
    patches = [
        ('ground_near', sk.axis_samples([(-26, -16, 1.0), (-16, 16, 0.5), (16, 26, 1.0)]),
         sk.axis_samples([(-20, -12, 1.0), (-12, 14, 0.5)])),
        ('ground_mid', sk.axis_samples([(-90, -26, 2.0), (-26, 26, 1.0), (26, 90, 2.0)]),
         sk.axis_samples([(-20, 14, 2.0), (14, 60, 1.0)])),
        ('ground_far', sk.axis_samples([(-200, 200, 4.0)]), sk.axis_samples([(-20, 60, 4.0), (60, 260, 3.0)])),
    ]
    obs = []
    for name, xs, ys in patches:
        def cut(cx, cy, name=name):
            if name == 'ground_mid':
                return abs(cx) < 26 and cy < 14
            if name == 'ground_far':
                return (abs(cx) < 90 and cy < 60)
            return False
        ob = sk.heightfield(name, xs, ys, lambda X, Y: H(X, Y) - (0.0 if name == 'ground_near' else 0.02),
                            M_GRASS, uv_scale=1 / 3.0, cut=cut)
        obs.append(ob)
    return obs


# ============================================================================ the path
def path_points():
    main = [(x, 0.15 * math.sin(x * 0.17) + 0.08 * math.sin(x * 0.5)) for x in np.linspace(-70, 70, 141)]
    br = [(2.2, 0.6), (2.6, 3.0), (3.4, 6.5), (4.6, 10.5), (4.0, 15.0), (2.4, 20.0), (3.0, 26.0), (6.5, 33.0),
          (9.5, 41.0), (8.0, 50.0), (3.5, 58.0), (2.5, 66.0), (6.0, 74.0), (9.0, 81.0), (7.5, 88.0), (7.0, 91.5)]
    return main, br


def strip(name, pts, width_fn, mat, lift=0.012, seed=0, across=4, edge_tint=(0.75, 0.8, 0.55)):
    """Ribbon along pts (XY), conformed to the terrain; irregular edges; world-scale UVs; edge tint in Col."""
    P = [Vector((p[0], p[1], 0)) for p in pts]
    # resample by arc length (~0.5 m)
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = (b - a).length
        n = max(1, int(L / 0.5))
        for i in range(1, n + 1):
            out.append(a.lerp(b, i / n))
    P = out
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    cl = bm.loops.layers.color.new('Col')
    rows = []
    s_acc = 0.0
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        nrm = Vector((-t.y, t.x, 0))
        if i > 0:
            s_acc += (P[i] - P[i - 1]).length
        w = width_fn(s_acc, p)
        row = []
        for k in range(across + 1):
            u = k / across * 2 - 1
            e = abs(u)
            jit = mnoise.noise(Vector((s_acc * 0.35, k * 3.1, seed))) * 0.35 * e ** 2 + \
                mnoise.noise(Vector((s_acc * 1.3, k * 1.7, seed + 9))) * 0.12 * e ** 2
            q = p + nrm * (u * w / 2 * (1 + jit))
            z = h_at(q.x, q.y) + lift - 0.006 * (1 - e)
            v = bm.verts.new((q.x, q.y, z))
            row.append((v, e))
        rows.append(row)
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(across):
            f = bm.faces.new((a[k][0], a[k + 1][0], b[k + 1][0], b[k][0]))
            for l in f.loops:
                l[uvl].uv = (l.vert.co.x / 2.5, l.vert.co.y / 2.5)
                e = next(ee for (vv, ee) in a + b if vv is l.vert)
                t = S(0.55, 1.0, e)
                c = Vector((1, 1, 1)).lerp(Vector(edge_tint), t)
                n = 0.9 + 0.2 * mnoise.noise(l.vert.co * 0.6)
                l[cl] = (c.x * n, c.y * n, c.z * n, 1)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    me.shade_smooth()
    return ob


# ============================================================================ chapel (landmark)
def pointed_arch(w, h_spring, rise=None, n=7):
    """Outline (x,z) of a pointed (gothic) arch opening, bottom at z=0, centred on x=0."""
    r = w * 0.8
    rise = rise if rise is not None else math.sqrt(r * r - (r - w / 2) ** 2)
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, h_spring)]
    cx = w / 2 - r
    a0 = 0.0
    a1 = math.acos((w / 2 - cx - w / 2) / r) if False else math.acos(max(-1, min(1, (0 - cx) / r)))
    for i in range(1, n + 1):
        a = a1 * i / n
        pts.append((cx + r * math.cos(a), h_spring + r * math.sin(a)))
    cx2 = -cx
    for i in range(n - 1, -1, -1):
        a = math.pi - a1 * i / n
        pts.append((cx2 + r * math.cos(a), h_spring + r * math.sin(a)))
    return pts


def cutter(name, pts, depth, loc, rotz=0.0):
    ob = dj.extrude_xz(name, pts, depth)
    dj.xform(ob, loc=loc, rot=(0, 0, rotz))
    return ob


def boolean(ob, cutters):
    for c in cutters:
        md = ob.modifiers.new('B', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
        md.object = c
        dj.apply_mods(ob)
        bpy.data.objects.remove(c)
    return ob


def jag(x0, x1, z_fn, n, seed):
    rr = random.Random(seed)
    return [(x0 + (x1 - x0) * i / n, z_fn(x0 + (x1 - x0) * i / n) + rr.uniform(-0.35, 0.35)) for i in range(n + 1)]


def build_chapel():
    st = mats.stone('ch_stone', base='#8d917f', light='#b1b29b', dark='#4a4d40', warm='#b8ab88', moss=0.45,
                    lichen=0.6, blocks=(0.9, 0.42, 0.018), scale=0.6, seed=3, edge=0.6)
    st2 = mats.stone('ch_stone2', base='#7f8574', light='#a3a68f', dark='#3f4337', moss=0.65, seed=5, scale=0.8)
    slate = mats.stone('ch_slate', base='#4d535a', light='#6e7580', dark='#25292e', warm='#5f5a55', moss=0.25,
                       lichen=0.3, blocks=(0.32, 0.22, 0.03), scale=1.0, seed=7, edge=0.2)
    wd = mats.wood('ch_wood', base='#5e4330', dark='#2e2016', light='#7d5f45', weather=0.6)
    dark = mats.void('ch_dark', '#14120f')
    parts = []
    W, D, HW = 17.0, 7.6, 7.2
    t = 0.75
    # front wall (faces the camera, -Y), ruined jagged top in the middle
    def ftop(x):
        dip = 3.2 * math.exp(-((x - 1.5) / 3.2) ** 2)
        return HW - dip
    outline = [(-W / 2, 0.0), (W / 2, 0.0)] + list(reversed(jag(-W / 2, W / 2, ftop, 24, 4)))
    front = dj.extrude_xz('front', outline, t, st.mat, y=-D / 2)
    cuts = []
    for i, x in enumerate((-6.0, -3.0, 4.5, 7.0)):
        cuts.append(cutter(f'w{i}', pointed_arch(1.5, 2.6, n=6), 3.0, (x, -D / 2, 2.2)))
    cuts.append(cutter('door', pointed_arch(2.0, 2.2, n=6), 3.0, (0.8, -D / 2, 0.0)))
    boolean(front, cuts)
    parts.append(front)
    # back wall (taller, intact) with windows we see through the ruined front
    back = dj.extrude_xz('back', [(-W / 2, 0), (W / 2, 0), (W / 2, HW), (-W / 2, HW)], t, st.mat, y=D / 2)
    boolean(back, [cutter(f'bw{i}', pointed_arch(1.4, 2.6, n=6), 3.0, (x, D / 2, 2.4)) for i, x in enumerate((-5.6, -1.9, 1.9, 5.6))])
    parts.append(back)
    # gable ends (east = +X intact with a rose window, west joins the tower)
    for sx in (-1, 1):
        g = [(-D / 2 - t / 2, 0), (D / 2 + t / 2, 0), (D / 2 + t / 2, HW), (0, HW + 4.3), (-D / 2 - t / 2, HW)]
        gab = dj.extrude_xz('gable', g, t, st.mat)
        dj.xform(gab, rot=(0, 0, 90))
        dj.xform(gab, loc=(sx * W / 2, 0, 0))
        if sx > 0:
            rw = cutter('rose', [(math.cos(a) * 1.3, 7.4 + math.sin(a) * 1.3) for a in np.linspace(0, 2 * math.pi, 17)[:-1]], 3.0, (0, 0, 0))
            dj.xform(rw, rot=(0, 0, 90))
            dj.xform(rw, loc=(sx * W / 2, 0, 0))
            tall = cutter('ew', pointed_arch(1.6, 2.8, n=6), 3.0, (0, 0, 2.0))
            dj.xform(tall, rot=(0, 0, 90))
            dj.xform(tall, loc=(sx * W / 2, 0, 0))
            boolean(gab, [rw, tall])
        parts.append(gab)
    # buttresses on the front and back
    for y0, sgn in ((-D / 2, -1), (D / 2, 1)):
        for x in (-W / 2 + 0.2, -3.75, 0.0, 3.75, W / 2 - 0.2):
            b1 = dj.box('but', 0.8, 1.3, HW * 0.62, loc=(x, y0 + sgn * 0.9, 0), mat=st2.mat)
            b2 = dj.box('but', 0.7, 0.8, HW * 0.3, loc=(x, y0 + sgn * 0.65, HW * 0.62), mat=st2.mat)
            cap = dj.box('butc', 0.8, 0.9, 0.35, loc=(x, y0 + sgn * 0.7, HW * 0.92), rot=(sgn * 28, 0, 0), mat=st2.mat)
            parts += [b1, b2, cap]
    # roof: back slope mostly intact, front slope a few rafters and a torn patch of slate
    pitch = math.atan2(4.3, D / 2 + t / 2)
    slope_len = math.hypot(4.3, D / 2 + 0.6)
    for i, x in enumerate(np.linspace(-W / 2 + 0.6, W / 2 - 0.6, 12)):
        # back rafters (all) and front rafters (some broken)
        r1 = dj.box('raf', 0.22, slope_len, 0.26, loc=(x, D / 4 + 0.15, HW + 2.1), rot=(-math.degrees(pitch), 0, 0), mat=wd.mat)
        parts.append(r1)
        if i % 3 != 1:
            k = 0.45 + 0.55 * R.random()
            r2 = dj.box('raf', 0.22, slope_len * k, 0.26, loc=(x, -D / 2 + slope_len * k / 2 * math.cos(pitch) - 0.25,
                                                             HW + slope_len * k / 2 * math.sin(pitch) - 0.05),
                        rot=(math.degrees(pitch), 0, R.uniform(-4, 4)), mat=wd.mat)
            parts.append(r2)
    ridge = dj.box('ridge', W - 0.6, 0.3, 0.32, loc=(0, 0, HW + 4.1), mat=wd.mat)
    dj.xform(ridge, rot=(0, 0, 0))
    parts.append(ridge)
    roofb = dj.box('roofb', W * 0.78, slope_len + 0.3, 0.16, loc=(1.6, D / 4 + 0.35, HW + 2.25), rot=(-math.degrees(pitch), 0, 0), mat=slate.mat)
    parts.append(roofb)
    roofp = dj.box('roofp', 4.2, slope_len * 0.55, 0.16, loc=(-5.5, -D / 4 - 0.4, HW + 1.2), rot=(math.degrees(pitch), 0, 2), mat=slate.mat)
    parts.append(roofp)
    # dark interior floor (so the ruined front reads as a hollow shell)
    parts.append(dj.box('floor', W - 0.5, D - 0.5, 0.15, loc=(0, 0, -0.05), mat=dark.mat))
    # bell tower at the west end
    TX = -W / 2 - 2.2
    TH = 15.5
    tower = dj.box('tower', 4.6, 4.6, TH, loc=(TX, 0, 0), mat=st.mat)
    tc = []
    for k, rz in enumerate((0, 90)):
        c = cutter(f'bel{k}', pointed_arch(1.6, 2.2, n=6), 6.0, (0, 0, TH - 4.3))
        dj.xform(c, rot=(0, 0, rz))
        dj.xform(c, loc=(TX, 0, 0))
        tc.append(c)
    for k, (dx, dy, rz) in enumerate(((0, -2.3, 0), (2.3, 0, 90))):
        c = cutter(f'slit{k}', pointed_arch(0.45, 1.3, n=4), 1.2, (0, 0, 6.5))
        dj.xform(c, rot=(0, 0, rz))
        dj.xform(c, loc=(TX + dx, dy, 0))
        tc.append(c)
    boolean(tower, tc)
    parts.append(tower)
    parts.append(dj.box('tbase', 5.2, 5.2, 1.2, loc=(TX, 0, 0), mat=st2.mat))
    parts.append(dj.box('tband', 5.0, 5.0, 0.4, loc=(TX, 0, TH - 4.9), mat=st2.mat))
    parts.append(dj.box('tcap', 5.1, 5.1, 0.5, loc=(TX, 0, TH), mat=st2.mat))
    # corner pinnacles (one broken)
    for k, (dx, dy) in enumerate(((-2.3, -2.3), (2.3, -2.3), (-2.3, 2.3), (2.3, 2.3))):
        hh = 2.2 if k != 1 else 0.9
        pn = dj.cyl('pin', 0.32, hh, segs=4, r2=0.04 if k != 1 else 0.25, loc=(TX + dx, dy, TH + 0.5), rot=(0, 0, 45), mat=st2.mat)
        parts.append(pn)
    # broken spire: a stump of the pyramid, leaning
    sp = dj.cyl('spire', 2.4, 3.2, segs=4, r2=1.1, loc=(TX, 0, TH + 0.5), rot=(0, 0, 45), mat=slate.mat)
    dj.xform(sp, rot=(4, -6, 0), pivot=(TX, 0, TH + 0.5))
    parts.append(sp)
    # the bell (dark bronze) hanging in the belfry
    bell = dj.lathe('bell', [(0.0, 0.0), (0.75, 0.02), (0.68, 0.25), (0.5, 0.7), (0.42, 1.0), (0.2, 1.12), (0.0, 1.14)], 16,
                    mats.brass('ch_bell', base='#7a5a2c', dark='#3a2a14', light='#a8844a', verd=0.4).mat)
    dj.xform(bell, loc=(TX, 0, TH - 3.4))
    parts.append(bell)
    parts.append(dj.box('beam', 4.4, 0.3, 0.3, loc=(TX, 0, TH - 2.2), mat=wd.mat))
    # leaning cross on the east gable
    cx = W / 2
    crs = [dj.box('cr', 0.22, 0.22, 2.0, loc=(cx, 0, HW + 4.1), mat=st2.mat), dj.box('cr', 1.1, 0.22, 0.22, loc=(cx, 0, HW + 5.3), mat=st2.mat)]
    for c in crs:
        dj.xform(c, rot=(0, 12, 0), pivot=(cx, 0, HW + 4.1))
    parts += crs
    # rubble at the foot of the broken front
    for i in range(26):
        x = R.uniform(-3.5, 6.0)
        y = -D / 2 - R.uniform(0.6, 3.0)
        s = R.uniform(0.25, 0.7)
        rb = dj.ico('rub', s, 1, loc=(x, y, s * 0.3), scale=(1, R.uniform(0.6, 1), R.uniform(0.5, 0.8)), mat=st2.mat)
        dj.warp(rb, 0.1, 2.0, i)
        parts.append(rb)
    for o in parts:
        if o.data.attributes.get('rest') is None:
            dj.store_rest(o)
    for o in parts:
        mn = o.data.materials[0].name if o.data.materials else ''
        if mn == 'ch_wood':
            dj.grain(o, (1, 0, 0) if o.name.startswith('ridge') else (0, 1, 0))
    ob = dj.join(parts, 'chapel')
    dj.smooth(ob, 35)
    gz = h_at(CH_X, CH_Y)
    ob.location = (CH_X, CH_Y, gz - 0.15)
    ob.rotation_euler = (0, 0, math.radians(-4))
    return ob


# ============================================================================ notices
def notice_mat(name, title='NOTICE TO QUIT', seed=0, big=False):
    lines = [(title, 0.80, 0.085), ('~', 0.64, 0.045), ('~', 0.55, 0.045), ('~', 0.46, 0.045),
             ('~', 0.37, 0.045), ('MANAGEMENT', 0.12, 0.06)]
    img = sk.text_image(name + '_img', lines, 1.0, 1.4, res=384, stroke=0.13, seed=seed)
    m = dj.M(name)
    uv = m.uvmap('UVMap')
    m.set(color=m.image(img, uv, 'CLIP'), rough=0.85)
    return m


def notice(name, mat, w=0.32, h=0.44, curl=0.04):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    nx, ny = 4, 5
    vs = [[bm.verts.new(((i / nx - 0.5) * w, -curl * (2 * i / nx - 1) ** 2 - curl * 0.6 * (j / ny) ** 2, j / ny * h - h * 0.85))
           for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (a / nx, b / ny)
    ob = dj.mesh_obj(name, bm, mat.mat)
    dj.solidify(ob, 0.004)
    nail = dj.cyl('nail', 0.012, 0.03, 6, loc=(0, -0.03, -0.02), rot=(90, 0, 0), mat=mats.iron('nail_iron').mat)
    return [ob, nail]


# ============================================================================ build
log = sk.log
log('ground')
grounds = build_ground()
for g in grounds:
    sk.unique(g)
main_pts, br_pts = path_points()
p_main = strip('path_main', main_pts, lambda s, p: 2.9 + 0.35 * math.sin(s * 0.23), M_DIRT, seed=1)
p_br = strip('path_branch', br_pts, lambda s, p: max(1.1, 2.2 - s * 0.012), M_DIRT, seed=2, across=3)
sk.unique(p_main)
sk.unique(p_br)

# --- templates
log('templates')
PP = sk.P_PROPS
T_hs = [sk.load(os.path.join(PP, f'headstone_{k}.glb')) for k in 'abcdef']
T_fence = sk.load(os.path.join(PP, 'iron_fence.glb'))
T_post = sk.load(os.path.join(PP, 'iron_fence_post.glb'))
T_gate = sk.load(os.path.join(PP, 'iron_gate.glb'))
T_lamp = sk.load(os.path.join(PP, 'lantern_post.glb'))
T_bench = sk.load(os.path.join(PP, 'stone_bench.glb'))
T_urn = sk.load(os.path.join(PP, 'stone_urn.glb'))
T_coffin = sk.load(os.path.join(PP, 'coffin_open.glb'))
T_mound = sk.load(os.path.join(PP, 'grave_dirt_mound.glb'))
T_col = sk.load(os.path.join(PP, 'broken_column.glb'))
T_pil = sk.load(os.path.join(PP, 'crypt_pillar_broken.glb'))
T_maus = sk.load(os.path.join(PP, 'mausoleum.glb'))
T_ridge = sk.load(os.path.join(PP, 'crypt_ridge.glb'))
N = sk.P_NATURE
T_twist = [sk.load(os.path.join(N, f'TwistedTree_{k}.gltf'), wrap=False) for k in (1, 3)]
T_dead = sk.load(os.path.join(N, 'DeadTree_2.gltf'), wrap=False)
T_pine = sk.load(os.path.join(N, 'Pine_5.gltf'), wrap=False)
T_bush = sk.load(os.path.join(N, 'Bush_Common.gltf'), wrap=False)
T_peb = [sk.load(os.path.join(N, f'Pebble_Round_{k}.gltf')) for k in (1, 2, 3)] + \
        [sk.load(os.path.join(N, f'Pebble_Square_{k}.gltf')) for k in (1, 3, 5)]

# grass tufts / flowers (vertex coloured)
T_tuft = []
for i in range(6):
    t = sk.grass_tuft(f'tuft{i}', R, n=R.randint(7, 12), h=(0.1, 0.22) if i < 4 else (0.14, 0.24))
    t.data.materials.append(M_FOL)
    T_tuft.append(sk.template([t], f'tuft{i}', rest=False))
FLOWER_COLS = [('#f4f0d8', '#e8b830'), ('#f2d64a', '#c8901a'), ('#b9a0e8', '#f0e070'), ('#ffffff', '#f2c23a'),
               ('#e88aa8', '#f8e0a0')]
T_flower = []
for i, (pc, cc) in enumerate(FLOWER_COLS):
    f = sk.flower_clump(f'flw{i}', R, n=R.randint(4, 7), h=(0.08, 0.2), petal=pc, centre=cc)
    f.data.materials.append(M_FOL)
    T_flower.append(sk.template([f], f'flower{i}', rest=False))

# notices
NOTICE_M = [notice_mat('notice_a', seed=1), notice_mat('notice_b', 'EVICTION', seed=2)]
T_notice = [sk.template(notice('ntc_a', NOTICE_M[0]), 'notice_a'), sk.template(notice('ntc_b', NOTICE_M[1]), 'notice_b')]


# low-poly far trees (vertex coloured canopy blobs)
def blob_tree(name, rng, h=6.0, cols=('#2f4f22', '#4f7a30', '#7fa04a'), trunk='#4a3626'):
    parts = []
    tr = dj.cyl('trunk', 0.18 * h / 6, h * 0.45, segs=5, r2=0.1 * h / 6)
    parts.append(tr)
    for k in range(3):
        r = h * rng.uniform(0.2, 0.28) * (1 - k * 0.18)
        c = dj.ico('can', r, 1, loc=(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), h * (0.5 + 0.17 * k)),
                   scale=(1, 1, rng.uniform(0.8, 1.05)))
        dj.warp(c, r * 0.18, 1.3 / r, rng.randint(0, 99))
        parts.append(c)
    ob = dj.join(parts, name)
    a = sk.vcol_layer(ob)
    me = ob.data
    zs = np.array([v.co.z for v in me.vertices])
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    c0, c1, c2 = (np.array(dj.col(c)[:3]) for c in cols)
    ct = np.array(dj.col(trunk)[:3])
    out = np.ones((len(me.loops), 4), np.float32)
    for i, v in enumerate(vi):
        z = zs[v] / h
        if z < 0.38:
            out[i, :3] = ct
        else:
            t = min(1, max(0, (z - 0.38) / 0.62))
            out[i, :3] = c0 * (1 - t) + c1 * t if t < 0.6 else c1 * (1 - (t - 0.6) / 0.4) + c2 * ((t - 0.6) / 0.4)
    a.data.foreach_set('color', out.ravel())
    me.materials.append(M_FOL)
    dj.flat(ob)
    return ob


T_blob = [sk.template([blob_tree(f'blob{i}', R, h=R.uniform(5, 8))], f'blob{i}', rest=False) for i in range(5)]

# ============================================================================ bake atlases (templates)
log('atlases')
A = sk.Atlas('crypt_props', size=2048, emission=True, mode='iso', ao_strength=0.0, emission_strength=4.0)
for t in T_hs:
    A.add(t, 1.2)
for t in (T_lamp, T_bench, T_urn, T_coffin, T_mound, T_col, T_pil, T_ridge):
    A.add(t, 1.0)
for t in T_peb:
    A.add(t, 1.0)
for t in T_notice:
    A.add(t, 2.5)
A.bake()
B = sk.Atlas('crypt_iron', size=2048, mode='iso', ao_strength=0.0)
for t in (T_fence, T_post, T_gate):
    B.add(t, 1.0)
B.add(T_maus, 0.8)
B.bake()
# LODs (after baking: they keep the atlas material and UVs)
T_hs_mid = [sk.lod(t, 0.45) for t in T_hs]
T_hs_far = [sk.lod(t, 0.18) for t in T_hs]
T_fence_l = sk.lod(T_fence, 0.5)
T_post_l = sk.lod(T_post, 0.5)
T_lamp_l = sk.lod(T_lamp, 0.5)

# ============================================================================ placement
log('placement')


def gz(x, y):
    return h_at(x, y)


def put(t, x, y, rz=0.0, s=1.0, sink=0.02, **kw):
    return sk.put(t, x, y, gz(x, y) - sink, rz=rz, s=s, **kw)


# -- big framing trees with eviction notices
put(T_twist[0], -12.5, 7.5, rz=40, s=0.62)
put(T_twist[1], 13.5, 10.0, rz=-110, s=0.55)
put(T_dead, -7.8, 15.5, rz=200, s=0.75)
put(T_bush, -10.5, 4.6, rz=10, s=0.9)
put(T_bush, 11.5, 5.4, rz=80, s=0.8)
put(T_bush, 16.5, 8.0, rz=30, s=1.1)
put(T_bush, -16.0, 9.0, rz=140, s=1.2)
put(T_notice[0], -11.65, 6.92, rz=8, s=1.2, sink=-1.75)
put(T_notice[1], 12.85, 9.35, rz=-12, s=1.1, sink=-1.6)
put(T_notice[0], -7.45, 15.0, rz=-5, s=1.3, sink=-1.45)

# -- the Caretaker's open grave (left midground)
GX, GY = -6.2, 6.6
put(T_mound, GX + 0.2, GY + 1.9, rz=92, s=1.05)
put(T_coffin, GX + 2.15, GY + 0.1, rz=-80, s=1.0)
put(T_hs[1], GX - 1.55, GY + 0.3, rz=-8, s=1.35)
put(T_lamp, GX + 2.2, GY + 1.6, rz=-30, s=1.0)
put(T_notice[1], GX - 1.5, GY - 0.05, rz=-8, s=1.0, sink=-0.95)

# -- graves: rows behind the path (keep the band behind the torsos low)
hs_low = [0, 3, 4]       # wide / low ones
hs_tall = [1, 2, 5]
taken = [(GX, GY), (GX + 1, GY + 1.9)]
rows = [(3.6, 0.55, hs_low), (5.6, 0.6, hs_low + hs_tall[:1]), (8.8, 0.7, hs_low + hs_tall),
        (11.4, 0.7, hs_low + hs_tall), (15.0, 0.7, hs_tall + hs_low), (19.0, 0.7, hs_tall + hs_low),
        (23.5, 0.7, hs_tall + hs_low)]
for (ry, dens, pool) in rows:
    x = -19.0 + R.uniform(0, 1.5)
    while x < 19.0:
        x += R.uniform(1.6, 2.6)
        if abs(x - 3.0) < 1.8 + ry * 0.02:        # the branch path
            continue
        if R.random() > dens:
            continue
        y = ry + R.uniform(-0.35, 0.35)
        if any((x - a) ** 2 + (y - b) ** 2 < 2.6 for a, b in taken):
            continue
        k = R.choice(pool)
        if ry < 6.0 and abs(x) < 7.0 and k in hs_tall:
            k = R.choice(hs_low)
        t = (T_hs if ry < 10 else T_hs_mid)[k]
        taken.append((x, y))
        put(t, x, y, rz=R.uniform(-12, 12), s=R.uniform(0.85, 1.1), rx=R.uniform(-4, 4), ry=R.uniform(-5, 5))

# -- fences at the sides, a gate on the branch path
for x0, x1 in ((-21.0, -6.5), (8.5, 21.0)):
    nseg = int((x1 - x0) / 2.0)
    for i in range(nseg + 1):
        x = x0 + i * 2.0
        y = 12.6 + 0.08 * x
        put(T_post_l, x, y, rz=0)
        if i < nseg and R.random() > 0.12:
            put(T_fence_l, x + 1.0, y + 0.08, rz=-2.3 + R.uniform(-3, 3), rx=R.uniform(-3, 3))
put(T_gate, 3.4, 12.9, rz=-5)
put(T_notice[0], 3.0, 12.55, rz=-5, s=1.1, sink=-1.25)

# -- mausoleum and ruins on the right / left
put(T_maus, 15.5, 17.5, rz=-28, s=1.0)
put(T_col, -15.0, 13.5, rz=30)
put(T_pil, -17.5, 11.0, rz=-20)
put(T_pil, 9.0, 21.0, rz=60)
put(T_urn, 7.8, 13.0, rz=0)
put(T_urn, -5.6, 12.9, rz=0)
put(T_bench, -9.6, 11.2, rz=12)
put(T_lamp, 5.4, 9.2, rz=-90)
put(T_lamp_l, 5.0, 24.0, rz=-90)
put(T_ridge, -22.0, 16.0, rz=20, s=1.4)
put(T_ridge, 23.0, 22.0, rz=-25, s=1.6)

# -- lanterns up the hill path
for (x, y) in ((10.8, 40.0), (5.0, 57.0), (7.8, 72.0), (9.2, 86.0)):
    put(T_lamp_l, x, y, rz=-90, s=1.4)

# -- hillside graves (sparser, decimated) and trees around the chapel
for i in range(55):
    x = R.uniform(-30, 34)
    y = R.uniform(28, 84)
    if abs(x - (5 + 3 * math.sin(y * 0.1))) < 2.5:
        continue
    put(R.choice(T_hs_far), x, y, rz=R.uniform(-20, 20), s=R.uniform(1.0, 1.3))
for (x, y, s) in ((-6.0, 92.0, 1.0), (-4.0, 100.0, 1.2), (20.0, 90.0, 0.95), (22.0, 101.0, 1.15), (16.5, 108.0, 1.0),
                  (-12.0, 104.0, 1.1), (28.0, 96.0, 0.9)):
    put(T_pine, x, y, rz=R.uniform(0, 360), s=(s * 0.55, s * 0.55, s * 1.25))
for i in range(60):
    x = R.uniform(-110, 110)
    y = R.uniform(34, 150)
    if abs(x - CH_X) < 24 and abs(y - CH_Y) < 16:
        continue
    if abs(x) < 24 and y < 46:
        continue
    put(R.choice(T_blob), x, y, rz=R.uniform(0, 360), s=R.uniform(0.9, 1.6), sink=0.3)

# -- near floor detail: tufts, flowers, pebbles (low: <= 0.25 m)
pts = sk.poisson(420, -24, 24, -14, 14, 0.55, R)
for (x, y) in pts:
    on_path = abs(y - 0.15 * math.sin(x * 0.17)) < 1.25
    if on_path and R.random() < 0.85:
        continue
    k = R.random()
    if k < 0.66:
        put(R.choice(T_tuft), x, y, rz=R.uniform(0, 360), s=R.uniform(0.8, 1.25), sink=0.0)
    elif k < 0.92:
        put(R.choice(T_flower), x, y, rz=R.uniform(0, 360), s=R.uniform(0.8, 1.2), sink=0.0)
    else:
        put(R.choice(T_peb), x, y, rz=R.uniform(0, 360), s=R.uniform(0.25, 0.5), sink=0.03)
for i in range(60):          # pebbles along the path edges
    x = R.uniform(-22, 22)
    side = R.choice((-1, 1))
    y = 0.15 * math.sin(x * 0.17) + side * R.uniform(1.0, 1.7)
    put(R.choice(T_peb), x, y, rz=R.uniform(0, 360), s=R.uniform(0.18, 0.4), sink=0.03)
pts = sk.poisson(240, -60, 60, 14, 60, 1.2, R)
for (x, y) in pts:
    t = R.choice(T_flower + T_tuft)
    put(t, x, y, rz=R.uniform(0, 360), s=R.uniform(1.2, 2.0), sink=0.0)

# ============================================================================ chapel (baked in place)
log('chapel')
chapel = build_chapel()
sk.unique(chapel)
C = sk.Atlas('crypt_chapel', size=2048, mode='inplace', ao_strength=0.4, ao_dist=1.5)
C.add(chapel, 1.0)
C.bake()

# ============================================================================ ground colour (AO + tint)
log('ground vertex colour')
for g in grounds + [p_main, p_br]:
    def tint(co, n, g=g):
        nn = mnoise.fractal(Vector((co.x * 0.08, co.y * 0.08, 0)), 0.5, 2.0, 3)
        n2 = mnoise.noise(Vector((co.x * 0.3, co.y * 0.3, 5)))
        k = 0.95 + 0.12 * nn + 0.05 * n2
        warm = S(0.15, 0.6, nn)
        return (k * (1 + 0.05 * warm), k * (1 + 0.02 * warm), k * (1 - 0.06 * warm))
    if g.name.startswith('path'):
        sk.vcol_layer(g)
    else:
        sk.vcol_from_points(g, tint)
sk.bake_vertex_ao([grounds[0], grounds[1], p_main, p_br], dist=2.0, samples=48, strength=0.85)

# ============================================================================ export
if '--no-export' not in ARGS:
    sk.export(SID)

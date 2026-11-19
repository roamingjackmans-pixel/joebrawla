"""Zone 2 kit, The Fungal Hollows (sinkhole cave open to the sky): boundary, interior, scatter, set-piece and hazard
props, exported to assets/custom/props/fungal_<name>.glb (zone 1's folder convention). Front faces Blender -Y
(Godot +Z); origin at the base centre on the ground; lengths along X. Each prop is one baked PBR atlas; glowing
props carry an emission texture (bioluminescence).

blender -b --factory-startup --python fungal_kit.py -- [name ...] [--list]
(no names = all). Then fungal_stairs.py (the stairs) and fungal_jpeg.py (re-packs every fungal_*.glb with JPEG
textures for the LFS quota; run it after any rebuild), fungal_preview.py for the review renders. The slot each prop fills in the zone style is in KIT (see src/Look/FungalHollows.cs)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import dj_common as dj
import dj_mats as mats
import fungal_mats as fm
from mathutils import Vector, Matrix, noise as mnoise

# ----------------------------------------------------------------------------- geometry helpers


def _lin(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def cap_profile(cap_r, cap_h, stalk_r, shape):
    """(r, z) from the stalk under the cap, out along the gills to the rim, then over the top to the apex."""
    under = [(stalk_r * 0.95, -cap_h * 0.18), (cap_r * 0.45, -cap_h * 0.12), (cap_r * 0.8, -cap_h * 0.06),
             (cap_r * 0.97, 0.0)]
    if shape == 'bell':
        top = [(cap_r, cap_h * 0.05), (cap_r * 0.97, cap_h * 0.3), (cap_r * 0.86, cap_h * 0.6), (cap_r * 0.66, cap_h * 0.84),
               (cap_r * 0.4, cap_h * 0.97), (cap_r * 0.15, cap_h * 1.02), (0.0, cap_h * 1.03)]
    elif shape == 'flat':      # parasol with an umbo
        top = [(cap_r, cap_h * 0.12), (cap_r * 0.85, cap_h * 0.3), (cap_r * 0.6, cap_h * 0.45), (cap_r * 0.35, cap_h * 0.58),
               (cap_r * 0.15, cap_h * 0.8), (0.0, cap_h * 0.9)]
    elif shape == 'funnel':    # upturned rim, dished middle
        top = [(cap_r * 1.02, cap_h * 0.45), (cap_r * 0.85, cap_h * 0.42), (cap_r * 0.6, cap_h * 0.3), (cap_r * 0.3, cap_h * 0.18),
               (0.0, cap_h * 0.12)]
        under = [(stalk_r * 0.95, -cap_h * 0.1), (cap_r * 0.5, cap_h * 0.05), (cap_r * 0.85, cap_h * 0.25), (cap_r * 0.98, cap_h * 0.38)]
    else:                      # dome
        top = [(cap_r, cap_h * 0.08), (cap_r * 0.94, cap_h * 0.38), (cap_r * 0.8, cap_h * 0.64), (cap_r * 0.58, cap_h * 0.85),
               (cap_r * 0.3, cap_h * 0.97), (0.0, cap_h)]
    return under + top


def mushroom(name, h, cap_r, stalk_r, capm, stalkm, shape='dome', cap_h=None, lean=(0.0, 0.0), segs=20, seed=0,
             rim_wave=0.06, bulb=1.35, droop=0.0):
    """A mushroom standing on the ground at the origin: curved, tapered stalk with a bulbous foot and a cap tilted
    along the stalk's top. Returns [stalk, cap]."""
    R = random.Random(seed)
    cap_h = cap_h if cap_h is not None else cap_r * 0.7
    n = 8
    path, radii = [], []
    for i in range(n):
        t = i / (n - 1)
        path.append(Vector((lean[0] * h * t * t, lean[1] * h * t * t, h * t)))
        radii.append(stalk_r * (1.0 + (bulb - 1.0) * max(0.0, 1 - t * 4) ** 2) * (1.0 - 0.15 * t))
    st = dj.tube(name + '_stalk', [path[0] - Vector((0, 0, 0.15))] + path, stalk_r, max(8, segs // 2), stalkm,
                 radii=[radii[0]] + radii)
    dj.warp(st, stalk_r * 0.12, 3.0 / max(stalk_r, 0.05), seed=seed)
    dj.store_rest(st)
    prof = cap_profile(cap_r, cap_h, stalk_r * 0.85, shape)
    cp = dj.lathe(name + '_cap', prof, segs, capm, cap_bottom=True, cap_top=False, phase=R.random())
    k = R.randint(4, 7)
    ph = R.random() * 6.28
    for v in cp.data.vertices:
        rr = math.hypot(v.co.x, v.co.y)
        if rr > cap_r * 0.6:
            a = math.atan2(v.co.y, v.co.x)
            f = (rr - cap_r * 0.6) / (cap_r * 0.4)
            v.co.z += math.sin(a * k + ph) * rim_wave * cap_r * f - droop * cap_r * f * f
    cp.data.update()
    dj.warp(cp, cap_r * 0.04, 2.0 / max(cap_r, 0.05), seed=seed + 3)
    dj.store_rest(cp)   # material masks use the cap's own frame (gills by normal)
    tang = (path[-1] - path[-2]).normalized()
    q = Vector((0, 0, 1)).rotation_difference(tang)
    M = Matrix.Translation(path[-1]) @ q.to_matrix().to_4x4()
    cp.data.transform(M)
    cp.data.update()
    return [st, cp]


def rock(name, sx, sy, sz, mat, seed=0, subdiv=3, amp=0.22, terrace=0.0, step=0.35, sink=0.12):
    ob = dj.ico(name, 1.0, subdiv, mat=mat)
    dj.xform(ob, scale=(sx * 0.5, sy * 0.5, sz * 0.55))
    dj.warp(ob, amp * min(sx, sy, sz) * 0.5, 1.2 / max(min(sx, sy), 0.2), seed=seed)
    dj.warp(ob, amp * min(sx, sy, sz) * 0.12, 4.5 / max(min(sx, sy), 0.2), seed=seed + 7)
    if terrace > 0:
        for v in ob.data.vertices:
            z = v.co.z
            v.co.z = z + (round(z / step) * step - z) * terrace
    zs = [v.co.z for v in ob.data.vertices]
    z0 = min(zs)
    for v in ob.data.vertices:
        v.co.z = max(v.co.z - z0 - sink * sz, -sink * sz * 0.5)
    ob.data.update()
    dj.store_rest(ob)
    return ob


def slab_rock(name, sx, sy, sz, mat, seed=0, cuts=8, amp=0.3, top_amp=0.35, terrace=0.45, step=0.42):
    """Blocky-but-natural rock mass (cliff faces, ridges): a subdivided box, warped, terraced into strata, the top
    torn by noise. Base centred at the origin, length along X."""
    ob = dj.box(name, sx, sy, sz, mat=mat, cuts=cuts)
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in ob.data.vertices:
        c = v.co
        # round the footprint: square -> superellipse (no box corners), wider foot, narrower crown
        u, w = 2 * c.x / sx, 2 * c.y / sy
        m_ = max(abs(u), abs(w))
        if m_ > 1e-6:
            r = (abs(u) ** 2.4 + abs(w) ** 2.4) ** (1 / 2.4)
            k = m_ / r
            zf0 = c.z / sz
            k *= 1.08 - 0.22 * zf0
            c.x *= k
            c.y *= k
        n = mnoise.noise_vector(c * (1.0 / max(1.0, sz * 0.5)) + off)
        c.x += n.x * amp * 0.6
        c.y += n.y * amp
        zf = c.z / sz
        if zf > 0.6:
            c.z += mnoise.noise(Vector((c.x * 0.7, c.y * 0.7, 3.3)) + off) * top_amp * sz * (zf - 0.6) * 2.0
        # overhang: the upper part bellies outward a little
        c.y *= 1.0 + 0.18 * math.sin(zf * math.pi) * (1 if c.y < 0 else 0.6)
        if terrace > 0 and 0.05 < zf < 0.97:
            c.z = c.z + (round(c.z / step) * step - c.z) * terrace
    ob.data.update()
    dj.warp(ob, amp * 0.18, 3.5 / max(sy, 0.5), seed=seed + 11)
    dj.store_rest(ob)
    return ob


def shelf_fungus(name, r, mat, pos, yaw_deg, tilt=8.0, seed=0, squash=0.65):
    """A half-disc bracket fungus whose flat back sits against +Y before rotation; faces local -Y."""
    prof = [(0.0, -0.1 * r), (0.55 * r, -0.09 * r), (0.95 * r, -0.03 * r), (r, 0.02 * r), (0.85 * r, 0.1 * r),
            (0.5 * r, 0.17 * r), (0.0, 0.2 * r)]
    ob = dj.lathe(name, prof, 18, mat, cap_bottom=False, cap_top=False, phase=0.1)
    dj.xform(ob, scale=(1.0, squash, 1.0))
    dj.delete_faces(ob, lambda c, n_: c.y > 0.05 * r)
    dj.warp(ob, r * 0.05, 3.0 / r, seed=seed)
    dj.store_rest(ob)
    dj.xform(ob, rot=(tilt, 0, yaw_deg), loc=pos)
    return ob


def shelf_tiers(prefix, mat, base, yaw, rmax, n, seed, dz=0.18):
    R = random.Random(seed)
    out = []
    for i in range(n):
        r = rmax * (1.0 - 0.17 * i) * R.uniform(0.85, 1.05)
        p = Vector(base) + Vector((R.uniform(-0.15, 0.15), 0, -i * dz))
        out.append(shelf_fungus(f'{prefix}{i}', r, mat, p, yaw + R.uniform(-18, 18), tilt=R.uniform(4, 12), seed=seed + i))
    return out


def hanging_roots(prefix, mat, top, length, n, seed, spread=0.6, rad=0.05, out=(0, -1, 0)):
    """Roots dangling from a ledge: start at `top`, curl outward (`out`) then down."""
    R = random.Random(seed)
    res = []
    o = Vector(out)
    for i in range(n):
        st = Vector(top) + Vector((R.uniform(-spread, spread), R.uniform(-0.05, 0.05), R.uniform(-0.05, 0.05)))
        L = length * R.uniform(0.55, 1.1)
        pts, radii = [], []
        for k in range(7):
            t = k / 6
            pts.append(st + o * (0.12 * math.sin(t * math.pi * 0.8)) + Vector((R.uniform(-0.04, 0.04), 0, -L * t)))
            radii.append(rad * (1.0 - 0.8 * t) * R.uniform(0.8, 1.2))
        res.append(dj.tube(f'{prefix}{i}', pts, rad, 5, mat, radii=radii))
    return res


def ground_roots(prefix, mat, centre, n, r0, r1, seed, rad=0.09, z=0.0):
    R = random.Random(seed)
    res = []
    for i in range(n):
        a = 2 * math.pi * i / n + R.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        L = R.uniform(r0, r1)
        pts = [Vector(centre) + d * (L * t) + Vector((0, 0, z + 0.25 * (1 - t) ** 2 * (1 + R.random()) - 0.05 * t)) for t in _lin(0.0, 1.0, 6)]
        radii = [rad * (1 - 0.75 * t) for t in _lin(0.0, 1.0, 6)]
        res.append(dj.tube(f'{prefix}{i}', pts, rad, 6, mat, radii=radii))
    return res


def glow_cluster(prefix, capm, stalkm, base, n, seed, hmin=0.12, hmax=0.3, spread=0.14, lean=0.25, shape='dome'):
    R = random.Random(seed)
    out = []
    for i in range(n):
        h = R.uniform(hmin, hmax)
        a = R.uniform(0, 6.28)
        p = Vector(base) + Vector((math.cos(a), math.sin(a), 0)) * R.uniform(0, spread)
        parts = mushroom(f'{prefix}{i}', h, h * R.uniform(0.32, 0.45), h * 0.07, capm, stalkm, shape=shape,
                         lean=(R.uniform(-lean, lean), R.uniform(-lean, lean)), segs=12, seed=seed * 7 + i)
        for o in parts:
            dj.xform(o, loc=p)
        out += parts
    return out


def moss_pads(prefix, mat, pts, seed, r=(0.15, 0.4), h=(0.04, 0.09)):
    R = random.Random(seed)
    return [dj.cushion(f'{prefix}{i}', R.uniform(*r), R.uniform(*h), p, mat, seed=seed + i) for i, p in enumerate(pts)]


def top_points(ob, n, seed, zmin_frac=0.7, up=0.75):
    """Sample n world points on upward faces of ob above zmin_frac of its height."""
    R = random.Random(seed)
    zs = [v.co.z for v in ob.data.vertices]
    zt = min(zs) + (max(zs) - min(zs)) * zmin_frac
    faces = [p for p in ob.data.polygons if p.normal.z > up and p.center.z > zt]
    R.shuffle(faces)
    return [p.center.copy() for p in faces[:n]]


def side_points(ob, n, seed, facing=(0, -1, 0), zlo=0.25, zhi=0.85, dot=0.55):
    R = random.Random(seed)
    zs = [v.co.z for v in ob.data.vertices]
    z0, z1 = min(zs), max(zs)
    f = Vector(facing)
    faces = [p for p in ob.data.polygons if p.normal.dot(f) > dot and z0 + (z1 - z0) * zlo < p.center.z < z0 + (z1 - z0) * zhi]
    R.shuffle(faces)
    return [(p.center.copy(), p.normal.copy()) for p in faces[:n]]


def yaw_of(nrm):
    """Rotation (deg about Z) taking local -Y to the face normal's ground direction."""
    return math.degrees(math.atan2(nrm.x, -nrm.y))


def bracket_on_faces(prefix, mat, ob, n, seed, rmin, rmax, facing=(0, -1, 0), tiers=2):
    R = random.Random(seed)
    out = []
    for i, (c, nr) in enumerate(side_points(ob, n, seed, facing)):
        out += shelf_tiers(f'{prefix}{i}_', mat, c - nr * 0.03, yaw_of(nr), R.uniform(rmin, rmax), R.randint(1, tiers), seed + i * 13)
    return out


# ----------------------------------------------------------------------------- shared materials (made per build)
def M():
    return {
        'stone': fm.cave_stone('fh_stone', seed=1, moss=0.45, glow=0.55),
        'stone2': fm.cave_stone('fh_stone2', seed=4, moss=0.3, glow=0.3, base='#665e70', light='#958ca0'),
        'moss': fm.cave_moss('fh_moss', seed=2),
        'roots': fm.roots('fh_roots', seed=3),
        'stalk': fm.stalk('fh_stalk', seed=1, moss=0.4),
        'violet': fm.cap('fh_cap_violet', top='#6e4282', top2='#9a62ad', rim='#2f1c38', gill='#d9e8de', spots=7.0,
                         spot_col='#8ff0de', spot_glow=1.0, gill_glow=0.9, seed=1),
        'ochre': fm.cap('fh_cap_ochre', top='#b5762f', top2='#d69c4c', rim='#5a3216', gill='#efe3c8', gill_glow=0.8,
                        glow_col=fm.TEAL, seed=2),
        'rust': fm.cap('fh_cap_rust', top='#9e3b26', top2='#c45a35', rim='#4d1a12', gill='#efe3cf', spots=11.0,
                       spot_col='#efe6d2', seed=3),
        'pale': fm.cap('fh_cap_pale', top='#cfc4d6', top2='#e8e0ea', rim='#7c6d86', gill='#bfa9d6', gill_glow=1.0,
                       glow_col=fm.VIOLET_GLOW, seed=4),
        'shelf': fm.shelf('fh_shelf', seed=1),
        'shelf_v': fm.shelf('fh_shelf_violet', top='#5a3f7a', band='#8d6aa8', under='#e4d6ee', seed=2, glow=0.8),
        'glow': fm.glowcap('fh_glowcap', colour=fm.TEAL),
        'glow_v': fm.glowcap('fh_glowcap_violet', colour=fm.VIOLET_GLOW),
        'glow_s': fm.stalk('fh_glowstalk', base='#d8eee6', dark='#8fb0a6', seed=5),
        'puff': fm.puffball('fh_puff', seed=1),
        'wood': fm.roots('fh_rotwood', base='#4e3a30', dark='#241913', light='#7a6250', seed=6, moss=0.55),
    }


# ----------------------------------------------------------------------------- props
def b_cliff(seed, sx, sy, sz):
    def build():
        m = M()
        ob = slab_rock('cliff', sx, sy, sz, m['stone'], seed=seed, cuts=10, amp=0.35 * sy, top_amp=0.18, terrace=0.5)
        P = [ob]
        P += bracket_on_faces('sh', m['shelf'], ob, 4, seed + 1, 0.35, 0.6)
        P += bracket_on_faces('shv', m['shelf_v'], ob, 2, seed + 2, 0.3, 0.45, facing=(0, 1, 0), tiers=1)
        tops = top_points(ob, 10, seed + 3)
        P += moss_pads('mp', m['moss'], tops[:6], seed, r=(0.3, 0.7), h=(0.06, 0.14))
        for i, p in enumerate(tops[6:9]):
            P += glow_cluster(f'gc{i}_', m['glow'], m['glow_s'], p, 4, seed + 20 + i, 0.15, 0.32)
        if len(tops) > 9:
            P += mushroom('tm', sz * 0.32, sz * 0.14, 0.06, m['violet'], m['stalk'], lean=(0.1, -0.15), seed=seed)
            for o in P[-2:]:
                dj.xform(o, loc=tops[9])
        # roots spilling over the front lip
        lip = max((v.co for v in ob.data.vertices if v.co.y < 0), key=lambda c: c.z)
        P += hanging_roots('hr', m['roots'], (lip.x * 0.5, -sy * 0.55, sz * 0.92), sz * 0.6, 6, seed + 4, spread=sx * 0.35)
        P += glow_cluster('fg', m['glow_v'], m['glow_s'], (sx * 0.3, -sy * 0.6, 0), 5, seed + 5, 0.12, 0.25, 0.3)
        return P, 1024, True
    return build


def b_boulder(seed, sx, sy, sz, extras=0):
    def build():
        m = M()
        ob = rock('boulder', sx, sy, sz, m['stone2'], seed=seed, subdiv=3, amp=0.3, terrace=0.25, step=sz * 0.2)
        P = [ob]
        tops = top_points(ob, 6, seed + 1, 0.6)
        P += moss_pads('mp', m['moss'], tops[:3], seed, r=(0.2 * sx, 0.3 * sx), h=(0.05, 0.1))
        if extras >= 1 and len(tops) > 3:
            P += glow_cluster('gc', m['glow'], m['glow_s'], tops[3], 4, seed + 2, 0.1, 0.22)
        if extras >= 2:
            P += bracket_on_faces('sh', m['shelf'], ob, 2, seed + 3, 0.18, 0.3)
            P += glow_cluster('fg', m['rust'], m['stalk'], (sx * 0.45, -sy * 0.3, 0), 3, seed + 4, 0.12, 0.22, 0.12)
        return P, 1024 if sx > 1.5 else 512, extras >= 1 or True
    return build


def b_giant(seed, kind):
    def build():
        m = M()
        P = []
        if kind == 'a':      # violet bell with glowing warts, a younger one at its foot
            P += mushroom('big', 5.6, 2.3, 0.42, m['violet'], m['stalk'], shape='bell', cap_h=2.0, lean=(0.08, 0.05), segs=28, seed=seed)
            sm = mushroom('small', 2.2, 0.9, 0.18, m['violet'], m['stalk'], shape='bell', cap_h=0.8, lean=(-0.2, -0.1), segs=20, seed=seed + 1)
            for o in sm:
                dj.xform(o, loc=(1.2, -0.6, 0))
            P += sm
        elif kind == 'b':    # ochre parasol, gills glowing teal
            P += mushroom('big', 4.8, 2.6, 0.36, m['ochre'], m['stalk'], shape='flat', cap_h=0.9, lean=(-0.1, 0.06), segs=28, seed=seed, droop=0.12)
        else:                # three slender pale caps with violet-glowing gills
            for i, (x, y, h, r) in enumerate(((0, 0, 4.4, 1.3), (1.0, 0.4, 3.2, 0.95), (-0.8, 0.5, 2.6, 0.8))):
                parts = mushroom(f'm{i}', h, r, 0.2 * r / 1.3 + 0.08, m['pale'], m['stalk'], shape='dome', cap_h=r * 0.55,
                                 lean=(x * 0.12, y * 0.1), segs=22, seed=seed + i)
                for o in parts:
                    dj.xform(o, loc=(x, y, 0))
                P += parts
        P += ground_roots('gr', m['roots'], (0, 0, 0), 6, 0.9, 1.6, seed + 3, rad=0.1)
        P += moss_pads('mp', m['moss'], [Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 0)) for a in (0.4, 2.2, 4.1)], seed, r=(0.3, 0.5))
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.7, -0.5, 0), 5, seed + 4, 0.1, 0.24, 0.25)
        return P, 1024, True
    return build


def b_shelf_trunk(seed):
    def build():
        m = M()
        st = dj.tube('trunk', [(0, 0, -0.2), (0.05, 0.02, 1.2), (-0.05, 0.08, 2.4), (0.06, 0.04, 3.4)], 0.45, 14, m['wood'],
                     radii=[0.62, 0.5, 0.42, 0.34])
        dj.warp(st, 0.06, 1.5, seed=seed)
        dj.store_rest(st)
        top = dj.cyl('top', 0.36, 0.25, 12, r2=0.15, loc=(0.06, 0.04, 3.35), mat=m['wood'])
        dj.warp(top, 0.08, 4.0, seed=seed + 1)
        P = [st, top]
        R = random.Random(seed)
        for i in range(5):
            a = R.uniform(0, 360)
            z = R.uniform(0.6, 3.1)
            d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
            P += shelf_tiers(f't{i}_', m['shelf'] if i % 2 else m['shelf_v'], d * 0.42 + Vector((0, 0, z)), a, R.uniform(0.35, 0.6), 3, seed + i * 5)
        P += ground_roots('gr', m['roots'], (0, 0, 0), 5, 0.8, 1.3, seed + 2, rad=0.14)
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.0, 0.0, 3.45), 4, seed + 7, 0.1, 0.22, 0.15)
        return P, 1024, True
    return build


def b_root_curtain(seed):
    def build():
        m = M()
        ledge = slab_rock('ledge', 3.6, 1.1, 1.5, m['stone'], seed=seed, cuts=6, amp=0.25, top_amp=0.12, terrace=0.3)
        P = [ledge]
        R = random.Random(seed)
        # thick roots arching from the ledge top down to the ground in front, a curtain of fine ones between
        for i in range(7):
            x = -1.6 + i * 0.53 + R.uniform(-0.1, 0.1)
            pts = [Vector((x, 0.2, 1.45)), Vector((x + R.uniform(-0.1, 0.1), -0.45, 1.5)), Vector((x, -0.8, 1.0)),
                   Vector((x + R.uniform(-0.15, 0.15), -0.95, 0.4)), Vector((x, -1.05, -0.05))]
            P.append(dj.tube(f'ar{i}', pts, 0.1, 7, m['roots'], radii=[0.14, 0.12, 0.1, 0.09, 0.11]))
        P += hanging_roots('hr', m['roots'], (0, -0.62, 1.48), 1.2, 14, seed + 2, spread=1.7, rad=0.035)
        P += moss_pads('mp', m['moss'], top_points(ledge, 5, seed + 3), seed, r=(0.3, 0.55))
        P += glow_cluster('gc', m['glow'], m['glow_s'], (-0.9, -1.0, 0), 4, seed + 4, 0.1, 0.22, 0.2)
        P += glow_cluster('gv', m['glow_v'], m['glow_s'], (1.1, -0.95, 0), 3, seed + 5, 0.1, 0.2, 0.2)
        return P, 1024, True
    return build


def b_gate_post(seed):
    def build():
        m = M()
        ob = slab_rock('post', 0.6, 0.55, 2.1, m['stone2'], seed=seed, cuts=4, amp=0.08, top_amp=0.05, terrace=0.3, step=0.3)
        P = [ob]
        P += mushroom('cap', 0.55, 0.42, 0.06, m['glow'], m['glow_s'], shape='bell', cap_h=0.34, lean=(0.05, -0.1), segs=16, seed=seed)
        for o in P[-2:]:
            dj.xform(o, loc=(0.02, 0.0, 2.05))
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.0, 0.0, 2.08), 3, seed + 1, 0.1, 0.2, 0.15)
        P += hanging_roots('hr', m['roots'], (0, -0.2, 2.0), 1.1, 4, seed + 2, spread=0.25, rad=0.03)
        P += moss_pads('mp', m['moss'], [Vector((0.25, -0.3, 0.0)), Vector((-0.3, 0.2, 0.0))], seed)
        return P, 512, True
    return build


def b_ruin(seed):
    def build():
        m = M()
        stone = mats.stone('fh_ruin', base='#6f6878', light='#958ca2', dark='#2a2433', warm='#8a7c7a', patches='#4b4558',
                           moss=0.5, lichen=0.4, seed=seed, blocks=(0.55, 0.3, 0.012))
        P = []
        for i, (x, h) in enumerate(((-1.2, 2.6), (1.2, 1.4))):
            c = dj.box(f'col{i}', 0.6, 0.6, h, loc=(x, 0, 0), mat=stone, cuts=3)
            dj.bevel(c, 0.04, 2, 35)
            dj.warp(c, 0.03, 2.0, seed=seed + i)
            P.append(c)
        lin = dj.box('lintel', 1.9, 0.55, 0.45, loc=(-0.55, 0, 2.55), rot=(0, 14, 0), mat=stone, cuts=2)
        dj.warp(lin, 0.03, 2.0, seed=seed + 3)
        P.append(lin)
        for i in range(4):
            r = dj.ico(f'rub{i}', 0.25, 1, loc=(0.4 + i * 0.25, -0.3 + (i % 2) * 0.5, 0.08), scale=(1.2, 0.9, 0.6), mat=stone)
            dj.warp(r, 0.05, 4, seed=i)
            P.append(r)
        for o in P:
            dj.store_rest(o)
        P += hanging_roots('hr', m['roots'], (-1.0, -0.3, 2.6), 1.4, 6, seed + 2, spread=0.6, rad=0.04)
        P += mushroom('m', 1.4, 0.55, 0.09, m['violet'], m['stalk'], shape='bell', cap_h=0.5, lean=(-0.2, -0.1), seed=seed)
        for o in P[-2:]:
            dj.xform(o, loc=(0.2, -0.5, 0))
        P += glow_cluster('gc', m['glow'], m['glow_s'], (1.2, -0.1, 1.42), 4, seed + 4, 0.1, 0.2, 0.15)
        P += moss_pads('mp', m['moss'], [Vector((-1.2, 0, 2.62)), Vector((1.2, 0, 1.42))], seed, r=(0.25, 0.32))
        return P, 1024, True
    return build


def b_ridge(seed):
    """WallPanel slot (template glyph 'P'): an irregular natural rock-and-root ridge, not a panel. A chain of merged,
    tilted boulder lobes with a craggy crest and tilted strata (ridge_common.ridge_body), a rubbly rooty foot, fungal
    roots and moss draped over it, glowcaps and shelf fungi. x ~+-1.12 (rounded ends overlap the neighbours), 3.12 m
    tall (the placer sinks it 0.6-1.2 m), core depth ~+-0.2 with the foot to ~+-0.34."""
    def build():
        import ridge_common as rc
        m = M()
        R = random.Random(seed)
        ob = rc.ridge_body('ridge', m['stone'], seed)
        bvh = rc.bvh_of(ob)
        P = [ob]
        # roots draped over the crest, down the front (camera side) and a couple down the back
        for i, x in enumerate((-0.75, -0.1, 0.6)):
            r = rc.drape_root(f'dr{i}', bvh, x + R.uniform(-0.1, 0.1), m['roots'], seed + i, back=R.uniform(20, 45),
                              phi1=R.uniform(-85, -120), rad=R.uniform(0.035, 0.055), wig=R.uniform(0.1, 0.2),
                              drift=R.uniform(-0.45, 0.45))
            if r: P.append(r)
        for i, x in enumerate((-0.45, 0.6)):
            r = rc.drape_root(f'db{i}', bvh, x, m['roots'], seed + 10 + i, back=-25, phi1=R.uniform(105, 120), rad=0.05)
            if r: P.append(r)
        # rooty foot: tumbled stones and roots spreading out over the ground on both sides
        # (the placer sinks the piece 0.6-1.2 m: the visible foot is around z 0.6-1.4, so the foot dressing lives there)
        tal, th = rc.talus('rb', m['stone2'], bvh, seed + 3, n=9, rmin=0.08, rmax=0.14)
        P += tal
        for i, x in enumerate((-0.7, 0.1, 0.8)):
            for side in (-1, 1):
                p0, _ = rc.side_hit(bvh, x, 1.7, side)
                if p0 is None:
                    continue
                pts = [p0, p0 + Vector((R.uniform(-0.1, 0.1), side * 0.06, -0.4)), p0 + Vector((R.uniform(-0.2, 0.2), side * 0.16, -0.8)),
                       Vector((p0.x + R.uniform(-0.25, 0.25), side * 0.3, 0.4))]
                t = dj.tube(f'fr{i}{side}', pts, 0.06, 6, m['roots'], radii=[0.06, 0.055, 0.045, 0.03])
                dj.store_rest(t)
                P.append(t)
        # moss over the crest and on the ledges of the front face
        crest = rc.crest_points(bvh, [R.uniform(-0.95, 0.95) for _ in range(7)], y=R.uniform(-0.05, 0.05))
        P += rc.moss_on('mc', m['moss'], crest[:3], seed + 4, r=(0.12, 0.2), h=(0.03, 0.05))
        ledges = [rc.surf(bvh, R.uniform(-0.9, 0.9), R.uniform(-30, -60)) for _ in range(3)]
        P += rc.moss_on('ml', m['moss'], ledges, seed + 5, r=(0.1, 0.16), h=(0.03, 0.05))
        # glowcaps on the crest and at the foot, shelf fungi stepping up the front face
        # glowcaps (low-poly): a small clump in a crest notch, another at the front foot
        spots = [(crest[5][0] - Vector((0, 0, 0.02)), 2, m['glow']) if len(crest) > 5 else None,
                 (th[0][0] if th else Vector((0, -0.36, 0.9)), 3, m['glow_v'])]
        for j, sp in enumerate(s_ for s_ in spots if s_):
            base, n, cm = sp
            for i in range(n):
                h = R.uniform(0.1, 0.22)
                a_ = R.uniform(0, 6.28)
                parts = mushroom(f'g{j}{i}', h, h * R.uniform(0.32, 0.45), h * 0.07, cm, m['glow_s'], lean=(R.uniform(-0.25, 0.25), R.uniform(-0.25, 0.25)),
                                 segs=8, seed=seed * 7 + j * 5 + i)
                for o in parts:
                    dj.xform(o, loc=base + Vector((math.cos(a_), math.sin(a_), 0)) * R.uniform(0, 0.12))
                P += parts
        for i, (x, z) in enumerate(((-0.5, 1.9), (0.45, 1.5))):
            p, nr = rc.side_hit(bvh, x, z, -1)
            if p is not None:
                P += shelf_tiers(f'sh{i}_', m['shelf'], p - nr * 0.03, yaw_of(nr), R.uniform(0.15, 0.22), 2, seed + 30 + i, dz=0.14)
        p, nr = rc.side_hit(bvh, 0.2, 1.7, 1)
        if p is not None:
            P += shelf_tiers('sb_', m['shelf_v'], p - nr * 0.03, yaw_of(nr), 0.18, 2, seed + 40, dz=0.13)
        return P, 1024, True
    return build


def stalag_mesh(m, h, broken, seed, r=0.42):
    k = r / 0.42
    prof = [(0.42 * k, -0.1), (0.4 * k, 0.15), (0.34 * k, h * 0.3), (0.27 * k, h * 0.55), (0.18 * k, h * 0.8)]
    prof += [(0.2 * k, h * 0.98), (0.0, h * 0.92)] if broken else [(0.08 * k, h * 0.96), (0.0, h)]
    ob = dj.lathe('stg', prof, 14, m['stone'], cap_bottom=False, cap_top=False)
    dj.warp(ob, 0.06 * k, 1.8 / k, seed=seed)
    for v in ob.data.vertices:
        v.co.z += (round(v.co.z / 0.32) * 0.32 - v.co.z) * 0.35
    ob.data.update()
    dj.store_rest(ob)
    return ob


def b_stalagmite(seed, broken=False):
    def build():
        m = M()
        h = 1.6 if broken else 3.0
        ob = stalag_mesh(m, h, broken, seed)
        P = [ob]
        P += bracket_on_faces('sh', m['shelf'], ob, 2, seed + 1, 0.16, 0.24, facing=(0, -1, 0), tiers=2)
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.3, -0.25, 0), 3, seed + 2, 0.08, 0.18, 0.1)
        if broken:
            P += glow_cluster('gt', m['glow_v'], m['glow_s'], (0, 0, h * 0.95), 3, seed + 3, 0.08, 0.16, 0.08)
        P += moss_pads('mp', m['moss'], [Vector((-0.3, 0.2, 0))], seed)
        return P, 512, True
    return build


def _unused_old_stalagmite(seed, broken=False):
    def build():
        m = M()
        h = 1.6 if broken else 3.0
        prof = [(0.42, -0.1), (0.4, 0.15), (0.34, h * 0.3), (0.27, h * 0.55), (0.18, h * 0.8)]
        prof += [(0.2, h * 0.98), (0.0, h * 0.92)] if broken else [(0.08, h * 0.96), (0.0, h)]
        ob = dj.lathe('stg', prof, 14, m['stone'], cap_bottom=False, cap_top=False)
        dj.warp(ob, 0.06, 1.8, seed=seed)
        for v in ob.data.vertices:
            v.co.z += (round(v.co.z / 0.32) * 0.32 - v.co.z) * 0.35
        ob.data.update()
        dj.store_rest(ob)
        P = [ob]
        P += bracket_on_faces('sh', m['shelf'], ob, 2, seed + 1, 0.16, 0.24, facing=(0, -1, 0), tiers=2)
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.3, -0.25, 0), 3, seed + 2, 0.08, 0.18, 0.1)
        if broken:
            P += glow_cluster('gt', m['glow_v'], m['glow_s'], (0, 0, h * 0.95), 3, seed + 3, 0.08, 0.16, 0.08)
        P += moss_pads('mp', m['moss'], [Vector((-0.3, 0.2, 0))], seed)
        return P, 512, True
    return build


def b_log(seed, hollow=False):
    """Coffin / CoffinOpen slot: a fallen rotting stalk-log along Y, 2.06 x 0.82 (hollow: 2.0 x 0.75, open on top)."""
    def build():
        m = M()
        L, r = (2.0, 0.34) if hollow else (2.06, 0.38)
        lg = dj.tube('log', [(0, -L / 2, r), (0.03, 0, r * 1.05), (0, L / 2, r * 0.95)], r, 14, m['wood'], radii=[r * 1.05, r, r * 0.92])
        dj.warp(lg, 0.04, 2.0, seed=seed)
        dj.store_rest(lg)
        P = [lg]
        if hollow:
            dj.delete_faces(lg, lambda c, n_: c.z > r * 1.55 and abs(c.y) < L * 0.42)
            inner = dj.tube('inner', [(0, -L * 0.45, r * 1.05), (0, L * 0.45, r * 1.05)], r * 0.8, 12, mats.void('fh_dark', c='#14100f'),
                            cap=False)
            P.append(inner)
            P += glow_cluster('gin', m['glow'], m['glow_s'], (0, 0.1, r * 0.55), 6, seed + 1, 0.08, 0.18, 0.3)
        P += shelf_tiers('s1', m['shelf'], (r * 0.95, 0.3, r * 1.1), -90, 0.22, 2, seed + 2)
        P += shelf_tiers('s2', m['shelf_v'], (-r * 0.95, -0.4, r * 1.0), 90, 0.18, 2, seed + 3)
        P += glow_cluster('gt', m['rust'], m['stalk'], (0.05, 0.55, r * 1.9), 3, seed + 4, 0.08, 0.16, 0.12)
        P += moss_pads('mp', m['moss'], [Vector((0, -0.5, r * 1.9)), Vector((0.05, 0.2, r * 1.95))], seed, r=(0.15, 0.22))
        return P, 512, True
    return build


def b_slab(seed):
    def build():
        m = M()
        ob = slab_rock('slab', 1.6, 0.62, 0.48, m['stone2'], seed=seed, cuts=4, amp=0.06, top_amp=0.05, terrace=0.0)
        P = [ob]
        P += moss_pads('mp', m['moss'], top_points(ob, 3, seed + 1, 0.8), seed, r=(0.15, 0.25))
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.7, -0.32, 0), 3, seed + 2, 0.08, 0.15, 0.08)
        return P, 512, True
    return build


def b_puffball(seed, small=False):
    def build():
        m = M()
        R = random.Random(seed)
        P = []
        spec = [(0, 0, 0.32), (0.38, 0.12, 0.2), (-0.3, 0.2, 0.17), (0.12, -0.33, 0.12)] if not small else [(0, 0, 0.12), (0.14, 0.06, 0.08), (-0.1, 0.1, 0.06)]
        for i, (x, y, r) in enumerate(spec):
            s = dj.sphere(f'p{i}', r, 16, 10, loc=(x, y, r * 0.8), scale=(1.0, 1.0, 0.85), mat=m['puff'])
            dj.warp(s, r * 0.06, 3.0 / r, seed=seed + i)
            dj.store_rest(s)
            P.append(s)
        if not small:
            P += moss_pads('mp', m['moss'], [Vector((0.1, 0.25, 0)), Vector((-0.2, -0.2, 0))], seed, r=(0.18, 0.28))
        return P, 512 if not small else 256, False
    return build


def b_spore_mound(seed):
    def build():
        m = M()
        mound = dj.cushion('mound', 1.0, 0.45, (0, 0, 0), fm.cave_stone('fh_soil', seed=7, moss=0.65, glow=0.2, base='#4a3f44',
                                                                         light='#6c5d60', strata=0.0), seed=seed, segs=18)
        dj.xform(mound, scale=(1.3, 0.9, 1.0))
        dj.store_rest(mound)
        P = [mound]
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.2, 0.0, 0.4), 6, seed + 1, 0.1, 0.24, 0.35)
        P += glow_cluster('gr', m['rust'], m['stalk'], (-0.6, -0.2, 0.15), 3, seed + 2, 0.1, 0.2, 0.2)
        P += [dj.sphere('pf', 0.16, 12, 8, loc=(0.7, 0.25, 0.2), mat=m['puff'])]
        return P, 512, True
    return build


def b_capstone(seed, kind):
    """Headstones slot: small upright pieces (0.9-1.3 m; e/f are the bigger 'g' boss-arena pieces ~1.6 m)."""
    def build():
        m = M()
        P = []
        if kind == 'a':
            ob = rock('stub', 0.55, 0.4, 0.9, m['stone2'], seed=seed, subdiv=2, amp=0.2)
            P.append(ob)
            P += glow_cluster('t', m['rust'], m['stalk'], (0.05, -0.05, 0.85), 3, seed + 1, 0.12, 0.22, 0.1)
        elif kind == 'b':
            P.append(stalag_mesh(m, 1.15, False, seed, r=0.24))
            P += glow_cluster('g', m['glow'], m['glow_s'], (0.2, -0.2, 0), 3, seed, 0.08, 0.16, 0.1)
        elif kind == 'c':
            for i, (x, y, h) in enumerate(((0, 0, 1.15), (0.22, 0.1, 0.8), (-0.18, 0.08, 0.6))):
                parts = mushroom(f'm{i}', h, 0.17 + h * 0.08, 0.04, m['violet'], m['stalk'], shape='bell', cap_h=0.2,
                                 lean=(x * 0.4, -0.05), segs=14, seed=seed + i)
                for o in parts:
                    dj.xform(o, loc=(x, y, 0))
                P += parts
        elif kind == 'd':
            ob = rock('rk', 0.8, 0.5, 1.0, m['stone'], seed=seed, subdiv=2, amp=0.25, terrace=0.4, step=0.2)
            P.append(ob)
            P += shelf_tiers('s', m['shelf'], (0.0, -0.2, 0.75), 0, 0.25, 3, seed + 2, dz=0.14)
        elif kind == 'e':
            ob = slab_rock('stand', 0.7, 0.45, 1.6, m['stone'], seed=seed, cuts=4, amp=0.1, top_amp=0.12, terrace=0.4, step=0.25)
            P.append(ob)
            P += glow_cluster('g', m['glow'], m['glow_s'], (0.0, 0.0, 1.55), 4, seed + 1, 0.1, 0.2, 0.12)
            P += glow_cluster('f', m['glow_v'], m['glow_s'], (0.3, -0.3, 0), 3, seed + 2, 0.08, 0.16, 0.1)
        else:
            P += mushroom('m', 1.6, 0.7, 0.12, m['rust'], m['stalk'], shape='dome', cap_h=0.45, lean=(0.05, -0.08), segs=20, seed=seed)
            P += glow_cluster('f', m['glow'], m['glow_s'], (0.3, -0.2, 0), 4, seed + 2, 0.08, 0.18, 0.12)
        P += moss_pads('mp', m['moss'], [Vector((0.15, -0.2, 0)), Vector((-0.2, 0.15, 0))], seed, r=(0.12, 0.2))
        return P, 512, True
    return build


def b_glowcap(seed, kind):
    """Candles slot (and scatter): clusters of bioluminescent caps."""
    def build():
        m = M()
        if kind == 'a':
            P = glow_cluster('g', m['glow'], m['glow_s'], (0, 0, 0), 7, seed, 0.12, 0.34, 0.16)
        elif kind == 'b':
            P = glow_cluster('g', m['glow_v'], m['glow_s'], (0, 0, 0), 5, seed, 0.14, 0.4, 0.12, shape='bell')
        else:
            P = glow_cluster('g', m['glow'], m['glow_s'], (0, 0, 0), 3, seed, 0.07, 0.15, 0.06)
        P += moss_pads('mp', m['moss'], [Vector((0, 0, 0))], seed, r=(0.12, 0.18), h=(0.03, 0.05))
        return P, 256, True
    return build


def b_toadstools(seed):
    def build():
        m = M()
        P = glow_cluster('t', m['rust'], m['stalk'], (0, 0, 0), 5, seed, 0.1, 0.28, 0.18)
        P += moss_pads('mp', m['moss'], [Vector((0.05, 0, 0))], seed, r=(0.15, 0.2), h=(0.03, 0.05))
        return P, 256, False
    return build


def b_moss_tuft(seed):
    def build():
        m = M()
        R = random.Random(seed)
        P = moss_pads('mp', m['moss'], [Vector((R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3), 0)) for _ in range(4)], seed, r=(0.15, 0.32), h=(0.04, 0.1))
        return P, 256, False
    return build


def b_bracket_small(seed):
    def build():
        m = M()
        stub = dj.tube('stub', [(0, 0, -0.1), (0.02, 0, 0.25), (0, 0.02, 0.45)], 0.12, 10, m['wood'], radii=[0.16, 0.12, 0.1])
        dj.store_rest(stub)
        P = [stub] + shelf_tiers('s', m['shelf'], (0, -0.1, 0.4), 0, 0.2, 3, seed, dz=0.11)
        P += shelf_tiers('v', m['shelf_v'], (0.1, 0.08, 0.3), 160, 0.14, 2, seed + 3, dz=0.1)
        return P, 256, True
    return build


def b_lamp(seed):
    """LanternPost slot: a tall stalk curling over toward -Y with a glowing bulb hanging at (0, -0.56, ~1.5);
    the placer puts its light at (front 0.56, 1.6 m)."""
    def build():
        m = M()
        path = [Vector((0, 0.05, -0.15)), Vector((0, 0.05, 0.6)), Vector((0, 0.0, 1.4)), Vector((0, -0.12, 1.95)),
                Vector((0, -0.38, 2.18)), Vector((0, -0.56, 2.08))]
        st = dj.tube('stalk', path, 0.08, 10, m['stalk'], radii=[0.16, 0.11, 0.09, 0.08, 0.07, 0.06])
        dj.warp(st, 0.01, 3.0, seed=seed)
        dj.store_rest(st)
        P = [st]
        cp = dj.lathe('hood', cap_profile(0.3, 0.26, 0.05, 'bell'), 16, m['pale'], cap_bottom=True, cap_top=False)
        dj.store_rest(cp)
        dj.xform(cp, rot=(180 - 25, 0, 0), loc=(0, -0.56, 2.1))
        P.append(cp)
        bulb = dj.sphere('bulb', 0.13, 14, 10, loc=(0, -0.56, 1.72), scale=(1, 1, 1.25), mat=m['glow'])
        dj.store_rest(bulb)
        P.append(bulb)
        P.append(dj.tube('tether', [(0, -0.56, 1.98), (0.01, -0.56, 1.88), (0, -0.56, 1.86)], 0.012, 5, m['glow_s']))
        P += ground_roots('gr', m['roots'], (0, 0.05, 0), 4, 0.35, 0.6, seed + 1, rad=0.06)
        P += glow_cluster('gc', m['glow'], m['glow_s'], (0.2, 0.15, 0), 3, seed + 2, 0.08, 0.16, 0.08)
        P += moss_pads('mp', m['moss'], [Vector((-0.15, 0.1, 0))], seed)
        return P, 512, True
    return build


def b_great_cap(seed):
    """Mausoleum slot (landmark set piece ~5 x 5 m footprint): an ancient giant mushroom, 9 m tall, cap 4.2 m across
    radius, a root-hollow doorway in its foot facing -Y, shelf fungi up the stalk."""
    def build():
        m = M()
        P = mushroom('great', 8.6, 4.2, 1.05, m['violet'], m['stalk'], shape='bell', cap_h=3.2, lean=(0.04, 0.06), segs=36,
                     seed=seed, bulb=1.6)
        # doorway: a dark arch on the front of the stalk foot
        door = dj.extrude_xz('door', [(-0.45, 0), (0.45, 0)] + [(0.45 * math.cos(a), 1.2 + 0.45 * math.sin(a)) for a in _lin(0.0, math.pi, 9)],
                             0.4, mats.void('fh_hollow', c='#0a0709'), y=-1.42)
        dj.xform(door, loc=(0, 0, 0))
        dj.store_rest(door)
        P.append(door)
        for i in range(8):
            a = 2 * math.pi * i / 8 + 0.3
            d = Vector((math.cos(a), math.sin(a), 0))
            if d.y < -0.8:
                continue
            pts = [d * 1.1 + Vector((0, 0, 1.3)), d * 1.6 + Vector((0, 0, 0.6)), d * 2.3 + Vector((0, 0, 0.1)), d * 2.9 + Vector((0, 0, -0.1))]
            P.append(dj.tube(f'but{i}', pts, 0.3, 8, m['roots'], radii=[0.36, 0.3, 0.2, 0.1]))
        for k in range(4):
            a = [40, 140, 220, 320][k]
            d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
            P += shelf_tiers(f'st{k}_', m['shelf'] if k % 2 else m['shelf_v'], d * 1.0 + Vector((0, 0, 2.5 + k * 0.9)), a, 0.7, 3, seed + k)
        P += glow_cluster('g1', m['glow'], m['glow_s'], (1.0, -1.6, 0), 7, seed + 9, 0.12, 0.3, 0.4)
        P += glow_cluster('g2', m['glow_v'], m['glow_s'], (-1.2, -1.5, 0), 5, seed + 10, 0.12, 0.3, 0.35)
        P += moss_pads('mp', m['moss'], [Vector((math.cos(a) * 1.9, math.sin(a) * 1.9, 0)) for a in (0.2, 1.4, 2.8, 4.0, 5.3)], seed, r=(0.4, 0.7))
        return P, 2048, True
    return build


def b_breaker_nook(seed):
    """Dressing round breaker_panel.glb (same origin and facing): rock shoulders either side of its 2.3 x 2.7 m alcove,
    roots draping over the lintel, glowcaps at the feet. Keeps clear of |x| < 1.25 below z 2.75 in front."""
    def build():
        m = M()
        P = []
        for sg in (-1, 1):
            r = slab_rock(f'sh{sg}', 1.3, 1.4, 2.6 + 0.3 * sg, m['stone'], seed=seed + sg, cuts=5, amp=0.18, top_amp=0.2, terrace=0.4)
            dj.xform(r, loc=(sg * 1.95, 0.25, 0))
            dj.store_rest(r)
            P.append(r)
        cap = slab_rock('crown', 3.8, 1.5, 0.9, m['stone'], seed=seed + 5, cuts=5, amp=0.12, top_amp=0.3, terrace=0.2)
        dj.xform(cap, loc=(0, 0.45, 2.65))
        dj.store_rest(cap)
        P.append(cap)
        P += hanging_roots('hr', m['roots'], (0, -0.45, 3.3), 0.9, 10, seed + 2, spread=1.6, rad=0.035)
        P += shelf_tiers('s', m['shelf'], (-1.9, -0.45, 1.8), 0, 0.3, 3, seed + 3)
        P += glow_cluster('g1', m['glow'], m['glow_s'], (-1.35, -0.75, 0), 5, seed + 4, 0.1, 0.25, 0.18)
        P += glow_cluster('g2', m['glow'], m['glow_s'], (1.4, -0.7, 0), 4, seed + 5, 0.1, 0.22, 0.18)
        P += glow_cluster('g3', m['glow_v'], m['glow_s'], (0.6, 0.4, 3.4), 4, seed + 6, 0.1, 0.2, 0.3)
        P += moss_pads('mp', m['moss'], top_points(cap, 4, seed + 7), seed, r=(0.3, 0.5))
        return P, 1024, True
    return build


def b_tent_dressing(seed):
    """Dressing round camp_tent.glb (3.4 x 2.8 m tent, porch to y -2.6; same origin): glowcap clusters, moss, a few
    toadstools and roots at the corners, clear of the entrance (|x| < 1.6 for y < -1.7)."""
    def build():
        m = M()
        P = []
        spots = [(-1.9, -1.2), (1.95, -0.6), (1.8, 1.6), (-1.75, 1.9), (0.3, 2.1), (-2.3, -2.4), (2.2, -2.6)]
        for i, (x, y) in enumerate(spots):
            kind = i % 3
            if kind == 0:
                P += glow_cluster(f'g{i}', m['glow'], m['glow_s'], (x, y, 0), 5, seed + i, 0.1, 0.28, 0.2)
            elif kind == 1:
                P += glow_cluster(f't{i}', m['rust'], m['stalk'], (x, y, 0), 4, seed + i, 0.1, 0.24, 0.18)
            else:
                P += glow_cluster(f'v{i}', m['glow_v'], m['glow_s'], (x, y, 0), 4, seed + i, 0.12, 0.3, 0.2, shape='bell')
        P += moss_pads('mp', m['moss'], [Vector((x * 1.05, y * 1.05, 0)) for x, y in spots], seed, r=(0.3, 0.5))
        P += ground_roots('gr', m['roots'], (1.9, 1.8, 0), 3, 0.6, 1.0, seed + 9, rad=0.07)
        st = mushroom('tall', 1.5, 0.6, 0.1, m['violet'], m['stalk'], shape='bell', cap_h=0.5, lean=(0.15, 0.05), seed=seed)
        for o in st:
            dj.xform(o, loc=(-2.1, 1.2, 0))
        P += st
        return P, 1024, True
    return build


def b_spikes(seed):
    """Hurt terrain tile (D167 spike field in caverns lime): a 1 m round patch of dark ground with spike clusters; the
    game tiles / scales it over the patch."""
    def build():
        sp = fm.spike('fh_spike')
        R = random.Random(seed)
        P = []
        base = dj.cushion('ground', 0.55, 0.03, (0, 0, 0), sp, seed=seed, segs=14)
        dj.store_rest(base)
        P.append(base)
        for k in range(9):
            a = R.uniform(0, 6.28)
            d = R.uniform(0, 0.42)
            c = Vector((math.cos(a) * d, math.sin(a) * d, 0))
            for j in range(R.randint(2, 4)):
                h = R.uniform(0.18, 0.34)
                o = dj.cyl(f's{k}_{j}', R.uniform(0.025, 0.04), h, 6, r2=0.003, mat=sp)
                dj.store_rest(o)
                dj.xform(o, rot=(R.uniform(-18, 18), R.uniform(-18, 18), 0), loc=c + Vector((R.uniform(-0.05, 0.05), R.uniform(-0.05, 0.05), -0.01)))
                P.append(o)
        return P, 256, True
    return build


def b_sludge(seed):
    """Slow terrain patch (spore sludge): a 2 m wobbly blob of glossy goo with a raised lip; scaled per patch."""
    def build():
        s = fm.sludge('fh_sludge', seed=seed)
        prof = [(1.0, -0.02), (0.98, 0.03), (0.9, 0.05), (0.7, 0.045), (0.4, 0.04), (0.0, 0.04)]
        ob = dj.lathe('goo', prof, 32, s, cap_bottom=False, cap_top=False)
        R = random.Random(seed)
        ph = [R.uniform(0, 6.28) for _ in range(3)]
        for v in ob.data.vertices:
            a = math.atan2(v.co.y, v.co.x)
            k = 1 + 0.12 * math.sin(3 * a + ph[0]) + 0.07 * math.sin(5 * a + ph[1]) + 0.04 * math.sin(9 * a + ph[2])
            v.co.x *= k
            v.co.y *= k
        ob.data.update()
        dj.store_rest(ob)
        P = [ob]
        for i in range(6):
            a = R.uniform(0, 6.28)
            d = R.uniform(0.1, 0.75)
            b = dj.sphere(f'bub{i}', R.uniform(0.03, 0.07), 10, 6, loc=(math.cos(a) * d, math.sin(a) * d, 0.04), scale=(1, 1, 0.6), mat=s)
            dj.store_rest(b)
            P.append(b)
        return P, 512, True
    return build


KIT = {
    # boundary (BoundaryKit: Boulders / SmallRocks / Trees / Yews / Bushes / Ruins / GatePost)
    'fungal_cliff_a': b_cliff(11, 6.0, 2.4, 5.0),
    'fungal_cliff_b': b_cliff(23, 4.4, 2.0, 3.8),
    'fungal_boulder_a': b_boulder(31, 2.6, 2.2, 1.8, 2),
    'fungal_boulder_b': b_boulder(37, 1.9, 1.6, 1.3, 1),
    'fungal_boulder_c': b_boulder(41, 1.2, 1.0, 0.8, 0),
    'fungal_giant_mushroom_a': b_giant(51, 'a'),
    'fungal_giant_mushroom_b': b_giant(53, 'b'),
    'fungal_giant_mushroom_c': b_giant(57, 'c'),
    'fungal_shelf_trunk': b_shelf_trunk(61),
    'fungal_root_curtain': b_root_curtain(67),
    'fungal_gate_post': b_gate_post(71),
    'fungal_ruin': b_ruin(73),
    # interiors (template glyph slots)
    'fungal_ridge': b_ridge(81),
    'fungal_stalagmite': b_stalagmite(83),
    'fungal_stalagmite_broken': b_stalagmite(89, broken=True),
    'fungal_log': b_log(91),
    'fungal_log_hollow': b_log(93, hollow=True),
    'fungal_slab': b_slab(97),
    'fungal_puffball': b_puffball(101),
    'fungal_spore_mound': b_spore_mound(103),
    'fungal_capstone_a': b_capstone(107, 'a'),
    'fungal_capstone_b': b_capstone(109, 'b'),
    'fungal_capstone_c': b_capstone(113, 'c'),
    'fungal_capstone_d': b_capstone(127, 'd'),
    'fungal_capstone_e': b_capstone(131, 'e'),
    'fungal_capstone_f': b_capstone(137, 'f'),
    'fungal_glowcap_a': b_glowcap(139, 'a'),
    'fungal_glowcap_b': b_glowcap(149, 'b'),
    'fungal_glowcap_c': b_glowcap(151, 'c'),
    # scatter
    'fungal_toadstools': b_toadstools(157),
    'fungal_moss_tuft': b_moss_tuft(163),
    'fungal_bracket_small': b_bracket_small(167),
    'fungal_puffball_small': b_puffball(173, small=True),
    # set pieces
    'fungal_lamp': b_lamp(179),
    'fungal_great_cap': b_great_cap(181),
    'fungal_breaker_nook': b_breaker_nook(191),
    'fungal_tent_dressing': b_tent_dressing(193),
    # hazards
    'fungal_spikes': b_spikes(197),
    'fungal_sludge': b_sludge(199),
}


def run(name):
    dj.reset()
    parts, tex, emission = KIT[name]()
    for o in parts:
        if o.data.attributes.get('rest') is None:
            dj.store_rest(o)
    ob = dj.join(parts, name)
    dj.smooth(ob, 50)
    return dj.finish(ob, name, tex=tex, emission=emission, emission_strength=4.0, ao_dist=0.6, samples=32)


if __name__ == '__main__':
    args = [a for a in dj.script_args() if not a.startswith('--')]
    if '--list' in dj.script_args():
        print('\n'.join(KIT))
        sys.exit(0)
    names = args or list(KIT)
    failed = []
    for n in names:
        try:
            run(n)
        except Exception as e:  # keep going; report at the end
            import traceback
            traceback.print_exc()
            failed.append(n)
    print('FUNGAL KIT DONE; failed:', failed)

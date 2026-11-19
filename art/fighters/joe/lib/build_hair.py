"""Hair and beards fitted to each UBC body (Head-bone skinned GLBs).

blender -b --factory-startup --python build_hair.py -- [--styles a,b] [--bodies m,f] [--look]

Stock Quaternius styles are moved from the male head frame to the target body's head frame and conformed:
vertices near the skin keep their original distance from it (nothing sinks into the female scalp or floats
off her jaw); far vertices (buns, long ends) move rigidly. Custom styles are clumped strands built on the
face / scalp. Materials keep "Hair" in the name so HumanoidRig.TintHair colours them (textures are neutral).
Output: assets/custom/characters/hair/<style>_<m|f>.glb
"""
import bpy, bmesh, sys, os, math, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agcore as C
import agbuild as AB
import agctx
import aggeo as G
import agmats as M
import djlib as dj
from djlib import MB, NB, srgb
from mathutils import Vector, Matrix, noise
from mathutils.kdtree import KDTree
from agcore import smooth01, lerp

OUT_HAIR = os.path.join(C.OUT_CHAR, 'hair')
os.makedirs(OUT_HAIR, exist_ok=True)
STOCK = ['Hair_Buzzed', 'Hair_SimpleParted', 'Hair_Long', 'Hair_Buns', 'Hair_BuzzedFemale', 'Hair_Beard']
CUSTOM = ['Beard_Long', 'Beard_Braided', 'Hair_Mane', 'Beard_Goatee']


# ----------------------------------------------------------------------------------------------
def conform_stock(body, style):
    objs = dj.import_gltf(C.UBC + '/hair/' + style + '.gltf')
    harm = next(o for o in objs if o.type == 'ARMATURE')
    hm = [o for o in objs if o.type == 'MESH']
    Mh = harm.matrix_world @ harm.data.bones['Head'].matrix_local
    Fb = body.arm.matrix_world @ body.arm.data.bones['Head'].matrix_local
    T = Fb @ Mh.inverted()
    # male reference body for the original skin distances
    male = None
    if body.sex != 'm':
        marm, mms = dj.load_body(C.BODY_FILES['m'])
        mbody = next(o for o in mms if o.name.lower().startswith('superhero'))
        male = dj.bvh_from([mbody])
        dj.delete(mms + [marm])
    out = []
    for o in hm:
        o.modifiers.clear()
        o.parent = None
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        if male is not None:
            me = o.data
            n = len(me.vertices)
            disp = []
            for v in me.vertices:
                p = v.co.copy()
                loc, nrm, idx, d = male.find_nearest(p, 0.2)
                q = T @ p
                if loc is None:
                    disp.append(Vector())
                    continue
                sd = (p - loc).dot(nrm)
                loc2, nrm2, idx2, d2 = body.bvh.find_nearest(q, 0.2)
                if loc2 is None:
                    disp.append(Vector())
                    continue
                target = loc2 + nrm2 * max(sd, 0.0015)
                w = 1 - smooth01(abs(sd), 0.025, 0.06)
                disp.append((target - q) * w)
            adj = dj.adjacency(me)
            for _ in range(4):
                disp = [(disp[i] + sum((disp[j] for j in adj[i]), Vector()) / max(len(adj[i]), 1)) * 0.5 if adj[i] else disp[i]
                        for i in range(n)]
            for v, dv in zip(me.vertices, disp):
                v.co = T @ v.co + dv
            dj.push_out(o, body.bvh, 0.0015, iters=3)
        out.append(o)
    bpy.data.objects.remove(harm, do_unlink=True)
    for o in out:
        dj.set_weights_rigid(o, 'Head')
        for m in o.data.materials:
            if 'Hair' not in m.name:
                m.name = 'Hair_' + m.name
    return out


def export_hair(body, objs, name):
    arm = body.arm
    for o in objs:
        for m in o.data.materials:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.size[0] > 1024:
                    n.image.scale(1024, 1024)
    for o in objs:
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        mm = o.modifiers.new('Armature', 'ARMATURE')
        mm.object = arm
        o.name = name
        o.data.name = name
    path = os.path.join(OUT_HAIR, '%s_%s.glb' % (name, body.sex))
    dj.export_glb(path, objs + [arm], skinned=True)
    return path


# ----------------------------------------------------------------------------------------------
# custom clumped strands
# ----------------------------------------------------------------------------------------------
def clump(mb, pts, r0, r1, flat=0.6, sides=5):
    n = len(pts)
    radii = [(lerp(r0, r1, (i / (n - 1)) ** 0.8), lerp(r0, r1, (i / (n - 1)) ** 0.8) * flat) for i in range(n)]
    mb.sweep(pts, radii, sides=sides, cap0='flat', cap1='round', cap_segs=1)


def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(n):
        t = i / (n - 1)
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return out


def skin_point(body, x, z, y_front=-0.3):
    """Point on the face skin seen from the front at (x, z)."""
    loc, n, i, d = body.bvh.ray_cast(Vector((x, y_front, z)), Vector((0, 1, 0)), 0.5)
    return (loc, n) if loc is not None else (None, None)


def beard_roots(body, dens=1.0, top=0.0, cheeks=True):
    L = body.L
    nose, chin = L['nose'], L['chin']
    roots = []
    rnd = random.Random(3)
    zt = nose.z - 0.035 + top
    for k in range(int(70 * dens)):
        x = rnd.uniform(-0.062, 0.062)
        z = rnd.uniform(chin.z - 0.02, zt if abs(x) > 0.03 else nose.z - 0.045)
        # jaw line limit: the beard sits on the lower face
        if abs(x) > 0.045 and z > chin.z + 0.05 + (0.0 if cheeks else -0.03):
            continue
        p, n = skin_point(body, x, z)
        if p is None:
            continue
        mouth_z = (nose.z + chin.z) * 0.5 + 0.006
        if abs(x) < 0.022 and abs(z - mouth_z) < 0.01:
            continue
        roots.append((p, n))
    return roots


def build_beard_long(body, length=0.17, braids=0, spread=1.0, dens=1.0, curl=0.0):
    L = body.L
    chin = L['chin']
    mb = MB()
    tip = Vector((0, chin.y - 0.03, chin.z - length))
    rnd = random.Random(7)
    for p, n in beard_roots(body, dens):
        side = p.x / 0.06
        t_end = tip + Vector((side * 0.045 * spread + rnd.uniform(-0.012, 0.012), rnd.uniform(-0.01, 0.015),
                              rnd.uniform(0, 0.04) + abs(side) * 0.03))
        p1 = p + n * 0.022 + Vector((0, -0.01, -0.02))
        p2 = t_end + Vector((0, -0.02, 0.06))
        pts = bez(p - n * 0.002, p1, p2, t_end, 9)
        if curl:
            pts = [q + Vector((0, 0, 0)) + Vector((math.sin(i * 1.3 + p.x * 90) * curl, 0, 0)) for i, q in enumerate(pts)]
        clump(mb, pts, rnd.uniform(0.006, 0.009), 0.0015)
    # moustache: from under the nose out and down past the mouth corners
    nose = L['nose']
    for sx in (-1, 1):
        for k in range(5):
            x0 = sx * (0.004 + 0.005 * k)
            p, n = skin_point(body, x0, nose.z - 0.024 - 0.002 * k)
            if p is None:
                continue
            e = Vector((sx * (0.036 + 0.004 * k), p.y + 0.012, nose.z - 0.06 - 0.01 * k))
            pts = bez(p, p + n * 0.012 + Vector((sx * 0.01, 0, -0.004)), e + Vector((0, -0.01, 0.015)), e, 7)
            clump(mb, pts, 0.005, 0.0015)
    for bi in range(braids):
        sx = (-1 if bi == 0 else 1) * 0.016 if braids > 1 else 0.0
        top = Vector((sx, chin.y - 0.01, chin.z - length * 0.55))
        for k in range(9):
            c = top + Vector((math.sin(k * 0.9) * 0.003, -0.002 * k, -0.017 * k))
            mb.ellipsoid(c, (0.011 - 0.0006 * k, 0.009, 0.012), segs=7, rings=5)
        mb.box(top + Vector((0, -0.016, -0.16)), (0.012, 0.012, 0.01))
    ob = mb.to_object('beard')
    dj.push_out(ob, body.bvh, 0.003, iters=3)
    return ob


def build_mane(body):
    """Wild shoulder-length mane swept back from the forehead."""
    L = body.L
    hc = L['head_c']
    mb = MB()
    rnd = random.Random(11)
    for k in range(95):
        th = rnd.uniform(-math.pi, math.pi)          # 0 = front
        el = rnd.uniform(0.15, 1.45)
        if abs(th) < 0.75 and el < 0.75:
            continue
        d = Vector((math.sin(th) * math.cos(el), -math.cos(th) * math.cos(el), math.sin(el)))
        loc, n, i, dd = body.bvh.ray_cast(hc + d * 0.3, -d, 0.3)
        if loc is None:
            continue
        back = Vector((math.sin(th) * 0.06, 0.08, 0))
        end = Vector((loc.x * 1.6 + math.sin(th) * 0.05, hc.y + 0.1 + rnd.uniform(-0.03, 0.04),
                      L['neck'].z - 0.05 + rnd.uniform(-0.06, 0.03)))
        if abs(th) < 1.2:
            end = Vector((loc.x * 1.5, hc.y + 0.13, L['head'].z + rnd.uniform(-0.05, 0.03)))
        p1 = loc + n * 0.035 + back * 0.4
        p2 = end + Vector((0, -0.01, 0.07))
        pts = bez(loc - n * 0.004, p1, p2, end, 10)
        pts = [q + Vector((noise.noise(q * 25) * 0.008, noise.noise(q * 25 + Vector((5, 0, 0))) * 0.008, 0)) for q in pts]
        clump(mb, pts, rnd.uniform(0.011, 0.016), 0.002)
    ob = mb.to_object('mane')
    dj.push_out(ob, body.bvh, 0.004, iters=4)
    return ob


def build_goatee(body):
    L = body.L
    chin, nose = L['chin'], L['nose']
    mb = MB()
    rnd = random.Random(5)
    for k in range(26):
        x = rnd.uniform(-0.018, 0.018)
        z = rnd.uniform(chin.z - 0.012, chin.z + 0.022)
        p, n = skin_point(body, x, z)
        if p is None:
            continue
        e = Vector((x * 0.5, chin.y - 0.02, chin.z - 0.06 + rnd.uniform(0, 0.015)))
        clump(mb, bez(p, p + n * 0.012, e + Vector((0, -0.005, 0.02)), e, 7), 0.0045, 0.001)
    for sx in (-1, 1):
        for k in range(3):
            p, n = skin_point(body, sx * (0.005 + 0.006 * k), nose.z - 0.025)
            if p is None:
                continue
            e = Vector((sx * 0.03, p.y + 0.014, nose.z - 0.05))
            clump(mb, bez(p, p + n * 0.008, e + Vector((0, -0.006, 0.01)), e, 6), 0.0032, 0.001)
    ob = mb.to_object('goatee')
    dj.push_out(ob, body.bvh, 0.002, iters=3)
    return ob


def hair_material(name):
    """Neutral strand material (colour from the factor / TintHair)."""
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    strands = nb.noise(nb.mapping(co, scale=(60, 60, 8)), 6.0, 6, 0.7)
    base = nb.ramp(strands, [(0.25, srgb('#6a6a6a')), (0.55, srgb('#c8c8c8')), (0.8, srgb('#f2f2f2'))])
    cav = M.cavity(nb, 0.02)
    c = nb.mix(nb.mul(cav, 0.7), base, srgb('#202020'))
    nrm = nb.bump(strands, 0.7, 0.003)
    nb.finish(c, nb.add(0.45, nb.mul(strands, 0.2)), 0.0, nrm)
    return m


def build_custom(body, style, default_col='#5a3a22'):
    cx = agctx.Ctx(body)
    cx.begin('Hair_' + style, 'hair', 1024, dye=default_col, trim='#808080', set_id='hair')
    cx.piece.out_dir = OUT_HAIR
    cx.piece.file_name = '%s_%s.glb' % (style, body.sex)
    m = hair_material('Hair_%s_strands' % style)
    if style == 'Beard_Long':
        ob = build_beard_long(body, length=0.19, spread=1.0)
    elif style == 'Beard_Braided':
        ob = build_beard_long(body, length=0.13, braids=2, spread=0.7, dens=0.9)
    elif style == 'Hair_Mane':
        ob = build_mane(body)
    else:
        ob = build_goatee(body)
    cx.add(style, ob, m, 'dye', 'Head', edge=False)
    cx.piece.build(samples=8)
    path = cx.piece.export()
    return path


if __name__ == '__main__':
    a = C.args()
    styles = C.opt(a, '--styles', ','.join(STOCK + CUSTOM)).split(',')
    bodies = C.opt(a, '--bodies', 'm,f').split(',')
    for sex in bodies:
        for st in styles:
            dj.reset()
            body = C.Body(sex)
            if st in STOCK:
                objs = conform_stock(body, st)
                p = export_hair(body, objs, st)
            else:
                p = build_custom(body, st)
            dj.log('HAIR', st, sex, p)

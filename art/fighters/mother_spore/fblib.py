"""JoeBrawla fighter build library (Blender 5.2, headless).

Adapted from Dungeon Joe 3D's tools/blender/characters/djlib.py (geometry builder MB, material DSL NB, weight
transfer) plus new helpers for fighters: UBC body loading/reshaping (scale, bigger head and hands, long fingers),
direct procedural-material baking into per-material texture sets (colour, ORM with baked AO, normal, emission),
tint materials (base colour factor), UAL clip posing (three.js semantics: local rotations only) and export.

Conventions: metres, Blender Z-up, the character faces -Y (her left = +X); glTF export is Y-up facing +Z.
"""
import bpy, bmesh, math, os, sys, json, random, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler, noise
from mathutils.bvhtree import BVHTree

V = Vector
T0 = time.time()
BLENDER = r"C:\dev\AverageJoe\tools\blender\blender-5.2.3-windows-x64\blender.exe"
UBC = r"C:\dev\AverageJoe\_downloads\quaternius-universal-base-characters\x\Universal Base Characters[Standard]"
FEMALE = UBC + r"\Base Characters\Godot - UE\Superhero_Female_FullBody.gltf"
MALE = UBC + r"\Base Characters\Godot - UE\Superhero_Male_FullBody.gltf"
UBC_TEX = UBC + r"\Base Characters\Godot - UE"
UAL1 = r"C:\dev\AverageJoe\_downloads\quaternius-ual1\x\Universal Animation Library[Standard]\Unreal-Godot\UAL1_Standard.glb"
UAL2 = r"C:\dev\AverageJoe\_downloads\quaternius-ual2\x\Universal Animation Library 2[Standard]\Unreal-Godot\UAL2_Standard.glb"
JB = r"C:\dev\JoeBrawla"

UAL_BONES = ("root pelvis spine_01 spine_02 spine_03 neck_01 Head clavicle_l upperarm_l lowerarm_l hand_l index_01_l "
             "index_02_l index_03_l index_04_leaf_l middle_01_l middle_02_l middle_03_l middle_04_leaf_l pinky_01_l "
             "pinky_02_l pinky_03_l pinky_04_leaf_l ring_01_l ring_02_l ring_03_l ring_04_leaf_l thumb_01_l thumb_02_l "
             "thumb_03_l thumb_04_leaf_l clavicle_r upperarm_r lowerarm_r hand_r index_01_r index_02_r index_03_r "
             "index_04_leaf_r middle_01_r middle_02_r middle_03_r middle_04_leaf_r pinky_01_r pinky_02_r pinky_03_r "
             "pinky_04_leaf_r ring_01_r ring_02_r ring_03_r ring_04_leaf_r thumb_01_r thumb_02_r thumb_03_r "
             "thumb_04_leaf_r thigh_l calf_l foot_l ball_l ball_leaf_l thigh_r calf_r foot_r ball_r ball_leaf_r").split()
FINGERS = ('index', 'middle', 'ring', 'pinky', 'thumb')


def log(*a):
    print('[fb %6.1fs]' % (time.time() - T0), *a, flush=True)


def args():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


# ============================================================================================ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'


def gpu_setup(samples=16):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX', 'CUDA'):
            try:
                prefs.compute_device_type = t
                prefs.refresh_devices()
                devs = [d for d in prefs.devices if d.type == t]
                if devs:
                    for d in prefs.devices:
                        d.use = (d.type == t)
                    break
            except Exception:
                pass
        sc.cycles.device = 'GPU'
    except Exception as e:
        log('no cycles prefs', e)
    sc.cycles.samples = samples


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def deselect_all():
    for o in bpy.context.scene.objects:
        try:
            o.select_set(False)
        except Exception:
            pass


def activate(ob):
    deselect_all()
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE':
            continue
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e:
            log('modifier_apply failed', ob.name, m.name, e)
            ob.modifiers.remove(m)


def delete(obs):
    for o in list(obs):
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def import_gltf(path):
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path, bone_heuristic='BLENDER', disable_bone_shape=True)
    except TypeError:
        bpy.ops.import_scene.gltf(filepath=path, bone_heuristic='BLENDER')
    new = [o for o in bpy.data.objects if o not in before]
    for o in list(new):
        if o.type == 'MESH' and o.name.startswith('Icosphere') and o.parent is None and not o.vertex_groups:
            bpy.data.objects.remove(o, do_unlink=True)
            new.remove(o)
    return new


def rest_pose(arm):
    ad = arm.animation_data
    if ad:
        ad.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def triangulate(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(ob.data)
    bm.free()


def join(obs, name):
    obs = [o for o in obs if o is not None]
    if len(obs) == 1:
        obs[0].name = name
        obs[0].data.name = name
        return obs[0]
    activate(obs[0])
    for o in obs[1:]:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def mesh_from(name, verts, faces, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if smooth:
        me.shade_smooth()
    return ob


def copy_obj(ob, name):
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    c.modifiers.clear()
    link(c)
    return c


def set_attr(ob, name, values, domain='POINT'):
    me = ob.data
    a = me.attributes.get(name)
    if a is None:
        a = me.attributes.new(name, 'FLOAT', domain)
    a.data.foreach_set('value', np.asarray(values, np.float32))


def solidify(ob, thick, offset=-1.0, rim=True):
    m = ob.modifiers.new('sol', 'SOLIDIFY')
    m.thickness = thick
    m.offset = offset
    m.use_rim = rim
    m.use_even_offset = True
    m.use_quality_normals = True
    apply_mods(ob)


def subdivide(ob, levels=1, simple=False):
    m = ob.modifiers.new('ss', 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    if simple:
        m.subdivision_type = 'SIMPLE'
    apply_mods(ob)


def smooth_verts(ob, iters=3, factor=0.5, mask=None):
    """Laplacian smoothing of vertex positions (mask: per-vertex 0..1)."""
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(n, 3)
    ed = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ed)
    ed = ed.reshape(-1, 2)
    m = np.ones(n, np.float32) if mask is None else np.asarray(mask, np.float32)
    for _ in range(iters):
        acc = np.zeros_like(co)
        cnt = np.zeros(n, np.float32)
        np.add.at(acc, ed[:, 0], co[ed[:, 1]])
        np.add.at(acc, ed[:, 1], co[ed[:, 0]])
        np.add.at(cnt, ed[:, 0], 1)
        np.add.at(cnt, ed[:, 1], 1)
        avg = acc / np.maximum(cnt, 1)[:, None]
        co = co + (avg - co) * (factor * m)[:, None]
    me.vertices.foreach_set('co', co.ravel())
    me.update()


# ============================================================================================ geometry
def _perp(t):
    a = V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))
    return (a - t * a.dot(t)).normalized()


def frames_along(pts, up=None):
    n = len(pts)
    Ts = []
    for i in range(n):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == n - 1:
            d = pts[-1] - pts[-2]
        else:
            d = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        Ts.append(d.normalized())
    if up is None:
        N = _perp(Ts[0])
    else:
        up = V(up)
        N = (up - Ts[0] * up.dot(Ts[0]))
        N = N.normalized() if N.length > 1e-6 else _perp(Ts[0])
    out = []
    for i, T in enumerate(Ts):
        if i > 0:
            q = Ts[i - 1].rotation_difference(T)
            N = q @ N
            N = (N - T * N.dot(T)).normalized()
        B = T.cross(N).normalized()
        out.append((T, N, B))
    return out


def superellipse(a, e):
    c, s = math.cos(a), math.sin(a)
    if e == 2.0:
        return c, s
    p = 2.0 / e
    return math.copysign(abs(c) ** p, c), math.copysign(abs(s) ** p, s)


class MB:
    """bmesh accumulator with primitive builders (world space). Optional per-vertex float params 'pu','pv'."""

    def __init__(self):
        self.bm = bmesh.new()
        self.pu = self.bm.verts.layers.float.new('pu')
        self.pv = self.bm.verts.layers.float.new('pv')

    def v(self, co, u=0.0, w=0.0):
        vt = self.bm.verts.new(co)
        vt[self.pu] = u
        vt[self.pv] = w
        return vt

    def f(self, vs):
        try:
            return self.bm.faces.new(vs)
        except ValueError:
            return None

    def ring_bridge(self, r0, r1, closed=True):
        n = len(r0)
        for i in (range(n) if closed else range(n - 1)):
            j = (i + 1) % n
            self.f([r0[i], r0[j], r1[j], r1[i]])

    def fan(self, ring, center, flip=False, u=0.0, w=0.0):
        c = self.v(center, u, w)
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            self.f([ring[j], ring[i], c] if flip else [ring[i], ring[j], c])
        return c

    def sweep(self, pts, radii, sides=8, cap0='round', cap1='round', up=None, exp=2.0, rot=0.0, cap_segs=2,
              twist=0.0, us=None):
        """Tube along pts. radii: r or (rx, ry) per point. us: per-point 'pu' param (default 0..1 along)."""
        pts = [V(p) for p in pts]
        fr = frames_along(pts, up)
        rad = [(r, r) if not isinstance(r, (tuple, list)) else tuple(r) for r in radii]
        nP = len(pts)
        us = us or [i / max(1, nP - 1) for i in range(nP)]
        angs = [rot + 2 * math.pi * k / sides for k in range(sides)]

        def ring_at(p, T, N, B, rx, ry, tw, u):
            out = []
            for k, a in enumerate(angs):
                c, s = superellipse(a + tw, exp)
                out.append(self.v(p + N * (c * rx) + B * (s * ry), u, k / sides))
            return out

        rings = []
        for i, (p, (T, N, B), (rx, ry)) in enumerate(zip(pts, fr, rad)):
            rings.append(ring_at(p, T, N, B, rx, ry, twist * i / max(1, nP - 1), us[i]))
        for i in range(nP - 1):
            self.ring_bridge(rings[i], rings[i + 1])

        def cap(end):
            idx = 0 if end == 0 else nP - 1
            p = pts[idx]
            T, N, B = fr[idx]
            rx, ry = rad[idx]
            sgn = -1 if end == 0 else 1
            mode = cap0 if end == 0 else cap1
            ring = rings[idx]
            if mode is None:
                return
            if mode == 'flat':
                self.fan(ring, p, flip=(end == 0), u=us[idx])
                return
            prev = ring
            rr = min(rx, ry)
            tw = 0 if end == 0 else twist
            for k in range(1, cap_segs + 1):
                ph = (math.pi / 2) * k / (cap_segs + 1)
                q = p + T * (sgn * rr * math.sin(ph))
                nr = ring_at(q, T, N, B, rx * math.cos(ph), ry * math.cos(ph), tw, us[idx])
                if end == 0:
                    self.ring_bridge(nr, prev)
                else:
                    self.ring_bridge(prev, nr)
                prev = nr
            self.fan(prev, p + T * (sgn * rr), flip=(end == 0), u=us[idx])

        cap(0)
        cap(1)
        return rings

    def lathe(self, prof, segs=16, M=None, close_top=True, close_bot=True, rfn=None, us=None):
        """prof: list of (r, z) revolved around local Z. rfn(a, r, z) -> (r, z) per-vertex modulation."""
        M = M or Matrix.Identity(4)
        rings = []
        us = us or [i / max(1, len(prof) - 1) for i in range(len(prof))]
        for i, (r, z) in enumerate(prof):
            ring = []
            for k in range(segs):
                a = 2 * math.pi * k / segs
                rr, zz = (r, z) if rfn is None else rfn(a, r, z)
                ring.append(self.v(M @ V((rr * math.cos(a), rr * math.sin(a), zz)), us[i], k / segs))
            rings.append(ring)
        for i in range(len(rings) - 1):
            self.ring_bridge(rings[i], rings[i + 1])
        if close_bot and prof[0][0] > 1e-6:
            self.fan(rings[0], M @ V((0, 0, prof[0][1])), flip=True, u=us[0])
        if close_top and prof[-1][0] > 1e-6:
            self.fan(rings[-1], M @ V((0, 0, prof[-1][1])), u=us[-1])
        return rings

    def ellipsoid(self, c, r, segs=12, rings=8, M=None, hemi=False):
        r = (r, r, r) if not isinstance(r, (tuple, list, Vector)) else r
        k0 = rings // 2 if hemi else 0
        prof = []
        for k in range(k0, rings + 1):
            ph = -math.pi / 2 + math.pi * k / rings
            prof.append((math.cos(ph), math.sin(ph)))
        M0 = Matrix.Translation(V(c)) @ (M if M else Matrix.Identity(4)) @ Matrix.Diagonal((r[0], r[1], r[2], 1))
        prof2 = prof[1:-1] if not hemi else prof[:-1]
        rs = self.lathe(prof2, segs, M0, close_top=False, close_bot=False)
        if hemi:
            self.fan(rs[0], M0 @ V((0, 0, 0)), flip=True)
        else:
            self.fan(rs[0], M0 @ V((0, 0, -1)), flip=True)
        self.fan(rs[-1], M0 @ V((0, 0, 1)), u=1.0)
        return rs

    def grid(self, fn, nu, nv, closed_v=False, mask=None, uv=None):
        """Parametric surface fn(u, v) -> Vector; u rows 0..1, v cols 0..1. uv(u,v)->(pu,pv) params."""
        cols = nv if closed_v else nv + 1
        G = []
        for i in range(nu + 1):
            row = []
            for j in range(cols):
                u, w = i / nu, j / nv
                pu, pv = uv(u, w) if uv else (u, w)
                row.append(self.v(fn(u, w), pu, pv))
            G.append(row)
        for i in range(nu):
            for j in range(nv):
                if mask and not mask(i, j):
                    continue
                j1 = (j + 1) % cols
                self.f([G[i][j], G[i][j1], G[i + 1][j1], G[i + 1][j]])
        return G

    def to_object(self, name, smooth=True):
        me = bpy.data.meshes.new(name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        loose = [v for v in self.bm.verts if not v.link_faces]
        bmesh.ops.delete(self.bm, geom=loose, context='VERTS')
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(name, me)
        link(ob)
        if smooth:
            me.shade_smooth()
        return ob


def displace(ob, fn):
    """fn(co, normal) -> offset along normal (metres)."""
    me = ob.data
    me.update()
    for v in me.vertices:
        v.co += v.normal * fn(v.co, v.normal)
    me.update()


def nz(p, s=1.0, seed=0.0):
    return noise.noise(V((p[0] * s + seed, p[1] * s + seed * 0.7, p[2] * s + seed * 0.3)))


# ============================================================================================ body
class Body:
    """UBC body + its armature, reshaped for a fighter."""

    def __init__(self, path=FEMALE):
        objs = import_gltf(path)
        self.arm = next(o for o in objs if o.type == 'ARMATURE')
        self.arm.name = 'Armature'
        self.arm.data.name = 'Armature'
        for o in list(objs):
            if o.type == 'MESH' and o.name.startswith('Icosphere'):
                bpy.data.objects.remove(o, do_unlink=True)
                objs.remove(o)
        self.meshes = [o for o in objs if o.type == 'MESH']
        self.mesh = next(o for o in self.meshes if o.name.lower().startswith('superhero'))
        self.eyes = next((o for o in self.meshes if o.name.lower().startswith('eyes')), None)
        self.brows = next((o for o in self.meshes if o.name.lower().startswith('eyebrows')), None)
        for o in self.meshes:
            assert o.matrix_world == Matrix.Identity(4), o.name
            uvl = o.data.uv_layers
            while len(uvl) > 1:
                uvl.remove(uvl[-1])
            uvl[0].name = 'UVMap'
        rest_pose(self.arm)

    # ---- skeleton access
    def h(self, b):
        return self.arm.matrix_world @ self.arm.data.bones[b].head_local

    def t(self, b):
        return self.arm.matrix_world @ self.arm.data.bones[b].tail_local

    def edit_bones(self, fn):
        activate(self.arm)
        bpy.ops.object.mode_set(mode='EDIT')
        fn(self.arm.data.edit_bones)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.update()

    def scale_all(self, s):
        for o in self.meshes:
            me = o.data
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get('co', co)
            me.vertices.foreach_set('co', co * s)
            me.update()

        def f(eb):
            for b in eb:
                b.head = b.head * s
                b.tail = b.tail * s
        self.edit_bones(f)

    def reshape(self, groups, fn, bones=(), tails=()):
        """Move vertices by fn (world->world), blended by the summed weight of `groups`; move the heads and
        tails of `bones` (and only the tails of `tails`) by fn too, so joints stay where the mesh is."""
        groups = set(groups)
        for o in self.meshes:
            idx = {g.index for g in o.vertex_groups if g.name in groups}
            if not idx:
                continue
            me = o.data
            for v in me.vertices:
                w = sum(g.weight for g in v.groups if g.group in idx)
                if w <= 1e-4:
                    continue
                w = min(1.0, w)
                v.co = v.co.lerp(fn(v.co.copy()), w)
            me.update()

        def f(eb):
            for n in bones:
                b = eb[n]
                h, t = fn(b.head.copy()), fn(b.tail.copy())
                b.head, b.tail = h, t
            for n in tails:
                eb[n].tail = fn(eb[n].tail.copy())
        self.edit_bones(f)

    def bigger_head(self, k=1.08):
        P = self.h('Head').copy()
        self.reshape({'Head'}, lambda c: P + (c - P) * k, tails=('Head',))

    def bigger_hands(self, k=1.08, finger_stretch=1.0, knuckle=0.075):
        """Scale each hand about the wrist by k; optionally lengthen the fingers past the knuckle line."""
        for s in ('l', 'r'):
            P = self.h('hand_' + s).copy()
            ax = (self.t('hand_' + s) - P).normalized()
            kn = knuckle * k

            def fn(c, P=P, ax=ax, kn=kn):
                d = (c - P) * k
                u = d.dot(ax)
                if finger_stretch != 1.0 and u > kn:
                    d = d + ax * ((u - kn) * (finger_stretch - 1.0))
                return P + d
            fb = [f'{f}_{i:02d}_{s}' for f in FINGERS for i in (1, 2, 3)] + \
                 [f'{f}_04_leaf_{s}' for f in FINGERS]
            groups = {'hand_' + s} | set(fb)
            self.reshape(groups, fn, bones=fb, tails=('hand_' + s,))

    # ---- measurement
    def bvh(self, pred=None):
        """BVH of the body mesh (optionally only faces whose dominant bone passes pred)."""
        me = self.mesh.data
        dom = self.dominant()
        co = [v.co.copy() for v in me.vertices]
        polys = []
        for p in me.polygons:
            if pred is None or all(pred(dom[i], co[i]) for i in p.vertices):
                polys.append(list(p.vertices))
        return BVHTree.FromPolygons(co, polys)

    def dominant(self):
        names = {g.index: g.name for g in self.mesh.vertex_groups}
        out = []
        for v in self.mesh.data.vertices:
            best, bw = '', -1
            for g in v.groups:
                if g.weight > bw:
                    best, bw = names.get(g.group, ''), g.weight
            out.append(best)
        return out

    def landmarks(self):
        co = [v.co.copy() for v in self.mesh.data.vertices]
        L = {}
        L['top'] = max(c.z for c in co)
        for b in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'Head', 'upperarm_l', 'lowerarm_l', 'hand_l',
                  'thigh_l', 'calf_l', 'foot_l', 'ball_l', 'clavicle_l'):
            L[b] = self.h(b)
        if self.eyes:
            ev = [v.co.copy() for v in self.eyes.data.vertices]
            le = [p for p in ev if p.x > 0]
            re = [p for p in ev if p.x < 0]
            L['eye_l'] = sum(le, V()) / len(le)
            L['eye_r'] = sum(re, V()) / len(re)
            L['eye_rad'] = max((p - L['eye_l']).length for p in le)
        hz = L['Head'].z
        face = [c for c in co if c.z > hz - 0.05 and abs(c.x) < 0.02]
        nose = min(face, key=lambda c: c.y)
        L['nose'] = nose
        chin_c = [c for c in co if abs(c.x) < 0.012 and c.z < nose.z - 0.03 and c.z > L['neck_01'].z and c.y < nose.y + 0.05]
        L['chin'] = min(chin_c, key=lambda c: c.z + 0.6 * c.y)
        back = max(c.y for c in co if c.z > hz)
        L['head_c'] = V((0, (nose.y + back) * 0.5, (L['top'] + L['chin'].z) * 0.5))
        cr = [c for c in co if abs(c.x) < 0.02 and 0.5 < c.z < L['pelvis'].z]
        L['crotch_z'] = min(c.z for c in cr) if cr else L['thigh_l'].z - 0.12
        self.L = L
        return L

    def delete_faces(self, pred):
        """Delete body faces where pred(list_of_vertex_cos, list_of_dominant_bones) is True."""
        me = self.mesh.data
        dom = self.dominant()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        kill = [f for f in bm.faces if pred([v.co for v in f.verts], [dom[v.index] for v in f.verts])]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(me)
        bm.free()
        me.update()
        log('body faces deleted', len(kill), 'tris now', tri_count(self.mesh))


def ray_radius(bvh, center, d, maxd=0.6):
    """distance from center along d to the OUTERMOST surface (ray from outside inwards)."""
    d = V(d).normalized()
    st = V(center) + d * maxd
    loc, nrm, idx, dist = bvh.ray_cast(st, -d, maxd)
    return (maxd - dist) if loc is not None else None


def bvh_objs(objs, evaluated=False):
    verts, polys = [], []
    dg = bpy.context.evaluated_depsgraph_get() if evaluated else None
    for o in objs:
        if evaluated:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
        else:
            me = o.data
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        if evaluated:
            ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def push_out(ob, bvh, clearance=0.008, iters=6, smooth_iters=2, max_dist=0.2):
    """move vertices of ob out of (or closer than clearance to) the obstacle surfaces."""
    me = ob.data
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    total = 0
    for it in range(iters):
        disp = [V() for _ in me.vertices]
        moved = 0
        for v in me.vertices:
            loc, nrm, idx, d = bvh.find_nearest(v.co, max_dist)
            if loc is None:
                continue
            if (v.co - loc).dot(nrm) < 0 or d < clearance:
                disp[v.index] = loc + nrm * clearance - v.co
                moved += 1
        if not moved:
            break
        total += moved
        orig = disp
        for _ in range(smooth_iters):
            nd = []
            for i, dv in enumerate(disp):
                if adj[i]:
                    avg = sum((disp[j] for j in adj[i]), V()) / len(adj[i])
                    s = dv * 0.5 + avg * 0.5
                else:
                    s = dv
                nd.append(s if s.length > orig[i].length else orig[i])
            disp = nd
        for v, dv in zip(me.vertices, disp):
            v.co += dv
    me.update()
    return total


# ============================================================================================ weights
def read_weights(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        d = {}
        for ge in v.groups:
            if ge.weight > 0:
                d[names[ge.group]] = ge.weight
        out.append(d)
    return out


def write_weights(ob, W, limit=4):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        items = sorted(w.items(), key=lambda kv: -kv[1])[:limit]
        items = [(g, x) for g, x in items if x > 0.01]
        s = sum(x for _, x in items) or 1
        for g, x in items:
            if g not in groups:
                groups[g] = ob.vertex_groups.new(name=g)
            groups[g].add([i], x / s, 'REPLACE')


def weights_rigid(ob, bone):
    write_weights(ob, [{bone: 1.0}] * len(ob.data.vertices))


def weights_fn(ob, fn):
    write_weights(ob, [fn(v.co.copy()) for v in ob.data.vertices])


def _bary(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
    d20, d21 = v2.dot(v0), v2.dot(v1)
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return (1 / 3, 1 / 3, 1 / 3)
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    u = 1 - v - w
    u, v, w = max(0, u), max(0, v), max(0, w)
    s = u + v + w or 1
    return (u / s, v / s, w / s)


class WeightSource:
    """Nearest-surface barycentric weight lookup on a skinned reference mesh (rest pose, world == local)."""

    def __init__(self, src, face_pred=None):
        me = src.data
        me.calc_loop_triangles()
        self.co = [v.co.copy() for v in me.vertices]
        self.w = read_weights(src)
        tris = []
        for lt in me.loop_triangles:
            vs = tuple(lt.vertices)
            if face_pred and not face_pred(self, vs):
                continue
            tris.append(vs)
        self.tris = tris
        self.bvh = BVHTree.FromPolygons(self.co, tris)

    def at(self, p):
        loc, nrm, idx, dist = self.bvh.find_nearest(p)
        if idx is None:
            return {}
        a, b, c = self.tris[idx]
        out = {}
        for vi, bw in zip((a, b, c), _bary(loc, self.co[a], self.co[b], self.co[c])):
            for g, w in self.w[vi].items():
                out[g] = out.get(g, 0.0) + w * bw
        return out


def weights_transfer(ob, src, smooth_iters=3, smooth_factor=0.5, post=None, limit=4):
    me = ob.data
    W = [src.at(v.co) for v in me.vertices]
    if post:
        W = [post(v.co.copy(), w) for v, w in zip(me.vertices, W)]
    W = smooth_weights(ob, W, smooth_iters, smooth_factor)
    write_weights(ob, W, limit)


def smooth_weights(ob, W, iters=3, factor=0.5):
    me = ob.data
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    for _ in range(iters):
        NW = []
        for i, w in enumerate(W):
            if not adj[i]:
                NW.append(w)
                continue
            acc = {}
            for j in adj[i]:
                for g, x in W[j].items():
                    acc[g] = acc.get(g, 0) + x / len(adj[i])
            NW.append({g: w.get(g, 0) * (1 - factor) + acc.get(g, 0) * factor for g in set(w) | set(acc)})
        W = NW
    return W


def blend(*pairs):
    """blend({bone:w}, f, {bone:w}, f, ...) -> weighted sum."""
    out = {}
    for d, f in zip(pairs[0::2], pairs[1::2]):
        for k, x in d.items():
            out[k] = out.get(k, 0) + x * f
    return out


def sstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))) if e1 != e0 else (1.0 if x >= e0 else 0.0)
    return t * t * (3 - 2 * t)


# ============================================================================================ UVs
def uv_unwrap(ob, angle=66.0, weight=1.0, margin=0.004):
    activate(ob)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = ob.data
    a3 = sum(p.area for p in me.polygons)
    uvl = me.uv_layers.active.data
    au = 0.0
    for p in me.polygons:
        pts = [uvl[li].uv for li in p.loop_indices]
        for i in range(1, len(pts) - 1):
            au += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) * 0.5
    if au > 0:
        s = math.sqrt(a3 / au) * math.sqrt(weight)
        for l in uvl:
            l.uv = l.uv * s


def uv_pack(ob, margin=0.003):
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    try:
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True,
                                merge_overlap=False, margin_method='FRACTION', margin=margin, shape_method='CONCAVE')
    except Exception as e:
        log('pack concave failed', e)
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


# ============================================================================================ material DSL
def srgb(c):
    """sRGB hex/tuple -> linear RGBA."""
    if isinstance(c, str):
        c = c.lstrip('#')
        c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


class NB:
    """Small node-building DSL for procedural Cycles materials (bakeable channels)."""

    def __init__(self, mat):
        mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def node(self, typ, **kw):
        n = self.nt.nodes.new(typ)
        n.location = (self.x, 0)
        self.x += 40
        for k, v in kw.items():
            if hasattr(n, k):
                setattr(n, k, v)
        return n

    def inp(self, n, key, val):
        s = n.inputs[key]
        if isinstance(val, bpy.types.NodeSocket):
            self.nt.links.new(val, s)
        elif val is not None:
            try:
                s.default_value = val
            except Exception:
                if isinstance(val, (int, float)):
                    s.default_value = (val, val, val, 1.0)[:len(s.default_value)]
                else:
                    raise
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def coord(self, kind='Object'):
        return self.node('ShaderNodeTexCoord').outputs[kind]

    def geo(self, out):
        return self.node('ShaderNodeNewGeometry').outputs[out]

    def attr(self, name, out='Fac'):
        n = self.node('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')
        return n.outputs[out] if out in n.outputs else n.outputs[2]

    def rgb(self, c):
        n = self.node('ShaderNodeRGB')
        n.outputs[0].default_value = c
        return n.outputs[0]

    def noise(self, vec=None, scale=5.0, detail=4.0, rough=0.55, dist=0.0, out='Fac', dims='3D', lac=2.0):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dims)
        if vec is not None:
            self.inp(n, 'Vector', vec)
        self.inp(n, 'Scale', scale); self.inp(n, 'Detail', detail); self.inp(n, 'Roughness', rough)
        self.inp(n, 'Distortion', dist); self.inp(n, 'Lacunarity', lac)
        return n.outputs['Fac' if out == 'Fac' else 'Color']

    def voronoi(self, vec=None, scale=5.0, feature='F1', metric='EUCLIDEAN', out='Distance', rand=1.0, dims='3D'):
        n = self.node('ShaderNodeTexVoronoi', feature=feature, distance=metric, voronoi_dimensions=dims)
        if vec is not None:
            self.inp(n, 'Vector', vec)
        self.inp(n, 'Scale', scale); self.inp(n, 'Randomness', rand)
        return n.outputs[out]

    def wave(self, vec=None, scale=5.0, dist=2.0, detail=2.0, kind='BANDS', axis='X', profile='SIN', dscale=1.0):
        n = self.node('ShaderNodeTexWave', wave_type=kind, wave_profile=profile)
        if kind == 'BANDS':
            n.bands_direction = axis
        else:
            n.rings_direction = axis
        if vec is not None:
            self.inp(n, 'Vector', vec)
        self.inp(n, 'Scale', scale); self.inp(n, 'Distortion', dist); self.inp(n, 'Detail', detail)
        self.inp(n, 'Detail Scale', dscale)
        return n.outputs['Fac'] if 'Fac' in n.outputs else n.outputs[1]

    def mapping(self, vec, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        n = self.node('ShaderNodeMapping')
        self.inp(n, 'Vector', vec)
        n.inputs['Location'].default_value = loc
        n.inputs['Rotation'].default_value = rot
        n.inputs['Scale'].default_value = scale
        return n.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.inp(n, 0, a)
        if b is not None:
            self.inp(n, 1, b)
        return n.outputs[0]

    def mul(self, a, b, clamp=False):
        return self.math('MULTIPLY', a, b, clamp)

    def add(self, a, b, clamp=False):
        return self.math('ADD', a, b, clamp)

    def sub(self, a, b, clamp=False):
        return self.math('SUBTRACT', a, b, clamp)

    def inv(self, a):
        return self.math('SUBTRACT', 1.0, a, True)

    def mx(self, a, b):
        return self.math('MAXIMUM', a, b)

    def mn(self, a, b):
        return self.math('MINIMUM', a, b)

    def mr(self, v, f0, f1, t0=0.0, t1=1.0, interp='SMOOTHSTEP', clamp=True):
        n = self.node('ShaderNodeMapRange', interpolation_type=interp, clamp=clamp)
        self.inp(n, 'Value', v)
        n.inputs[1].default_value = f0; n.inputs[2].default_value = f1
        n.inputs[3].default_value = t0; n.inputs[4].default_value = t1
        return n.outputs['Result']

    def vmath(self, op, a, b=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        self.inp(n, 0, a)
        if b is not None:
            self.inp(n, 1, b)
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def sep(self, vec):
        n = self.node('ShaderNodeSeparateXYZ')
        self.inp(n, 0, vec)
        return n.outputs

    def comb(self, x, y, z):
        n = self.node('ShaderNodeCombineXYZ')
        self.inp(n, 0, x); self.inp(n, 1, y); self.inp(n, 2, z)
        return n.outputs[0]

    def mix(self, fac, a, b, blend='MIX', clamp=True):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_result=clamp)
        self.inp(n, 0, fac)
        self.inp(n, 6, a)
        self.inp(n, 7, b)
        return n.outputs[2]

    def mixf(self, fac, a, b):
        n = self.node('ShaderNodeMix', data_type='FLOAT')
        self.inp(n, 0, fac)
        self.inp(n, 2, a)
        self.inp(n, 3, b)
        return n.outputs[0]

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.node('ShaderNodeValToRGB')
        self.inp(n, 0, fac)
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > len(stops):
            cr.elements.remove(cr.elements[-1])
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = srgb(col) if isinstance(col, str) else col
        return n.outputs['Color']

    def hsv(self, col, h=0.5, s=1.0, v=1.0):
        n = self.node('ShaderNodeHueSaturation')
        self.inp(n, 'Color', col); self.inp(n, 'Hue', h); self.inp(n, 'Saturation', s); self.inp(n, 'Value', v)
        return n.outputs[0]

    def bump(self, height, strength=0.5, dist=0.002, normal=None):
        n = self.node('ShaderNodeBump')
        self.inp(n, 'Height', height); self.inp(n, 'Strength', strength); self.inp(n, 'Distance', dist)
        if normal is not None:
            self.inp(n, 'Normal', normal)
        return n.outputs['Normal']

    def img(self, image, uvmap=None, out='Color'):
        n = self.node('ShaderNodeTexImage')
        n.image = image
        if uvmap:
            u = self.node('ShaderNodeUVMap')
            u.uv_map = uvmap
            self.link(u.outputs[0], n.inputs[0])
        return n.outputs[out]

    def normal_map(self, col, strength=1.0):
        n = self.node('ShaderNodeNormalMap')
        self.inp(n, 'Color', col)
        self.inp(n, 'Strength', strength)
        return n.outputs['Normal']

    def ell(self, co, cen, r, rot=(0, 0, 0), soft=0.4):
        """soft ellipsoid mask (1 inside) around cen with semi-axes r."""
        d = self.vmath('SUBTRACT', co, tuple(cen))
        if any(rot):
            d = self.mapping(d, rot=rot)
        d = self.mapping(d, scale=(1 / r[0], 1 / r[1], 1 / r[2]))
        ln = self.vmath('LENGTH', d)
        return self.mr(ln, 1.0 - soft, 1.0, 1.0, 0.0)

    def paint(self, c, mask, col, alpha=1.0, blend='MIX'):
        return self.mix(self.mul(mask, alpha) if alpha != 1.0 else mask, c, srgb(col) if isinstance(col, str) else col, blend)

    def finish(self, color, rough, normal=None, emit=None, metal=0.0):
        """Principled preview + bake channels: CH_color, CH_rough, CH_emit (emission colour 0..1)."""
        p = self.node('ShaderNodeBsdfPrincipled')
        out = self.node('ShaderNodeOutputMaterial')
        out.name = 'OUT'
        p.name = 'BSDF'
        self.inp(p, 'Base Color', color)
        self.inp(p, 'Roughness', rough)
        self.inp(p, 'Metallic', metal)
        if normal is not None:
            self.inp(p, 'Normal', normal)
        if emit is not None:
            self.inp(p, 'Emission Color', emit)
            self.inp(p, 'Emission Strength', 4.0)
        self.link(p.outputs[0], out.inputs['Surface'])
        for key, val in (('color', color), ('rough', rough), ('emit', emit if emit is not None else (0, 0, 0, 1)),
                         ('metal', metal)):
            em = self.node('ShaderNodeEmission')
            em.name = 'CH_' + key
            if isinstance(val, bpy.types.NodeSocket):
                self.link(val, em.inputs['Color'])
            else:
                em.inputs['Color'].default_value = val if hasattr(val, '__len__') else (val, val, val, 1)
        return p


def set_channel(mats, ch):
    for m in mats:
        nt = m.node_tree
        out = nt.nodes.get('OUT')
        if out is None:
            continue
        src = nt.nodes['BSDF'].outputs[0] if ch == 'bsdf' else nt.nodes['CH_' + ch].outputs[0]
        nt.links.new(src, out.inputs['Surface'])


# ============================================================================================ bake
def new_image(name, size, non_color=False, fill=(0, 0, 0, 1), float_buffer=False):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer)
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    img.generated_color = fill
    return img


def img_np(img):
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def np_to_img(name, arr, non_color=False):
    h, w = arr.shape[:2]
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    a = np.ones((h, w, 4), np.float32)
    a[:, :, :arr.shape[2] if arr.ndim == 3 else 1] = arr if arr.ndim == 3 else arr[:, :, None]
    im.pixels.foreach_set(a.ravel())
    return im


def save_png(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.filepath = path  # keep the source path for the exporter


def world_for_ao(dist=0.12):
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.light_settings.distance = dist


def bake_set(LO, size, prefix, workdir, samples_ao=64, ao_dist=0.1, ao_in_color=0.55, emit=True, margin=16):
    """Bake the procedural materials of LO (all slots) into textures on LO's active UV map. Returns a dict of
    numpy arrays: color (with AO multiplied in), orm, normal, emit (or None) and the raw ao."""
    sc = bpy.context.scene
    gpu_setup(4)
    sc.render.bake.margin = margin
    world_for_ao(ao_dist)
    mats = [s.material for s in LO.material_slots if s.material]
    mats = list(dict.fromkeys(mats))
    imgs = {
        'color': new_image(prefix + '_color', size, False, (0.5, 0.5, 0.5, 1)),
        'rough': new_image(prefix + '_rough', size, True, (0.7, 0.7, 0.7, 1)),
        'normal': new_image(prefix + '_normalraw', size, True, (0.5, 0.5, 1, 1)),
        'ao': new_image(prefix + '_ao', size, True, (1, 1, 1, 1)),
    }
    if emit:
        imgs['emit'] = new_image(prefix + '_emitraw', size, False, (0, 0, 0, 1))
    for m in mats:
        t = m.node_tree.nodes.get('BAKE_TGT') or m.node_tree.nodes.new('ShaderNodeTexImage')
        t.name = 'BAKE_TGT'
    activate(LO)
    for o in sc.objects:
        if o.type == 'MESH':
            o.hide_render = False
    passes = [('color', 'EMIT', 'color', 1), ('rough', 'EMIT', 'rough', 1), ('normal', 'NORMAL', 'bsdf', 1),
              ('ao', 'AO', 'bsdf', samples_ao)]
    if emit:
        passes.append(('emit', 'EMIT', 'emit', 1))
    for key, btype, ch, smp in passes:
        t0 = time.time()
        set_channel(mats, ch)
        sc.cycles.samples = smp
        for m in mats:
            n = m.node_tree.nodes['BAKE_TGT']
            n.image = imgs[key]
            m.node_tree.nodes.active = n
        kw = dict(type=btype, use_selected_to_active=False, margin=margin, use_clear=True, target='IMAGE_TEXTURES')
        if btype == 'NORMAL':
            kw.update(normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
        bpy.ops.object.bake(**kw)
        log('baked', prefix, key, '%.1fs' % (time.time() - t0))
    set_channel(mats, 'bsdf')
    out = {k: img_np(v) for k, v in imgs.items()}
    ao = out['ao'][:, :, 0]
    col = out['color'][:, :, :3] * (1 - ao_in_color + ao_in_color * ao)[:, :, None]
    orm = np.stack([ao, out['rough'][:, :, 0], np.zeros_like(ao)], -1)
    res = {'color': col, 'orm': orm, 'normal': out['normal'][:, :, :3], 'ao': ao,
           'emit': out['emit'][:, :, :3] if emit else None}
    for im in imgs.values():
        bpy.data.images.remove(im)
    return res


def final_material(name, maps, workdir, emit_strength=4.0, tint=None, double_sided=False, normal_strength=1.0,
                   rough_mul=1.0, alpha=None):
    """Write the maps as PNGs and build a glTF-friendly principled material. tint: sRGB hex -> base colour factor
    (image x factor via a MULTIPLY mix, which the glTF exporter writes as baseColorFactor)."""
    os.makedirs(workdir, exist_ok=True)
    ims = {}
    for k in ('color', 'orm', 'normal', 'emit'):
        a = maps.get(k)
        if a is None:
            continue
        if k == 'orm' and rough_mul != 1.0:
            a = a.copy()
            a[:, :, 1] = np.clip(a[:, :, 1] * rough_mul, 0, 1)
        im = np_to_img(name + '_' + k, a, non_color=(k in ('orm', 'normal')))
        save_png(im, os.path.join(workdir, name + '_' + k + '.png'))
        ims[k] = im
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = ims['color']
    if tint:
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs[0].default_value = 1.0
        nt.links.new(tc.outputs['Color'], mx.inputs[6])
        mx.inputs[7].default_value = srgb(tint)
        nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    else:
        nt.links.new(tc.outputs['Color'], p.inputs['Base Color'])
    if alpha is not None:
        nt.links.new(tc.outputs['Alpha'], p.inputs['Alpha'])
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = ims['orm']
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sp.inputs[0])
    nt.links.new(sp.outputs['Green'], p.inputs['Roughness'])
    nt.links.new(sp.outputs['Blue'], p.inputs['Metallic'])
    # glTF occlusion: a 'glTF Material Output' group with an Occlusion socket
    ng = gltf_output_group()
    g = nt.nodes.new('ShaderNodeGroup')
    g.node_tree = ng
    nt.links.new(sp.outputs['Red'], g.inputs['Occlusion'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = ims['normal']
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = normal_strength
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    if 'emit' in ims:
        te = nt.nodes.new('ShaderNodeTexImage'); te.image = ims['emit']
        nt.links.new(te.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = emit_strength
    m.use_backface_culling = not double_sided
    return m


def gltf_output_group():
    ng = bpy.data.node_groups.get('glTF Material Output')
    if ng is None:
        ng = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        ng.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        ng.interface.new_socket('Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    return ng


class Kit:
    """A texture set / material: parts (meshes with procedural materials and weights) joined, UV-packed, baked."""

    def __init__(self, name, size=2048):
        self.name, self.size = name, size
        self.parts = []

    def add(self, ob, mat=None, uvw=1.0, angle=66.0):
        if mat is not None:
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        self.parts.append((ob, uvw, angle))
        return ob

    def tris(self):
        return sum(tri_count(o) for o, _, _ in self.parts)

    def build(self, workdir, arm=None, tint=None, emit_strength=4.0, double_sided=False, keep_uv=False,
              ao_dist=0.1, ao_in_color=0.55, normal_strength=1.0, emit=True, rough_mul=1.0, margin=0.003):
        objs = []
        for ob, uvw, angle in self.parts:
            if not keep_uv:
                for l in list(ob.data.uv_layers):
                    ob.data.uv_layers.remove(l)
                uv_unwrap(ob, angle=angle, weight=uvw)
            objs.append(ob)
        LO = join(objs, self.name)
        if not keep_uv:
            uv_pack(LO, margin)
        log('kit', self.name, 'tris', tri_count(LO))
        maps = bake_set(LO, self.size, self.name, workdir, ao_dist=ao_dist, ao_in_color=ao_in_color, emit=emit)
        mat = final_material(self.name, maps, workdir, emit_strength, tint, double_sided, normal_strength, rough_mul)
        LO.data.materials.clear()
        LO.data.materials.append(mat)
        triangulate(LO)
        for a in list(LO.data.attributes):
            if a.name in ('pu', 'pv', 'pw') or a.name.startswith('p_'):
                LO.data.attributes.remove(a)
        if arm is not None:
            LO.parent = arm
            LO.matrix_parent_inverse = Matrix.Identity(4)
            if not any(m.type == 'ARMATURE' for m in LO.modifiers):
                md = LO.modifiers.new('Armature', 'ARMATURE')
                md.object = arm
        self.LO = LO
        return LO


# ============================================================================================ posing (three.js semantics)
def bone_order(arm):
    out = []

    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    return out


def load_clip_source(clip):
    """Import the UAL library holding `clip`; returns (armature, action) with its meshes removed."""
    for src in (UAL1, UAL2):
        objs = import_gltf(src)
        for ac in bpy.data.actions:
            ac.use_fake_user = True
        a_src = next(o for o in objs if o.type == 'ARMATURE')
        act = bpy.data.actions.get(clip) or bpy.data.actions.get(clip + '_Loop')
        if act is not None:
            delete([o for o in objs if o.type != 'ARMATURE'])
            a_src.name = 'UAL_SRC'
            ad = a_src.animation_data_create()
            ad.action = act
            try:
                if ad.action_slot is None and len(act.slots):
                    ad.action_slot = act.slots[0]
            except Exception:
                pass
            a_src.hide_render = True
            return a_src, act
        delete(objs)
        for a in list(bpy.data.actions):
            bpy.data.actions.remove(a)
    raise KeyError(clip)


def pose_from(src, targets, frame, pelvis_scale=1.0):
    """Copy the source armature's local (parent-relative) bone ROTATIONS at `frame` onto the targets, keeping
    each target's own bone offsets; root/pelvis translation scaled by pelvis_scale (rest-relative)."""
    sc = bpy.context.scene
    for t in targets:
        rest_pose(t)
    sc.frame_set(int(frame))
    sub = frame - int(frame)
    if sub > 1e-4:
        sc.frame_set(int(frame), subframe=sub)
    bpy.context.view_layer.update()
    loc = {}
    rest_loc = {}
    for pb in src.pose.bones:
        M = pb.matrix
        loc[pb.name] = (pb.parent.matrix.inverted() @ M) if pb.parent else M.copy()
        b = pb.bone
        rest_loc[pb.name] = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()
    for arm in targets:
        for name in bone_order(arm):
            pb = arm.pose.bones.get(name)
            if pb is None or name not in loc:
                continue
            b = pb.bone
            own = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()
            Ls = loc[name]
            R = Ls.to_quaternion().to_matrix().to_4x4()
            t = own.translation.copy()
            if name in ('root', 'pelvis'):
                t = own.translation + (Ls.translation - rest_loc[name].translation) * pelvis_scale
            Mloc = Matrix.Translation(t) @ R
            P = pb.parent.matrix if pb.parent else Matrix.Identity(4)
            pb.matrix = P @ Mloc
            bpy.context.view_layer.update()


# ============================================================================================ export
def export_glb(path, objs):
    deselect_all()
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for o in objs:
        if o.type == 'ARMATURE':
            rest_pose(o)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
              export_animations=False, export_skins=True, export_influence_nb=4, export_all_influences=False,
              export_def_bones=False, export_leaf_bone=False, export_texcoords=True, export_normals=True,
              export_tangents=False, export_materials='EXPORT', export_image_format='AUTO', export_morph=False,
              export_cameras=False, export_lights=False, export_extras=False, export_rest_position_armature=True,
              export_hierarchy_flatten_bones=False)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as e:
        log('export kw issue', e)
        for k in ('export_leaf_bone', 'export_hierarchy_flatten_bones', 'export_rest_position_armature'):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    log('EXPORTED', path, '%.2f MB' % (os.path.getsize(path) / 1e6))


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    log('saved', path)

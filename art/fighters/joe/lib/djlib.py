"""Dungeon Joe 3D -- shared Blender helpers for character / weapon asset generation.

Everything is procedural: geometry is authored with bmesh / metaballs, materials are procedural
Cycles node trees, and every asset is baked (high -> low, Cycles GPU) into plain PBR textures that
Godot can read (BaseColor sRGB, ORM packed [R=1, G=rough, B=metal], tangent-space OpenGL normal).

Conventions: metres, Blender Z-up, character faces -Y (its left = +X), glTF exported with +Y up.
"""
import bpy, bmesh, math, os, sys, json, random, time, tempfile
from mathutils import Vector, Matrix, Quaternion, Euler, noise
from mathutils.bvhtree import BVHTree

PROJ = r"C:\dev\AverageJoe\DungeonJoe3D"
QUAT = PROJ + r"\assets\thirdparty\quaternius"
UAL1 = QUAT + r"\anim\UAL1_Standard.glb"
UAL2 = QUAT + r"\anim\UAL2_Standard.glb"
MALE_BODY = QUAT + r"\ubc\bodies\Superhero_Male_FullBody.gltf"
OUT_CHAR = PROJ + r"\assets\custom\characters"
OUT_WPN = PROJ + r"\assets\custom\weapons"
OUT_PREV = PROJ + r"\assets\custom\_previews\characters"
WORK = os.environ.get("FIGHTER_WORK", os.path.join(tempfile.gettempdir(), "jb_char_work"))
os.makedirs(WORK, exist_ok=True)

V = Vector
T0 = time.time()


def log(*a):
    print('[dj %6.1fs]' % (time.time() - T0), *a, flush=True)


def args_after_dashdash():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


# ----------------------------------------------------------------------------------------------
# scene / gpu
# ----------------------------------------------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.engine = 'CYCLES'


def gpu_setup(samples=64):
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
                    log('GPU', t, [d.name for d in devs])
                    break
            except Exception as e:
                log('gpu fail', t, e)
        sc.cycles.device = 'GPU'
    except Exception as e:
        log('no cycles prefs', e)
    sc.cycles.samples = samples


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def deselect_all():
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        if o is not None:
            try:
                o.select_set(False)
            except Exception:
                pass


def activate(ob, select_only=True):
    if select_only:
        deselect_all()
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e:
            log('modifier_apply failed', ob.name, m.name, e)
            ob.modifiers.remove(m)


def delete(obs):
    for o in list(obs):
        bpy.data.objects.remove(o, do_unlink=True)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ----------------------------------------------------------------------------------------------
# armature
# ----------------------------------------------------------------------------------------------

def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, bone_heuristic='BLENDER', disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]


def rest_pose(arm):
    ad = arm.animation_data
    if ad:
        ad.action = None
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def load_ual(keep_mannequin=False):
    objs = import_gltf(UAL1)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    ref = None
    for o in objs:
        if o.type == 'MESH':
            if keep_mannequin and o.name.startswith('Mannequin'):
                o.name = 'REF_Mannequin'
                o.hide_render = True
                ref = o
            else:
                bpy.data.objects.remove(o, do_unlink=True)
    for a in bpy.data.actions:
        a.use_fake_user = True
    arm.name = 'Armature'
    arm.data.name = 'Armature'
    rest_pose(arm)
    return arm, ref


def load_body(path=MALE_BODY):
    """Import a UBC body; returns (armature, [meshes]). Armature renamed REF_BodyArmature."""
    objs = import_gltf(path)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    meshes = []
    for o in objs:
        if o.type == 'MESH':
            if o.name.startswith('Icosphere'):
                bpy.data.objects.remove(o, do_unlink=True)
            else:
                meshes.append(o)
    rest_pose(arm)
    return arm, meshes


class Bones:
    def __init__(self, arm):
        self.arm = arm
        self.b = arm.data.bones

    def h(self, n):
        return self.arm.matrix_world @ self.b[n].head_local

    def t(self, n):
        return self.arm.matrix_world @ self.b[n].tail_local

    def m(self, n):
        return self.arm.matrix_world @ self.b[n].matrix_local

    def names(self):
        return [b.name for b in self.b]


# ----------------------------------------------------------------------------------------------
# geometry builders (bmesh, world space)
# ----------------------------------------------------------------------------------------------

def _perp(t):
    a = V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))
    return (a - t * a.dot(t)).normalized()


def frames_along(pts, up=None):
    """Parallel-transport frames (T, N, B) along a polyline."""
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
            # rotate previous N by rotation taking T[i-1] to T[i]
            q = Ts[i - 1].rotation_difference(T)
            N = (q @ N)
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
    """bmesh accumulator with primitive builders. All coordinates world-space."""

    def __init__(self):
        self.bm = bmesh.new()

    # -- low level
    def v(self, co):
        return self.bm.verts.new(co)

    def f(self, vs):
        try:
            return self.bm.faces.new(vs)
        except ValueError:
            return None

    def ring_bridge(self, r0, r1, closed=True):
        n = len(r0)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            self.f([r0[i], r0[j], r1[j], r1[i]])

    def fan(self, ring, center, flip=False):
        c = self.v(center)
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            if flip:
                self.f([ring[j], ring[i], c])
            else:
                self.f([ring[i], ring[j], c])
        return c

    # -- sweep tube
    def sweep(self, pts, radii, sides=8, cap0='round', cap1='round', up=None, exp=2.0, rot=0.0,
              cap_segs=2, cap_scale=1.0, twist=0.0, offsets=None):
        """pts: list of Vector; radii: float | (rx, ry) per point (rx along N, ry along B).
        exp: superellipse exponent of the cross section (2 = ellipse, 4 = rounded box)."""
        pts = [V(p) for p in pts]
        fr = frames_along(pts, up)
        rad = [(r, r) if not isinstance(r, (tuple, list)) else tuple(r) for r in radii]
        rings = []
        angs = [rot + 2 * math.pi * k / sides for k in range(sides)]

        def ring_at(p, T, N, B, rx, ry, tw):
            out = []
            for a in angs:
                c, s = superellipse(a + tw, exp)
                out.append(self.v(p + N * (c * rx) + B * (s * ry)))
            return out

        nP = len(pts)
        for i, (p, (T, N, B), (rx, ry)) in enumerate(zip(pts, fr, rad)):
            tw = twist * i / max(1, nP - 1)
            rings.append(ring_at(p, T, N, B, rx, ry, tw))
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
                self.fan(ring, p, flip=(end == 0))
                return
            prev = ring
            rr = min(rx, ry) * cap_scale
            tw = 0 if end == 0 else twist
            for k in range(1, cap_segs + 1):
                ph = (math.pi / 2) * k / (cap_segs + 1)
                q = p + T * (sgn * rr * math.sin(ph))
                nr = ring_at(q, T, N, B, rx * math.cos(ph), ry * math.cos(ph), tw)
                if end == 0:
                    self.ring_bridge(nr, prev)
                else:
                    self.ring_bridge(prev, nr)
                prev = nr
            self.fan(prev, p + T * (sgn * rr), flip=(end == 0))

        cap(0)
        cap(1)
        return rings

    # -- lathe around an axis frame
    def lathe(self, prof, segs=16, M=None, close_top=True, close_bot=True, a0=0.0, a1=2 * math.pi, rxy=(1, 1)):
        """prof: list of (r, z). Revolved around local Z. M: world matrix."""
        M = M or Matrix.Identity(4)
        full = abs((a1 - a0) - 2 * math.pi) < 1e-6
        n = segs if full else segs + 1
        rings = []
        for (r, z) in prof:
            ring = []
            for k in range(n):
                a = a0 + (a1 - a0) * k / segs
                ring.append(self.v(M @ V((r * math.cos(a) * rxy[0], r * math.sin(a) * rxy[1], z))))
            rings.append(ring)
        for i in range(len(rings) - 1):
            self.ring_bridge(rings[i], rings[i + 1], closed=full)
        if full:
            if close_bot and prof[0][0] > 1e-6:
                self.fan(rings[0], M @ V((0, 0, prof[0][1])), flip=True)
            if close_top and prof[-1][0] > 1e-6:
                self.fan(rings[-1], M @ V((0, 0, prof[-1][1])))
        return rings

    def ellipsoid(self, c, r, segs=12, rings=8, M=None):
        r = (r, r, r) if not isinstance(r, (tuple, list, Vector)) else r
        prof = []
        for k in range(rings + 1):
            ph = -math.pi / 2 + math.pi * k / rings
            prof.append((math.cos(ph), math.sin(ph)))
        M0 = Matrix.Translation(V(c)) @ (M if M else Matrix.Identity(4)) @ Matrix.Diagonal((r[0], r[1], r[2], 1))
        # poles: replace first/last ring (r=0) by fans
        prof2 = prof[1:-1]
        rs = self.lathe(prof2, segs, M0, close_top=False, close_bot=False)
        self.fan(rs[0], M0 @ V((0, 0, -1)), flip=True)
        self.fan(rs[-1], M0 @ V((0, 0, 1)))
        return rs

    def box(self, c, size, M=None, bevel=0.0, bevel_segs=1):
        bm2 = bmesh.new()
        bmesh.ops.create_cube(bm2, size=1.0)
        S = Matrix.Diagonal((size[0], size[1], size[2], 1))
        Mt = Matrix.Translation(V(c)) @ (M if M else Matrix.Identity(4)) @ S
        bmesh.ops.transform(bm2, matrix=Mt, verts=bm2.verts)
        if bevel > 0:
            bmesh.ops.bevel(bm2, geom=list(bm2.edges), offset=bevel, segments=bevel_segs, profile=0.5, affect='EDGES')
        self.merge_bm(bm2)

    def merge_bm(self, bm2):
        me = bpy.data.meshes.new('_tmp')
        bm2.to_mesh(me)
        bm2.free()
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)

    def strip(self, pts, widths, ups, thick=0.0, closed=False):
        """Ribbon along pts; width direction given per point by ups (vectors). Optional thickness via
        offsetting along the ribbon normal. Returns grid rows."""
        n = len(pts)
        rows = []
        for i in range(n):
            p = V(pts[i]); u = V(ups[i]).normalized(); w = widths[i]
            rows.append([self.v(p - u * w * 0.5), self.v(p + u * w * 0.5)])
        for i in range(n - 1 if not closed else n):
            j = (i + 1) % n
            self.f([rows[i][0], rows[j][0], rows[j][1], rows[i][1]])
        return rows

    def grid(self, fn, nu, nv, closed_v=False, mask=None):
        """Parametric surface: fn(u, v) -> Vector, u in [0,1] (nu+1 rows), v in [0,1] (nv cols, wraps if closed_v).
        mask(i, j) -> bool to drop quad (i, j)."""
        cols = nv if closed_v else nv + 1
        G = [[self.v(fn(i / nu, j / nv)) for j in range(cols)] for i in range(nu + 1)]
        for i in range(nu):
            for j in range(nv):
                if mask and not mask(i, j):
                    continue
                j1 = (j + 1) % cols
                self.f([G[i][j], G[i][j1], G[i + 1][j1], G[i + 1][j]])
        return G

    def to_object(self, name, smooth=True, coll=None):
        me = bpy.data.meshes.new(name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        # drop loose verts
        loose = [v for v in self.bm.verts if not v.link_faces]
        bmesh.ops.delete(self.bm, geom=loose, context='VERTS')
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(name, me)
        link(ob, coll)
        if smooth:
            me.shade_smooth()
        return ob


def metaball_mesh(name, elems, res=0.003, threshold=0.6):
    """elems: list of dicts {type, co, r (surface radius), size (semi-axes for ELLIPSOID / half-len for CAPSULE),
    rot (Quaternion/Euler), neg, stiff}. Surface radius is corrected for the stiffness-2 falloff (0.575)."""
    fam = 'MB' + ''.join(c for c in name if c.isalnum())
    mb = bpy.data.metaballs.new(fam)
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = threshold
    ob = bpy.data.objects.new(fam, mb)
    link(ob)
    K = 0.575
    for e in elems:
        t = e.get('type', 'BALL')
        el = mb.elements.new(type=t)
        el.co = V(e['co'])
        el.stiffness = e.get('stiff', 2.0)
        el.use_negative = e.get('neg', False)
        if 'rot' in e:
            r = e['rot']
            el.rotation = r if isinstance(r, Quaternion) else Euler(r).to_quaternion()
        if t == 'BALL':
            el.radius = e['r'] / K
        elif t == 'ELLIPSOID':
            sx, sy, sz = e['size']
            el.radius = 1.0 / K
            el.size_x, el.size_y, el.size_z = sx, sy, sz
        elif t == 'CAPSULE':
            el.radius = e['r'] / K
            el.size_x = e['half']
        elif t == 'CUBE':
            el.radius = e['r'] / K
            el.size_x, el.size_y, el.size_z = e['size']
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    me.name = name
    out = bpy.data.objects.new(name, me)
    link(out)
    me.shade_smooth()
    return out


def capsule_between(a, b, r, **kw):
    """Metaball capsule element between two points (surface radius r)."""
    a, b = V(a), V(b)
    d = b - a
    q = V((1, 0, 0)).rotation_difference(d.normalized())
    e = dict(type='CAPSULE', co=(a + b) * 0.5, r=r, half=d.length * 0.5, rot=q)
    e.update(kw)
    return e


def decimate_copy(src, target_tris, name=None):
    me = src.data.copy()
    ob = bpy.data.objects.new(name or (src.name + '_lo'), me)
    link(ob)
    cur = tri_count(ob)
    if cur > target_tris:
        m = ob.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = target_tris / cur
        m.use_collapse_triangulate = True
        apply_mods(ob)
    ob.data.shade_smooth()
    return ob


def subsurf_copy(src, levels=2, name=None, smooth_shade=True):
    me = src.data.copy()
    ob = bpy.data.objects.new(name or (src.name + '_hi'), me)
    link(ob)
    if levels > 0:
        m = ob.modifiers.new('ss', 'SUBSURF')
        m.levels = levels
        m.render_levels = levels
        m.quality = 3
        apply_mods(ob)
    if smooth_shade:
        ob.data.shade_smooth()
    return ob


def smooth_mesh(ob, iters=5, factor=0.5):
    m = ob.modifiers.new('sm', 'SMOOTH')
    m.iterations = iters
    m.factor = factor
    apply_mods(ob)


def remesh(ob, voxel=0.003, smooth_iters=0):
    m = ob.modifiers.new('rm', 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.adaptivity = 0.0
    apply_mods(ob)
    if smooth_iters:
        m = ob.modifiers.new('cs', 'CORRECTIVE_SMOOTH')
        m.iterations = smooth_iters
        m.smooth_type = 'SIMPLE'
        m.use_only_smooth = True
        apply_mods(ob)
    ob.data.shade_smooth()


def boolean_cut(ob, cutters, solver='EXACT'):
    """Subtract cutter objects (deleted afterwards) from ob."""
    for c in cutters:
        m = ob.modifiers.new('bool', 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = c
        try:
            m.solver = solver
        except Exception:
            pass
        apply_mods(ob)
    delete(cutters)


def fold_displace(ob, amp=0.004, scale=(30, 30, 5), seed=0.0):
    """Hanging-cloth folds: anisotropic noise displacement along vertex normals (hi only)."""
    me = ob.data
    me.update()
    for v in me.vertices:
        p = v.co
        q = Vector((p.x * scale[0] + seed, p.y * scale[1] + seed * 0.7, p.z * scale[2]))
        n = noise.noise(q) + 0.5 * noise.noise(q * 2.1)
        v.co += v.normal * (n * amp)
    me.update()


def triangulate(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(ob.data)
    bm.free()


def join(obs, name):
    obs = [o for o in obs if o is not None]
    if not obs:
        return None
    activate(obs[0])
    for o in obs[1:]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def displace_noise(ob, strength=0.003, scale=0.05, seed=0, along_normal=True):
    """Bake a small organic wobble into the mesh (hand-made feel)."""
    me = ob.data
    off = V((seed * 13.1, seed * 7.7, seed * 3.3))
    me.update()
    for v in me.vertices:
        p = v.co / scale + off
        n = noise.noise(p)
        v.co += v.normal * (n * strength)


# ----------------------------------------------------------------------------------------------
# collision helpers (rest pose fitting)
# ----------------------------------------------------------------------------------------------

def bvh_from(objs):
    verts, polys = [], []
    for o in objs:
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def adjacency(me):
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    return adj


def push_out(ob, bvh, clearance=0.01, iters=6, smooth_iters=2, max_dist=0.25, normal_bias=0.0):
    """Move vertices of ob (world == local assumed) out of / away from obstacle surfaces.
    A vertex is pushed when it is inside (behind the nearest face) or closer than clearance."""
    me = ob.data
    adj = adjacency(me)
    total = 0
    for it in range(iters):
        disp = [Vector() for _ in me.vertices]
        moved = 0
        for v in me.vertices:
            co = v.co
            loc, nrm, idx, d = bvh.find_nearest(co, max_dist)
            if loc is None:
                continue
            inside = (co - loc).dot(nrm) < 0
            if inside or d < clearance:
                target = loc + nrm * clearance
                disp[v.index] = target - co
                moved += 1
        if not moved:
            break
        total += moved
        orig = disp
        for _ in range(smooth_iters):
            nd = []
            for i, dv in enumerate(disp):
                if adj[i]:
                    avg = sum((disp[j] for j in adj[i]), Vector()) / len(adj[i])
                    s = dv * 0.5 + avg * 0.5
                else:
                    s = dv
                nd.append(s if s.length > orig[i].length else orig[i])
            disp = nd
        for v, dv in zip(me.vertices, disp):
            v.co += dv
    me.update()
    return total


def push_out_along(ob, bvh, center=(0, 0.02, 0), mode='axis', clearance=0.012, reach=0.2, iters=4,
                   smooth_iters=3):
    """Cloth-style fitting: every vertex is moved outward (along its normal, oriented away from the body
    centre line / point) to sit `clearance` outside the OUTERMOST obstacle surface along that line.
    Correct for thin obstacles (scapulae, ribs) where nearest-face pushing picks the wrong side."""
    me = ob.data
    adj = adjacency(me)
    C = Vector(center)
    for it in range(iters):
        me.update()
        disp = [Vector() for _ in me.vertices]
        moved = 0
        for v in me.vertices:
            co = v.co
            radial = co - C
            if mode == 'axis':
                radial.z = 0
            if radial.length < 1e-6:
                continue
            radial.normalize()
            n = v.normal.copy()
            if n.dot(radial) < 0:
                n = -n
            d = (n * 0.6 + radial * 0.4).normalized()
            start = co + d * reach
            loc, nrm, idx, dist = bvh.ray_cast(start, -d, reach + clearance)
            if loc is None:
                continue
            # obstacle surface lies beyond (co + d*clearance)?
            need = (loc - co).dot(d) + clearance
            if need > 0:
                disp[v.index] = d * need
                moved += 1
        if not moved:
            break
        orig = disp
        for _ in range(smooth_iters):
            nd = []
            for i, dv in enumerate(disp):
                if adj[i]:
                    avg = sum((disp[j] for j in adj[i]), Vector()) / len(adj[i])
                    s = dv * 0.5 + avg * 0.5
                else:
                    s = dv
                nd.append(s if s.length > orig[i].length else orig[i])
            disp = nd
        for v, dv in zip(me.vertices, disp):
            v.co += dv
    me.update()


def inside_count(ob, bvh, tol=0.0):
    n = 0
    for v in ob.data.vertices:
        loc, nrm, idx, d = bvh.find_nearest(v.co, 0.3)
        if loc is not None and (v.co - loc).dot(nrm) < -tol:
            n += 1
    return n


# ----------------------------------------------------------------------------------------------
# weights
# ----------------------------------------------------------------------------------------------

def set_weights_rigid(ob, bone):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    g = ob.vertex_groups.new(name=bone)
    g.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')


def set_weights_fn(ob, fn):
    """fn(world_co) -> {bone: w}"""
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        ws = fn(mw @ v.co)
        s = sum(ws.values()) or 1.0
        for b, w in ws.items():
            if w <= 0:
                continue
            if b not in groups:
                groups[b] = ob.vertex_groups.new(name=b)
            groups[b].add([v.index], w / s, 'REPLACE')


def lerp_bones(axis, stops):
    """weight fn blending along a world axis: stops = [(coord, bone), ...] sorted."""
    ai = 'xyz'.index(axis)

    def fn(co):
        c = co[ai]
        if c <= stops[0][0]:
            return {stops[0][1]: 1.0}
        if c >= stops[-1][0]:
            return {stops[-1][1]: 1.0}
        for (c0, b0), (c1, b1) in zip(stops, stops[1:]):
            if c0 <= c <= c1:
                t = (c - c0) / (c1 - c0)
                t = t * t * (3 - 2 * t)
                if b0 == b1:
                    return {b0: 1.0}
                return {b0: 1 - t, b1: t}
        return {stops[-1][1]: 1.0}
    return fn


def read_weights(ob):
    """list per vertex of {group_name: w}"""
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        d = {}
        for ge in v.groups:
            if ge.weight > 0:
                d[names[ge.group]] = ge.weight
        out.append(d)
    return out


class WeightSource:
    """Nearest-surface barycentric weight lookup on a skinned reference mesh (rest pose)."""

    def __init__(self, src, exclude_fn=None):
        me = src.data
        mw = src.matrix_world
        me.calc_loop_triangles()
        self.co = [mw @ v.co for v in me.vertices]
        self.w = read_weights(src)
        tris = []
        for lt in me.loop_triangles:
            vs = tuple(lt.vertices)
            if exclude_fn and exclude_fn(self, vs):
                continue
            tris.append(vs)
        self.tris = tris
        self.bvh = BVHTree.FromPolygons(self.co, tris)

    def at(self, p):
        loc, nrm, idx, dist = self.bvh.find_nearest(p)
        if idx is None:
            return {}
        a, b, c = self.tris[idx]
        pa, pb, pc = self.co[a], self.co[b], self.co[c]
        bary = _bary(loc, pa, pb, pc)
        out = {}
        for vi, bw in zip((a, b, c), bary):
            for g, w in self.w[vi].items():
                out[g] = out.get(g, 0.0) + w * bw
        return out


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


def transfer_weights(ob, src_ws, smooth_iters=3, smooth_factor=0.5, limit=4, post=None):
    """Assign smooth weights from a WeightSource to ob (world space), smooth over mesh, limit & normalise.
    post(co, weights)->weights lets callers bias the result."""
    mw = ob.matrix_world
    me = ob.data
    W = [src_ws.at(mw @ v.co) for v in me.vertices]
    if post:
        W = [post(mw @ v.co, w) for v, w in zip(me.vertices, W)]
    # adjacency smoothing
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    for _ in range(smooth_iters):
        NW = []
        for i, w in enumerate(W):
            if not adj[i]:
                NW.append(w)
                continue
            acc = {}
            for j in adj[i]:
                for g, x in W[j].items():
                    acc[g] = acc.get(g, 0) + x / len(adj[i])
            nw = {}
            for g in set(w) | set(acc):
                nw[g] = w.get(g, 0) * (1 - smooth_factor) + acc.get(g, 0) * smooth_factor
            NW.append(nw)
        W = NW
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


def limit_normalize(ob, limit=4):
    W = read_weights(ob)
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        items = sorted(w.items(), key=lambda kv: -kv[1])[:limit]
        items = [(g, x) for g, x in items if x > 0.005]
        s = sum(x for _, x in items) or 1
        for g, x in items:
            if g not in groups:
                groups[g] = ob.vertex_groups.new(name=g)
            groups[g].add([i], x / s, 'REPLACE')
    unweighted = sum(1 for w in W if not w)
    if unweighted:
        log('WARNING unweighted verts', ob.name, unweighted)


# ----------------------------------------------------------------------------------------------
# UV
# ----------------------------------------------------------------------------------------------

def mesh_area(ob):
    mw = ob.matrix_world
    return sum(p.area for p in ob.data.polygons)


def uv_area(ob):
    me = ob.data
    uvl = me.uv_layers.active.data
    tot = 0.0
    for p in me.polygons:
        pts = [uvl[li].uv for li in p.loop_indices]
        a = 0.0
        for i in range(1, len(pts) - 1):
            a += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) * 0.5
        tot += a
    return tot


def uv_unwrap_part(ob, angle=60.0, weight=1.0, margin=0.01):
    activate(ob)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    a3 = mesh_area(ob)
    au = uv_area(ob)
    if au > 0:
        s = math.sqrt(a3 / au) * math.sqrt(weight)
        for l in ob.data.uv_layers.active.data:
            l.uv = l.uv * s


def uv_pack(ob, margin=0.004):
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


# ----------------------------------------------------------------------------------------------
# procedural material DSL
# ----------------------------------------------------------------------------------------------

def srgb(c):
    """sRGB hex/tuple -> linear tuple (RGBA)."""
    if isinstance(c, str):
        c = c.lstrip('#')
        c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


class NB:
    def __init__(self, mat):
        mat.use_nodes = True if hasattr(mat, 'use_nodes') else None
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def node(self, typ, **kw):
        n = self.nt.nodes.new(typ)
        n.location = (self.x, 0)
        self.x += 40
        for k, v in kw.items():
            if hasattr(n, k) and not k.startswith('i_'):
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

    # ---- inputs
    def coord(self, kind='Object'):
        return self.node('ShaderNodeTexCoord').outputs[kind]

    def geo(self, out):
        return self.node('ShaderNodeNewGeometry').outputs[out]

    def attr(self, name, out='Factor'):
        n = self.node('ShaderNodeAttribute', attribute_name=name)
        return n.outputs[out]

    def val(self, v):
        n = self.node('ShaderNodeValue')
        n.outputs[0].default_value = v
        return n.outputs[0]

    def rgb(self, c):
        n = self.node('ShaderNodeRGB')
        n.outputs[0].default_value = c
        return n.outputs[0]

    # ---- textures
    def noise(self, vec=None, scale=5.0, detail=4.0, rough=0.55, dist=0.0, out='Factor', dims='3D', lac=2.0):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dims)
        if vec is not None:
            self.inp(n, 'Vector', vec)
        self.inp(n, 'Scale', scale); self.inp(n, 'Detail', detail); self.inp(n, 'Roughness', rough)
        self.inp(n, 'Distortion', dist); self.inp(n, 'Lacunarity', lac)
        return n.outputs['Factor' if out == 'Factor' else 'Color']

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
        return n.outputs['Factor']

    def mapping(self, vec, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        n = self.node('ShaderNodeMapping')
        self.inp(n, 'Vector', vec)
        n.inputs['Location'].default_value = loc
        n.inputs['Rotation'].default_value = rot
        n.inputs['Scale'].default_value = scale
        return n.outputs[0]

    def ao(self, dist=0.05, samples=16, only_local=False, inside=False):
        n = self.node('ShaderNodeAmbientOcclusion', samples=samples, only_local=only_local, inside=inside)
        self.inp(n, 'Distance', dist)
        return n.outputs['AO']

    # ---- math
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
            el.color = col
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

    def bevel(self, radius=0.004, samples=8):
        n = self.node('ShaderNodeBevel', samples=samples)
        self.inp(n, 'Radius', radius)
        return n.outputs['Normal']

    # ---- finish: principled + named channel reroutes for baking
    def finish(self, color, rough, metal=0.0, normal=None, emit=None, emit_strength=0.0):
        p = self.node('ShaderNodeBsdfPrincipled')
        out = self.node('ShaderNodeOutputMaterial')
        out.name = 'OUT'
        self.inp(p, 'Base Color', color)
        self.inp(p, 'Roughness', rough)
        self.inp(p, 'Metallic', metal)
        if normal is not None:
            self.inp(p, 'Normal', normal)
        if emit is not None:
            self.inp(p, 'Emission Color', emit)
            self.inp(p, 'Emission Strength', emit_strength)
        self.link(p.outputs[0], out.inputs['Surface'])
        p.name = 'BSDF'
        # channel emitters for baking
        for key, sock in (('color', p.inputs['Base Color']), ('rough', p.inputs['Roughness']),
                          ('metal', p.inputs['Metallic'])):
            em = self.node('ShaderNodeEmission')
            em.name = 'CH_' + key
            if sock.is_linked:
                self.link(sock.links[0].from_socket, em.inputs['Color'])
            else:
                dv = sock.default_value
                em.inputs['Color'].default_value = (dv[0], dv[1], dv[2], 1) if hasattr(dv, '__len__') else (dv, dv, dv, 1)
        return p


def set_channel(mats, ch):
    """Route material outputs for baking: ch in ('bsdf', 'color', 'rough', 'metal')."""
    for m in mats:
        nt = m.node_tree
        out = nt.nodes.get('OUT')
        if out is None:
            continue
        src = nt.nodes['BSDF'].outputs[0] if ch == 'bsdf' else nt.nodes['CH_' + ch].outputs[0]
        nt.links.new(src, out.inputs['Surface'])


# ----------------------------------------------------------------------------------------------
# bake
# ----------------------------------------------------------------------------------------------

def new_image(name, size, non_color=False, alpha=False, fill=(0, 0, 0, 1)):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    img.generated_color = fill
    return img


def bake_hi_to_lo(lo, hi, size, prefix, extrusion=0.02, ray=0.04, margin=12, metal=True, samples=16, groups=None,
                  group_cfg=None, fallback=True):
    """Bake hi materials onto lo's UVs. Returns dict of images {color, rough, metal, normal}.
    groups: optional list of (lo_part_obj, hi_obj) pairs baked in isolation (no cross-talk between groups);
    the lo_part objects share lo's UV layout and write into the same images."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.render.bake.margin = margin
    pairs = groups or [(lo, hi)]
    hi_mats = []
    for _, h in pairs:
        hi_mats += [s_.material for s_ in h.material_slots if s_.material and s_.material not in hi_mats]
    imgs = {
        'color': new_image(prefix + '_BaseColor', size, False, fill=(0.5, 0.5, 0.5, 1)),
        'rough': new_image(prefix + '_Rough', size, True, fill=(0.7, 0.7, 0.7, 1)),
        'normal': new_image(prefix + '_Normal', size, True, fill=(0.5, 0.5, 1, 1)),
    }
    if metal:
        imgs['metal'] = new_image(prefix + '_Metal', size, True, fill=(0, 0, 0, 1))
    bm = bpy.data.materials.new(prefix + '_bake')
    bm.use_nodes = True
    tex = bm.node_tree.nodes.new('ShaderNodeTexImage')
    for l, _ in pairs:
        l.data.materials.clear()
        l.data.materials.append(bm)
    passes = [('normal', 'NORMAL', 'bsdf'), ('color', 'EMIT', 'color'), ('rough', 'EMIT', 'rough')]
    if metal:
        passes.append(('metal', 'EMIT', 'metal'))
    for key, btype, ch in passes:
        set_channel(hi_mats, ch)
        tex.image = imgs[key]
        bm.node_tree.nodes.active = tex
        t = time.time()
        for gi, (l, h) in enumerate(pairs):
            ext_g, ray_g = (group_cfg or {}).get(gi, (extrusion, ray))
            deselect_all()
            for o in bpy.context.scene.objects:
                if o.type == 'MESH':
                    o.hide_render = o not in (l, h)
            # the low-poly cage must not shadow / occlude (AO) the high-poly it is baked from
            for attr in ('visible_diffuse', 'visible_glossy', 'visible_shadow', 'visible_transmission',
                         'visible_volume_scatter'):
                if hasattr(l, attr):
                    setattr(l, attr, False)
            h.hide_set(False)
            l.hide_set(False)
            h.select_set(True)
            l.select_set(True)
            bpy.context.view_layer.objects.active = l
            # coarse pass first (generous cage, catches everything), then the precise pass on top: texels the
            # precise rays miss keep the coarse result instead of the clear colour
            settings = [(max(ext_g * 2.5, 0.04), max(ray_g * 2.5, 0.09)), (ext_g, ray_g)] if fallback else [(ext_g, ray_g)]
            for si, (e_, r_) in enumerate(settings):
                kw = dict(type=btype, use_selected_to_active=True, cage_extrusion=e_, max_ray_distance=r_,
                          margin=margin, use_clear=(gi == 0 and si == 0), target='IMAGE_TEXTURES')
                if btype == 'NORMAL':
                    kw.update(normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
                bpy.ops.object.bake(**kw)
        log('baked', key, '%.1fs' % (time.time() - t), 'groups', len(pairs))
    set_channel(hi_mats, 'bsdf')
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = False
    for k, img in imgs.items():
        img.filepath_raw = os.path.join(WORK, img.name + '.png')
        img.file_format = 'PNG'
        img.save()
    return imgs


def split_faces_copy(ob, attr, value, name):
    """Copy of ob keeping only faces whose int face attribute == value."""
    me = ob.data.copy()
    cp = bpy.data.objects.new(name, me)
    link(cp)
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.faces.layers.int.get(attr)
    kill = [f for f in bm.faces if f[lay] != value]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me)
    bm.free()
    return cp


def make_orm(imgs, prefix, size):
    import numpy as np
    r = np.empty(size * size * 4, dtype=np.float32)
    imgs['rough'].pixels.foreach_get(r)
    orm = np.ones(size * size * 4, dtype=np.float32)
    orm[1::4] = r[0::4]
    if 'metal' in imgs:
        m = np.empty(size * size * 4, dtype=np.float32)
        imgs['metal'].pixels.foreach_get(m)
        orm[2::4] = m[0::4]
    else:
        orm[2::4] = 0.0
    img = new_image(prefix + '_ORM', size, True)
    img.pixels.foreach_set(orm)
    img.filepath_raw = os.path.join(WORK, img.name + '.png')
    img.file_format = 'PNG'
    img.save()
    return img


def final_material(name, color_img, orm_img, normal_img, double_sided=False, normal_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = color_img
    nt.links.new(tc.outputs['Color'], p.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = orm_img
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sp.inputs[0])
    nt.links.new(sp.outputs['Green'], p.inputs['Roughness'])
    nt.links.new(sp.outputs['Blue'], p.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = normal_img
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = normal_strength
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    m.use_backface_culling = not double_sided
    return m


def glow_material(name, color=(0.35, 0.7, 1.0, 1), strength=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get('Principled BSDF') or nt.nodes.new('ShaderNodeBsdfPrincipled')
    p.inputs['Base Color'].default_value = (0.02, 0.03, 0.05, 1)
    p.inputs['Roughness'].default_value = 0.4
    p.inputs['Emission Color'].default_value = color
    p.inputs['Emission Strength'].default_value = strength
    return m


# ----------------------------------------------------------------------------------------------
# Kit: collects parts (lo/hi pairs + material + weights) and runs the bake/export pipeline
# ----------------------------------------------------------------------------------------------

class Part:
    def __init__(self, name, lo, hi, mat, weight, uvw=1.0, group='main'):
        self.name, self.lo, self.hi, self.mat, self.weight, self.uvw = name, lo, hi, mat, weight, uvw
        self.group = group


class Kit:
    def __init__(self, name, arm=None):
        self.name = name
        self.arm = arm
        self.parts = []
        self.extra = []   # objects joined after bake (e.g. emissive), with their own materials
        self.hi_extra = {}  # group -> [hi-only objects] (decals baked into the texture, no low-poly)

    def add(self, name, lo, mat, weight=None, hi='ss2', uvw=1.0, lo_mode=None, group=None):
        """lo: object (cage). hi: 'ss1'/'ss2'/'same'/object. lo_mode: ('decimate', tris) to derive lo from hi."""
        lo.name = name + '_lo'
        if isinstance(hi, str):
            if hi.startswith('ss'):
                hi_ob = subsurf_copy(lo, int(hi[2:]), name + '_hi')
            elif hi == 'same':
                hi_ob = lo.copy(); hi_ob.data = lo.data.copy(); link(hi_ob); hi_ob.name = name + '_hi'
            else:
                raise ValueError(hi)
        else:
            hi_ob = hi
            hi_ob.name = name + '_hi'
        if lo_mode and lo_mode[0] == 'decimate':
            new_lo = decimate_copy(hi_ob, lo_mode[1], name + '_lo')
            if lo is not hi_ob:
                delete([lo])
            lo = new_lo
        if isinstance(mat, str):
            mat = bpy.data.materials[mat]
        hi_ob.data.materials.clear()
        hi_ob.data.materials.append(mat)
        p = Part(name, lo, hi_ob, mat, weight, uvw, group or getattr(self, 'default_group', 'main'))
        self.parts.append(p)
        return p

    def tris(self):
        return sum(tri_count(p.lo) for p in self.parts) + sum(tri_count(o) for o in self.extra)

    def report(self):
        rows = sorted(((tri_count(p.lo), p.name) for p in self.parts), reverse=True)
        log('KIT', self.name, 'lo tris', self.tris(), 'parts', len(self.parts))
        for t, n in rows[:60]:
            log('   %6d  %s' % (t, n))

    def build(self, size=2048, extrusion=0.02, ray=0.04, metal=True, double_sided=False, weight_src=None,
              uv_angle=60.0, pack_margin=0.003, normal_strength=1.0, samples=16, group_cfg=None):
        rnd = random.Random(7)
        los = []
        gnames = []
        for p in self.parts:
            if p.group not in gnames:
                gnames.append(p.group)
        his = {g: [] for g in gnames}
        for p in self.parts:
            lo = p.lo
            triangulate(lo)
            # weights
            if self.arm is not None:
                w = p.weight
                if isinstance(w, str):
                    set_weights_rigid(lo, w)
                elif callable(w):
                    set_weights_fn(lo, w)
                elif isinstance(w, tuple) and w[0] == 'transfer':
                    opts = w[1] if len(w) > 1 else {}
                    transfer_weights(lo, weight_src, **opts)
                else:
                    raise ValueError('no weights for ' + p.name)
            uv_unwrap_part(lo, angle=uv_angle, weight=p.uvw)
            ga = lo.data.attributes.new('grp', 'INT', 'FACE')
            ga.data.foreach_set('value', [gnames.index(p.group)] * len(lo.data.polygons))
            # per-part random attribute on hi for colour variation
            hi = p.hi
            a = hi.data.attributes.new('prand', 'FLOAT', 'POINT')
            r = rnd.random()
            a.data.foreach_set('value', [r] * len(hi.data.vertices))
            los.append(lo)
            his[p.group].append(hi)
        LO = join(los, self.name)
        uv_pack(LO, pack_margin)
        for g, obs in self.hi_extra.items():
            if g in his:
                his[g] += obs
        HIS = {g: join(his[g], self.name + '_HI_' + g) for g in gnames}
        log('joined LO tris', tri_count(LO), 'HI tris', sum(tri_count(h) for h in HIS.values()), 'groups', gnames)
        pairs = None
        if len(gnames) > 1:
            pairs = [(split_faces_copy(LO, 'grp', gi, self.name + '_LO_' + g), HIS[g]) for gi, g in enumerate(gnames)]
        gcfg = {gnames.index(g): v for g, v in (group_cfg or {}).items() if g in gnames}
        imgs = bake_hi_to_lo(LO, None, size, self.name, extrusion=extrusion, ray=ray, metal=metal, samples=samples,
                             groups=pairs or [(LO, HIS[gnames[0]])], group_cfg=gcfg)
        if pairs:
            delete([l for l, _ in pairs])
        HI = join(list(HIS.values()), self.name + '_HI')
        orm = make_orm(imgs, self.name, size)
        mat = final_material('M_' + self.name, imgs['color'], orm, imgs['normal'], double_sided, normal_strength)
        LO.data.materials.clear()
        LO.data.materials.append(mat)
        self.LO, self.HI, self.imgs = LO, HI, imgs
        HI.hide_render = True
        HI.hide_set(True)
        if self.extra:
            for o in self.extra:
                triangulate(o)
            LO = join([LO] + self.extra, self.name)
            self.LO = LO
        if self.arm is not None:
            limit_normalize(LO, 4)
            LO.parent = self.arm
            LO.matrix_parent_inverse = Matrix.Identity(4)
            m = LO.modifiers.new('Armature', 'ARMATURE')
            m.object = self.arm
        return LO

    def export(self, path):
        objs = [self.LO] + ([self.arm] if self.arm is not None else [])
        export_glb(path, objs, skinned=self.arm is not None)


def export_glb(path, objs, skinned=True):
    deselect_all()
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if skinned:
        for o in objs:
            if o.type == 'ARMATURE':
                rest_pose(o)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
              export_animations=False, export_skins=skinned, export_influence_nb=4, export_all_influences=False,
              export_def_bones=False, export_leaf_bone=False, export_texcoords=True, export_normals=True,
              export_tangents=True, export_materials='EXPORT', export_image_format='AUTO', export_morph=False,
              export_cameras=False, export_lights=False, export_extras=False, export_rest_position_armature=True,
              export_hierarchy_flatten_bones=False, export_armature_object_remove=False)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as e:
        log('export kw issue', e)
        for k in ('export_leaf_bone', 'export_hierarchy_flatten_bones', 'export_armature_object_remove'):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    log('EXPORTED', path, '%.1f MB' % (os.path.getsize(path) / 1e6))


# ----------------------------------------------------------------------------------------------
# preview rendering (shared by preview.py and quick looks)
# ----------------------------------------------------------------------------------------------

VIEWDEF = {
    'front': (0, 8), 'threeq': (-35, 50), 'back': (180, 15), 'side': (90, 5), 'posed': (-30, 18),
    'top': (-30, 70), 'face': (-20, 12), 'backq': (150, 35), 'posedb': (150, 20), 'posedside': (70, 15),
}


def studio(samples=128, res=1024):
    sc = bpy.context.scene
    gpu_setup(samples)
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.cycles.use_denoising = True
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    lp = nt.nodes.new('ShaderNodeLightPath')
    sky = nt.nodes.new('ShaderNodeBackground')
    sky.inputs['Color'].default_value = (0.42, 0.55, 0.78, 1)
    sky.inputs['Strength'].default_value = 0.9
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.20, 0.205, 0.21, 1)
    bg.inputs['Strength'].default_value = 1.0
    mixs = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mixs.inputs[0])
    nt.links.new(sky.outputs[0], mixs.inputs[1])
    nt.links.new(bg.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs[0])
    sd = bpy.data.lights.new('Sun', 'SUN')
    sd.energy = 4.0
    sd.color = (1.0, 0.86, 0.68)
    sd.angle = math.radians(3)
    sun = bpy.data.objects.new('Sun', sd)
    link(sun)
    sun.rotation_euler = Euler((math.radians(42), 0, math.radians(-38)), 'XYZ')
    rd = bpy.data.lights.new('Rim', 'SUN')
    rd.energy = 1.2
    rd.color = (0.7, 0.8, 1.0)
    rim = bpy.data.objects.new('Rim', rd)
    link(rim)
    rim.rotation_euler = Euler((math.radians(-55), 0, math.radians(150)), 'XYZ')
    gm = bpy.data.materials.new('ground')
    gm.use_nodes = True
    gp = gm.node_tree.nodes.get('Principled BSDF')
    gp.inputs['Base Color'].default_value = (0.20, 0.205, 0.21, 1)
    gp.inputs['Roughness'].default_value = 0.9
    me = bpy.data.meshes.new('ground')
    s = 15
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('GROUND', me)
    link(g)
    me.materials.append(gm)
    cd = bpy.data.cameras.new('Cam')
    cd.lens = 70
    cam = bpy.data.objects.new('Cam', cd)
    link(cam)
    sc.camera = cam
    return cam, g


def eval_points(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        pts += [mw @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return pts


def render_view(cam, meshes, view, outpath, ground=None, ground_z=0.0, pad=1.08, focus=None):
    sc = bpy.context.scene
    pts = eval_points(meshes)
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    if ground is not None:
        ground.location.z = ground_z
    az, el = VIEWDEF[view] if isinstance(view, str) else view
    azr, elr = math.radians(az), math.radians(el)
    d = Vector((math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)))
    c = (mn + mx) * 0.5 if focus is None else Vector(focus[0])
    if focus is not None:
        pts = [p for p in pts if (p - c).length < focus[1]]
    q = (-d).to_track_quat('-Z', 'Y')
    R = q.to_matrix()
    right, up = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0))
    fov = 2 * math.atan(18 / cam.data.lens)
    best = 0.01
    step = max(1, len(pts) // 20000)
    for p in pts[::step]:
        v = p - c
        x, y, z = v.dot(right), v.dot(up), v.dot(d)
        best = max(best, max(abs(x), abs(y)) / math.tan(fov / 2) + z)
    dist = best * pad
    cam.location = c + d * dist
    cam.rotation_euler = q.to_euler()
    cam.data.clip_end = dist * 6
    cam.data.clip_start = 0.01
    sc.render.filepath = outpath
    bpy.ops.render.render(write_still=True)
    log('rendered', outpath)


def save_blend(name):
    p = os.path.join(WORK, name + '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    log('saved', p)

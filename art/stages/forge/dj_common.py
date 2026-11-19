# Copied from C:/dev/AverageJoe/DungeonJoe3D/tools/blender/props/dj_common.py (output paths patched to a temp folder).
"""Shared helpers for Dungeon Joe custom props ("storybook realism", Zone 1 The Mossy Crypt).

Pipeline per asset script:
    build parts (bmesh helpers below, each part gets a procedural material from dj_mats)
    -> join -> store_rest -> warp/lean -> finish(objs, name, tex)   (UV, Cycles GPU bake, export GLB)
    -> preview(name)                                               (re-imports the GLB and renders a preview)

Run headless:
    blender.exe -b --factory-startup --python <asset>.py [-- --no-preview]
"""
import bpy, bmesh, math, os, sys, random, json, time, tempfile
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion, noise as mnoise

ROOT = os.path.join(tempfile.gettempdir(), "jb_stage_djc")  # JoeBrawla copy: never writes under C:\dev\AverageJoe
OUT_DIR = os.path.join(ROOT, "out")
PREV_DIR = os.path.join(ROOT, "prev")
BAKE_DIR = os.path.join(ROOT, "bake")
STATS_FILE = os.path.join(BAKE_DIR, "_stats.json")
for _d in (OUT_DIR, PREV_DIR, BAKE_DIR):
    os.makedirs(_d, exist_ok=True)


def script_args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


# ----------------------------------------------------------------------------- colour
def _s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def col(h, a=1.0):
    """'#rrggbb' (sRGB) -> linear RGBA tuple."""
    if not isinstance(h, str):
        return tuple(h) if len(h) == 4 else (*h, a)
    h = h.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return (_s2l(r), _s2l(g), _s2l(b), a)


# ----------------------------------------------------------------------------- scene
def setup_gpu(samples=32):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        cp = bpy.context.preferences.addons['cycles'].preferences
        for dt in ('OPTIX', 'CUDA'):
            try:
                cp.compute_device_type = dt
            except TypeError:
                continue
            cp.get_devices()
            ok = False
            for d in cp.devices:
                d.use = (d.type == dt)
                ok = ok or d.use
            if ok:
                break
        sc.cycles.device = 'GPU'
    except Exception as e:  # pragma: no cover
        print("GPU setup failed:", e)
    sc.cycles.samples = samples


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PROC.clear()
    setup_gpu()


def rng(seed):
    return random.Random(seed)


# ----------------------------------------------------------------------------- mesh helpers
def mesh_obj(name, bm, mat=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat.mat if isinstance(mat, M) else mat)
    return ob


def set_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat.mat if isinstance(mat, M) else mat)
    return ob


def xform(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), pivot=(0, 0, 0)):
    """Transform mesh data: scale+rotate (degrees XYZ) about pivot then translate."""
    p = Vector(pivot)
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    S = Matrix.Diagonal((*scale, 1.0))
    R = Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4()
    ob.data.transform(Matrix.Translation(Vector(loc) + p) @ R @ S @ Matrix.Translation(-p))
    ob.data.update()
    return ob


def box(name, sx, sy, sz, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, cuts=0):
    """Box with its base centre at loc (before rotation about that base point)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, (v.co.z + 0.5) * sz))
    ob = mesh_obj(name, bm, mat)
    return xform(ob, loc=loc, rot=rot)


def cyl(name, r, h, segs=12, r2=None, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    ob = mesh_obj(name, bm, mat)
    return xform(ob, loc=loc, rot=rot)


def sphere(name, r, segs=12, rings=8, loc=(0, 0, 0), scale=(1, 1, 1), mat=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    ob = mesh_obj(name, bm, mat)
    return xform(ob, loc=loc, scale=scale)


def ico(name, r, subdiv=1, loc=(0, 0, 0), scale=(1, 1, 1), mat=None):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    ob = mesh_obj(name, bm, mat)
    return xform(ob, loc=loc, scale=scale)


def lathe(name, prof, segs=16, mat=None, cap_bottom=True, cap_top=True, loc=(0, 0, 0), phase=0.0):
    """prof: list of (radius, z) from bottom to top. Radius 0 points become poles."""
    bm = bmesh.new()
    rings = []
    for (r, z) in prof:
        if r <= 1e-5:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs + phase),
                                        r * math.sin(2 * math.pi * i / segs + phase), z)) for i in range(segs)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]) if True else ())
            elif len(b) == 1:
                bm.faces.new((a[i], a[j], b[0]))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat)
    return xform(ob, loc=loc)


def extrude_xz(name, pts, depth, mat=None, y=0.0):
    """Polygon outline in the XZ plane (list of (x,z)), extruded along Y, centred on y."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y - depth / 2, z)) for (x, z) in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, mat)


def extrude_xy(name, pts, height, mat=None, z=0.0):
    """Polygon outline in the XY plane, extruded up along Z from z."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for (x, y) in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0, 0, height))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, mat)


def arc_pts(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def cushion(name, r, h, loc, mat, seed=0, segs=10):
    """Soft moss pad: low dome with an irregular outline."""
    prof = [(r, -0.012), (r * 0.99, h * 0.25), (r * 0.9, h * 0.55), (r * 0.7, h * 0.82), (r * 0.38, h * 0.97), (0.0, h)]
    c = lathe(name, prof, segs, mat, cap_bottom=True, cap_top=False, loc=(0, 0, 0))
    off = Vector((seed * 3.7, seed * 1.3, seed * 2.9))
    for v in c.data.vertices:
        n = mnoise.noise_vector(v.co / max(r, 0.03) * 0.9 + off)
        rad = Vector((v.co.x, v.co.y, 0))
        v.co += rad * (0.35 * n.x) + Vector((0, 0, h * 0.35 * n.z * (v.co.z / max(h, 1e-4))))
    c.data.update()
    return xform(c, loc=loc)


def tube(name, path, radius, segs=6, mat=None, cap=True, radii=None, twist=0.0):
    """Sweep a circle along a polyline path (list of Vector-like)."""
    path = [Vector(p) for p in path]
    bm = bmesh.new()
    rings = []
    prev_n = None
    for i, p in enumerate(path):
        if i == 0:
            t = (path[1] - path[0])
        elif i == len(path) - 1:
            t = (path[-1] - path[-2])
        else:
            t = (path[i + 1] - path[i - 1])
        t.normalize()
        if prev_n is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n = t.cross(ref).normalized()
        else:
            n = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = n
        b = t.cross(n).normalized()
        r = radius if radii is None else radii[i]
        ring = []
        for k in range(segs):
            a = 2 * math.pi * k / segs + twist * i
            ring.append(bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * r))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((a[k], a[j], b[j], b[k]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, mat)


def grid(name, nx, ny, fn, mat=None, uv=True):
    """Parametric surface: fn(u,v)->(x,y,z) for u,v in [0,1]. Stores an 'aux' UV = (u,v)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('aux') if uv else None
    vs = [[bm.verts.new(fn(i / nx, j / ny)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            if uv:
                for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    l[uvl].uv = (a / nx, b / ny)
    return mesh_obj(name, bm, mat)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)
    return ob


def bevel(ob, w=0.02, segs=2, angle=35, profile=0.5, clamp=True, harden=False):
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width = w
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.profile = profile
    m.use_clamp_overlap = clamp
    return apply_mods(ob)


def subsurf(ob, levels=1):
    m = ob.modifiers.new('Sub', 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    return apply_mods(ob)


def solidify(ob, thick=0.02, offset=-1.0):
    m = ob.modifiers.new('Sol', 'SOLIDIFY')
    m.thickness = thick
    m.offset = offset
    m.use_even_offset = True
    return apply_mods(ob)


def decimate(ob, ratio):
    m = ob.modifiers.new('Dec', 'DECIMATE')
    m.ratio = ratio
    return apply_mods(ob)


def deform(ob, fn):
    """fn(Vector co) -> Vector new co, applied to every vertex."""
    me = ob.data
    for v in me.vertices:
        v.co = fn(v.co.copy())
    me.update()
    return ob


def warp(ob, amp=0.01, freq=2.0, seed=0, axes=(1, 1, 1)):
    """Coherent noise displacement: nothing perfectly straight."""
    off = Vector((seed * 13.17, seed * 7.71, seed * 3.37))
    for v in ob.data.vertices:
        n = mnoise.noise_vector(v.co * freq + off)
        v.co += Vector((n.x * amp * axes[0], n.y * amp * axes[1], n.z * amp * axes[2]))
    ob.data.update()
    return ob


def lean(ob, rx=0.0, ry=0.0, rz=0.0, pivot=(0, 0, 0)):
    return xform(ob, rot=(rx, ry, rz), pivot=pivot)


def smooth(ob, angle=40):
    me = ob.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))
    return ob


def flat(ob):
    ob.data.shade_flat()
    return ob


def face_attr(ob, name, value):
    me = ob.data
    n = len(me.polygons)
    if isinstance(value, (tuple, list, Vector)):
        a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT_VECTOR', 'FACE')
        a.data.foreach_set('vector', list(value) * n)
    else:
        a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'FACE')
        a.data.foreach_set('value', [float(value)] * n)
    return ob


def grain(ob, d):
    return face_attr(ob, 'grain', Vector(d).normalized())


def pid(ob, v):
    return face_attr(ob, 'pid', v)


def store_rest(ob):
    me = ob.data
    a = me.attributes.get('rest') or me.attributes.new('rest', 'FLOAT_VECTOR', 'POINT')
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    a.data.foreach_set('vector', co)
    return ob


def join(objs, name):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def merge_close(ob, dist=1e-4):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def delete_faces(ob, pred):
    """pred(center Vector, normal Vector) -> True to delete."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = [f for f in bm.faces if pred(f.calc_center_median(), f.normal)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def delete_bottom(ob, z=0.03):
    return delete_faces(ob, lambda c, n: n.z < -0.95 and c.z < z)


def triangulate(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def set_origin(ob, pivot):
    p = Vector(pivot)
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p
    return ob


def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    t = 0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        t += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return t


# ----------------------------------------------------------------------------- carved-text masks
_GLYPHS = {
    'J': [[(0.35, 1), (0.95, 1)], [(0.7, 1), (0.7, 0.28), (0.58, 0.05), (0.32, 0.05), (0.15, 0.25)]],
    'E': [[(0.85, 1), (0.2, 1), (0.2, 0), (0.85, 0)], [(0.2, 0.52), (0.7, 0.52)]],
    'R': [[(0.2, 0), (0.2, 1), (0.65, 1), (0.82, 0.88), (0.82, 0.64), (0.65, 0.52), (0.2, 0.52)], [(0.45, 0.52), (0.85, 0)]],
    'P': [[(0.2, 0), (0.2, 1), (0.65, 1), (0.82, 0.88), (0.82, 0.64), (0.65, 0.52), (0.2, 0.52)]],
    'I': [[(0.5, 0), (0.5, 1)], [(0.3, 1), (0.7, 1)], [(0.3, 0), (0.7, 0)]],
    'A': [[(0.1, 0), (0.5, 1), (0.9, 0)], [(0.27, 0.4), (0.73, 0.4)]],
    'N': [[(0.15, 0), (0.15, 1), (0.85, 0), (0.85, 1)]],
    '.': [[(0.5, 0.04), (0.5, 0.08)]],
    '+': [[(0.5, 0.0), (0.5, 1.0)], [(0.18, 0.66), (0.82, 0.66)]],
    '-': [[(0.2, 0.5), (0.8, 0.5)]],
    ' ': [],
}
_GLYPHS['O'] = [[(0.5 + 0.38 * math.cos(2 * math.pi * i / 14), 0.5 + 0.5 * math.sin(2 * math.pi * i / 14)) for i in range(15)]]


def text_strokes(text, x, y, h, width_frac=0.13, spacing=0.78, center=True):
    """Return stroke list [(a, b, w)] for text whose baseline-left is (x,y) with cap height h (metres)."""
    adv = h * spacing
    if center:
        x -= adv * len(text) / 2
    out = []
    for i, ch in enumerate(text.upper()):
        for poly in _GLYPHS.get(ch, []):
            for a, b in zip(poly[:-1], poly[1:]):
                out.append(((x + i * adv + a[0] * h * 0.75, y + a[1] * h),
                            (x + i * adv + b[0] * h * 0.75, y + b[1] * h), h * width_frac))
    return out


def scribble_strokes(x0, x1, y, h, seed=0, width_frac=0.11, k=(0.45, 0.8)):
    """Illegible weathered 'writing': clusters of short strokes between x0..x1 on baseline y."""
    r = rng(seed)
    out = []
    x = x0
    while x < x1 - h * 0.4:
        word = r.randint(2, 6)
        for _ in range(word):
            if x > x1 - h * 0.4:
                break
            kind = r.random()
            w = h * r.uniform(0.35, 0.6)
            if kind < 0.45:
                out.append(((x, y), (x, y + h * r.uniform(0.6, 1.0)), h * width_frac))
            elif kind < 0.7:
                out.append(((x, y), (x + w, y + h), h * width_frac))
            elif kind < 0.85:
                out.append(((x, y + h * 0.5), (x + w, y + h * 0.5), h * width_frac))
                out.append(((x, y), (x, y + h), h * width_frac))
            else:
                cx, cy = x + w / 2, y + h / 2
                pts = [(cx + w / 2 * math.cos(a), cy + h / 2 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)]
                out += [(a, b, h * width_frac) for a, b in zip(pts[:-1], pts[1:])]
            x += w + h * 0.18
        x += h * 0.45
    return [(a, b, w, r.uniform(*k)) for (a, b, w) in out]


def stroke_image(name, w, h, strokes, res=512):
    """Rasterise grooves (1 = groove centre) into a float Non-Color image covering [0,w]x[0,h]."""
    rx = res
    ry = max(16, int(res * h / w))
    xs = (np.arange(rx) + 0.5) / rx * w
    ys = (np.arange(ry) + 0.5) / ry * h
    X, Y = np.meshgrid(xs, ys)
    out = np.zeros((ry, rx), np.float32)
    for st in strokes:
        a, b, wd = st[:3]
        k = st[3] if len(st) > 3 else 1.0
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy + 1e-12
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        v = np.clip(1 - d / wd, 0, 1)
        v = v * v * (3 - 2 * v) * k
        np.maximum(out, v, out=out)
    img = bpy.data.images.new(name, rx, ry, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    px = np.ones((ry, rx, 4), np.float32)
    px[:, :, 0] = out
    px[:, :, 1] = out
    px[:, :, 2] = out
    img.pixels.foreach_set(px.ravel())
    img.update()
    return img


# ----------------------------------------------------------------------------- node builder
PROC = {}


class M:
    """Procedural material with bakeable channels: color, rough, metal, height (bump), emit."""

    def __init__(self, name, glow=False):
        mt = bpy.data.materials.new(name)
        self.mat = mt
        self.nt = mt.node_tree
        self.N = self.nt.nodes
        self.Lk = self.nt.links
        self.N.clear()
        self.out = self.N.new('ShaderNodeOutputMaterial')
        self.bsdf = self.N.new('ShaderNodeBsdfPrincipled')
        self.emitn = self.N.new('ShaderNodeEmission')
        self.bumpn = self.N.new('ShaderNodeBump')
        self.L(self.bumpn.outputs['Normal'], self.bsdf.inputs['Normal'])
        self.target = self.N.new('ShaderNodeTexImage')
        self.ch = {}
        self._rest = None
        self._geo = None
        self.glow = glow
        if glow:
            mt['dj_glow'] = 1
        PROC[mt.name] = self
        self.L(self.bsdf.outputs[0], self.out.inputs['Surface'])

    # -- basics
    def L(self, a, b):
        self.Lk.new(a, b)

    def inp(self, sock, x):
        if isinstance(x, bpy.types.NodeSocket):
            self.L(x, sock)
            return
        if isinstance(x, str):
            x = col(x)
        if sock.type == 'RGBA':
            if isinstance(x, (int, float)):
                x = (x, x, x, 1.0)
            elif len(x) == 3:
                x = (*x, 1.0)
        elif sock.type == 'VECTOR':
            if isinstance(x, (int, float)):
                x = (x, x, x)
            elif len(x) == 4:
                x = x[:3]
        sock.default_value = x

    def S(self, x):
        if isinstance(x, bpy.types.NodeSocket):
            return x
        if isinstance(x, (int, float)):
            n = self.N.new('ShaderNodeValue')
            n.outputs[0].default_value = float(x)
            return n.outputs[0]
        n = self.N.new('ShaderNodeRGB')
        n.outputs[0].default_value = col(x)
        return n.outputs[0]

    @property
    def rest(self):
        if self._rest is None:
            n = self.N.new('ShaderNodeAttribute')
            n.attribute_type = 'GEOMETRY'
            n.attribute_name = 'rest'
            self._rest = n.outputs['Vector']
        return self._rest

    def attr(self, name, out='Fac'):
        n = self.N.new('ShaderNodeAttribute')
        n.attribute_type = 'GEOMETRY'
        n.attribute_name = name
        return n.outputs[out]

    @property
    def geo(self):
        if self._geo is None:
            self._geo = self.N.new('ShaderNodeNewGeometry')
        return self._geo

    @property
    def normal(self):
        return self.geo.outputs['Normal']

    def sep(self, v):
        n = self.N.new('ShaderNodeSeparateXYZ')
        self.inp(n.inputs[0], v)
        return n.outputs['X'], n.outputs['Y'], n.outputs['Z']

    def comb(self, x, y, z):
        n = self.N.new('ShaderNodeCombineXYZ')
        self.inp(n.inputs[0], x)
        self.inp(n.inputs[1], y)
        self.inp(n.inputs[2], z)
        return n.outputs[0]

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.N.new('ShaderNodeMath')
        n.operation = op
        n.use_clamp = clamp
        self.inp(n.inputs[0], a)
        if b is not None:
            self.inp(n.inputs[1], b)
        if c is not None:
            self.inp(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b, clamp=False):
        return self.math('ADD', a, b, clamp=clamp)

    def sub(self, a, b, clamp=False):
        return self.math('SUBTRACT', a, b, clamp=clamp)

    def mul(self, a, b, clamp=False):
        return self.math('MULTIPLY', a, b, clamp=clamp)

    def madd(self, a, b, c, clamp=False):
        return self.math('MULTIPLY_ADD', a, b, c, clamp=clamp)

    def mx(self, a, b):
        return self.math('MAXIMUM', a, b)

    def mn(self, a, b):
        return self.math('MINIMUM', a, b)

    def inv(self, a):
        return self.math('SUBTRACT', 1.0, a, clamp=True)

    def clamp01(self, a):
        return self.math('ADD', a, 0.0, clamp=True)

    def mr(self, x, a, b, c=0.0, d=1.0, interp='SMOOTHSTEP', clamp=True):
        n = self.N.new('ShaderNodeMapRange')
        n.interpolation_type = interp
        n.clamp = clamp
        self.inp(n.inputs[0], x)
        self.inp(n.inputs[1], a)
        self.inp(n.inputs[2], b)
        self.inp(n.inputs[3], c)
        self.inp(n.inputs[4], d)
        return n.outputs[0]

    def lin(self, x, a, b, c=0.0, d=1.0, clamp=True):
        return self.mr(x, a, b, c, d, interp='LINEAR', clamp=clamp)

    def mix(self, fac, a, b, blend='MIX'):
        n = self.N.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = blend
        n.clamp_factor = True
        ins = {s.identifier: s for s in n.inputs}
        self.inp(ins['Factor_Float'], fac)
        self.inp(ins['A_Color'], a)
        self.inp(ins['B_Color'], b)
        return [s for s in n.outputs if s.identifier == 'Result_Color'][0]

    def lerp(self, fac, a, b):
        n = self.N.new('ShaderNodeMix')
        n.data_type = 'FLOAT'
        n.clamp_factor = True
        ins = {s.identifier: s for s in n.inputs}
        self.inp(ins['Factor_Float'], fac)
        self.inp(ins['A_Float'], a)
        self.inp(ins['B_Float'], b)
        return [s for s in n.outputs if s.identifier == 'Result_Float'][0]

    def vm(self, op, a, b=None, scale=None):
        n = self.N.new('ShaderNodeVectorMath')
        n.operation = op
        self.inp(n.inputs[0], a)
        if b is not None:
            self.inp(n.inputs[1], b)
        if scale is not None:
            self.inp(n.inputs[3], scale)
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def noise(self, vec, scale=1.0, detail=2.0, rough=0.5, dist=0.0, ntype='FBM', lac=2.0):
        n = self.N.new('ShaderNodeTexNoise')
        n.noise_dimensions = '3D'
        n.noise_type = ntype
        self.inp(n.inputs['Vector'], vec)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Detail'], detail)
        self.inp(n.inputs['Roughness'], rough)
        self.inp(n.inputs['Distortion'], dist)
        self.inp(n.inputs['Lacunarity'], lac)
        return n.outputs['Fac']

    def noisec(self, vec, scale=1.0, detail=2.0, rough=0.5):
        n = self.N.new('ShaderNodeTexNoise')
        self.inp(n.inputs['Vector'], vec)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Detail'], detail)
        self.inp(n.inputs['Roughness'], rough)
        return n.outputs['Color']

    def voronoi(self, vec, scale=5.0, feature='F1', metric='EUCLIDEAN', rand=1.0):
        n = self.N.new('ShaderNodeTexVoronoi')
        n.voronoi_dimensions = '3D'
        n.feature = feature
        n.distance = metric
        self.inp(n.inputs['Vector'], vec)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Randomness'], rand)
        outs = {s.identifier: s for s in n.outputs}
        return outs.get('Distance'), outs.get('Color')

    def wave(self, vec, scale=5.0, dist=2.0, detail=2.0, kind='BANDS', direction='X', profile='SIN'):
        n = self.N.new('ShaderNodeTexWave')
        n.wave_type = kind
        if kind == 'BANDS':
            n.bands_direction = direction
        else:
            n.rings_direction = direction
        n.wave_profile = profile
        self.inp(n.inputs['Vector'], vec)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Distortion'], dist)
        self.inp(n.inputs['Detail'], detail)
        return n.outputs['Fac']

    def ao(self, dist=0.2, inside=False, local=False, samples=12):
        n = self.N.new('ShaderNodeAmbientOcclusion')
        n.inside = inside
        n.only_local = local
        n.samples = samples
        n.inputs['Distance'].default_value = dist
        return n.outputs['AO']

    def image(self, img, vec, extension='CLIP', interp='Linear'):
        n = self.N.new('ShaderNodeTexImage')
        n.image = img
        n.extension = extension
        n.interpolation = interp
        self.inp(n.inputs['Vector'], vec)
        return n.outputs['Color']

    def uvmap(self, name='aux'):
        n = self.N.new('ShaderNodeUVMap')
        n.uv_map = name
        return n.outputs['UV']

    def bw(self, c):
        n = self.N.new('ShaderNodeRGBToBW')
        self.inp(n.inputs[0], c)
        return n.outputs[0]

    def hsv(self, c, h=0.5, s=1.0, v=1.0):
        n = self.N.new('ShaderNodeHueSaturation')
        self.inp(n.inputs['Hue'], h)
        self.inp(n.inputs['Saturation'], s)
        self.inp(n.inputs['Value'], v)
        self.inp(n.inputs['Color'], c)
        return n.outputs['Color']

    # common derived masks
    def edge_mask(self, dist=0.03, lo=0.08, hi=0.45):
        return self.mr(self.inv(self.ao(dist, inside=True, samples=12)), lo, hi)

    def cavity_mask(self, dist=0.2, lo=0.05, hi=0.6):
        return self.mr(self.inv(self.ao(dist, samples=12)), lo, hi)

    def up_mask(self, lo=0.4, hi=0.85):
        return self.mr(self.sep(self.normal)[2], lo, hi)

    # -- channels
    def set(self, color=None, rough=None, metal=None, height=None, emit=None, bump=0.4, bump_dist=0.01):
        for k, v in (('color', color), ('rough', rough), ('metal', metal), ('height', height), ('emit', emit)):
            if v is not None:
                self.ch[k] = self.S(v) if not isinstance(v, bpy.types.NodeSocket) else v
        self.bumpn.inputs['Strength'].default_value = bump
        self.bumpn.inputs['Distance'].default_value = bump_dist
        if 'height' in self.ch:
            self.L(self.ch['height'], self.bumpn.inputs['Height'])
        if 'color' in self.ch:
            self.L(self.ch['color'], self.bsdf.inputs['Base Color'])
        if 'rough' in self.ch:
            self.L(self.ch['rough'], self.bsdf.inputs['Roughness'])
        if 'metal' in self.ch:
            self.L(self.ch['metal'], self.bsdf.inputs['Metallic'])
        if 'emit' in self.ch:
            self.L(self.ch['emit'], self.bsdf.inputs['Emission Color'])
            self.bsdf.inputs['Emission Strength'].default_value = 1.0
        return self

    DEFAULTS = {'color': (0.5, 0.5, 0.5, 1), 'rough': (0.8, 0.8, 0.8, 1), 'metal': (0, 0, 0, 1), 'emit': (0, 0, 0, 1)}

    def wire(self, key):
        for l in list(self.out.inputs['Surface'].links):
            self.Lk.remove(l)
        for l in list(self.emitn.inputs['Color'].links):
            self.Lk.remove(l)
        if key in ('normal', 'final', 'ao'):
            self.L(self.bsdf.outputs[0], self.out.inputs['Surface'])
            return
        s = self.ch.get(key)
        if s is None:
            self.emitn.inputs['Color'].default_value = self.DEFAULTS[key]
        else:
            self.L(s, self.emitn.inputs['Color'])
        self.emitn.inputs['Strength'].default_value = 1.0
        self.L(self.emitn.outputs[0], self.out.inputs['Surface'])


def glow_mat(name, color, strength=4.0, base=None):
    m = M(name, glow=True)
    c = col(color)
    m.bsdf.inputs['Base Color'].default_value = col(base) if base else c
    m.bsdf.inputs['Emission Color'].default_value = c
    m.bsdf.inputs['Emission Strength'].default_value = strength
    m.bsdf.inputs['Roughness'].default_value = 0.2
    m.ch['color'] = m.S(base or color)
    m.ch['rough'] = m.S(0.2)
    m.mat.diffuse_color = c
    return m


# ----------------------------------------------------------------------------- bake + export
def _px(im):
    a = np.empty(len(im.pixels), np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)


def _save(im, path):
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()


def _gltf_output_group():
    ng = bpy.data.node_groups.get('glTF Material Output')
    if ng is None:
        ng = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        ng.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        ng.interface.new_socket('Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    return ng


def unwrap(objs, margin=0.006, angle=62):
    for o in objs:
        me = o.data
        uv = me.uv_layers.get('atlas') or me.uv_layers.new(name='atlas')
        me.uv_layers.active = uv
        uv.active_render = True
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=margin, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')


def bake(objs, name, size=1024, emission=False, ao_dist=0.6, samples=48, ao_strength=0.35, emission_strength=3.0):
    t0 = time.time()
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = ao_dist
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.bake.margin = max(8, size // 64)
    mats = []
    for o in objs:
        for s in o.material_slots:
            if s.material and s.material not in mats:
                mats.append(s.material)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    passes = [('color', True, 'EMIT'), ('rough', False, 'EMIT'), ('metal', False, 'EMIT'),
              ('normal', False, 'NORMAL'), ('ao', False, 'AO')]
    if emission:
        passes.append(('emit', True, 'EMIT'))
    imgs = {}
    for key, iscol, btype in passes:
        im = bpy.data.images.new(f"{name}_{key}_raw", size, size, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'sRGB' if iscol else 'Non-Color'
        for mt in mats:
            pm = PROC[mt.name]
            pm.wire(key)
            pm.target.image = im
            mt.node_tree.nodes.active = pm.target
        kw = dict(type=btype, margin=sc.render.bake.margin, use_clear=True)
        if btype == 'NORMAL':
            kw['normal_space'] = 'TANGENT'
        bpy.ops.object.bake(**kw)
        imgs[key] = im
        print(f"  baked {key} ({time.time() - t0:.1f}s)")
    for mt in mats:
        PROC[mt.name].wire('final')

    # combine
    base = _px(imgs['color']).copy()
    ao = _px(imgs['ao'])[:, :, 0]
    aof = 1.0 - ao_strength * (1.0 - ao)
    base[:, :, :3] *= aof[:, :, None]
    base[:, :, 3] = 1.0
    orm = np.ones_like(base)
    orm[:, :, 0] = ao
    orm[:, :, 1] = np.clip(_px(imgs['rough'])[:, :, 0], 0.04, 1.0)
    orm[:, :, 2] = _px(imgs['metal'])[:, :, 0]

    def mk(key, arr, srgb):
        im = bpy.data.images.new(f"{name}_{key}", size, size, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        im.pixels.foreach_set(arr.ravel())
        _save(im, os.path.join(BAKE_DIR, f"{name}_{key}.png"))
        return im

    out = {'base': mk('BaseColor', base, True), 'orm': mk('ORM', orm, False)}
    nrm = _px(imgs['normal']).copy()
    nrm[:, :, 3] = 1.0
    out['normal'] = mk('Normal', nrm, False)
    if emission:
        e = _px(imgs['emit']).copy()
        e[:, :, 3] = 1.0
        out['emit'] = mk('Emission', e, True)
    for im in imgs.values():
        bpy.data.images.remove(im)
    print(f"  bake done {time.time() - t0:.1f}s")
    return out


def baked_material(name, imgs, emission_strength=3.0, double_sided=False):
    mt = bpy.data.materials.new(name)
    nt = mt.node_tree
    N = nt.nodes
    L = nt.links.new
    N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    b = N.new('ShaderNodeBsdfPrincipled')
    L(b.outputs[0], out.inputs['Surface'])
    tb = N.new('ShaderNodeTexImage')
    tb.image = imgs['base']
    L(tb.outputs['Color'], b.inputs['Base Color'])
    to = N.new('ShaderNodeTexImage')
    to.image = imgs['orm']
    sp = N.new('ShaderNodeSeparateColor')
    L(to.outputs['Color'], sp.inputs[0])
    L(sp.outputs['Green'], b.inputs['Roughness'])
    L(sp.outputs['Blue'], b.inputs['Metallic'])
    tn = N.new('ShaderNodeTexImage')
    tn.image = imgs['normal']
    nm = N.new('ShaderNodeNormalMap')
    nm.uv_map = 'atlas'
    L(tn.outputs['Color'], nm.inputs['Color'])
    L(nm.outputs['Normal'], b.inputs['Normal'])
    g = N.new('ShaderNodeGroup')
    g.node_tree = _gltf_output_group()
    L(sp.outputs['Red'], g.inputs['Occlusion'])
    if 'emit' in imgs:
        te = N.new('ShaderNodeTexImage')
        te.image = imgs['emit']
        L(te.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emission_strength
    mt.use_backface_culling = not double_sided
    return mt


def swap_materials(objs, baked):
    for o in objs:
        me = o.data
        old = [s.material for s in o.material_slots]
        glows = []
        for m in old:
            if m is not None and m.get('dj_glow') and m not in glows:
                glows.append(m)
        newlist = [baked] + glows
        remap = np.array([(newlist.index(m) if (m in glows) else 0) for m in old] or [0], np.int32)
        mi = np.zeros(len(me.polygons), np.int32)
        me.polygons.foreach_get('material_index', mi)
        mi = remap[np.clip(mi, 0, len(remap) - 1)]
        me.materials.clear()
        for m in newlist:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', mi)
        me.update()


def cleanup_layers(objs):
    for o in objs:
        me = o.data
        for uv in list(me.uv_layers):
            if uv.name != 'atlas':
                me.uv_layers.remove(uv)
        for an in ('rest', 'grain', 'pid'):
            a = me.attributes.get(an)
            if a is not None:
                me.attributes.remove(a)


def export_glb(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(OUT_DIR, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_texcoords=True, export_normals=True, export_tangents=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False,
                              export_lights=False, export_extras=False, export_animations=False,
                              export_attributes=False)
    return path


def record_stats(name, **kw):
    try:
        with open(STATS_FILE) as f:
            st = json.load(f)
    except Exception:
        st = {}
    st[name] = kw
    with open(STATS_FILE, 'w') as f:
        json.dump(st, f, indent=1)


def finish(objs, name, tex=1024, emission=False, emission_strength=3.0, ao_dist=0.6, ao_strength=0.35,
           samples=48, margin=0.006, double_sided=False, smooth_angle=None):
    """UV-unwrap objs into one shared atlas, bake procedural materials, swap to baked PBR, export GLB."""
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    for o in objs:
        if o.data.attributes.get('rest') is None:
            store_rest(o)
        if smooth_angle is not None:
            smooth(o, smooth_angle)
        triangulate(o)
    unwrap(objs, margin=margin)
    imgs = bake(objs, name, size=tex, emission=emission, ao_dist=ao_dist, samples=samples,
                ao_strength=ao_strength, emission_strength=emission_strength)
    mt = baked_material(f"{name}_mat", imgs, emission_strength=emission_strength, double_sided=double_sided)
    swap_materials(objs, mt)
    cleanup_layers(objs)
    path = export_glb(objs, name)
    tris = tri_count(objs)
    record_stats(name, tris=tris, tex=tex, objects=[o.name for o in objs],
                 materials=sorted({s.material.name for o in objs for s in o.material_slots if s.material}))
    print(f"EXPORTED {name}: {tris} tris, tex {tex}, -> {path}")
    return tris


# ----------------------------------------------------------------------------- preview rendering
def _stage(hole=None, ground='#9aa08c', size=40.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('PreviewWorld')
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputWorld')
    sky = nt.nodes.new('ShaderNodeBackground')
    sky.inputs['Color'].default_value = col('#a9c3dd')
    sky.inputs['Strength'].default_value = 0.55
    cam = nt.nodes.new('ShaderNodeBackground')
    cam.inputs['Color'].default_value = col('#c8c6bc')
    cam.inputs['Strength'].default_value = 1.0
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(sky.outputs[0], mx.inputs[1])
    nt.links.new(cam.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], o.inputs[0])
    # sun: warm morning light from front-left, high
    sd = bpy.data.lights.new('Sun', 'SUN')
    sd.energy = 3.0
    sd.color = col('#f6e2b3')[:3]
    sd.angle = math.radians(3)
    so = bpy.data.objects.new('Sun', sd)
    sc.collection.objects.link(so)
    sdir = Vector((-0.55, -0.8, 1.05)).normalized()
    so.rotation_euler = sdir.to_track_quat('Z', 'Y').to_euler()
    # ground (with optional rectangular hole x0,y0,x1,y1)
    gm = bpy.data.materials.new('Ground')
    gb = gm.node_tree.nodes.get('Principled BSDF')
    gb.inputs['Base Color'].default_value = col(ground)
    gb.inputs['Roughness'].default_value = 1.0
    bm = bmesh.new()
    S = size
    rects = [(-S, -S, S, S)]
    if hole:
        x0, y0, x1, y1 = hole
        rects = [(-S, -S, S, y0), (-S, y1, S, S), (-S, y0, x0, y1), (x1, y0, S, y1)]
    for (a, b, c, d) in rects:
        vs = [bm.verts.new(p) for p in ((a, b, 0), (c, b, 0), (c, d, 0), (a, d, 0))]
        bm.faces.new(vs)
    g = mesh_obj('Ground', bm, gm)
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 128
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.render.film_transparent = False
    return g


def _bbox(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
    return mn, mx


def _camera(bmin, bmax, az, el, resx, resy, margin=1.12, lens=50, target=None):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get('PCam') or bpy.data.cameras.new('PCam')
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 500
    co = bpy.data.objects.get('PCam') or bpy.data.objects.new('PCam', cd)
    if co.name not in sc.collection.objects:
        sc.collection.objects.link(co)
    sc.camera = co
    sc.render.resolution_x = resx
    sc.render.resolution_y = resy
    az, el = math.radians(az), math.radians(el)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    fwd = -d
    q = fwd.to_track_quat('-Z', 'Y')
    R = q.to_matrix()
    right = R @ Vector((1, 0, 0))
    up = R @ Vector((0, 1, 0))
    center = (bmin + bmax) / 2 if target is None else Vector(target)
    tan_h = 18.0 / lens
    tan_v = tan_h * resy / resx
    dist = 0.5
    for i in range(8):
        c = Vector((bmax.x if i & 1 else bmin.x, bmax.y if i & 2 else bmin.y, bmax.z if i & 4 else bmin.z))
        rel = c - center
        x, y, z = rel.dot(right), rel.dot(up), rel.dot(fwd)
        dist = max(dist, z + abs(x) * margin / tan_h, z + abs(y) * margin / tan_v)
    co.location = center + d * dist
    co.rotation_euler = q.to_euler()
    return co


def _render(path):
    sc = bpy.context.scene
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _compose(paths, out, layout):
    ims = [bpy.data.images.load(p) for p in paths]
    arrs = [_px(i) for i in ims]
    if layout == 'h':
        full = np.concatenate([arrs[0], arrs[1]], axis=1)
        k = arrs[0].shape[1]
        full[:, k - 1:k + 1, :3] = 0.3
    else:
        full = np.concatenate([arrs[1], arrs[0]], axis=0)
        k = arrs[1].shape[0]
        full[k - 1:k + 1, :, :3] = 0.3
    full[:, :, 3] = 1.0
    h, w = full.shape[:2]
    im = bpy.data.images.new('compose', w, h, alpha=False)
    im.pixels.foreach_set(full.ravel())
    _save(im, out)
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


def preview(name, hole=None, front_az=0.0, az=35.0, el=50.0, front_el=14.0, front_target=None, front_margin=1.05,
            extra=None, bbox=None, front_bbox=None):
    """Fresh scene, import the exported GLB, render 3/4 high view + closer front view into one 1024x1024 PNG."""
    reset()
    path = os.path.join(OUT_DIR, name + '.glb')
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    _stage(hole=hole)
    if extra:
        extra()
    bmin, bmax = _bbox(objs) if bbox is None else (Vector(bbox[0]), Vector(bbox[1]))
    ext = bmax - bmin
    wide = max(ext.x, ext.y) > ext.z * 1.25
    layout = 'v' if wide else 'h'
    rx, ry = (1024, 512) if layout == 'v' else (512, 1024)
    t1 = os.path.join(BAKE_DIR, f"_{name}_a.png")
    t2 = os.path.join(BAKE_DIR, f"_{name}_b.png")
    _camera(bmin, bmax, az, el, rx, ry, margin=1.1)
    _render(t1)
    fb = (bmin, bmax) if front_bbox is None else (Vector(front_bbox[0]), Vector(front_bbox[1]))
    _camera(fb[0], fb[1], front_az, front_el, rx, ry, margin=front_margin, lens=60, target=front_target)
    _render(t2)
    out = os.path.join(PREV_DIR, name + '.png')
    _compose([t1, t2], out, layout)
    print("PREVIEW", out)
    return out


def main_finish(build, name, **preview_kw):
    """Standard entry: build() returns tris; then preview unless --no-preview."""
    build()
    if '--no-preview' not in script_args():
        preview(name, **preview_kw)

"""Shared helpers for the JoeBrawla fighter pipeline (Blender 5.2, headless).
Adapted from the Dungeon Joe 3D Caretaker toolkit (tools/blender/bosses/caretaker/ct_lib.py, owner's code).

Contents
  * paths / constants (fighter id = name of the folder this file lives in)
  * numpy gradient noise (3D Perlin + fBm + ridged)
  * signed-distance primitives + an SDF "sculpt" grid with smooth CSG ops
  * surface nets polygoniser (SDF grid -> quad mesh), Taubin smoothing, vertex normals
  * bpy mesh creation from numpy, Cycles setup, bake helpers, image <-> numpy
  * pose helpers ("rest-axes" rotations for UAL bones), UAL clip retargeting for previews
  * glTF-friendly PBR materials, EEVEE studio for previews
"""
import math
import os
import json
import numpy as np

# --------------------------------------------------------------------------------------------
# paths
HERE = os.path.dirname(os.path.abspath(__file__))
FID = os.path.basename(HERE)
GAME = r"C:\dev\JoeBrawla"
WORK = os.path.join(GAME, "art", "_work", FID)
PREV_DIR = os.path.join(HERE, "previews")
TEX = os.path.join(WORK, "tex")
DJ = r"C:\dev\AverageJoe\DungeonJoe3D"
UAL1 = os.path.join(DJ, r"assets\thirdparty\quaternius\anim\UAL1_Standard.glb")
UAL2 = os.path.join(DJ, r"assets\thirdparty\quaternius\anim\UAL2_Standard.glb")
UBC_MALE = os.path.join(DJ, r"assets\thirdparty\quaternius\ubc\bodies\Superhero_Male_FullBody.gltf")
BLENDER = r"C:\dev\AverageJoe\tools\blender\blender-5.2.3-windows-x64\blender.exe"
UAL_PELVIS_Z = 0.917          # pelvis rest height of the UAL1 skeleton the clips were authored on
for _d in (WORK, PREV_DIR, TEX):
    os.makedirs(_d, exist_ok=True)

F32 = np.float32


def v3(*a):
    if len(a) == 1:
        return np.asarray(a[0], F32)
    return np.asarray(a, F32)


def norm(v):
    v = np.asarray(v, F32)
    return v / max(1e-9, float(np.linalg.norm(v)))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# --------------------------------------------------------------------------------------------
# noise
class Noise:
    """Vectorised 3D gradient (Perlin) noise. Output roughly in [-1, 1]."""

    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        p = rng.permutation(256).astype(np.int32)
        self.perm = np.concatenate([p, p, p]).astype(np.int32)
        g = rng.normal(size=(256, 3))
        g /= np.linalg.norm(g, axis=1, keepdims=True)
        self.grad = g.astype(F32)

    def __call__(self, P):
        P = np.asarray(P, F32)
        shp = P.shape[:-1]
        P = P.reshape(-1, 3)
        Pi = np.floor(P)
        f = (P - Pi).astype(F32)
        Pi = Pi.astype(np.int64) & 255
        X, Y, Z = Pi[:, 0], Pi[:, 1], Pi[:, 2]
        u = f * f * f * (f * (f * 6 - 15) + 10)
        perm, grad = self.perm, self.grad
        out = np.zeros(len(P), F32)

        def gdot(dx, dy, dz):
            h = perm[perm[perm[X + dx] + Y + dy] + Z + dz]
            g = grad[h]
            return g[:, 0] * (f[:, 0] - dx) + g[:, 1] * (f[:, 1] - dy) + g[:, 2] * (f[:, 2] - dz)

        n000 = gdot(0, 0, 0); n100 = gdot(1, 0, 0)
        n010 = gdot(0, 1, 0); n110 = gdot(1, 1, 0)
        n001 = gdot(0, 0, 1); n101 = gdot(1, 0, 1)
        n011 = gdot(0, 1, 1); n111 = gdot(1, 1, 1)
        ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
        nx00 = n000 + ux * (n100 - n000)
        nx10 = n010 + ux * (n110 - n010)
        nx01 = n001 + ux * (n101 - n001)
        nx11 = n011 + ux * (n111 - n011)
        nxy0 = nx00 + uy * (nx10 - nx00)
        nxy1 = nx01 + uy * (nx11 - nx01)
        out = (nxy0 + uz * (nxy1 - nxy0)) * 1.6
        return out.reshape(shp)

    def fbm(self, P, octaves=4, lac=2.03, gain=0.5):
        P = np.asarray(P, F32)
        amp, tot, s = 1.0, 0.0, 0.0
        q = P
        for i in range(octaves):
            s = s + amp * self(q + F32(i * 17.31))
            tot += amp
            amp *= gain
            q = q * F32(lac)
        return s / tot

    def ridged(self, P, octaves=4, lac=2.1, gain=0.5):
        P = np.asarray(P, F32)
        amp, tot, s = 1.0, 0.0, 0.0
        q = P
        for i in range(octaves):
            s = s + amp * (1.0 - np.abs(self(q + F32(i * 7.77))))
            tot += amp
            amp *= gain
            q = q * F32(lac)
        return s / tot


NOISE = Noise(7)
NOISE2 = Noise(13)
NOISE3 = Noise(29)


# --------------------------------------------------------------------------------------------
# rotations
def rot_axis(axis, deg):
    axis = norm(axis)
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = axis
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]], F32)


def euler_xyz(rx=0, ry=0, rz=0):
    return rot_axis((0, 0, 1), rz) @ rot_axis((0, 1, 0), ry) @ rot_axis((1, 0, 0), rx)


def frame_from(yaxis, zhint=(0, 0, 1)):
    """rotation matrix whose columns are (x, y, z) with y along yaxis."""
    y = norm(yaxis)
    z = np.asarray(zhint, F32)
    x = np.cross(y, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(y, (1, 0, 0))
    x = norm(x)
    z = norm(np.cross(x, y))
    return np.stack([x, y, z], 1).astype(F32)


# --------------------------------------------------------------------------------------------
# SDF primitives.  Every primitive: .d(P) -> distances, .bbox -> (lo, hi)
class Prim:
    pad = 0.0

    def bb(self):
        lo, hi = self.bbox
        return np.asarray(lo, F32) - self.pad, np.asarray(hi, F32) + self.pad


class Sphere(Prim):
    def __init__(self, c, r):
        self.c, self.r = v3(c), float(r)
        self.bbox = (self.c - r, self.c + r)

    def d(self, P):
        return np.linalg.norm(P - self.c, axis=-1) - self.r


class Ellipsoid(Prim):
    """oriented ellipsoid; R columns = local axes (world)."""

    def __init__(self, c, radii, R=None):
        self.c = v3(c)
        self.r = v3(radii)
        self.R = np.eye(3, dtype=F32) if R is None else np.asarray(R, F32)
        m = float(self.r.max())
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = (P - self.c) @ self.R
        k0 = np.linalg.norm(q / self.r, axis=-1)
        k1 = np.linalg.norm(q / (self.r * self.r), axis=-1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


class RoundCone(Prim):
    """capsule between a and b with radii ra -> rb (iq sdRoundCone)."""

    def __init__(self, a, b, ra, rb=None):
        self.a, self.b = v3(a), v3(b)
        self.ra = float(ra)
        self.rb = float(ra if rb is None else rb)
        m = max(self.ra, self.rb)
        self.bbox = (np.minimum(self.a, self.b) - m, np.maximum(self.a, self.b) + m)

    def d(self, P):
        a, b, r1, r2 = self.a, self.b, self.ra, self.rb
        ba = b - a
        l2 = float(ba @ ba)
        rr = r1 - r2
        a2 = l2 - rr * rr
        il2 = 1.0 / l2
        pa = P - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - y[..., None] * ba
        x2 = (xv * xv).sum(-1)
        y2 = y * y * l2
        z2 = z * z * l2
        k = math.copysign(1.0, rr) * rr * rr * x2 if rr != 0 else np.zeros_like(x2)
        d1 = np.sqrt(x2 + z2) * il2 - r2
        d2 = np.sqrt(x2 + y2) * il2 - r1
        d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        c1 = np.sign(z) * a2 * z2 > k
        c2 = np.sign(y) * a2 * y2 < k
        return np.where(c1, d1, np.where(c2, d2, d3)).astype(F32)


class Tube(Prim):
    """polyline of points with radii -> union of round cones (sharp min)."""

    def __init__(self, pts, radii):
        pts = [v3(p) for p in pts]
        self.segs = [RoundCone(pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)]
        lo = np.min([s.bbox[0] for s in self.segs], 0)
        hi = np.max([s.bbox[1] for s in self.segs], 0)
        self.bbox = (lo, hi)

    def d(self, P):
        d = self.segs[0].d(P)
        for s in self.segs[1:]:
            d = np.minimum(d, s.d(P))
        return d


class RBox(Prim):
    """rounded box, half extents b, rounding r, oriented by R about c."""

    def __init__(self, c, b, r=0.0, R=None):
        self.c, self.b, self.r = v3(c), v3(b), float(r)
        self.R = np.eye(3, dtype=F32) if R is None else np.asarray(R, F32)
        m = float(np.linalg.norm(self.b)) + self.r
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = np.abs((P - self.c) @ self.R) - (self.b - self.r)
        return (np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - self.r).astype(F32)


class Torus(Prim):
    def __init__(self, c, R_major, r_minor, R=None):
        self.c, self.Rm, self.rm = v3(c), float(R_major), float(r_minor)
        self.R = np.eye(3, dtype=F32) if R is None else np.asarray(R, F32)
        m = self.Rm + self.rm
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = (P - self.c) @ self.R
        a = np.sqrt(q[..., 0] ** 2 + q[..., 1] ** 2) - self.Rm
        return np.sqrt(a * a + q[..., 2] ** 2) - self.rm


class Func(Prim):
    """arbitrary SDF given as a python function + bbox."""

    def __init__(self, fn, lo, hi):
        self.fn = fn
        self.bbox = (v3(lo), v3(hi))

    def d(self, P):
        return self.fn(P).astype(F32)


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


# --------------------------------------------------------------------------------------------
class SDFGrid:
    """dense SDF grid sculpting with bbox-limited smooth CSG ops."""

    def __init__(self, lo, hi, h):
        self.lo = v3(lo)
        self.h = float(h)
        self.n = (np.ceil((v3(hi) - self.lo) / h).astype(int) + 1)
        self.F = np.full(tuple(self.n), 0.5, F32)
        print("SDFGrid", self.n, "cells=%.1fM" % (np.prod(self.n) / 1e6))

    def _block(self, lo, hi):
        i0 = np.clip(np.floor((v3(lo) - self.lo) / self.h).astype(int), 0, self.n - 1)
        i1 = np.clip(np.ceil((v3(hi) - self.lo) / self.h).astype(int) + 1, 1, self.n)
        sl = tuple(slice(int(a), int(b)) for a, b in zip(i0, i1))
        xs = [self.lo[k] + self.h * np.arange(i0[k], i1[k], dtype=F32) for k in range(3)]
        return sl, xs

    def _pts(self, xs):
        X, Y, Z = np.meshgrid(xs[0], xs[1], xs[2], indexing='ij')
        return np.stack([X, Y, Z], -1).astype(F32)

    def union(self, prim, k=0.0):
        lo, hi = prim.bb()
        sl, xs = self._block(lo - k - 3 * self.h, hi + k + 3 * self.h)
        if any(s.stop <= s.start for s in sl):
            return
        P = self._pts(xs)
        self.F[sl] = smin(self.F[sl], prim.d(P), k)

    def sub(self, prim, k=0.0):
        lo, hi = prim.bb()
        sl, xs = self._block(lo - k - 3 * self.h, hi + k + 3 * self.h)
        if any(s.stop <= s.start for s in sl):
            return
        P = self._pts(xs)
        self.F[sl] = smax(self.F[sl], -prim.d(P), k)

    def inter(self, prim, k=0.0):
        P = self._pts([self.lo[i] + self.h * np.arange(self.n[i], dtype=F32) for i in range(3)])
        self.F = smax(self.F, prim.d(P), k)

    def layer(self, region, thick, k=0.0, lo=None, hi=None):
        """raise a layer of `thick` (float or fn(P)) over current surface where region(P) < 0."""
        if lo is None:
            lo, hi = region.bb()
        sl, xs = self._block(v3(lo) - 0.05, v3(hi) + 0.05)
        P = self._pts(xs)
        f = self.F[sl]
        t = thick(P) if callable(thick) else thick
        lay = np.maximum(f - t, region.d(P))
        self.F[sl] = smin(f, lay, k)

    def displace(self, fn, band, lo=None, hi=None):
        """F += fn(P) for grid points with |F| < band (inside optional bbox)."""
        if lo is None:
            sl = tuple(slice(0, int(n)) for n in self.n)
            off = np.zeros(3, int)
        else:
            sl, _ = self._block(lo, hi)
            off = np.array([s.start for s in sl])
        f = self.F[sl]
        idx = np.nonzero(np.abs(f) < band)
        if len(idx[0]) == 0:
            return
        P = self.lo + self.h * (np.stack(idx, 1) + off).astype(F32)
        f[idx] += fn(P.astype(F32)).astype(F32)
        self.F[sl] = f

    def apply(self, fn_combine, lo, hi):
        """generic: F_block = fn_combine(F_block, P_block)"""
        sl, xs = self._block(lo, hi)
        P = self._pts(xs)
        self.F[sl] = fn_combine(self.F[sl], P)

    def mesh(self):
        return surface_nets(self.F, self.lo, self.h)


def surface_nets(F, lo, h):
    S = F < 0
    nx, ny, nz = F.shape
    a = S[:-1, :-1, :-1]
    anyin = a.copy(); allin = a.copy()
    for dx, dy, dz in [(1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]:
        c = S[dx:nx - 1 + dx, dy:ny - 1 + dy, dz:nz - 1 + dz]
        anyin |= c
        allin &= c
    act = anyin & ~allin
    del anyin, allin
    ci, cj, ck = np.nonzero(act)
    del act
    nv = len(ci)
    vid = np.full((nx - 1, ny - 1, nz - 1), -1, np.int32)
    vid[ci, cj, ck] = np.arange(nv, dtype=np.int32)
    corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    fc = [F[ci + dx, cj + dy, ck + dz] for (dx, dy, dz) in corners]
    acc = np.zeros((nv, 3), F32)
    cnt = np.zeros(nv, F32)
    for ea, eb in edges:
        fa, fb = fc[ea], fc[eb]
        m = (fa < 0) != (fb < 0)
        t = (fa[m] / (fa[m] - fb[m])).astype(F32)
        pa = np.array(corners[ea], F32)
        pb = np.array(corners[eb], F32)
        acc[m] += pa + t[:, None] * (pb - pa)
        cnt[m] += 1
    V = lo + h * (np.stack([ci, cj, ck], 1).astype(F32) + acc / np.maximum(cnt, 1)[:, None])
    quads = []
    # x edges
    e = S[:-1, 1:-1, 1:-1] != S[1:, 1:-1, 1:-1]
    i, j, k = np.nonzero(e); j = j + 1; k = k + 1
    q = np.stack([vid[i, j - 1, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i, j - 1, k]], 1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    # y edges
    e = S[1:-1, :-1, 1:-1] != S[1:-1, 1:, 1:-1]
    i, j, k = np.nonzero(e); i = i + 1; k = k + 1
    q = np.stack([vid[i - 1, j, k - 1], vid[i - 1, j, k], vid[i, j, k], vid[i, j, k - 1]], 1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    # z edges
    e = S[1:-1, 1:-1, :-1] != S[1:-1, 1:-1, 1:]
    i, j, k = np.nonzero(e); i = i + 1; j = j + 1
    q = np.stack([vid[i - 1, j - 1, k], vid[i, j - 1, k], vid[i, j, k], vid[i - 1, j, k]], 1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    Q = np.concatenate(quads, 0)
    Q = Q[(Q >= 0).all(1)]
    return V.astype(F32), Q.astype(np.int32)


def mesh_edges(Q):
    e = np.concatenate([Q[:, [0, 1]], Q[:, [1, 2]], Q[:, [2, 3]], Q[:, [3, 0]]], 0) if Q.shape[1] == 4 else \
        np.concatenate([Q[:, [0, 1]], Q[:, [1, 2]], Q[:, [2, 0]]], 0)
    e = np.sort(e, 1)
    return np.unique(e, axis=0)


def laplacian(V, E, vals=None):
    """mean of neighbours (of vals, default positions)."""
    X = V if vals is None else vals
    acc = np.zeros_like(X)
    cnt = np.zeros(len(V), F32)
    np.add.at(acc, E[:, 0], X[E[:, 1]])
    np.add.at(acc, E[:, 1], X[E[:, 0]])
    np.add.at(cnt, E[:, 0], 1)
    np.add.at(cnt, E[:, 1], 1)
    shp = (-1,) + (1,) * (X.ndim - 1)
    return acc / np.maximum(cnt, 1).reshape(shp)


def taubin(V, E, iters=4, lam=0.5, mu=-0.53):
    V = V.copy()
    for _ in range(iters):
        V = V + lam * (laplacian(V, E) - V)
        V = V + mu * (laplacian(V, E) - V)
    return V


def vnormals(V, Q):
    if Q.shape[1] == 4:
        n = np.cross(V[Q[:, 2]] - V[Q[:, 0]], V[Q[:, 3]] - V[Q[:, 1]])
    else:
        n = np.cross(V[Q[:, 1]] - V[Q[:, 0]], V[Q[:, 2]] - V[Q[:, 0]])
    N = np.zeros_like(V)
    for c in range(Q.shape[1]):
        np.add.at(N, Q[:, c], n)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def curvature(V, Q, E=None, N=None, smooth=2):
    """signed convexity: + convex ridge, - cavity. ~ mean curvature * edge length."""
    if E is None:
        E = mesh_edges(Q)
    if N is None:
        N = vnormals(V, Q)
    L = laplacian(V, E) - V
    el = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1).mean()
    c = -(L * N).sum(1) / max(el, 1e-6)
    for _ in range(smooth):
        c = 0.5 * c + 0.5 * laplacian(V, E, c)
    return c.astype(F32)


# --------------------------------------------------------------------------------------------
# bpy helpers (import bpy lazily so the numpy parts work standalone)
def bpy_mesh(name, V, faces, coll=None):
    import bpy
    me = bpy.data.meshes.new(name)
    V = np.asarray(V, F32)
    faces = np.asarray(faces, np.int32)
    nf, fs = faces.shape
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(nf * fs)
    me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * fs, fs, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def bpy_mesh_np(ob):
    """(V, faces-as-list-of-arrays) world space of a mesh object (evaluated not applied)."""
    me = ob.data
    V = np.zeros(len(me.vertices) * 3, F32)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(ob.matrix_world, F32)
    V = V @ M[:3, :3].T + M[:3, 3]
    return V


def set_attr(ob, name, values, domain='POINT'):
    me = ob.data
    values = np.asarray(values, F32)
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    if values.ndim == 1:
        a = me.attributes.new(name, 'FLOAT', domain)
        a.data.foreach_set("value", values)
    else:
        if values.shape[1] == 3:
            values = np.concatenate([values, np.ones((len(values), 1), F32)], 1)
        a = me.attributes.new(name, 'FLOAT_COLOR', domain)
        a.data.foreach_set("color", values.ravel())
    return a


def get_attr(ob, name):
    a = ob.data.attributes[name]
    n = len(a.data)
    if a.data_type == 'FLOAT':
        out = np.zeros(n, F32); a.data.foreach_get("value", out); return out
    out = np.zeros(n * 4, F32); a.data.foreach_get("color", out); return out.reshape(n, 4)


def setup_cycles(samples=64, device='OPTIX'):
    import bpy
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = device
        prefs.get_devices()
        for d in prefs.devices:
            d.use = (d.type == device)
        sc.cycles.device = 'GPU'
    except Exception as e:
        print("GPU setup failed", e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    return sc


def new_image(name, size, float_buffer=True, alpha=True, fill=(0, 0, 0, 0)):
    import bpy
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    w, h = (size, size) if isinstance(size, int) else size
    img = bpy.data.images.new(name, w, h, alpha=alpha, float_buffer=float_buffer)
    px = np.empty(w * h * 4, F32)
    px.reshape(-1, 4)[:] = fill
    img.pixels.foreach_set(px)
    if float_buffer:
        img.colorspace_settings.name = 'Non-Color'
    return img


def img_np(img):
    w, h = img.size
    px = np.empty(w * h * 4, F32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def np_img(name, arr, colorspace='sRGB', float_buffer=False):
    """arr (h, w, 3|4) float 0..1 (linear values written as-is) -> new bpy image."""
    import bpy
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), F32)], 2)
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=float_buffer)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr, F32).ravel())
    return img


def save_png(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def save_np_png(arr, path, colorspace='sRGB'):
    img = np_img("_tmp_save", np.clip(arr, 0, 1), colorspace)
    save_png(img, path)
    import bpy
    bpy.data.images.remove(img)


def load_png_np(path):
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    a = img_np(img).copy()
    bpy.data.images.remove(img)
    return a


def dilate_index(mask, iters=16):
    """flat index map: every pixel within `iters` px of the mask points at a nearby valid pixel (-1 = none)."""
    h, w = mask.shape
    idx = np.where(mask.ravel(), np.arange(h * w, dtype=np.int64), -1).reshape(h, w)
    for _ in range(iters):
        if (idx >= 0).all():
            break
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nb = np.roll(np.roll(idx, dy, 0), dx, 1)
            fill = (idx < 0) & (nb >= 0)
            idx[fill] = nb[fill]
    return idx


def dilate_fast(arr, idxmap, fill=None):
    h, w = idxmap.shape
    flat = arr.reshape(h * w, -1)
    out = flat.copy()
    ok = idxmap.ravel() >= 0
    out[ok] = flat[idxmap.ravel()[ok]]
    if fill is not None:
        out[~ok] = fill
    return out.reshape(arr.shape)


def dilate(arr, mask, iters=8):
    """push valid pixels outward into invalid ones (simple uv-margin)."""
    arr = arr.copy()
    m = mask.copy()
    for _ in range(iters):
        acc = np.zeros_like(arr)
        cnt = np.zeros(m.shape, F32)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            sm = np.roll(np.roll(m, dy, 0), dx, 1)
            sa = np.roll(np.roll(arr, dy, 0), dx, 1)
            acc[sm] += sa[sm]
            cnt[sm] += 1
        grow = (~m) & (cnt > 0)
        arr[grow] = acc[grow] / cnt[grow][:, None] if arr.ndim == 3 else acc[grow] / cnt[grow]
        m = m | grow
    return arr, m


def blur(arr, r=1):
    out = arr.copy()
    for _ in range(r):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0)) / 3.0
        out = (out + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 3.0
    return out


def chart_seams(ob, min_faces=40, smooth_iters=4, dirs=None, max_rounds=30):
    """mark UV seams so faces are grouped into a modest number of charts by (smoothed) normal direction.
    Returns the number of charts."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    nf = len(bm.faces)
    fn = np.array([f.normal[:] for f in bm.faces], F32)
    fa = np.array([f.calc_area() for f in bm.faces], F32)
    # face adjacency via manifold edges
    pairs = []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2:
            pairs.append((lf[0].index, lf[1].index, e.index))
    pairs = np.array(pairs, np.int64).reshape(-1, 3)
    A, B = pairs[:, 0], pairs[:, 1]
    n = fn.copy()
    for _ in range(smooth_iters):
        acc = n * fa[:, None]
        np.add.at(acc, A, n[B] * fa[B, None])
        np.add.at(acc, B, n[A] * fa[A, None])
        n = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)
    if dirs is None:
        s = 1 / math.sqrt(2)
        dirs = np.array([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)], F32)
    lab = np.argmax(n @ dirs.T, 1)

    def components(lab):
        parent = np.arange(nf)

        def find(x):
            r = x
            while parent[r] != r:
                r = parent[r]
            while parent[x] != r:
                parent[x], x = r, parent[x]
            return r
        same = lab[A] == lab[B]
        for a, b in zip(A[same], B[same]):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        return np.array([find(i) for i in range(nf)])

    comp = components(lab)
    for _ in range(max_rounds):
        ids, inv, cnt = np.unique(comp, return_inverse=True, return_counts=True)
        small = cnt[inv] < min_faces
        if not small.any():
            break
        # each small-chart face adopts the chart of a neighbour in a bigger chart (longest shared border wins)
        changed = False
        border = comp[A] != comp[B]
        votes = {}
        for a, b in zip(A[border], B[border]):
            for x, y in ((a, b), (b, a)):
                if small[x] and cnt[inv[y]] >= cnt[inv[x]]:
                    key = (comp[x], comp[y])
                    votes[key] = votes.get(key, 0) + 1
        best = {}
        for (cx, cy), v in votes.items():
            if cx not in best or v > best[cx][1]:
                best[cx] = (cy, v)
        for cx, (cy, v) in best.items():
            comp[comp == cx] = cy
            changed = True
        if not changed:
            break
    for e in bm.edges:
        e.seam = False
    for a, b, ei in pairs:
        if comp[a] != comp[b]:
            bm.edges[ei].seam = True
    for e in bm.edges:
        if len(e.link_faces) != 2:
            e.seam = True
    bm.to_mesh(me)
    bm.free()
    return len(np.unique(comp))


# --------------------------------------------------------------------------------------------
# colour helpers
def srgb_to_lin(c):
    c = np.asarray(c, F32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(F32)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, F32), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(F32)


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], F32)


# --------------------------------------------------------------------------------------------
# pose helpers
def rq(rx=0.0, ry=0.0, rz=0.0):
    """quaternion (mathutils) for a rotation given as XYZ euler degrees in ARMATURE axes."""
    from mathutils import Euler
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_quaternion()


def rest_axes_to_local(pb, Q):
    """convert a rotation expressed in armature rest axes into the bone's local basis rotation."""
    R = pb.bone.matrix_local.to_quaternion()
    return R.inverted() @ Q @ R


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def clear_scene():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_ual(path=UAL1):
    import bpy
    bpy.ops.import_scene.gltf(filepath=path)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    return arm


def import_gltf(path):
    import bpy
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, bone_heuristic='BLENDER', disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]


# --------------------------------------------------------------------------------------------
# joints (modeling pose, written by s0_rig.py)
J = None


def load_joints():
    global J
    J = load_json(os.path.join(WORK, "joints.json"))
    return J


def H(b):
    return np.array(J[b]["head"], F32)


def T(b):
    return np.array(J[b]["tail"], F32)


# --------------------------------------------------------------------------------------------
# skin weights (numpy), un-posing to the rest skeleton
def dseg(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def wdist(P, spec, p=5.0):
    """spec: list of (bone, radius[, head, tail]) -> dict bone -> weights (normalised)"""
    cols = []
    for s in spec:
        b, r = s[0], s[1]
        a = s[2] if len(s) > 2 else H(b)
        e = s[3] if len(s) > 3 else T(b)
        cols.append(dseg(P, a, e) / r)
    D = np.stack(cols, 1)
    W = 1.0 / (D ** p + 1e-4)
    W /= W.sum(1, keepdims=True)
    return {s[0]: W[:, i] for i, s in enumerate(spec)}


def to_matrix(W, bones, n):
    M = np.zeros((n, len(bones)), F32)
    for b, w in W.items():
        M[:, bones.index(b)] += w
    return M


def limit_norm(M, k=4):
    if M.shape[1] > k:
        idx = np.argsort(-M, 1)[:, k:]
        np.put_along_axis(M, idx, 0, 1)
    M[M < 0.01] = 0
    s = M.sum(1, keepdims=True)
    return M / np.maximum(s, 1e-9)


def mesh_edges_ob(ob):
    me = ob.data
    E = np.zeros(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", E)
    return E.reshape(-1, 2)


def smooth_weights(M, ob, iters=4, keep=0.5):
    E = mesh_edges_ob(ob)
    for _ in range(iters):
        M = keep * M + (1 - keep) * laplacian(np.zeros((len(M), 1), F32), E, M)
    return M


def mesh_verts(ob):
    V = np.zeros(len(ob.data.vertices) * 3, F32)
    ob.data.vertices.foreach_get("co", V)
    return V.reshape(-1, 3)


def unpose(V, M, bones):
    """modeling-pose vertices -> rest-pose vertices with the inverse of each vertex's blended skin matrix."""
    S = []
    for b in bones:
        Pm = np.array(J[b]["pose"], np.float64)
        Rm = np.array(J[b]["rest"], np.float64)
        S.append(Pm @ np.linalg.inv(Rm))
    S = np.stack(S)
    Sv = np.einsum('vb,bij->vij', M.astype(np.float64), S)
    Vh = np.concatenate([V, np.ones((len(V), 1))], 1)
    R = np.linalg.solve(Sv, Vh[:, :, None])[:, :, 0]
    return R[:, :3].astype(F32)


def assign_groups(ob, M, bones):
    ob.vertex_groups.clear()
    for j, b in enumerate(bones):
        idx = np.nonzero(M[:, j] > 0)[0]
        if len(idx) == 0:
            continue
        vg = ob.vertex_groups.new(name=b)
        for i in idx:
            vg.add([int(i)], float(M[i, j]), 'REPLACE')


def append_objects(path, suffix="_low"):
    import bpy
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith(suffix)]
    out = []
    for ob in dst.objects:
        bpy.context.scene.collection.objects.link(ob)
        out.append(ob)
    return out


# --------------------------------------------------------------------------------------------
# low-poly helpers
def decimate(ob, target_tris):
    import bpy, bmesh
    me = ob.data
    ntri = sum(len(p.vertices) - 2 for p in me.polygons)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = min(1.0, target_tris / max(ntri, 1))
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-4, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bad = [f for f in bm.faces if f.calc_area() < 2e-8]
    bmesh.ops.delete(bm, geom=bad, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    ob.select_set(False)
    return len(ob.data.polygons)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# --------------------------------------------------------------------------------------------
# glTF-friendly materials
def gltf_output_group():
    import bpy
    name = "glTF Material Output"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    g.interface.new_socket("Thickness", in_out='INPUT', socket_type='NodeSocketFloat')
    g.nodes.new("NodeGroupInput")
    return g


def load_img(path, colorspace):
    import bpy
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def pbr_material(name, albedo, normal=None, orm=None, emission=None, emission_strength=1.0, alpha_clip=None,
                 normal_strength=1.0, factor=None, double_sided=False):
    """Principled material wired the way the glTF exporter understands. factor = base colour factor (linear RGB),
    exported as baseColorFactor via a Multiply mix (used for the tint1_/tint2_ palette materials)."""
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    ia = nt.nodes.new("ShaderNodeTexImage"); ia.image = load_img(albedo, 'sRGB'); ia.location = (-900, 300)
    col_out = ia.outputs["Color"]
    if factor is not None:
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.location = (-500, 300)
        mx.inputs["Factor"].default_value = 1.0
        nt.links.new(col_out, mx.inputs[6])
        mx.inputs[7].default_value = (factor[0], factor[1], factor[2], 1.0)
        col_out = mx.outputs[2]
    nt.links.new(col_out, bsdf.inputs["Base Color"])
    if alpha_clip is not None:
        ia.image.alpha_mode = 'STRAIGHT'
        rnd = nt.nodes.new("ShaderNodeMath"); rnd.operation = 'ROUND'
        nt.links.new(ia.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
        try:
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        double_sided = True
    if normal:
        inn = nt.nodes.new("ShaderNodeTexImage"); inn.image = load_img(normal, 'Non-Color'); inn.location = (-900, -300)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-500, -300)
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(inn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if orm:
        io = nt.nodes.new("ShaderNodeTexImage"); io.image = load_img(orm, 'Non-Color'); io.location = (-900, 0)
        sp = nt.nodes.new("ShaderNodeSeparateColor"); sp.location = (-500, 0)
        nt.links.new(io.outputs["Color"], sp.inputs["Color"])
        nt.links.new(sp.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sp.outputs["Blue"], bsdf.inputs["Metallic"])
        grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = gltf_output_group(); grp.location = (0, -500)
        nt.links.new(sp.outputs["Red"], grp.inputs["Occlusion"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.8
    if emission:
        ie = nt.nodes.new("ShaderNodeTexImage"); ie.image = load_img(emission, 'sRGB'); ie.location = (-900, -650)
        nt.links.new(ie.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    bsdf.inputs["Specular IOR Level"].default_value = 0.4
    m.use_backface_culling = not double_sided
    return m


# --------------------------------------------------------------------------------------------
# UAL clips -> our skeleton (previews).  glTF clips carry absolute local rotations; the game drops every
# translation except root/pelvis, so we do the same and scale the pelvis translation by `k`.
def rest_local(bone):
    if bone.parent is None:
        return bone.matrix_local.copy()
    return bone.parent.matrix_local.inverted() @ bone.matrix_local


def load_clip_sources():
    """import UAL1 + UAL2 armatures (actions kept, meshes dropped). returns {action_name: (src_arm, action)}"""
    import bpy
    out = {}
    for path in (UAL1, UAL2):
        before = set(bpy.data.actions)
        objs = import_gltf(path)
        arm = [o for o in objs if o.type == 'ARMATURE'][0]
        for o in objs:
            if o.type != 'ARMATURE':
                bpy.data.objects.remove(o, do_unlink=True)
        arm.hide_render = True
        arm.name = "SRC_" + os.path.basename(path).split("_")[0]
        if arm.animation_data:
            arm.animation_data.action = None
        for a in bpy.data.actions:
            if a not in before:
                a.use_fake_user = True
                out[a.name.split(".")[0]] = (arm, a)
    return out


def pose_from_clip(src_arm, action, frame, dst_arm, k=1.0):
    import bpy
    from mathutils import Matrix
    ad = src_arm.animation_data or src_arm.animation_data_create()
    ad.action = action
    if action.slots:
        ad.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    for pb in dst_arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        sp = src_arm.pose.bones.get(pb.name)
        if sp is None:
            pb.matrix_basis = Matrix.Identity(4)
            continue
        Ls = rest_local(sp.bone) @ sp.matrix_basis
        Rd = rest_local(pb.bone)
        if pb.name in ("root", "pelvis"):
            t = Ls.to_translation() * k
        else:
            t = Rd.to_translation()
        Ld = Matrix.Translation(t) @ Ls.to_quaternion().to_matrix().to_4x4()
        pb.matrix_basis = Rd.inverted() @ Ld
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------------------------
# EEVEE studio for previews: neutral grey cyclorama, warm key, cool rim, soft fill, bloom
def eevee_studio(res=1024, samples=64):
    import bpy, bmesh
    from mathutils import Euler
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng
            break
        except Exception:
            pass
    ee = sc.eevee
    for k_, v_ in (("taa_render_samples", samples), ("use_shadows", True), ("use_raytracing", True),
                   ("shadow_ray_count", 2), ("shadow_step_count", 8), ("use_gtao", True)):
        try:
            setattr(ee, k_, v_)
        except Exception:
            pass
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = -0.3
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.16, 0.16, 0.16, 1)
    bg.inputs["Strength"].default_value = 0.45
    # cyclorama: floor curving up into a back wall (behind the fighter, +Y)
    me = bpy.data.meshes.new("cyc")
    bm = bmesh.new()
    pts = [(-40.0, 0.0)] + [(6.0 + 4.0 * math.sin(i / 23 * math.pi / 2), 4.0 - 4.0 * math.cos(i / 23 * math.pi / 2))
                            for i in range(24)] + [(10.0, 30.0)]
    vs = []
    for x in (-30.0, 30.0):
        vs.append([bm.verts.new((x, y, z)) for (y, z) in pts])
    for i in range(len(pts) - 1):
        bm.faces.new((vs[0][i], vs[1][i], vs[1][i + 1], vs[0][i + 1]))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    cyc = bpy.data.objects.new("CYC", me)
    sc.collection.objects.link(cyc)
    gm = bpy.data.materials.new("studio_grey")
    gm.use_nodes = True
    gp = gm.node_tree.nodes.get("Principled BSDF")
    gp.inputs["Base Color"].default_value = (0.13, 0.13, 0.13, 1)
    gp.inputs["Roughness"].default_value = 0.85
    me.materials.append(gm)

    def light(name, kind, energy, color, loc, rot, size=None):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = color
        if size is not None:
            ld.size = size
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = Euler([math.radians(r) for r in rot], 'XYZ')
        return ob
    light("Key", 'AREA', 600.0, (1.0, 0.82, 0.62), (-2.4, -3.0, 3.8), (50, 0, -38), 2.0)
    light("Rim", 'AREA', 1300.0, (0.62, 0.76, 1.0), (2.4, 2.8, 3.2), (-52, 0, 141), 1.2)
    light("Rim2", 'AREA', 600.0, (0.62, 0.76, 1.0), (-2.6, 2.6, 2.4), (-58, 0, -135), 1.0)
    light("Fill", 'AREA', 90.0, (0.9, 0.93, 1.0), (3.2, -3.2, 1.4), (78, 0, 45), 4.0)
    for n in ("Rim", "Rim2"):
        try:
            bpy.data.objects[n].data.spread = math.radians(55)
        except Exception as e:
            print("spread", e)
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cd.clip_start = 0.02
    cd.clip_end = 200
    setup_bloom(sc)
    return cam


def setup_bloom(sc, threshold=1.0, strength=0.35, size=0.42):
    import bpy
    try:
        ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        if "Type" in gl.inputs:
            for v in ("Bloom", "Fog Glow"):
                try:
                    gl.inputs["Type"].default_value = v
                    break
                except Exception:
                    pass
            try:
                gl.inputs["Quality"].default_value = "High"
            except Exception:
                pass
        else:
            gl.glare_type = 'BLOOM'
        for nm, v in (("Threshold", threshold), ("Strength", strength), ("Size", size)):
            if nm in gl.inputs:
                gl.inputs[nm].default_value = v
        out = ng.nodes.new("NodeGroupOutput")
        ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs["Image"], out.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
        print("BLOOM compositor ok", gl.inputs["Type"].default_value if "Type" in gl.inputs else "")
    except Exception as e:
        print("BLOOM setup failed", e)


def aim(cam, target, direction, dist, lens=50):
    from mathutils import Vector
    d = Vector(direction).normalized()
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens


def el(az, elev):
    a, e = math.radians(az), math.radians(elev)
    return (math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e))


def render(path):
    import bpy
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER", path)

"""Vexthorn, the Hollow Stag: SDF sculpt definitions (modeling pose, metres, faces -Y, left = +X, Z up).

Each Part:  name, atlas ('bark' | 'bone'), h (voxel), lo/hi (grid bounds), tris (low budget), texel (uv weight)
  build(g)        sculpt into an SDFGrid
  post(V, N)      displacement on the polygonised high-poly
  masks(P, N)     region masks for painting
  weights(P)      {bone: w} skin weights in the modeling pose
  flow()          list of polylines the bark grain follows
"""
import math
import numpy as np
import fblib as L
from fblib import (F32, v3, norm, rot_axis, frame_from, smoothstep, Sphere, Ellipsoid, RoundCone, Tube, RBox,
                   Torus, Func, NOISE, NOISE2, NOISE3, smin, smax, H, T, wdist)


def X(P):
    return P[..., 0]


def Y(P):
    return P[..., 1]


def Z(P):
    return P[..., 2]


SIDES = (("l", 1.0), ("r", -1.0))


def spline(pts, n=5):
    """Catmull-Rom through pts -> dense polyline (np array)."""
    pts = [v3(p) for p in pts]
    if len(pts) == 2:
        return np.array([pts[0] + (pts[1] - pts[0]) * (k / n) for k in range(n + 1)], F32)
    P = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return np.array(out, F32)


def arclen(pts):
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(d)])
    return s / max(s[-1], 1e-9)


def taper(pts, r0, r1, pw=1.0):
    t = arclen(pts)
    return list(r0 + (r1 - r0) * t ** pw)


def tube(pts, r0, r1=None, n=5, pw=1.0):
    p = spline(pts, n)
    return Tube(p, taper(p, r0, r0 if r1 is None else r1, pw)), p


def mirror(p, s):
    p = v3(p)
    return v3(p[0] * s, p[1], p[2])


def twisted(a, b, r_ax0, r_ax1, ns, r_str, turns=0.5, phase=0.0, n=10, wob=0.0, seed=0):
    """ns strands spiralling round the a->b axis; returns list of (pts, radii)."""
    a, b = v3(a), v3(b)
    ax = norm(b - a)
    R = frame_from(ax, (0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))
    u, w = R[:, 0], R[:, 2]
    out = []
    rng = np.random.default_rng(seed)
    for k in range(ns):
        pts = []
        for i in range(n + 1):
            t = i / n
            th = phase + 2 * math.pi * (k / ns + turns * t)
            rr = r_ax0 + (r_ax1 - r_ax0) * t
            pts.append(a + (b - a) * t + (u * math.cos(th) + w * math.sin(th)) * rr * (1 + wob * rng.normal()))
        out.append((np.array(pts, F32), r_str))
    return out


def dseg(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(P - (a + t[..., None] * ab), axis=-1)


def flow_field_brute(P, lines, tau=0.02):
    """soft-nearest grain tensor D(x)D of a set of polylines at points P (N,3) -> (N,3,3) (sign-free)."""
    A = np.concatenate([l[:-1] for l in lines], 0).astype(F32)
    B = np.concatenate([l[1:] for l in lines], 0).astype(F32)
    D = B - A
    Ln = np.linalg.norm(D, axis=1)
    Dn = D / np.maximum(Ln, 1e-9)[:, None]
    DD = (Dn[:, :, None] * Dn[:, None, :]).reshape(-1, 9)
    out = np.zeros((len(P), 9), F32)
    CH = max(200, 3000000 // max(len(A), 1))
    for i0 in range(0, len(P), CH):
        p = P[i0:i0 + CH]
        pa = p[:, None, :] - A[None]
        t = np.clip((pa * D[None]).sum(-1) / np.maximum(Ln * Ln, 1e-12)[None], 0, 1)
        d = np.linalg.norm(pa - t[..., None] * D[None], axis=-1)
        w = np.exp(-(d - d.min(1, keepdims=True)) / tau)
        out[i0:i0 + CH] = (w @ DD) / w.sum(1, keepdims=True)
    return out.reshape(-1, 3, 3)


class FlowGrid:
    """grain tensor sampled on a coarse grid over the polylines' bbox, trilinear lookup (fast for millions of pts)."""

    def __init__(self, lines, h=0.01, pad=0.08, tau=0.02):
        allp = np.concatenate(lines, 0)
        self.lo = allp.min(0) - pad
        hi = allp.max(0) + pad
        self.h = h
        self.n = np.ceil((hi - self.lo) / h).astype(int) + 1
        xs = [self.lo[k] + h * np.arange(self.n[k], dtype=F32) for k in range(3)]
        G = np.stack(np.meshgrid(*xs, indexing='ij'), -1).reshape(-1, 3).astype(F32)
        self.F = flow_field_brute(G, lines, tau).reshape(tuple(self.n) + (9,))

    def __call__(self, P):
        q = (P - self.lo) / self.h
        q = np.clip(q, 0, self.n - 1.001)
        i = np.floor(q).astype(int)
        f = (q - i).astype(F32)
        out = np.zeros((len(P), 9), F32)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                    out += w[:, None] * self.F[i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz]
        return out.reshape(-1, 3, 3)


_FG = {}


def flow_field(P, lines, tau=0.02):
    key = (round(sum(float(l.sum()) for l in lines), 4), len(lines), tau)
    if key not in _FG:
        _FG[key] = FlowGrid(lines, tau=tau)
    out = np.zeros((len(P), 3, 3), F32)
    for i0 in range(0, len(P), 500000):
        out[i0:i0 + 500000] = _FG[key](P[i0:i0 + 500000])
    return out


def principal(M):
    """dominant direction of grain tensors (N,3,3) by power iteration."""
    v = np.einsum('nij,j->ni', M, np.array([0.3, 0.4, 0.86], F32))
    for _ in range(4):
        v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        v = np.einsum('nij,nj->ni', M, v)
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def dist_polys(P, polys, pad=0.03):
    """distance from P (N,3) to the surface of tubes [(pts, radii)], bbox-culled. returns (d, t_along)"""
    d = np.full(len(P), 9.0, F32)
    tt = np.zeros(len(P), F32)
    for pts, rr in polys:
        rr = np.asarray(rr, F32)
        lo = pts.min(0) - rr.max() - pad
        hi = pts.max(0) + rr.max() + pad
        idx = np.nonzero(np.all((P > lo) & (P < hi), axis=1))[0]
        if len(idx) == 0:
            continue
        p = P[idx]
        al = arclen(pts)
        dl = np.full(len(idx), 9.0, F32)
        tl = np.zeros(len(idx), F32)
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            ab = b - a
            t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            dd = np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - (rr[i] + (rr[i + 1] - rr[i]) * t)
            upd = dd < dl
            dl = np.where(upd, dd, dl)
            tl = np.where(upd, al[i] + (al[i + 1] - al[i]) * t, tl)
        upd = dl < d[idx]
        d[idx] = np.where(upd, dl, d[idx])
        tt[idx] = np.where(upd, tl, tt[idx])
    return d, tt


def aniso(P, M, s_along, s_across):
    """coordinates stretched along the grain for anisotropic noise. M = grain tensor (N,3,3) or direction (N,3)."""
    if M.ndim == 2:
        M = M[:, :, None] * M[:, None, :]
    return P * s_across + np.einsum('nij,nj->ni', M, P) * (s_along - s_across)


def bark_height(P, D, scale=1.0):
    """bark: long fibrous ridges + deep cracks along the grain. returns height in metres (~ +-1)."""
    Q = aniso(P, D, 9.0 * scale, 70.0 * scale)
    r = NOISE.ridged(Q, 3)
    c = np.clip(NOISE2.fbm(aniso(P, D, 4.0 * scale, 26.0 * scale), 2) * 1.6 + 0.2, 0, 1)
    return (r - 0.55) - 0.9 * smoothstep(0.55, 0.95, c)


# ============================================================================================
HEART_C = v3(0.0, -0.018, 1.385)
CAVITY = (HEART_C, (0.112, 0.074, 0.15))


class Part:
    name = "part"
    atlas = "bark"
    h = 0.004
    lo = (-1, -1, 0)
    hi = (1, 1, 2)
    tris = 2000
    texel = 1.0
    smooth_iters = 3

    def build(self, g):
        pass

    def post(self, V, N):
        return V

    def masks(self, P, N):
        return {}

    def flow(self):
        return [np.array([[0, 0, 0], [0, 0, 1]], F32)]

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


def bark_post(part, V, N, amp=0.0026, scale=1.0, mask=None):
    D = flow_field(V, part.flow())
    h = bark_height(V, D, scale)
    if mask is not None:
        h = h * mask
    return V + N * (amp * h)[:, None]


# ============================================================================================ TORSO
def prof(z):
    return np.sqrt(np.clip(1 - ((np.asarray(z, F32) - 1.385) / 0.215) ** 2, 0, 1)).astype(F32)


def rib_w(z):
    return 0.158 * prof(z)


def rib_d(z):
    return 0.124 * prof(z) + 0.004


def rib_defs():
    out = []
    for i in range(5):
        z0 = 1.548 - i * 0.062
        for _, s in SIDES:
            pts = [(s * 0.02, 0.088, z0 + 0.004),
                   (s * 0.075, 0.098, z0),
                   (s * 0.92 * rib_w(z0 - 0.012), 0.058, z0 - 0.012),
                   (s * rib_w(z0 - 0.03), -0.004, z0 - 0.03),
                   (s * 0.86 * rib_w(z0 - 0.05), -0.072, z0 - 0.05)]
            if i <= 2:
                pts += [(s * 0.45 * rib_w(z0 - 0.066), -rib_d(z0 - 0.066), z0 - 0.066),
                        (s * 0.02, -rib_d(z0 - 0.072) - 0.004, z0 - 0.072)]
                r0, r1 = 0.0175, 0.0125
            else:
                pts += [(s * 0.55 * rib_w(z0 - 0.064), -rib_d(z0 - 0.064) + 0.006, z0 - 0.066)]
                r0, r1 = 0.0175, 0.006
            out.append((pts, r0, r1, i, s))
    return out


def torso_tubes():
    """(polyline, radii, tag) for every tube in the torso."""
    tubes = []

    def add(pts, r0, r1, tag, n=5, pw=1.0):
        p = spline(pts, n)
        tubes.append((p, taper(p, r0, r1, pw), tag))
    # spine column
    add([(0, 0.060, 0.99), (0, 0.084, 1.12), (0, 0.096, 1.26), (0, 0.097, 1.40), (0, 0.086, 1.52), (0, 0.062, 1.60),
         (0, 0.048, 1.66)], 0.036, 0.029, "column")
    # ribs
    for pts, r0, r1, i, s in rib_defs():
        add(pts, r0, r1, "rib", 6, 1.3)
    # sternum + collar branches
    add([(0, -0.112, 1.535), (0, -0.119, 1.49), (0, -0.117, 1.445), (0, -0.108, 1.415)], 0.017, 0.006, "sternum")
    for _, s in SIDES:
        add([(0, -0.104, 1.538), (s * 0.08, -0.075, 1.565), (s * 0.165, -0.02, 1.582)], 0.016, 0.019, "collar")
    # neck: core + twisted root strands
    add([(0, 0.058, 1.575), (0, 0.050, 1.64), (0, 0.030, 1.70), (0, 0.018, 1.745)], 0.034, 0.027, "neck")
    for pts, r in twisted((0, 0.05, 1.575), (0, 0.022, 1.74), 0.052, 0.03, 5, 0.0, 0.35, 0.4, 8, 0.0, 3):
        p = spline(pts, 3)
        tubes.append((p, taper(p, 0.0155, 0.012), "neck"))
    # hackles: bark shards down the back of the neck
    for k, (z, l) in enumerate(((1.60, 0.07), (1.645, 0.085), (1.69, 0.075), (1.73, 0.055))):
        yb = 0.072 - (z - 1.6) * 0.42
        for s in (-1, 1):
            p0 = (s * 0.012, yb, z)
            p1 = (s * 0.03, yb + l * 0.8, z + l * 0.55)
            add([p0, p1], 0.013, 0.003, "shard", 4)
    # abdomen roots between ribcage and pelvis
    for _, s in SIDES:
        add([(s * 0.07, -0.082, 1.262), (s * 0.048 + 0.006, -0.08, 1.17), (s * 0.066, -0.074, 1.075)], 0.0145, 0.017, "root")
        add([(s * 0.142, -0.012, 1.275), (s * 0.11, -0.004, 1.18), (s * 0.122, 0.0, 1.085)], 0.018, 0.019, "root")
        add([(s * 0.055, 0.085, 1.27), (s * 0.065, 0.085, 1.17), (s * 0.07, 0.08, 1.07)], 0.024, 0.026, "root")
    for pts, r in twisted((0, 0.075, 1.075), (0, 0.09, 1.27), 0.045, 0.048, 3, 0.0, 0.6, 0.3, 8, 0.0, 11):
        p = spline(pts, 3)
        tubes.append((p, taper(p, 0.012, 0.011), "root"))
    # vine belt round the hips
    belt = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        belt.append((0.142 * math.sin(a), 0.022 - 0.112 * math.cos(a), 1.066 + 0.006 * math.sin(3 * a)))
    p = np.array(belt, F32)
    tubes.append((p, [0.0125] * len(p), "belt"))
    # trapezius branches from the neck base to the shoulders
    for _, s in SIDES:
        add([(s * 0.03, 0.06, 1.615), (s * 0.12, 0.06, 1.6), (s * 0.19, 0.06, 1.565)], 0.042, 0.038, "trap")
    return tubes


class Slab(L.Prim):
    """tapered, curved bark slab: local x = width, y = thickness (normal), z = height; centre c, rotation R."""

    def __init__(self, c, R, w_top, w_bot, hh, th, bend=3.0):
        self.c, self.R = v3(c), np.asarray(R, F32)
        self.wt, self.wb, self.hh, self.th, self.bend = w_top, w_bot, hh, th, bend
        m = max(w_top, w_bot, hh) + 0.03
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = (P - self.c) @ self.R
        x, y, z = q[..., 0], q[..., 1], q[..., 2]
        y = y - self.bend * x * x
        t = np.clip(0.5 + z / (2 * self.hh), 0, 1)
        w = self.wb + (self.wt - self.wb) * t
        return np.maximum.reduce([np.abs(x) - w, np.abs(y) - self.th, np.abs(z) - self.hh]) - 0.003


def tasset_prims():
    """hanging bark slabs over the hips: (prim, tag)."""
    out = []
    for _, s in SIDES:
        Rf = rot_axis((0, 0, 1), s * 8) @ rot_axis((1, 0, 0), 9) @ rot_axis((0, 1, 0), -s * 4)
        out.append((Slab((s * 0.04, -0.112 - 0.006 * (s > 0), 0.93), Rf, 0.05, 0.036, 0.10, 0.008, 2.5), "flap_f"))
    Rb = rot_axis((1, 0, 0), -12)
    out.append((Slab((0, 0.145, 0.925), Rb, 0.095, 0.06, 0.125, 0.009, -2.5), "flap_b"))
    for _, s in SIDES:
        Rs = rot_axis((0, 0, 1), s * 90) @ rot_axis((1, 0, 0), -14 * 1) @ rot_axis((0, 0, 1), 0)
        Rs = rot_axis((0, 0, 1), s * 8) @ rot_axis((0, 1, 0), -s * 14) @ rot_axis((0, 0, 1), s * 90)
        out.append((Slab((s * 0.158, 0.012, 0.972), Rs, 0.07, 0.05, 0.075, 0.008, 2.0), "flap_s"))
    return out


def ragged(P, lo_z, amp=0.016, f=26.0):
    return (lo_z + amp * NOISE3(P * f)) - Z(P)


class Torso(Part):
    name = "torso"
    atlas = "bark"
    h = 0.0036
    lo = (-0.30, -0.20, 0.76)
    hi = (0.30, 0.20, 1.80)
    tris = 11500
    texel = 1.0
    smooth_iters = 2

    def build(self, g):
        # solid masses: back plate, scapulae, upper chest, pelvis girdle
        g.union(Ellipsoid((0, 0.068, 1.405), (0.142, 0.064, 0.165)))
        for _, s in SIDES:
            R = rot_axis((0, 0, 1), -s * 16) @ rot_axis((0, 1, 0), -s * 18)
            g.union(Ellipsoid((s * 0.098, 0.098, 1.47), (0.074, 0.024, 0.088), R=R), 0.025)
        g.union(Ellipsoid((0, 0.045, 1.585), (0.12, 0.075, 0.05)), 0.04)
        g.union(Ellipsoid((0, 0.03, 1.035), (0.132, 0.102, 0.082)), 0.03)
        g.union(Ellipsoid((0, 0.105, 1.045), (0.065, 0.03, 0.07)), 0.02)
        for _, s in SIDES:
            g.union(RoundCone((s * 0.055, -0.055, 1.072), (s * 0.135, 0.025, 1.098), 0.02, 0.024), 0.02)
        # hollow the ribcage
        c, r = CAVITY
        g.sub(Ellipsoid(c, r), 0.02)
        # tubes
        for p, rr, tag in torso_tubes():
            k = {"rib": 0.012, "sternum": 0.01, "collar": 0.014, "neck": 0.012, "shard": 0.008, "root": 0.012,
                 "belt": 0.006, "trap": 0.03, "column": 0.02}[tag]
            g.union(Tube(p, rr), k)
        # vertebra knobs down the back
        for z in np.arange(1.06, 1.585, 0.046):
            yc = float(np.interp(z, [0.99, 1.12, 1.26, 1.40, 1.52, 1.60], [0.06, 0.084, 0.096, 0.097, 0.086, 0.062]))
            g.union(Ellipsoid((0, yc + 0.034, z), (0.017, 0.017, 0.015)), 0.016)
        # bark slabs over the hips (ragged bottom edges)
        for pr, tag in tasset_prims():
            lo_z = {"flap_f": 0.845, "flap_b": 0.815, "flap_s": 0.915}[tag]
            g.union(Func(lambda P, pr=pr, lo_z=lo_z: np.maximum(pr.d(P), ragged(P, lo_z)), *pr.bb()), 0.01)

    def flow(self):
        out = [p for p, r, tag in torso_tubes() if tag != "belt"]
        out.append(np.array([[0, 0.03, 0.80], [0, 0.03, 1.10]], F32))
        for pr, tag in tasset_prims():
            c = pr.c
            out.append(np.array([c + v3(0, 0, 0.12), c - v3(0, 0, 0.12)], F32))
        return out

    def post(self, V, N):
        return bark_post(self, V, N, 0.0028, 1.0)

    def masks(self, P, N):
        m = {}
        c, r = CAVITY
        q = (P - c) / np.array(r, F32)
        rr = np.linalg.norm(q, axis=1)
        to_h = HEART_C - P
        dh = np.linalg.norm(to_h, axis=1)
        facing = (N * to_h).sum(1) / np.maximum(dh, 1e-6)
        m["inner"] = np.clip((1.45 - rr) / 0.5, 0, 1) * np.clip(facing * 1.5 + 0.2, 0, 1)
        m["heart_d"] = dh
        m["facing"] = facing
        d_tag = {}
        tt = torso_tubes()
        for tag in ("rib", "belt", "shard", "root", "sternum", "collar", "column", "neck"):
            d_tag[tag] = dist_polys(P, [(p, r) for p, r, t in tt if t == tag])[0]
        m["d_tag"] = d_tag
        m["slab"] = np.zeros(len(P), bool)
        for pr, tag in tasset_prims():
            m["slab"] |= pr.d(P) < 0.004
        return m

    def weights(self, P):
        z, x, y = P[:, 2], P[:, 0], P[:, 1]
        spec = [("pelvis", 0.16, v3(0, 0.03, 0.95), v3(0, 0.03, 1.10)), ("spine_01", 0.15), ("spine_02", 0.15),
                ("spine_03", 0.17), ("neck_01", 0.07), ("Head", 0.06, H("Head"), H("Head") + v3(0, 0, 0.05)),
                ("clavicle_l", 0.09), ("clavicle_r", 0.09)]
        W = wdist(P, spec, 5.0)
        # the ribcage moves as one: spine_03 above the heart, spine_02 below, smooth
        cage = smoothstep(1.17, 1.24, z) * smoothstep(1.64, 1.58, z)
        t = smoothstep(1.26, 1.47, z)
        for b in list(W):
            W[b] = W[b] * (1 - cage)
        W["spine_03"] = W["spine_03"] + cage * t * 0.85
        W["spine_02"] = W["spine_02"] + cage * (1 - t) * 0.75 + cage * t * 0.15
        W["spine_01"] = W.get("spine_01", 0) + cage * (1 - t) * 0.25
        # clavicles only on their own side
        W["clavicle_l"] = W["clavicle_l"] * (x > 0.02)
        W["clavicle_r"] = W["clavicle_r"] * (x < -0.02)
        # hip slabs + belt follow the thighs below the hip line
        hang = smoothstep(1.02, 0.86, z)
        sd = smoothstep(-0.08, 0.08, x)
        front = (y < -0.05)
        back = (y > 0.08)
        legw = hang * np.where(front | back, 0.5, 0.7)
        for b in list(W):
            W[b] = W[b] * (1 - legw)
        W["pelvis"] = W["pelvis"] + 0.0
        W["thigh_l"] = legw * sd
        W["thigh_r"] = legw * (1 - sd)
        return W


# ============================================================================================ SHOULDERS
def sh_pts(side):
    return H("upperarm_" + side), H("lowerarm_" + side)


def pauldron_plates(side, s):
    S, E = sh_pts(side)
    ud = norm(E - S)
    out = []
    for k in range(3):
        c = S + v3(s * (-0.024 + 0.006 * k), 0.004, 0.032) + ud * (0.064 * k)
        R = 0.112 - 0.015 * k
        n = norm(v3(s * (0.45 + 0.4 * k), 0.05, 1.0))
        out.append((c, R, n, k))
    return out


def plate_d(P, c, R, n, k, s, thick=0.0085):
    d = np.linalg.norm(P - c, axis=-1)
    h = ((P - c) * n).sum(-1)
    e = h + R * (0.30 - 0.05 * k) + 0.014 * NOISE3(P * 24.0 + k * 3.1)
    lip = np.clip(1 - e / 0.022, 0, 1)
    shell = np.abs(d - R - 0.004 * lip) - thick - 0.0055 * lip
    inner = -(s * X(P) - (0.09 + 0.032 * k))
    return np.maximum(np.maximum(shell, -e), inner)


class Shoulder(Part):
    atlas = "bark"
    h = 0.003
    tris = 1500
    texel = 1.0
    smooth_iters = 2

    def __init__(self, side):
        self.side = side
        self.s = 1.0 if side == "l" else -1.0
        self.name = "shoulder_" + side
        x0 = 0.04 if self.s > 0 else -0.40
        self.lo = (x0, -0.17, 1.33)
        self.hi = (x0 + 0.36, 0.20, 1.72)

    def build(self, g):
        for c, R, n, k in pauldron_plates(self.side, self.s):
            g.union(Func(lambda P, c=c, R=R, n=n, k=k: plate_d(P, c, R, n, k, self.s), c - R - 0.02, c + R + 0.02), 0.004)
        # a couple of bracket-fungus shelves on the outer plate
        S, E = sh_pts(self.side)
        for j, (off, rr) in enumerate((((0.105, -0.045, -0.035), 0.03), ((0.10, 0.04, -0.06), 0.024))):
            c = S + v3(self.s * off[0], off[1], off[2])
            g.union(Func(lambda P, c=c, rr=rr: np.maximum(Ellipsoid(c, (rr, rr, rr * 0.35)).d(P), -(Z(P) - c[2] + 0.002)),
                         c - 0.05, c + 0.05), 0.004)

    def flow(self):
        S, E = sh_pts(self.side)
        out = []
        for c, R, n, k in pauldron_plates(self.side, self.s):
            out.append(np.array([c + n * R, c + v3(self.s * R, 0, -R * 0.4)], F32))
        return out

    def post(self, V, N):
        return bark_post(self, V, N, 0.0034, 1.1)

    def masks(self, P, N):
        S, E = sh_pts(self.side)
        m = {"fungus": np.zeros(len(P), bool)}
        for j, (off, rr) in enumerate((((0.105, -0.045, -0.035), 0.03), ((0.10, 0.04, -0.06), 0.024))):
            c = S + v3(self.s * off[0], off[1], off[2])
            m["fungus"] |= Ellipsoid(c, (rr, rr, rr * 0.35)).d(P) < 0.003
        return m

    def weights(self, P):
        S, E = sh_pts(self.side)
        ud = norm(E - S)
        t = ((P - S) @ ud) / 0.10
        wu = np.clip(0.55 + 0.35 * t, 0.35, 0.95).astype(F32)
        return {"upperarm_" + self.side: wu, "clavicle_" + self.side: (1 - wu) * 0.8,
                "spine_03": (1 - wu) * 0.2}


# ============================================================================================ ARMS
def arm_pts(side):
    return H("upperarm_" + side), H("lowerarm_" + side), H("hand_" + side)


class Arm(Part):
    atlas = "bark"
    h = 0.0032
    tris = 1300
    texel = 0.9
    smooth_iters = 2

    def __init__(self, side):
        self.side = side
        self.s = 1.0 if side == "l" else -1.0
        self.name = "arm_" + side
        S, E, W = arm_pts(side)
        lo = np.minimum.reduce([S, E, W]) - 0.09
        hi = np.maximum.reduce([S, E, W]) + 0.09
        self.lo, self.hi = lo, hi

    def back(self):
        S, E, W = arm_pts(self.side)
        u, f = norm(E - S), norm(W - E)
        b = norm(u - f)          # direction the elbow points
        return b

    def tubes(self):
        S, E, W = arm_pts(self.side)
        out = []
        p = spline([S + v3(0, 0, 0.01), (S + E) * 0.5, E], 4)
        out.append((p, taper(p, 0.044, 0.037), "core"))
        p = spline([E, (E + W) * 0.5, W + norm(W - E) * 0.012], 4)
        out.append((p, taper(p, 0.037, 0.029), "core"))
        for pts, r in twisted(S + norm(E - S) * 0.03, E, 0.034, 0.03, 3, 0.0, 0.45, 0.3 * self.s, 8, 0.0, 5):
            out.append((spline(pts, 2), taper(spline(pts, 2), 0.017, 0.014), "strand"))
        for pts, r in twisted(E, W, 0.028, 0.022, 3, 0.0, -0.4, 1.1 * self.s, 8, 0.0, 7):
            out.append((spline(pts, 2), taper(spline(pts, 2), 0.0145, 0.011), "strand"))
        # elbow thorn
        b = self.back()
        p = spline([E + b * 0.025, E + b * 0.06 + v3(0, 0, -0.012), E + b * 0.095 + v3(0, 0, -0.04)], 3)
        out.append((p, taper(p, 0.016, 0.0025), "thorn"))
        return out

    def build(self, g):
        S, E, W = arm_pts(self.side)
        for p, r, tag in self.tubes():
            g.union(Tube(p, r), 0.012 if tag != "thorn" else 0.008)
        g.union(Sphere(E + self.back() * 0.012, 0.039), 0.02)
        # bark bracer rings near the wrist
        f = norm(W - E)
        R = frame_from(f)
        Rt = np.stack([R[:, 0], R[:, 2], R[:, 1]], 1)        # torus z axis along the forearm
        for t in (0.70, 0.79, 0.88):
            c = E + (W - E) * t
            rr = 0.04 + (0.031 - 0.04) * t
            g.union(Torus(c, rr + 0.002, 0.0062, R=Rt), 0.004)

    def flow(self):
        return [p for p, r, tag in self.tubes()]

    def post(self, V, N):
        return bark_post(self, V, N, 0.0024, 1.15)

    def masks(self, P, N):
        S, E, W = arm_pts(self.side)
        f = norm(W - E)
        t = ((P - E) @ f) / np.linalg.norm(W - E)
        rings = np.zeros(len(P), bool)
        for tt in (0.70, 0.79, 0.88):
            rings |= np.abs(t - tt) < 0.025
        return {"rings": rings, "thorn": dseg(P, E + self.back() * 0.03, E + self.back() * 0.095) < 0.012}

    def weights(self, P):
        s = self.side
        spec = [("clavicle_" + s, 0.07), ("upperarm_" + s, 0.06), ("lowerarm_" + s, 0.055),
                ("hand_" + s, 0.045, H("hand_" + s), H("middle_01_" + s))]
        W = wdist(P, spec, 5.0)
        W["clavicle_" + s] = W["clavicle_" + s] * 0.6
        W["upperarm_" + s] = W["upperarm_" + s] + 0.0
        return W


# ============================================================================================ HANDS
FING = ("index", "middle", "ring", "pinky")


def finger_chain(f, side):
    return [H("%s_01_%s" % (f, side)), H("%s_02_%s" % (f, side)), H("%s_03_%s" % (f, side)),
            H("%s_04_leaf_%s" % (f, side)), T("%s_04_leaf_%s" % (f, side))]


def claw_pts(chain, ln=0.075):
    d1 = norm(chain[1] - chain[0])
    d3 = norm(chain[4] - chain[3])
    curl = norm(d3 - d1 + v3(0, 0, -1e-4))
    c0 = chain[3] + (chain[4] - chain[3]) * 0.3
    return [c0, c0 + d3 * ln * 0.4 + curl * ln * 0.03, c0 + d3 * ln * 0.75 + curl * ln * 0.16,
            c0 + d3 * ln * 0.98 + curl * ln * 0.42]


class Hand(Part):
    atlas = "bark"
    h = 0.0021
    tris = 2300
    texel = 1.15
    smooth_iters = 2

    def __init__(self, side):
        self.side = side
        self.s = 1.0 if side == "l" else -1.0
        self.name = "hand_" + side
        allp = np.concatenate([p for p, r, t in self.tubes()], 0)
        self.lo = allp.min(0) - 0.04
        self.hi = allp.max(0) + 0.04

    def tubes(self):
        s = self.side
        W = H("hand_" + s)
        out = []
        knuck = [H("%s_01_%s" % (f, s)) for f in FING]
        hd = norm(np.mean(knuck, 0) - W)
        p = spline([W - hd * 0.045, W + hd * 0.01], 2)
        out.append((p, taper(p, 0.033, 0.03), "wrist"))
        for f, k in zip(FING, knuck):
            p = spline([W + hd * 0.005, k], 3)
            out.append((p, taper(p, 0.022, 0.0155), "palm"))
            ch = finger_chain(f, s)
            p = spline(ch[:4] + [ch[3] + (ch[4] - ch[3]) * 0.4], 3)
            out.append((p, taper(p, 0.0145, 0.0105), "finger"))
            c = claw_pts(ch, 0.078 if f != "pinky" else 0.064)
            p = spline(c, 4)
            out.append((p, taper(p, 0.0105, 0.0009, 0.9), "claw"))
        th = [H("thumb_01_" + s), H("thumb_02_" + s), H("thumb_03_" + s), H("thumb_04_leaf_" + s), T("thumb_04_leaf_" + s)]
        p = spline([W + hd * 0.01, th[1]], 3)
        out.append((p, taper(p, 0.024, 0.016), "palm"))
        p = spline(th[1:4] + [th[3] + (th[4] - th[3]) * 0.4], 3)
        out.append((p, taper(p, 0.0155, 0.012), "finger"))
        p = spline(claw_pts(th, 0.07), 4)
        out.append((p, taper(p, 0.011, 0.001, 0.9), "claw"))
        return out

    def build(self, g):
        s = self.side
        for p, r, tag in self.tubes():
            g.union(Tube(p, r), {"wrist": 0.02, "palm": 0.026, "finger": 0.006, "claw": 0.004}[tag])
        # knuckle knobs + thorns on the back of the hand
        W = H("hand_" + s)
        for f in FING:
            ch = finger_chain(f, s)
            for j in (0, 1, 2):
                g.union(Sphere(ch[j], 0.0145 - 0.0015 * j), 0.005)
        for f in ("index", "middle", "ring"):
            ch = finger_chain(f, s)
            d1 = norm(ch[1] - ch[0]); d3 = norm(ch[4] - ch[3])
            back = -norm(d3 - d1 + v3(0, 0, -1e-4))
            p = spline([ch[0] + back * 0.008, ch[0] + back * 0.026 - d1 * 0.008], 2)
            g.union(Tube(p, taper(p, 0.0065, 0.0012)), 0.003)

    def flow(self):
        return [p for p, r, tag in self.tubes()]

    def post(self, V, N):
        d = np.full(len(V), 9.0, F32)
        for p, r, tag in self.tubes():
            if tag == "claw":
                for a, b in zip(p[:-1], p[1:]):
                    d = np.minimum(d, dseg(V, a, b))
        m = smoothstep(0.012, 0.02, d)
        return bark_post(self, V, N, 0.0013, 1.7, m)

    def masks(self, P, N):
        d, tip = dist_polys(P, [(p, r) for p, r, tag in self.tubes() if tag == "claw"])
        return {"claw": d < 0.0035, "claw_t": tip}

    def weights(self, P):
        s = self.side
        spec = [("lowerarm_" + s, 0.05, H("lowerarm_" + s), H("hand_" + s) - norm(H("hand_" + s) - H("lowerarm_" + s)) * 0.02),
                ("hand_" + s, 0.04, H("hand_" + s), H("middle_01_" + s) * 0.7 + H("hand_" + s) * 0.3)]
        for f in FING:
            ch = finger_chain(f, s)
            for seg in (1, 2, 3):
                b = "%s_0%d_%s" % (f, seg, s)
                tail = ch[seg] if seg < 3 else ch[4] + (ch[4] - ch[3]) * 1.5
                spec.append((b, 0.016, ch[seg - 1], tail))
        th = [H("thumb_01_" + s), H("thumb_02_" + s), H("thumb_03_" + s), H("thumb_04_leaf_" + s), T("thumb_04_leaf_" + s)]
        for seg in (1, 2, 3):
            tail = th[seg] if seg < 3 else th[4] + (th[4] - th[3]) * 1.5
            spec.append(("thumb_0%d_%s" % (seg, s), 0.019, th[seg - 1], tail))
        return wdist(P, spec, 6.0)


# ============================================================================================ LEGS
def leg_pts(side):
    return H("thigh_" + side), H("calf_" + side), H("foot_" + side), H("ball_" + side), T("ball_" + side)


def hoof_d(P, side):
    """cloven hoof: two teardrop toes (flat sole, flat inner faces at the cleft)."""
    hip, knee, ank, ball, toe = leg_pts(side)
    out = None
    yb = ball[1] + 0.052
    for t in (-1, 1):
        cx = ball[0] + t * 0.025
        heel = v3(cx, yb, 0.042)
        tip = v3(cx + t * 0.007, yb - 0.112, 0.013)
        d = RoundCone(heel, tip, 0.042, 0.013).d(P)
        d = np.maximum(d, -Z(P))
        d = np.maximum(d, -(t * (X(P) - ball[0]) - 0.0035))
        out = d if out is None else np.minimum(out, d)
    return out


def hock_pt(side):
    hip, knee, ank, ball, toe = leg_pts(side)
    return knee + (ank - knee) * 0.40


class Leg(Part):
    atlas = "bark"
    h = 0.0034
    tris = 2600
    texel = 0.85
    smooth_iters = 2

    def __init__(self, side):
        self.side = side
        self.s = 1.0 if side == "l" else -1.0
        self.name = "leg_" + side
        hip, knee, ank, ball, toe = leg_pts(side)
        lo = np.minimum.reduce([hip, knee, ank, ball, toe]) - 0.12
        hi = np.maximum.reduce([hip, knee, ank, ball, toe]) + 0.12
        lo[2] = -0.01
        self.lo, self.hi = lo, hi

    def tubes(self):
        hip, knee, ank, ball, toe = leg_pts(self.side)
        hk = hock_pt(self.side)
        bk = v3(0, 1, 0)
        out = []
        p = spline([hip + v3(0, 0, 0.03), hip * 0.5 + knee * 0.5 + v3(0, -0.008, 0), knee], 4)
        out.append((p, taper(p, 0.078, 0.05), "thigh"))
        # upper shin (gaskin) -> false hock behind -> thin cannon down to the fetlock: reads as a reversed joint
        p = spline([knee, knee * 0.5 + hk * 0.5 + bk * 0.008, hk + bk * 0.022], 4)
        out.append((p, taper(p, 0.05, 0.04), "shin"))
        p = spline([hk + bk * 0.022, hk * 0.5 + ank * 0.5 + bk * 0.008, ank + v3(0, -0.004, 0.0)], 4)
        out.append((p, taper(p, 0.033, 0.028), "cannon"))
        # sharp front shin ridge
        p = spline([knee + v3(0, -0.034, -0.03), knee * 0.5 + hk * 0.5 + v3(0, -0.03, 0), hk + v3(0, -0.012, -0.02)], 3)
        out.append((p, taper(p, 0.017, 0.01), "ridge"))
        # hock spur
        p = spline([hk + bk * 0.05, hk + bk * 0.085 + v3(0, 0, -0.022), hk + bk * 0.105 + v3(0, 0, -0.06)], 3)
        out.append((p, taper(p, 0.016, 0.003), "spur"))
        # pastern -> hoof top
        top = v3(ball[0], ball[1] + 0.03, 0.062)
        p = spline([ank, ank * 0.4 + top * 0.6 + v3(0, 0.0, 0.012), top], 3)
        out.append((p, taper(p, 0.03, 0.033), "pastern"))
        # dewclaws behind the fetlock
        for t in (-1, 1):
            a = ank + v3(t * 0.017, 0.028, -0.02)
            p = spline([a, a + v3(t * 0.005, 0.028, -0.018), a + v3(t * 0.008, 0.045, -0.05)], 3)
            out.append((p, taper(p, 0.0115, 0.003), "dewclaw"))
        # thigh strands
        for pts, r in twisted(hip + v3(0, 0, -0.02), knee, 0.062, 0.042, 4, 0.0, 0.35, 0.5 * self.s, 8, 0.0, 9):
            out.append((spline(pts, 2), taper(spline(pts, 2), 0.022, 0.016), "strand"))
        # knee thorn
        p = spline([knee + v3(0, -0.06, 0.012), knee + v3(self.s * 0.006, -0.088, 0.03), knee + v3(self.s * 0.01, -0.1, 0.06)], 3)
        out.append((p, taper(p, 0.014, 0.003), "thorn"))
        return out

    def cuisse(self):
        hip, knee, ank, ball, toe = leg_pts(self.side)
        td = norm(knee - hip)
        c = hip * 0.62 + knee * 0.38 + v3(self.s * 0.035, -0.062, 0)
        R = frame_from(td, norm(v3(self.s * 0.5, -1, 0)))       # y = along thigh, z = outward normal
        return c, R

    def build(self, g):
        hip, knee, ank, ball, toe = leg_pts(self.side)
        hk = hock_pt(self.side)
        for p, r, tag in self.tubes():
            g.union(Tube(p, r), {"thigh": 0.03, "shin": 0.02, "cannon": 0.02, "ridge": 0.012, "pastern": 0.02,
                                 "dewclaw": 0.008, "strand": 0.012, "spur": 0.012, "thorn": 0.008}[tag])
        td = norm(knee - hip)
        R = frame_from(td, (0, -1, 0))
        g.union(Ellipsoid(hip * 0.58 + knee * 0.42 + v3(self.s * 0.006, -0.03, 0), (0.06, 0.15, 0.056), R=R), 0.03)
        g.union(Ellipsoid(hip * 0.55 + knee * 0.45 + v3(0, 0.032, 0), (0.05, 0.13, 0.046), R=R), 0.03)
        sd = norm(ank - knee)
        R2 = frame_from(sd, (0, -1, 0))
        g.union(Ellipsoid(knee * 0.75 + hk * 0.25 + v3(0, 0.03, 0), (0.042, 0.075, 0.042), R=R2), 0.025)   # calf
        g.union(Ellipsoid(knee + v3(0, -0.046, 0.008), (0.045, 0.05, 0.026), R=R2), 0.012)              # kneecap plate
        g.union(Ellipsoid(hk + v3(0, 0.045, 0.0), (0.026, 0.03, 0.04)), 0.02)                            # false hock
        g.union(Ellipsoid(ank + v3(0, 0.022, 0.006), (0.024, 0.028, 0.026)), 0.016)                      # fetlock
        g.union(Func(lambda P: hoof_d(P, self.side), ball - v3(0.08, 0.2, 0.03), ball + v3(0.08, 0.12, 0.12)), 0.01)
        # bark plate on the outer front thigh (ragged lower edge)
        c, Rc = self.cuisse()

        def cuisse_d(P, c=c, Rc=Rc):
            q = (P - c) @ Rc
            x, yl, z = q[..., 0], q[..., 1], q[..., 2]
            z = z + 4.0 * x * x                       # wrap round the thigh
            w = 0.05 - 0.012 * (yl / 0.11)
            d = np.maximum.reduce([np.abs(x) - w, np.abs(z) - 0.0085, np.abs(yl) - 0.11])
            return np.maximum(d, (yl - 0.075 - 0.014 * NOISE3(P * 30.0)))
        g.union(Func(cuisse_d, c - 0.15, c + 0.15), 0.008)

    def flow(self):
        return [p for p, r, tag in self.tubes()]

    def post(self, V, N):
        m = 1.0 - smoothstep(0.02, -0.004, hoof_d(V, self.side))
        return bark_post(self, V, N, 0.0028, 1.0, m)

    def masks(self, P, N):
        hip, knee, ank, ball, toe = leg_pts(self.side)
        hd = hoof_d(P, self.side)
        tb = self.tubes()
        dc = dist_polys(P, [(p, r) for p, r, tag in tb if tag in ("dewclaw", "spur", "thorn")])[0]
        coronet = (P[:, 2] < 0.1) & (P[:, 2] > 0.04) & (hd > 0.002) & (P[:, 1] < ank[1] + 0.02)
        return {"hoof": hd < 0.0035, "dewclaw": dc < 0.004, "coronet": coronet,
                "knee": np.linalg.norm(P - (knee + v3(0, -0.046, 0.008)), axis=1) < 0.05}

    def weights(self, P):
        s = self.side
        hip, knee, ank, ball, toe = leg_pts(s)
        spec = [("pelvis", 0.12, v3(0, 0.03, 0.98), v3(0, 0.03, 1.12)), ("thigh_" + s, 0.075), ("calf_" + s, 0.055),
                ("foot_" + s, 0.05, ank, ball), ("ball_" + s, 0.04, ball, toe)]
        W = wdist(P, spec, 6.0)
        hoof = hoof_d(P, s) < 0.006
        front = np.clip((ball[1] - P[:, 1] + 0.01) / 0.07, 0, 1) * 0.45
        W["foot_" + s] = np.where(hoof, 1 - front, W["foot_" + s])
        W["ball_" + s] = np.where(hoof, front, W["ball_" + s])
        for b in ("pelvis", "thigh_" + s, "calf_" + s):
            W[b] = np.where(hoof, 0, W[b])
        return W


# ============================================================================================ MOSS (bone atlas)
class Moss(Part):
    name = "moss"
    atlas = "bone"
    h = 0.003
    lo = (-0.40, -0.17, 1.42)
    hi = (0.40, 0.20, 1.74)
    tris = 2400
    texel = 0.8
    smooth_iters = 2

    def region(self, P, side, s):
        c, R, n, k = pauldron_plates(side, s)[0]
        up = ((P - c) * norm(v3(s * 0.25, 0.05, 1.0))).sum(-1)
        return (R * 0.52 - up) + 0.025 * NOISE.fbm(P * 9.0, 3)

    def build(self, g):
        for side, s in SIDES:
            c, R, n, k = pauldron_plates(side, s)[0]

            def fn(P, c=c, R=R, n=n, k=k, side=side, s=s):
                base = plate_d(P, c, R, n, k, s, 0.0085)
                clump = np.clip(NOISE2.fbm(P * 15.0, 3) + 0.5, 0, 1)
                t = 0.009 + 0.017 * clump
                reg = self.region(P, side, s)
                edge = smoothstep(0.0, -0.03, reg)
                return np.maximum(base - t * edge, reg)
            g.union(Func(fn, c - R - 0.05, c + R + 0.05), 0.0)
        # moss on the back of the neck / skull base, around the hackles
        def nk(P):
            core = dseg(P.reshape(-1, 3), v3(0, 0.07, 1.585), v3(0, 0.055, 1.70)).reshape(P.shape[:-1]) - 0.052
            reg = (Y(P) - 0.03) * -1.0 + 0.012 * NOISE.fbm(P * 12.0, 2)
            return np.maximum(core - 0.012 * np.clip(NOISE2.fbm(P * 18.0, 2) + 0.6, 0, 1), reg)
        g.union(Func(nk, (-0.08, 0.0, 1.55), (0.08, 0.15, 1.74)), 0.0)

    def post(self, V, N):
        b = NOISE3.fbm(V * 60.0, 2)
        return V + N * (0.0018 * b)[:, None]

    def weights(self, P):
        x = P[:, 0]
        W = {}
        neck = (np.abs(x) < 0.085) & (P[:, 1] > 0.02)
        for side, s in SIDES:
            w = Shoulder(side).weights(P)
            on = (s * x > 0.0) & ~neck
            for b, v in w.items():
                W[b] = W.get(b, 0) + v * on
        t = smoothstep(1.6, 1.72, P[:, 2])
        W["spine_03"] = W.get("spine_03", 0) + neck * (1 - t)
        W["neck_01"] = neck * t
        return W


# ============================================================================================ SKULL (bone atlas)
SKULL_EYE = [v3(s * 0.058, -0.072, 1.774) for s in (1, -1)]
SK = 1.12          # skull scale about the Head joint (fighting-game head size)


def socket_axis(s):
    return norm(v3(s * 1.0, -0.85, 0.22))


class Xf(L.Prim):
    """prim scaled by s about pivot, then moved by off."""

    def __init__(self, prim, pivot, s, off=(0, 0, 0)):
        self.p, self.c, self.s, self.off = prim, v3(pivot), float(s), v3(off)
        lo, hi = prim.bb()
        self.bbox = (self.c + (lo - self.c) * s + self.off, self.c + (hi - self.c) * s + self.off)

    def d(self, P):
        return self.p.d(self.c + (P - self.off - self.c) / self.s) * self.s


class GridXf:
    def __init__(self, g, pivot, s, off=(0, 0, 0)):
        self.g, self.c, self.s, self.off = g, v3(pivot), s, v3(off)

    def union(self, prim, k=0.0):
        self.g.union(Xf(prim, self.c, self.s, self.off), k * self.s)

    def sub(self, prim, k=0.0):
        self.g.sub(Xf(prim, self.c, self.s, self.off), k * self.s)


def skull_unscale(P):
    c = H("Head")
    return c + (P - c) / SK


def skull_scale(p):
    c = H("Head")
    return c + (v3(p) - c) * SK


class Skull(Part):
    name = "skull"
    atlas = "bone"
    h = 0.0021
    lo = (-0.13, -0.37, 1.60)
    hi = (0.13, 0.13, 1.89)
    tris = 4400
    texel = 1.5
    smooth_iters = 2

    def build(self, g0):
        g = GridXf(g0, H("Head"), SK)
        g.union(Ellipsoid((0, 0.004, 1.772), (0.071, 0.086, 0.068)))                       # braincase
        g.union(Ellipsoid((0, -0.058, 1.785), (0.066, 0.06, 0.05)), 0.04)                    # frontal
        g.union(Ellipsoid((0, 0.06, 1.76), (0.06, 0.04, 0.055)), 0.03)                       # occiput
        g.union(Ellipsoid((0, -0.135, 1.752), (0.047, 0.075, 0.043)), 0.05)                  # muzzle
        g.union(Ellipsoid((0, -0.212, 1.727), (0.035, 0.07, 0.033)), 0.04)
        g.union(Ellipsoid((0, -0.272, 1.708), (0.027, 0.042, 0.028)), 0.03)
        for s in (1, -1):
            g.union(RoundCone((s * 0.06, -0.05, 1.742), (s * 0.044, -0.135, 1.728), 0.016, 0.011), 0.02)   # cheek
            g.union(RoundCone((s * 0.044, 0.02, 1.70), (s * 0.05, 0.0, 1.75), 0.013, 0.015), 0.02)         # jaw ramus
            g.union(RoundCone((s * 0.042, 0.012, 1.698), (s * 0.013, -0.25, 1.679), 0.0125, 0.009), 0.01)  # mandible
            g.union(Torus(SKULL_EYE[0 if s > 0 else 1], 0.029, 0.009, R=frame_from(socket_axis(s))[:, [0, 2, 1]]), 0.012)
            g.union(RoundCone((s * 0.038, -0.035, 1.809), (s * 0.07, -0.075, 1.804), 0.0145, 0.0125), 0.02)  # brow
        g.union(RoundCone((0.013, -0.25, 1.679), (-0.013, -0.25, 1.679), 0.009, 0.009), 0.006)            # chin
        # mouth slit (sides only, the chin stays closed)
        Rm = rot_axis((1, 0, 0), -7)
        g.sub(RBox((0, -0.13, 1.6935), (0.06, 0.095, 0.004), 0.0018, R=Rm), 0.002)
        # eye sockets + glowing eyes deep inside
        for i, s in enumerate((1, -1)):
            c = SKULL_EYE[i]
            ax = socket_axis(s)
            g.sub(Sphere(c + ax * 0.004, 0.0275), 0.006)
            g.union(Sphere(c - ax * 0.007, 0.0138), 0.004)
        # nasal opening at the tip + nasal groove on top
        g.sub(Ellipsoid((0, -0.307, 1.716), (0.015, 0.026, 0.0135)), 0.006)
        g.sub(Ellipsoid((0, -0.205, 1.758), (0.0055, 0.055, 0.008)), 0.004)
        # molars in the mouth slit
        for s in (1, -1):
            for j in range(5):
                yj = -0.055 - j * 0.022
                zj = 1.6955 + 0.0021 * j
                g.union(RBox((s * (0.029 - 0.0025 * j), yj, zj), (0.0065, 0.0085, 0.0062), 0.0022), 0.0015)

    def post(self, V, N):
        U = skull_unscale(V)
        b = 0.4 * NOISE.ridged(V * 70.0, 2) + 0.6 * NOISE2.fbm(V * 30.0, 2)
        far = np.ones(len(V), F32)
        for c in SKULL_EYE:
            far *= smoothstep(0.03, 0.042, np.linalg.norm(U - c, axis=1))
        return V + N * (0.0009 * b * far)[:, None]

    def masks(self, P, N):
        U = skull_unscale(P)
        m = {}
        eye = np.zeros(len(P), bool)
        sock = np.zeros(len(P), F32)
        for i, s in enumerate((1, -1)):
            c = SKULL_EYE[i]
            ax = socket_axis(s)
            eye |= np.linalg.norm(U - (c - ax * 0.007), axis=1) < 0.0155
            sock = np.maximum(sock, np.clip(1 - np.linalg.norm(U - c, axis=1) / 0.036, 0, 1))
        m["eye"] = eye
        m["socket"] = sock
        teeth = np.zeros(len(P), bool)
        for s in (1, -1):
            for j in range(5):
                c = v3(s * (0.029 - 0.0025 * j), -0.055 - j * 0.022, 1.6955 + 0.0021 * j)
                teeth |= np.all(np.abs(U - c) < v3(0.009, 0.011, 0.0085), axis=1)
        m["teeth"] = teeth
        m["mouth"] = (np.abs(U[:, 2] - (1.6935 + (U[:, 1] + 0.13) * math.tan(math.radians(7)))) < 0.0075) & (U[:, 1] > -0.235)
        m["nose"] = np.linalg.norm((U - v3(0, -0.307, 1.716)) / v3(1.0, 1.0, 1.0), axis=1) < 0.03
        return m

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


# ============================================================================================ ANTLERS (bone atlas)
TINE_K = 1.15


def antler_defs(s, jit=0.0):
    """list of (pts, r0, r1, tag) for one antler (s = +1 left)."""
    burr = v3(0.046, -0.006, 1.826)
    shift = skull_scale(burr) - burr + v3(0, 0, -0.004)

    def m(p):
        return v3(s * p[0], p[1], p[2] - 0.012 * (p[2] > 1.95)) + v3(s * shift[0], shift[1], shift[2])
    beam = [m((0.046, -0.006, 1.826)), m((0.105, 0.03, 1.872)), m((0.18, 0.082, 1.918)), m((0.262, 0.118, 1.962)),
            m((0.345, 0.122, 2.0)), m((0.418, 0.088, 2.032)), m((0.468, 0.03, 2.05)), m((0.49, -0.025, 2.058))]
    out = [(beam, 0.04, 0.011, "beam")]
    tines = [
        ([(0.068, 0.006, 1.846), (0.092, -0.05, 1.852), (0.125, -0.115, 1.875), (0.148, -0.162, 1.92)], TINE_K * 0.022, TINE_K * 0.0055),  # brow
        ([(0.122, 0.044, 1.885), (0.15, -0.012, 1.915), (0.18, -0.06, 1.958), (0.195, -0.088, 2.0)], TINE_K * 0.018, TINE_K * 0.005),      # bez
        ([(0.215, 0.098, 1.937), (0.24, 0.07, 1.985), (0.262, 0.045, 2.03), (0.27, 0.03, 2.062)], TINE_K * 0.017, TINE_K * 0.0048),         # trez
        ([(0.31, 0.123, 1.982), (0.338, 0.14, 2.03), (0.355, 0.148, 2.066), (0.36, 0.146, 2.084)], TINE_K * 0.0155, TINE_K * 0.0045),      # crown back
        ([(0.37, 0.118, 2.01), (0.39, 0.085, 2.048), (0.405, 0.062, 2.074)], TINE_K * 0.014, TINE_K * 0.0042),                              # crown
        ([(0.44, 0.07, 2.04), (0.47, 0.085, 2.06), (0.505, 0.1, 2.072)], TINE_K * 0.0125, TINE_K * 0.004),                                  # crown out
        ([(0.16, 0.074, 1.912), (0.17, 0.14, 1.93), (0.175, 0.19, 1.965)], TINE_K * 0.0145, TINE_K * 0.0042),                               # back snag
        ([(0.296, 0.12, 1.976), (0.31, 0.06, 1.995), (0.33, 0.0, 2.02), (0.338, -0.035, 2.05)], TINE_K * 0.0145, TINE_K * 0.0042),           # forward crown
    ]
    for pts, r0, r1 in tines:
        out.append(([m(p) for p in pts], r0, r1, "tine"))
    return out


def antler_polys(s):
    return [(spline(pts, 5), r0, r1, tag) for pts, r0, r1, tag in antler_defs(s)]


class Antler(Part):
    atlas = "bone"
    h = 0.0024
    tris = 2700
    texel = 1.0
    smooth_iters = 2

    def __init__(self, side):
        self.side = side
        self.s = 1.0 if side == "l" else -1.0
        self.name = "antler_" + side
        if self.s > 0:
            self.lo, self.hi = (0.0, -0.21, 1.79), (0.545, 0.225, 2.105)
        else:
            self.lo, self.hi = (-0.545, -0.21, 1.79), (0.0, 0.225, 2.105)

    def build(self, g):
        for p, r0, r1, tag in antler_polys(self.s):
            g.union(Tube(p, taper(p, r0, r1, 0.8)), 0.014 if tag == "tine" else 0.0)
        b0 = antler_defs(self.s)[0][0]
        ax = norm(b0[1] - b0[0])
        R = frame_from(ax)[:, [0, 2, 1]]
        g.union(Torus(b0[0] + ax * 0.014, 0.027, 0.0105, R=R), 0.006)                      # burr / coronet

    def flow(self):
        return [p for p, r0, r1, tag in antler_polys(self.s)]

    def post(self, V, N):
        D = flow_field(V, self.flow(), 0.01)
        g = NOISE.ridged(aniso(V, D, 14.0, 120.0), 2) - 0.6
        b0 = antler_defs(self.s)[0][0][0]
        base = smoothstep(0.16, 0.03, np.linalg.norm(V - b0, axis=1))
        pearl = np.clip(NOISE2(V * 160.0) * 1.8 - 0.3, 0, 1) * base
        return V + N * (0.0012 * g + 0.0022 * pearl)[:, None]

    def masks(self, P, N):
        tip = np.zeros(len(P), F32)
        best = np.full(len(P), 9.0, F32)
        for p, r0, r1, tag in antler_polys(self.s):
            d, t = dist_polys(P, [(p, taper(p, r0, r1, 0.8))])
            upd = d < best
            best = np.where(upd, d, best)
            tip = np.where(upd, t if tag == "tine" else 0.75 * t, tip)
        b0 = antler_defs(self.s)[0][0][0]
        return {"tip": tip, "base": smoothstep(0.08, 0.02, np.linalg.norm(P - b0, axis=1))}


# ============================================================================================ LANTERN-HEART (bone atlas)
def heart_core_d(P, c=HEART_C, sc=1.0):
    q = (P - c) / sc
    x, y, z = q[..., 0], q[..., 1] / 0.78, q[..., 2]
    lobes = np.minimum(np.sqrt((x - 0.0165) ** 2 + y ** 2 + (z - 0.011) ** 2),
                       np.sqrt((x + 0.0165) ** 2 + y ** 2 + (z - 0.011) ** 2)) - 0.026
    cone = RoundCone((0, 0, 0.004), (0, 0, -0.046), 0.03, 0.004).d(np.stack([x, y, z], -1))
    return smin(lobes, cone, 0.02) * sc


def heart_bars():
    c = HEART_C
    out = []
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        dx, dy = math.cos(a), math.sin(a) * 0.8
        pts = [c + v3(dx * 0.016, dy * 0.016, 0.056), c + v3(dx * 0.044, dy * 0.044, 0.02),
               c + v3(dx * 0.044, dy * 0.044, -0.02), c + v3(dx * 0.014, dy * 0.014, -0.058)]
        out.append(spline(pts, 4))
    return out


HS = 1.22          # lantern-heart scale about its centre


class Heart(Part):
    name = "heart"
    atlas = "bone"
    h = 0.0015
    lo = HEART_C - v3(0.075, 0.07, 0.085) * HS
    hi = HEART_C + v3(0.075, 0.105, 0.16) * HS
    tris = 2400
    texel = 1.4
    smooth_iters = 2

    def build(self, g0):
        c = HEART_C
        g = GridXf(g0, c, HS)
        g.union(Func(lambda P: heart_core_d(P), c - 0.06, c + 0.06))
        for p in heart_bars():
            g.union(Tube(p, [0.0046] * len(p)), 0.003)
        g.union(Func(lambda P: np.maximum(Ellipsoid(c + v3(0, 0, 0.062), (0.03, 0.026, 0.017)).d(P), c[2] + 0.054 - Z(P)),
                     c - 0.06, c + 0.09), 0.004)                                                 # cap
        g.union(Torus(c + v3(0, 0, 0.083), 0.0115, 0.0034, R=rot_axis((1, 0, 0), 90)), 0.002)    # ring
        g.union(Ellipsoid(c + v3(0, 0, -0.06), (0.02, 0.017, 0.008)), 0.004)                      # base knob
        # roots holding it to the spine column
        p = spline([c + v3(0, 0, 0.09), c + v3(0, 0.02, 0.115), v3(0, 0.068, c[2] + 0.122)], 4)
        g.union(Tube(p, taper(p, 0.0045, 0.009)), 0.004)
        for s in (1, -1):
            p = spline([c + v3(0, 0, -0.062), c + v3(s * 0.02, 0.03, -0.072), v3(s * 0.022, 0.068, c[2] - 0.07)], 4)
            g.union(Tube(p, taper(p, 0.004, 0.008)), 0.004)

    def masks(self, P, N):
        U = HEART_C + (P - HEART_C) / HS
        return {"core": heart_core_d(U) < 0.002}

    def weights(self, P):
        return {"spine_03": np.ones(len(P), F32)}


# ============================================================================================ tiny lantern (instanced)
class Lantern(Part):
    """tiny hanging lantern, modelled around LANTERN_OFF (out of the way of the body for AO baking; hang point at
    the top of the cord), instanced on the antlers by s6_rig."""
    name = "lantern"
    atlas = "bone"
    h = 0.0008
    off = v3(1.5, 0.0, 1.0)
    lo = off + v3(-0.024, -0.024, -0.082)
    hi = off + v3(0.024, 0.024, 0.004)
    tris = 600
    texel = 1.6
    smooth_iters = 1

    def build(self, g0):
        g = GridXf(g0, v3(0, 0, 0), 1.0, self.off)
        g.union(RoundCone((0, 0, 0.0), (0, 0, -0.022), 0.0016, 0.0016))                         # cord
        g.union(Torus((0, 0, -0.026), 0.0055, 0.0017, R=rot_axis((1, 0, 0), 90)), 0.001)        # ring
        g.union(Func(lambda P: np.maximum(RoundCone((0, 0, -0.03), (0, 0, -0.044), 0.006, 0.016).d(P),
                                          -0.045 - Z(P)), (-0.02, -0.02, -0.05), (0.02, 0.02, -0.025)), 0.002)   # roof
        g.union(RBox((0, 0, -0.0465), (0.0155, 0.0155, 0.0022), 0.0012), 0.001)
        g.union(RBox((0, 0, -0.0755), (0.0145, 0.0145, 0.0026), 0.0012), 0.001)
        for sx in (1, -1):
            for sy in (1, -1):
                g.union(RoundCone((sx * 0.0125, sy * 0.0125, -0.047), (sx * 0.0125, sy * 0.0125, -0.075), 0.0018), 0.001)
        g.union(RBox((0, 0, -0.061), (0.0108, 0.0108, 0.0125), 0.004), 0.001)                   # glass
        g.union(Sphere((0, 0, -0.0795), 0.004), 0.002)

    def masks(self, P, N):
        P = P - self.off
        glass = RBox((0, 0, -0.061), (0.0108, 0.0108, 0.0125), 0.004).d(P) < 0.0009
        cord = (P[:, 2] > -0.021)
        return {"glass": glass, "cord": cord}

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


def all_parts():
    ps = [Torso()]
    for side, s in SIDES:
        ps += [Shoulder(side), Arm(side), Hand(side), Leg(side)]
    ps += [Moss(), Skull(), Antler("l"), Antler("r"), Heart(), Lantern()]
    return ps


def parts(atlas):
    return [p for p in all_parts() if p.atlas == atlas]


ATLAS_SIZE = {"bark": 2048, "bone": 2048}

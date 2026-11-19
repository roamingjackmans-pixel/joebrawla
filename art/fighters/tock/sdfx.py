"""Generic SDF helpers shared by the fighter part scripts (splines, tubes, grain flow, culled distances, slabs,
scaled/moved prims). Extracted from vexthorn/parts.py."""
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


def bark_height(P, M, scale=1.0):
    """bark: long fissures along the grain (noise zero-crossings), fibrous ridges, broad plates. ~[-1, 0.5]"""
    n = NOISE2(aniso(P, M, 5.0 * scale, 40.0 * scale))
    fiss = smoothstep(0.17, 0.0, np.abs(n))
    fib = NOISE.ridged(aniso(P, M, 11.0 * scale, 105.0 * scale), 2)
    plate = NOISE3.fbm(aniso(P, M, 2.5 * scale, 9.0 * scale), 2)
    return 0.35 * plate + 0.4 * (fib - 0.55) - 1.0 * fiss


# ============================================================================================

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



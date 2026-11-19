"""Foreman Ignatius' forge hammer (SDF part in its own frame).

Hammer local frame: origin = grip centre (inside the right fist), haft along +Z toward the head, head's long axis
along +Y (the hot striking face at +Y, a square pein at -Y), X across.  s6_rig maps +Z onto the measured UAL
fist grip axis (index side) and +Y onto the hand's distal direction (the fist's punching face).
"""
import math
import numpy as np
from jb_lib import (F32, v3, norm, rot_axis, frame_from, smoothstep, Sphere, Ellipsoid, RoundCone, Tube, RBox, Torus,
                    Func, NOISE, NOISE2, NOISE3, smin, smax)
from f_parts import Part

HAFT_R = 0.0200
POMMEL_Z = -0.105
HEAD_Z = 0.90          # head centre along the haft
HEAD_HL = 0.22         # half length along Y
HEAD_HX = 0.100        # half width (X)
HEAD_HZ = 0.095        # half height (Z, along the haft)


def haft_r(z):
    return HAFT_R + 0.004 * np.clip((z - 0.25) / 0.55, 0, 1)


def haft_d(P):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    r = haft_r(z)
    # slightly octagonal
    a = np.arctan2(y, x)
    oct_ = 1.0 + 0.04 * np.cos(8 * a)
    rho = np.sqrt(x * x + y * y) * oct_
    d = rho - r
    d = np.maximum(d, POMMEL_Z + 0.01 - z)
    d = np.maximum(d, z - (HEAD_Z + 0.02))
    return d


def head_d(P):
    q = P - v3(0, 0, HEAD_Z)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    # flare toward the striking face (+Y), taper to the pein (-Y)
    t = np.clip(y / HEAD_HL, -1, 1)
    sx = HEAD_HX * (1 + 0.10 * np.clip(t, 0, 1) ** 3 - 0.30 * np.clip(-t, 0, 1) ** 1.5)
    sz = HEAD_HZ * (1 + 0.10 * np.clip(t, 0, 1) ** 3 - 0.30 * np.clip(-t, 0, 1) ** 1.5)
    # waist in the middle where the haft eye is
    w = 1 - 0.07 * np.exp(-(y / 0.06) ** 2)
    bx = np.abs(x) - sx * w
    bz = np.abs(z) - sz * w
    by = np.abs(y) - HEAD_HL
    ch = 0.018                                                # chamfered edges
    d = np.maximum.reduce([bx, bz, by, (np.abs(x) + np.abs(z) - (sx + sz) * w + ch) * 0.7071,
                           (np.abs(x) + np.abs(y) - (sx * w + HEAD_HL) + ch) * 0.7071,
                           (np.abs(z) + np.abs(y) - (sz * w + HEAD_HL) + ch) * 0.7071])
    # slightly domed striking face
    face = (y - HEAD_HL) + 0.012 * (1 - (x / (sx + 1e-6)) ** 2 - (z / (sz + 1e-6)) ** 2)
    d = np.maximum(d, np.where(y > 0, face, -1))
    return d


def band_prims():
    out = []
    for yy in (-0.072, 0.072):
        c = v3(0, yy, HEAD_Z)
        def d(P, c=c):
            q = P - c
            bx = np.abs(q[..., 0]) - HEAD_HX * 0.97 - 0.011
            bz = np.abs(q[..., 2]) - HEAD_HZ * 0.97 - 0.011
            by = np.abs(q[..., 1]) - 0.016
            return np.maximum.reduce([bx, bz, by]) - 0.003
        out.append(Func(d, c - 0.14, c + 0.14))
    return out


def langet_prims():
    """iron straps running down the haft from the head, riveted."""
    out = []
    for s in (1, -1):
        def d(P, s=s):
            x, y, z = P[..., 0], P[..., 1], P[..., 2]
            r = haft_r(z)
            dd = np.abs(np.sqrt(x * x + y * y) - r - 0.002) - 0.0035
            dd = np.maximum(dd, np.abs(y) - 0.011)
            dd = np.maximum(dd, -s * x)
            dd = np.maximum(dd, (HEAD_Z - 0.32) - z)
            dd = np.maximum(dd, z - (HEAD_Z - 0.05))
            return dd
        out.append(Func(d, (-0.05, -0.05, HEAD_Z - 0.36), (0.05, 0.05, HEAD_Z)))
    return out


def rivets():
    out = []
    for s in (1, -1):
        for zz in (HEAD_Z - 0.29, HEAD_Z - 0.20, HEAD_Z - 0.11):
            r = float(haft_r(np.array(zz)))
            out.append(v3(s * (r + 0.006), 0, zz))
    # head rivets on the bands
    for yy in (-0.072, 0.072):
        for sx in (1, -1):
            for zz in (-0.045, 0.045):
                out.append(v3(sx * (HEAD_HX * 0.97 + 0.014), yy, HEAD_Z + zz))
    return out


def wrap_d(P):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    r = haft_r(z) + 0.0035
    a = np.arctan2(y, x)
    spiral = 0.0015 * np.abs(np.sin(z * 120.0 + a * 1.0))
    d = np.sqrt(x * x + y * y) - r - spiral
    d = np.maximum(d, -0.075 - z)
    d = np.maximum(d, z - 0.215)
    return d


def pommel_d(P):
    q = P - v3(0, 0, POMMEL_Z)
    rho = np.sqrt(q[..., 0] ** 2 + q[..., 1] ** 2)
    r = 0.027 - 0.008 * np.clip(q[..., 2] / 0.035, 0, 1)
    d = np.maximum(rho - r, np.maximum(-q[..., 2] - 0.004, q[..., 2] - 0.035))
    return d - 0.004


class Hammer(Part):
    name = "hammer"
    h = 0.0016
    lo = (-0.14, -0.26, -0.16)
    hi = (0.14, 0.26, HEAD_Z + 0.13)
    tris = 3600
    texel = 1.0
    aset = "hammer"
    mat = "hammer"
    smooth_iters = 1

    def prims(self):
        pr = [("wood", Func(haft_d, self.lo, self.hi), 0.0),
              ("leather", Func(wrap_d, (-0.04, -0.04, -0.09), (0.04, 0.04, 0.23)), 0.002),
              ("iron", Func(pommel_d, (-0.05, -0.05, POMMEL_Z - 0.02), (0.05, 0.05, POMMEL_Z + 0.05)), 0.003),
              ("head", Func(head_d, (-0.13, -0.24, HEAD_Z - 0.13), (0.13, 0.24, HEAD_Z + 0.13)), 0.004)]
        for b in band_prims():
            pr.append(("iron", b, 0.002))
        for l in langet_prims():
            pr.append(("iron", l, 0.002))
        for p in rivets():
            pr.append(("iron", Sphere(p, 0.0062), 0.0015))
        # wedge collar where the haft enters the head (bottom)
        pr.append(("iron", RoundCone(v3(0, 0, HEAD_Z - HEAD_HZ - 0.03), v3(0, 0, HEAD_Z - HEAD_HZ + 0.005), 0.026, 0.031), 0.004))
        return pr

    def build(self, g):
        for grp, pr, k in self.prims():
            g.union(pr, k)
        # cracks in the hot head (shallow grooves)
        def crack(P):
            q = P - v3(0, 0, HEAD_Z)
            n = NOISE.ridged(q * 9.0, 2)
            return 0.93 - n + 0.0 * q[..., 0]
        def cut(P):
            return np.maximum(crack(P) * 0.03, -head_d(P) - 0.0025)
        g.sub(Func(cut, (-0.13, -0.24, HEAD_Z - 0.13), (0.13, 0.24, HEAD_Z + 0.13)), 0.001)

    def masks(self, P, N):
        dg = {}
        for grp, pr, k in self.prims():
            d = pr.d(P)
            dg[grp] = d if grp not in dg else np.minimum(dg[grp], d)
        names = list(dg.keys())
        st = np.stack([dg[n] for n in names], 0)
        win = np.argmin(st, 0)
        m = {n: win == i for i, n in enumerate(names)}
        q = P - v3(0, 0, HEAD_Z)
        n = NOISE.ridged(q * 9.0, 2)
        m["crack"] = m["head"] & (n > 0.90)
        return m

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        grain = 0.0006 * NOISE(P * np.array([300, 300, 8], F32))
        ham = 0.0012 * NOISE.fbm(P * 35.0, 2) - 0.002 * np.clip(NOISE3(P * 12.0) - 0.45, 0, 1)
        wood = m["wood"].astype(F32)
        head = m["head"].astype(F32)
        return V + N * (grain * wood + ham * head)[:, None]

"""SDF sculpt definitions for Foreman Ignatius (modeling pose, UAL1 space before the 1.144 armature scale,
metres, -Y = front, +X = his left).

Each Part:
  name, h (voxel), lo/hi (grid bounds), tris (low-poly budget), texel (relative uv density), aset (texture atlas),
  mat (material), build(g) -> sculpt into an SDFGrid, post(V, N) -> displaced high-poly, masks(P, N) -> paint regions
"""
import math
import numpy as np
from jb_lib import (F32, v3, norm, rot_axis, frame_from, smoothstep, Sphere, Ellipsoid, RoundCone, Tube,
                    RBox, Torus, Func, NOISE, NOISE2, NOISE3, smin, smax)

J = None


def setJ(j):
    global J
    J = j


def H(b):
    return np.array(J[b]["head"], F32)


def T(b):
    return np.array(J[b]["tail"], F32)


def X(P):
    return P[..., 0]


def Y(P):
    return P[..., 1]


def Z(P):
    return P[..., 2]


class Part:
    name = "part"
    h = 0.004
    lo = (-1, -1, 0)
    hi = (1, 1, 2)
    tris = 2000
    texel = 1.0
    smooth_iters = 3
    aset = "body"
    mat = "body"

    def build(self, g):
        pass

    def post(self, V, N):
        return V

    def masks(self, P, N):
        return {}


def seg_t(P, a, b):
    ab = b - a
    t = ((P - a) @ ab) / float(ab @ ab)
    d = np.linalg.norm(P - (a + np.clip(t, 0, 1)[..., None] * ab), axis=-1)
    return t, d


def arm_pts(side):
    return H("upperarm_" + side), H("lowerarm_" + side), H("hand_" + side)


# ============================================================================================ TORSO (body + mail)
def torso_prims():
    """(prim, smooth k) list of the bare body: barrel chest, gut, huge traps and deltoids, bull neck, upper arms."""
    pr = [(Ellipsoid((0, 0.02, 0.975), (0.235, 0.20, 0.17)), 0.0),                    # hips
          (Ellipsoid((0, -0.035, 1.085), (0.255, 0.232, 0.20)), 0.08),                 # gut
          (Ellipsoid((0, -0.055, 1.30), (0.292, 0.245, 0.215)), 0.09),                 # barrel chest
          (Ellipsoid((0, 0.07, 1.33), (0.29, 0.20, 0.225)), 0.08),                     # back
          (Ellipsoid((0, 0.075, 1.45), (0.25, 0.17, 0.13), R=rot_axis((1, 0, 0), -18)), 0.07),   # upper back hump
          (RoundCone((0, 0.025, 1.40), (0, -0.01, 1.585), 0.105, 0.088), 0.06)]          # bull neck
    for s in (1, -1):
        side = "l" if s > 0 else "r"
        sh, el, wr = arm_pts(side)
        pr.append((RoundCone((s * 0.05, 0.06, 1.525), (s * 0.235, 0.05, 1.47), 0.10, 0.12), 0.06))    # traps
        pr.append((Ellipsoid(sh + v3(s * 0.035, -0.005, 0.0), (0.135, 0.13, 0.12), R=rot_axis((0, 1, 0), s * 30)), 0.06))  # deltoid
    pr.append((Ellipsoid((0, -0.13, 1.345), (0.255, 0.13, 0.115)), 0.07))              # broad flat pec slab
    return pr


def upper_arm_prims(side):
    sh, el, wr = arm_pts(side)
    ud = norm(el - sh)
    out = [RoundCone(sh, el, 0.102, 0.083),
           Ellipsoid(sh + (el - sh) * 0.45 + v3(0, -0.02, 0), (0.096, 0.096, 0.13), R=frame_from(ud)[:, [0, 2, 1]]),  # bicep
           Sphere(el + v3(0, 0.03, 0), 0.075)]                                                                     # elbow
    return out


def torso_body_d(P):
    d = None
    for pr, k in torso_prims():
        x = pr.d(P)
        d = x if d is None else smin(d, x, k)
    return d


MAIL_T = 0.011          # chainmail layer thickness over the body


def sleeve_prims(side):
    sh, el, wr = arm_pts(side)
    ud = norm(el - sh)
    return [RoundCone(sh - ud * 0.03, sh + (el - sh) * 0.58, 0.128, 0.112)]


def sleeve_factor(P):
    """1 on the arms, 0 on the torso, soft in between."""
    db = torso_body_d(P)
    da = None
    for side in ("l", "r"):
        for pr in upper_arm_prims(side) + sleeve_prims(side):
            x = pr.d(P)
            da = x if da is None else np.minimum(da, x)
    return smoothstep(-0.035, 0.035, db - da)


def mail_hem_sleeve(P, side):
    """signed: >0 above the sleeve hem (mail), <0 below (bare arm)."""
    sh, el, wr = arm_pts(side)
    t, d = seg_t(P, sh, el)
    ang = np.arctan2(P[..., 1] - sh[1], P[..., 2] - sh[2])
    hem = 0.56 + 0.025 * np.sin(ang * 3 + 1.0) + 0.012 * np.sign(np.sin(ang * 26.0))
    return (hem - t) * float(np.linalg.norm(el - sh))


class Torso(Part):
    name = "torso"
    h = 0.0045
    lo = (-0.58, -0.40, 0.80)
    hi = (0.58, 0.36, 1.66)
    tris = 7600
    texel = 1.0

    def build(self, g):
        for pr, k in torso_prims():
            g.union(pr, k)
        for side in ("l", "r"):
            a, b, c = upper_arm_prims(side)
            g.union(a, 0.07)
            g.union(b, 0.03)
            g.union(c, 0.03)
        # chainmail shirt: whole torso raised (not the neck), short sleeves
        def mail_region(P):
            neck = 1.50 + 0.02 * np.cos(np.arctan2(X(P), -Y(P)))
            r = Z(P) - neck
            for side in ("l", "r"):
                sf = self._arm_mask(P, side)
                r = np.where(sf > 0.5, np.maximum(r, -mail_hem_sleeve(P, side)), r)
            return r
        g.layer(Func(mail_region, (-0.58, -0.40, 0.80), (0.58, 0.36, 1.62)), MAIL_T, 0.003)
        # mail collar standing round the neck base
        def collar(P):
            c = v3(0, 0.02, 1.47)
            q = P - c
            rho = np.sqrt(q[..., 0] ** 2 + (q[..., 1] * 1.08) ** 2)
            d = np.abs(rho - 0.118) - 0.014
            d = np.maximum(d, -q[..., 2] - 0.01)
            d = np.maximum(d, q[..., 2] - 0.065 + 0.02 * (q[..., 1] < 0))
            return d
        g.union(Func(collar, (-0.2, -0.2, 1.42), (0.2, 0.2, 1.56)), 0.01)
        g.apply(lambda f, P: np.maximum(f, 0.86 - Z(P)), (-0.6, -0.5, 0.79), (0.6, 0.5, 0.88))

    def _arm_mask(self, P, side):
        sh, el, wr = arm_pts(side)
        t, d = seg_t(P, sh, el)
        s = 1 if side == "l" else -1
        lateral = s * (X(P) - sh[0] * 0.75)
        return ((t > 0.12) & (lateral > 0)).astype(F32)

    def masks(self, P, N):
        m = {}
        mail = np.ones(P.shape[:-1], bool)
        skin = np.zeros(P.shape[:-1], bool)
        for side in ("l", "r"):
            am = self._arm_mask(P, side) > 0.5
            below = mail_hem_sleeve(P, side) < -0.002
            skin |= am & below
        neck = Z(P) > 1.50 + 0.02 * np.cos(np.arctan2(X(P), -Y(P))) + 0.004
        c = v3(0, 0.02, 1.47)
        q = P - c
        rho = np.sqrt(q[..., 0] ** 2 + (q[..., 1] * 1.08) ** 2)
        collar = (np.abs(rho - 0.118) < 0.02) & (q[..., 2] > -0.015) & (q[..., 2] < 0.07)
        skin |= neck & ~collar
        m["skin"] = skin
        m["collar"] = collar & ~skin
        m["mail"] = mail & ~skin
        m["sleeve"] = (sleeve_factor(P) > 0.5) & m["mail"]
        return m

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        skin = m["skin"].astype(F32)
        lump = 0.004 * NOISE.fbm(P * 5.0, 3)
        # mail sags in soft horizontal folds over the gut, pulled diagonals at the armpits
        fold = 0.004 * np.sin(Z(P) * 70.0 + 2.0 * NOISE(P * 6.0)) * smoothstep(1.2, 1.0, Z(P))
        musc = 0.003 * NOISE2.fbm(P * 14.0, 2)
        disp = (1 - skin) * (lump + fold) + skin * (lump * 0.5 + musc)
        return V + N * disp[:, None]


# ============================================================================================ APRON BIB (tint1)
def bib_region(P):
    """the bib panel on the chest/gut: tapered top, full width at the waist."""
    z = Z(P)
    hw = np.interp(z, [0.95, 1.05, 1.20, 1.36, 1.44], [0.235, 0.235, 0.205, 0.16, 0.15]).astype(F32)
    top = 1.43 + 0.012 * np.cos(X(P) * 18.0)
    return np.maximum.reduce([np.abs(X(P)) - hw, z - top, 0.955 - z, Y(P) + 0.04])


def mail_d(P):
    return torso_body_d(P) - MAIL_T


class Bib(Part):
    name = "bib"
    h = 0.003
    lo = (-0.30, -0.36, 0.93)
    hi = (0.30, -0.02, 1.47)
    tris = 1300
    texel = 1.2
    aset = "gear"
    mat = "apron"
    smooth_iters = 2

    def build(self, g):
        def bib(P):
            d = np.abs(mail_d(P) - 0.0055) - 0.0055
            return np.maximum(d, bib_region(P))
        g.union(Func(bib, self.lo, self.hi))
        # thick rolled edge binding along the top and sides
        def hem(P):
            r = bib_region(P)
            d = np.abs(mail_d(P) - 0.007) - 0.0075
            return np.maximum(d, np.maximum(r, -r - 0.012))
        g.union(Func(hem, self.lo, self.hi), 0.003)
        # big chest pocket with flap, rivets at the corners
        for pr in self.pocket_prims():
            g.layer(pr, 0.004, 0.002)

    def pocket_prims(self):
        c = v3(0.075, -0.32, 1.235)
        n = norm(v3(0.25, -1, 0.15))
        R = frame_from(n, (0, 0, 1))
        return [RBox(c, (0.07, 0.05, 0.06), 0.008, R=R)]

    def masks(self, P, N):
        r = bib_region(P)
        pocket = self.pocket_prims()[0].d(P) < 0.001
        return {"hem": r > -0.012, "pocket": pocket}

    def post(self, V, N):
        P = V
        crease = 0.0025 * NOISE.fbm(P * 7.0, 3) + 0.0012 * NOISE2.fbm(P * 22.0, 2)
        # stiff leather: a few horizontal bends where it folds over the gut
        bend = -0.002 * np.abs(np.sin(Z(P) * 38.0 + 1.5 * NOISE(P * 4.0))) * smoothstep(1.15, 1.02, Z(P))
        return V + N * (crease + bend)[:, None]


# ============================================================================================ HELMET
CC = None          # cranium centre (set in init_head)
HS = 1.10          # head gear scale (fighting-game readability: big head)


def init_head():
    global CC
    CC = H("Head") + v3(0, -0.018, 0.128)


def hq(P):
    return (P - CC) / HS


def hw(q):
    """head-local (q) -> world"""
    return CC + HS * v3(q)


BRIM_Z = 0.083     # hardhat brim plane above CC
MASK_TOP = 0.072


def mask_shell_r(q):
    """distance-ish to the mask outer surface: elliptic cylinder bulging forward + a vertical centre ridge."""
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    ax = 0.140 - 0.012 * np.clip(-z / 0.15, 0, 1)            # narrows to the chin
    ay = 0.176 - 0.02 * np.clip(-z / 0.15, 0, 1) ** 2
    yc = 0.012
    rr = np.sqrt((x / ax) ** 2 + ((y - yc) / ay) ** 2)
    ridge = 0.012 * np.clip(1 - np.abs(x) / 0.06, 0, 1) * (y < 0)
    return (rr - 1.0) * np.minimum(ax, ay) - ridge


def mask_lower_edge(x):
    return -0.150 + 0.065 * (np.abs(x) / 0.13) ** 2


SLITS = []         # (centre q, half-length, half-height, roll deg)


def slit_d(q):
    d = None
    for s in (1, -1):
        c = v3(s * 0.052, -0.17, 0.004)
        R = rot_axis((0, 1, 0), s * 9.0)                     # inner ends lower: a scowl
        qq = (q - c) @ R
        dd = np.maximum(np.abs(qq[..., 0]) - 0.037, np.abs(qq[..., 2]) - 0.0088)
        dd = np.maximum(dd, np.abs(qq[..., 1]) - 0.08)
        d = dd if d is None else np.minimum(d, dd)
    return d


def slit2d_d(q):
    """slit footprint seen from the front (x/z only)."""
    d = None
    for s in (1, -1):
        c = v3(s * 0.052, 0.0, 0.004)
        R = rot_axis((0, 1, 0), s * 9.0)
        qq = (q * v3(1, 0, 1) - c) @ R
        dd = np.maximum(np.abs(qq[..., 0]) - 0.037, np.abs(qq[..., 2]) - 0.0088)
        d = dd if d is None else np.minimum(d, dd)
    return d


def mask_d(P):
    q = hq(P)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    s = mask_shell_r(q)
    d = np.abs(s + 0.005) - 0.0065
    d = np.maximum(d, y - 0.03)                              # front + wraps to behind the ears
    d = np.maximum(d, z - MASK_TOP)
    d = np.maximum(d, mask_lower_edge(x) - z)
    d = np.maximum(d, -slit_d(q))                            # the eye slits cut through
    # breathing vents: short horizontal grooves on the snout (not through)
    return d


def vent_d(q):
    d = None
    for i, zz in enumerate((-0.072, -0.090, -0.108)):
        w = 0.030 - 0.004 * i
        dd = np.maximum(np.abs(q[..., 0]) - w, np.abs(q[..., 2] - zz) - 0.0038)
        d = dd if d is None else np.minimum(d, dd)
    return d


def mask_rivets():
    pts = []
    for i in range(13):
        t = -1 + 2 * i / 12
        x = t * 0.125
        z = mask_lower_edge(np.array(x)) + 0.014
        pts.append((x, z))
    for i in range(7):
        x = -0.12 + 0.24 * i / 6
        pts.append((x, MASK_TOP - 0.012))
    out = []
    for x, z in pts:
        x = float(x); z = float(z)
        q = v3(x, -0.3, z)
        # project onto the shell along +y
        ys = np.linspace(-0.25, 0.05, 300).astype(F32)
        Q = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], 1)
        s = mask_shell_r(Q)
        k = int(np.argmin(np.abs(s + 0.0)))
        if ys[k] > 0.02:
            continue
        out.append(v3(x, ys[k], z))
    return out


class Mask(Part):
    """welding mask: iron face plate with glowing slits, hinge bolts, rivets, vents; the dark face behind it."""
    name = "mask"
    h = 0.0016
    tris = 2000
    texel = 1.7

    def __init__(self):
        init_head()
        self.lo = tuple(hw((-0.20, -0.25, -0.20)))
        self.hi = tuple(hw((0.20, 0.10, 0.11)))

    def build(self, g):
        g.union(Func(mask_d, self.lo, self.hi))
        # face block behind the plate (seen through the slits; painted glowing there)
        g.union(Func(lambda P: np.maximum(mask_shell_r(hq(P)) + 0.026, np.maximum(-hq(P)[..., 2] - 0.12, hq(P)[..., 2] - 0.06)),
                     self.lo, self.hi), 0.0)
        g.sub(Func(lambda P: np.maximum(vent_d(hq(P)), mask_shell_r(hq(P)) + 0.002), self.lo, self.hi), 0.002)
        # rim bead around the plate edge
        def rim(P):
            q = hq(P)
            s = mask_shell_r(q)
            e1 = np.abs(q[..., 2] - mask_lower_edge(q[..., 0])) - 0.006
            e2 = np.abs(q[..., 2] - MASK_TOP) - 0.006
            dd = np.maximum(np.abs(s + 0.004) - 0.0095, np.minimum(e1, e2))
            dd = np.maximum(dd, q[..., 1] - 0.03)
            dd = np.maximum(dd, mask_lower_edge(q[..., 0]) - 0.003 - q[..., 2])
            dd = np.maximum(dd, q[..., 2] - MASK_TOP - 0.003)
            return dd
        g.union(Func(rim, self.lo, self.hi), 0.002)
        for p in mask_rivets():
            g.union(Sphere(hw(p + v3(0, -0.006, 0)), 0.0065 * HS), 0.002)
        # hinge bolts at the temples
        for s in (1, -1):
            c = hw((s * 0.142, -0.012, 0.035))
            R = frame_from(v3(s, 0, 0), (0, 0, 1))
            g.union(Torus(c, 0.018 * HS, 0.0065 * HS, R=R[:, [0, 2, 1]]), 0.003)
            g.union(Ellipsoid(c + v3(s * 0.004, 0, 0), (0.012 * HS, 0.016 * HS, 0.016 * HS)), 0.003)
        # brow guard: a thick bar over the slits
        def brow(P):
            q = hq(P)
            s = mask_shell_r(q)
            dd = np.maximum(np.abs(s + 0.012) - 0.011, np.abs(q[..., 2] - 0.034) - 0.010 + 0.004 * np.abs(q[..., 0]) / 0.1)
            return np.maximum(dd, np.maximum(q[..., 1] + 0.05, np.abs(q[..., 0]) - 0.115))
        g.union(Func(brow, self.lo, self.hi), 0.004)

    def masks(self, P, N):
        q = hq(P)
        s = mask_shell_r(q)
        inner = (s > -0.016) & (s < 0.004) | (s < -0.02)
        face = s < -0.021                                    # the dark face block behind the plate
        sd = slit_d(q)
        sd2 = slit2d_d(q)
        glow = (face & (sd < 0.012)) | ((sd2 < 0.0035) & (s < 0.004))
        slit_wall = (sd < 0.0025) & ~face
        bolt = np.zeros(P.shape[:-1], bool)
        for sx in (1, -1):
            bolt |= np.linalg.norm(q - v3(sx * 0.142, -0.012, 0.035), axis=-1) < 0.03
        riv = np.zeros(P.shape[:-1], bool)
        for p in mask_rivets():
            riv |= np.linalg.norm(q - (p + v3(0, -0.006, 0)), axis=-1) < 0.009
        return {"face": face, "glow": glow, "slit_wall": slit_wall, "bolt": bolt, "rivet": riv,
                "vent": (vent_d(q) < 0.002) & ~face, "sd": sd, "q": q}

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        hammered = 0.0011 * NOISE.fbm(P * 45.0, 2) + 0.0007 * (NOISE2.ridged(P * 30.0, 2) - 0.6)
        dent = -0.003 * np.clip(NOISE3(P * 9.0) - 0.45, 0, 1)
        k = (~m["face"] & ~m["rivet"] & ~m["bolt"]).astype(F32)
        return V + N * ((hammered + dent) * k)[:, None]


# ---- hardhat (tint2) + leather neck flap
def hat_d(P):
    q = hq(P)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    dome_e = Ellipsoid((0, 0.012, BRIM_Z - 0.030), (0.146, 0.166, 0.172))
    dome = dome_e.d(q)
    dome = np.maximum(dome, BRIM_Z - 0.006 - z)
    # crest ridge front->back + two side ribs
    crest = np.maximum(np.abs(x) - 0.017, dome - 0.013)
    crest = np.maximum(crest, BRIM_Z + 0.03 - z)
    for sx in (1, -1):
        rib = np.maximum(np.abs(x - sx * 0.07) - 0.008, dome - 0.006)
        crest = np.minimum(crest, np.maximum(rib, BRIM_Z + 0.045 - z))
    d = smin(dome, crest, 0.012)
    # brim: thin plate, peak at the front
    th = np.arctan2(x, -y)                                    # 0 = front
    rho_base = 0.150 * 0.170 / np.sqrt((0.170 * np.sin(th)) ** 2 + (0.150 * np.cos(th)) ** 2)
    ext = 0.040 + 0.055 * np.clip(np.cos(th), 0, 1) ** 1.5 + 0.012 * np.clip(-np.cos(th), 0, 1)
    rho = np.sqrt(x * x + (y - 0.012) ** 2)
    zb = BRIM_Z - 0.004 - 0.07 * np.clip((rho - rho_base) / 0.09, 0, 1) ** 2 * (0.4 + 0.6 * np.clip(-np.cos(th), 0, 1)) \
        + 0.012 * np.clip((rho - rho_base) / 0.09, 0, 1) * np.clip(np.cos(th), 0, 1)
    brim = np.maximum(np.abs(z - zb) - 0.0065, rho - (rho_base + ext))
    brim = np.maximum(brim, rho_base - 0.02 - rho)
    lip = np.sqrt((rho - (rho_base + ext - 0.006)) ** 2 + (z - zb) ** 2) - 0.0095
    brim = np.minimum(brim, np.maximum(lip, rho_base - rho))
    d = smin(d, brim, 0.008)
    return d


def hat_band_d(P):
    q = hq(P)
    rho = np.sqrt(q[..., 0] ** 2 + (q[..., 1] - 0.012) ** 2)
    return np.maximum(np.abs(q[..., 2] - (BRIM_Z + 0.013)) - 0.012, rho - 0.165)


class Hardhat(Part):
    name = "hardhat"
    h = 0.0022
    tris = 1500
    texel = 1.3
    mat = "trim"

    def __init__(self):
        init_head()
        self.lo = tuple(hw((-0.25, -0.30, BRIM_Z - 0.10)))
        self.hi = tuple(hw((0.25, 0.25, 0.28)))

    def build(self, g):
        g.union(Func(hat_d, self.lo, self.hi))
        g.layer(Func(hat_band_d, self.lo, self.hi), 0.004, 0.002)
        # forge badge on the front of the crown
        c = hw((0, -0.150, BRIM_Z + 0.06))
        g.union(Ellipsoid(c, (0.026 * HS, 0.012 * HS, 0.024 * HS)), 0.006)

    def masks(self, P, N):
        q = hq(P)
        band = hat_band_d(P) < 0.0006
        badge = np.linalg.norm(q - v3(0, -0.15, BRIM_Z + 0.06), axis=-1) < 0.032
        under = (N[..., 2] < -0.35)
        return {"band": band, "badge": badge, "under": under, "q": q}

    def post(self, V, N):
        P = V
        dents = -0.0022 * np.clip(NOISE.fbm(P * 11.0, 2) - 0.25, 0, 1) - 0.0015 * np.clip(NOISE2(P * 30) - 0.5, 0, 1)
        return V + N * dents[:, None]


def flap_d(P):
    q = hq(P)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    th = np.arctan2(x, -y)                                   # 0 front
    t = np.clip((BRIM_Z - 0.01 - z) / 0.26, 0, 1.2)
    r = 0.152 + 0.06 * t ** 1.4 + 0.006 * np.sin(th * 9 + 1.5 * NOISE(np.stack([np.cos(th) * 2, np.sin(th) * 2, z * 3], -1)))
    rho = np.sqrt((x / 1.0) ** 2 + ((y - 0.02) / 1.10) ** 2)
    d = (np.abs(rho - r) - 0.0065) * 0.9
    d = np.maximum(d, z - (BRIM_Z - 0.004))
    hem = -0.21 - 0.02 * np.cos(th) ** 2 - 0.012 * np.abs(np.sin(th * 5.0)) - 0.01 * NOISE(np.stack([np.cos(th) * 3, np.sin(th) * 3, th * 0 + 0.3], -1))
    d = np.maximum(d, hem - z)
    d = np.maximum(d, 1.42 - np.abs(th) + 0.25 * np.clip(-z - 0.08, 0, 1))   # sides + back (front = mask)
    return d


class Flap(Part):
    name = "flap"
    h = 0.0025
    tris = 1300
    texel = 1.0

    def __init__(self):
        init_head()
        self.lo = tuple(hw((-0.30, -0.20, -0.30)))
        self.hi = tuple(hw((0.30, 0.32, BRIM_Z + 0.01)))

    def build(self, g):
        g.union(Func(flap_d, self.lo, self.hi))
        # rivets fixing the flap under the brim
        for i in range(9):
            th = 1.15 + (2 * math.pi - 2.3) * i / 8
            p = hw((0.158 * math.sin(th) * 1.0, 0.02 - 0.158 * 1.1 * math.cos(th), BRIM_Z - 0.03))
            g.union(Sphere(p, 0.0055 * HS), 0.002)

    def masks(self, P, N):
        q = hq(P)
        return {"q": q}

    def post(self, V, N):
        P = V
        crease = 0.0025 * NOISE.fbm(P * np.array([14, 14, 4], F32), 2) + 0.0015 * NOISE2.fbm(P * 25.0, 2)
        return V + N * crease[:, None]


# ============================================================================================ BEARD (braided)
def chest_front_y(x, z):
    """y of the front of the apron bib / mail at (x, z) (approx)."""
    ys = np.linspace(-0.45, 0.0, 200).astype(F32)
    P = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], 1)
    d = mail_d(P)
    inside = np.nonzero(d < 0)[0]
    if len(inside) == 0:
        return -0.05
    return float(ys[inside[0]]) - 0.011


def braid_path(x0, z0, z1, sway, n=9):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        z = z0 + (z1 - z0) * t
        x = x0 + sway * math.sin(t * 2.2) * t
        y = chest_front_y(x, z) - 0.03 - 0.008 * t
        pts.append(v3(x, y, z))
    return pts


def braid_prims(pts, r0, r1, twists=5.0, tag="braid"):
    """three interleaved strands along a path (+ the core), radius tapering r0 -> r1."""
    pts = [v3(p) for p in pts]
    # resample densely
    seg = []
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + float(np.linalg.norm(b - a)))
    Ltot = L[-1]
    M = 46
    out = []
    samples = []
    for i in range(M + 1):
        s = Ltot * i / M
        k = min(int(np.searchsorted(L, s, side='right')) - 1, len(pts) - 2)
        u = (s - L[k]) / max(L[k + 1] - L[k], 1e-6)
        p = pts[k] * (1 - u) + pts[k + 1] * u
        tng = norm(pts[k + 1] - pts[k])
        samples.append((p, tng, i / M))
    for strand in range(3):
        sp, sr = [], []
        for p, tng, t in samples:
            r = r0 + (r1 - r0) * t
            side = norm(np.cross(tng, v3(0, 1, 0)))
            if np.linalg.norm(side) < 1e-3:
                side = v3(1, 0, 0)
            fwd = norm(np.cross(side, tng))
            ph = 2 * math.pi * (t * twists + strand / 3.0)
            off = side * (math.sin(ph) * r * 0.62) + fwd * (math.sin(2 * ph) * r * 0.32)
            sp.append(p + off)
            sr.append(r * 0.62)
        out.append((tag, Tube(sp, sr), 0.004))
    return out, samples


BRAIDS = None


def beard_braids():
    """[(path pts, r0, r1, rings at t)] -- one long centre braid + two side braids."""
    global BRAIDS
    if BRAIDS is None:
        init_head()
        c = CC
        BRAIDS = [
            (braid_path(0.0, c[2] - 0.225 * HS, 1.05, 0.012, 10), 0.044, 0.022, (0.36, 0.62)),
            (braid_path(0.10, c[2] - 0.20 * HS, 1.25, 0.03, 8), 0.032, 0.018, (0.55,)),
            (braid_path(-0.10, c[2] - 0.20 * HS, 1.25, -0.03, 8), 0.032, 0.018, (0.55,)),
        ]
    return BRAIDS


def beard_all():
    """(group, prim, k) for the beard part, + ember tuft centres."""
    init_head()
    c = CC
    pr = []
    # bushy mass under the mask: jaw-wide, flattened onto the chest
    pr.append(("bush", Ellipsoid(hw((0, -0.150, -0.180)), (0.13, 0.085, 0.075)), 0.0))
    for s in (1, -1):
        pr.append(("bush", Ellipsoid(hw((s * 0.10, -0.115, -0.150)), (0.058, 0.066, 0.08), R=rot_axis((0, 1, 0), -s * 15)), 0.03))
        pr.append(("bush", Ellipsoid(hw((s * 0.055, -0.19, -0.215)), (0.068, 0.056, 0.058)), 0.03))
    tips = []
    for pts, r0, r1, rings in beard_braids():
        b, samples = braid_prims(pts, r0, r1, twists=len(pts) * 0.55)
        pr += b
        p0 = pts[0]
        pr.append(("bush", Sphere(p0 + v3(0, 0.0, 0.01), r0 * 1.15), 0.02))
        for t in rings:
            k = int(t * (len(samples) - 1))
            p, tng, _ = samples[k]
            R = frame_from(tng)
            pr.append(("ring", Torus(p, r0 + (r1 - r0) * t + 0.006, 0.0068, R=R[:, [0, 2, 1]]), 0.002))
            pr.append(("ring", RoundCone(p - tng * 0.012, p + tng * 0.012, r0 + (r1 - r0) * t + 0.004, r0 + (r1 - r0) * t + 0.004), 0.002))
        # frayed ember tuft at the tip
        p, tng, _ = samples[-1]
        tip = p + tng * 0.03
        tips.append((tip, tng, r1))
        for j in range(5):
            a = 2 * math.pi * j / 5
            side = norm(np.cross(tng, v3(0, 1, 0)))
            fwd = norm(np.cross(side, tng))
            q = tip + tng * (0.012 + 0.012 * (j % 2)) + (side * math.cos(a) + fwd * math.sin(a)) * r1 * 0.9
            pr.append(("tuft", RoundCone(p, q, r1 * 0.7, 0.003), 0.008))
    return pr, tips


class Beard(Part):
    name = "beard"
    h = 0.0018
    tris = 2800
    texel = 1.3

    def __init__(self):
        init_head()
        self.lo = (-0.22, -0.40, 0.96)
        self.hi = (0.22, -0.02, float(CC[2]) - 0.08)

    def build(self, g):
        prs, tips = beard_all()
        for grp, pr, k in prs:
            g.union(pr, k)
        # don't let the bush poke through the mask: carve the mask volume
        g.sub(Func(lambda P: np.maximum(mask_shell_r(hq(P)) + 0.002, mask_lower_edge(hq(P)[..., 0]) + 0.004 - hq(P)[..., 2]),
                   self.lo, self.hi), 0.006)
        # rest on the bib
        g.sub(Func(lambda P: mail_d(P) - 0.013, self.lo, self.hi), 0.012)

    def masks(self, P, N):
        prs, tips = beard_all()
        dm = {}
        for grp, pr, k in prs:
            d = pr.d(P)
            dm[grp] = d if grp not in dm else np.minimum(dm[grp], d)
        ring = dm["ring"] < np.minimum(dm["braid"], dm["bush"]) + 0.0005
        ember = np.zeros(P.shape[:-1], F32)
        for tip, tng, r in tips:
            dd = np.linalg.norm(P - tip, axis=-1)
            ember = np.maximum(ember, smoothstep(0.12, 0.02, dd))
        return {"ring": ring, "ember": ember, "tuft": dm["tuft"] < dm["braid"] - 0.001}

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        ring = m["ring"].astype(F32)
        q = P * np.array([60.0, 60.0, 8.0], F32)
        strands = 0.0022 * NOISE.fbm(q, 2) + 0.001 * NOISE2(P * np.array([150, 150, 18], F32))
        return V + N * (strands * (1 - ring) + 0.0004 * NOISE3(P * 120) * ring)[:, None]


# ============================================================================================ HANDS
FINGER_R = {"index": (0.0175, 0.0165, 0.0152, 0.0136), "middle": (0.018, 0.0172, 0.016, 0.0142),
            "ring": (0.0172, 0.0162, 0.015, 0.0134), "pinky": (0.0155, 0.0145, 0.0134, 0.0118)}


def hand_frame(s):
    w0 = H("hand_" + s)
    mid = H("middle_01_" + s)
    hd = norm(mid - w0)
    across = norm(H("index_01_" + s) - H("pinky_01_" + s))
    up = norm(np.cross(hd, across)) * (1 if s == "l" else -1)
    return w0, hd, across, up


def hand_prims(side, fat=1.0):
    s = side
    pr = []
    w0, hd, across, up = hand_frame(s)
    R = np.stack([across, hd, up], 1)
    knuck = H("middle_01_" + s)
    plen = float(np.linalg.norm(knuck - w0))
    pr.append(("skin", Ellipsoid(w0 + hd * plen * 0.55 + up * 0.002, (0.058 * fat, plen * 0.62, 0.030 * fat), R=R), 0.0))
    pr.append(("skin", RoundCone(w0 - hd * 0.06, w0 + hd * 0.02, 0.046 * fat, 0.05 * fat), 0.03))
    for f, rads in FINGER_R.items():
        pts = [H("%s_0%d_%s" % (f, i, s)) for i in (1, 2, 3)] + [H("%s_04_leaf_%s" % (f, s))]
        tip = pts[-1] + norm(pts[-1] - pts[-2]) * 0.004
        pts = pts[:-1] + [tip]
        pts[0] = pts[0] - hd * 0.012
        rr = [r * fat for r in rads]
        pr.append(("skin", Tube(pts, rr), 0.006))
        pr.append(("skin", Sphere(pts[0] + up * 0.008, rr[0] * 1.15), 0.01))
        for kj in (1, 2):
            pr.append(("skin", Sphere(pts[kj] + up * 0.004, rr[kj] * 1.06), 0.006))
        pr.append(("nail", Ellipsoid(tip - norm(tip - pts[2]) * 0.009 + up * rr[3] * 0.62,
                                     (rr[3] * 0.78, 0.012, 0.0045), R=frame_from(norm(tip - pts[2]), up)), 0.002))
    tp = [H("thumb_0%d_%s" % (i, s)) for i in (1, 2, 3)] + [H("thumb_04_leaf_" + s)]
    ttip = tp[-1] + norm(tp[-1] - tp[-2]) * 0.006
    pr.append(("skin", Tube(tp[:-1] + [ttip], [0.027 * fat, 0.024 * fat, 0.021 * fat, 0.0185 * fat]), 0.015))
    return pr


def forearm_prims(side, scale=1.0):
    sh, el, wr = arm_pts(side)
    fv = wr - el
    fd = norm(fv)
    return [(RoundCone(el, wr - fd * 0.005, 0.085 * scale, 0.058 * scale), 0.0),
            (Ellipsoid(el + fv * 0.30 + v3(0, 0.0, 0.0), (0.088 * scale, 0.088 * scale, 0.11), R=frame_from(fd)[:, [0, 2, 1]]), 0.05)]


class ArmR(Part):
    """right forearm + hand: bare soot-black skin, leather wrist wrap."""
    name = "arm_r"
    h = 0.0017
    tris = 2100
    texel = 1.4

    def __init__(self):
        c = H("lowerarm_r") * 0.5 + H("hand_r") * 0.5
        self.lo = tuple(c - 0.30)
        self.hi = tuple(c + 0.30)

    def wrap_prims(self):
        sh, el, wr = arm_pts("r")
        fd = norm(wr - el)
        return [RoundCone(wr - fd * 0.075, wr + fd * 0.008, 0.067, 0.064)]

    def build(self, g):
        for pr, k in forearm_prims("r"):
            g.union(pr, k)
        for grp, pr, k in hand_prims("r", 1.05):
            g.union(pr, k)
        for pr in self.wrap_prims():
            g.union(pr, 0.006)
        # elbow blend (hidden in the upper-arm mesh)
        sh, el, wr = arm_pts("r")
        g.apply(lambda f, P: np.maximum(f, -((P - el) @ norm(wr - el)) - 0.03), self.lo, self.hi)

    def masks(self, P, N):
        dn = None
        for grp, pr, k in hand_prims("r", 1.05):
            if grp == "nail":
                d = pr.d(P)
                dn = d if dn is None else np.minimum(dn, d)
        wrap = self.wrap_prims()[0].d(P) < 0.0012
        return {"nail": dn < 0.0012, "wrap": wrap}

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        sh, el, wr = arm_pts("r")
        fd = norm(wr - el)
        veins = 0.0013 * np.clip(NOISE2(P * 28.0 + np.outer(P @ fd, fd) * 18.0) * 2 - 0.9, 0, 1)
        crag = 0.0009 * (NOISE.ridged(P * 40.0, 3) - 0.6)
        wrapf = m["wrap"].astype(F32)
        t = (P - wr) @ fd
        band = -0.0018 * np.abs(np.sin(t * 160.0 + np.arctan2(P[:, 1] - wr[1], P[:, 2] - wr[2]) * 1.0))
        return V + N * ((veins + crag) * (1 - wrapf) + band * wrapf)[:, None]


# ============================================================================================ GAUNTLET (left)
def gaunt_vambrace(P):
    sh, el, wr = arm_pts("l")
    fd = norm(wr - el)
    t = (P - el) @ fd
    L = float(np.linalg.norm(wr - el))
    tt = t / L
    c = el + np.clip(t, -0.1, L + 0.1)[..., None] * fd
    rad = np.linalg.norm(P - c, axis=-1)
    r = 0.098 - 0.03 * np.clip(tt, 0, 1) + 0.03 * smoothstep(0.18, -0.06, tt)      # flared cuff at the elbow
    d = np.abs(rad - r) - 0.009
    d = np.maximum(d, -0.06 * L - t)
    d = np.maximum(d, t - (L + 0.008))
    return d


def gaunt_bands():
    sh, el, wr = arm_pts("l")
    fd = norm(wr - el)
    L = float(np.linalg.norm(wr - el))
    out = []
    for tt in (0.04, 0.42, 0.86):
        c = el + fd * (tt * L)
        r = 0.098 - 0.03 * tt + 0.03 * float(smoothstep(0.18, -0.06, np.array(tt))) + 0.01
        out.append((c, fd, r))
    return out


class Gauntlet(Part):
    """riveted iron gauntlet on the left forearm and hand (over a bare elbow)."""
    name = "gauntlet"
    h = 0.0017
    tris = 3200
    texel = 1.3

    def __init__(self):
        c = H("lowerarm_l") * 0.5 + H("hand_l") * 0.5
        self.lo = tuple(c - 0.32)
        self.hi = tuple(c + 0.32)

    def plates(self):
        """(group, prim, k)"""
        s = "l"
        pr = []
        w0, hd, across, up = hand_frame(s)
        R = np.stack([across, hd, up], 1)
        knuck = H("middle_01_" + s)
        plen = float(np.linalg.norm(knuck - w0))
        # hand under-glove (leather) = a fat hand
        for grp, p, k in hand_prims(s, 1.1):
            pr.append(("glove", p, k))
        # back-of-hand plate (domed), knuckle ridge
        pr.append(("iron", Ellipsoid(w0 + hd * plen * 0.5 + up * 0.026, (0.066, plen * 0.62, 0.022), R=R), 0.006))
        pr.append(("iron", RoundCone(H("index_01_l") + up * 0.022 + across * 0.01, H("pinky_01_l") + up * 0.020 - across * 0.008, 0.019, 0.017), 0.006))
        # finger lames: one shell per phalanx
        for f in ("index", "middle", "ring", "pinky"):
            pts = [H("%s_0%d_%s" % (f, i, s)) for i in (1, 2, 3)] + [H("%s_04_leaf_%s" % (f, s))]
            rads = FINGER_R[f]
            for i in range(3):
                a, b = pts[i], pts[i + 1]
                dirn = norm(b - a)
                c = a + (b - a) * 0.5 + up * rads[i] * 0.55
                Rf = frame_from(dirn, up)
                pr.append(("iron", Ellipsoid(c, (rads[i] * 1.32, float(np.linalg.norm(b - a)) * 0.55, rads[i] * 0.95), R=Rf), 0.002))
        tp = [H("thumb_0%d_%s" % (i, s)) for i in (1, 2, 3)] + [H("thumb_04_leaf_" + s)]
        for i in range(3):
            a, b = tp[i], tp[i + 1]
            pr.append(("iron", RoundCone(a, b, 0.029 - 0.003 * i, 0.026 - 0.003 * i), 0.002))
        # vambrace + bands + elbow couter
        pr.append(("iron", Func(gaunt_vambrace, self.lo, self.hi), 0.0))
        for c, fd, r in gaunt_bands():
            Rb = frame_from(fd)
            pr.append(("band", Torus(c, r, 0.0085, R=Rb[:, [0, 2, 1]]), 0.002))
        sh, el, wr = arm_pts("l")
        # cuff/wrist flare
        fd = norm(wr - el)
        pr.append(("iron", Torus(wr - fd * 0.01, 0.07, 0.012, R=frame_from(fd)[:, [0, 2, 1]]), 0.004))
        # spike-less heavy knuckle studs
        for f in ("index", "middle", "ring", "pinky"):
            pr.append(("rivet", Sphere(H("%s_01_l" % f) + up * 0.04, 0.0105), 0.003))
        return pr

    def rivets(self):
        out = []
        for c, fd, r in gaunt_bands():
            Rb = frame_from(fd)
            for k in range(10):
                a = 2 * math.pi * k / 10
                p = c + (Rb[:, 0] * math.cos(a) + Rb[:, 2] * math.sin(a)) * (r + 0.008)
                out.append(p)
        return out

    def build(self, g):
        for grp, pr, k in self.plates():
            g.union(pr, k)
        for p in self.rivets():
            g.union(Sphere(p, 0.0062), 0.0015)
        # forearm inside (hidden) + bare elbow above the cuff
        for pr, k in forearm_prims("l", 0.98):
            g.union(pr, k)
        sh, el, wr = arm_pts("l")
        g.apply(lambda f, P: np.maximum(f, -((P - el) @ norm(wr - el)) - 0.05), self.lo, self.hi)

    def masks(self, P, N):
        dg = {}
        for grp, pr, k in self.plates():
            d = pr.d(P)
            dg[grp] = d if grp not in dg else np.minimum(dg[grp], d)
        dr = None
        for p in self.rivets():
            d = np.linalg.norm(P - p, axis=-1) - 0.0062
            dr = d if dr is None else np.minimum(dr, d)
        dg["rivet"] = np.minimum(dg["rivet"], dr)
        names = list(dg.keys())
        st = np.stack([dg[n] for n in names], 0)
        win = np.argmin(st, 0)
        m = {n: win == i for i, n in enumerate(names)}
        sh, el, wr = arm_pts("l")
        t = (P - el) @ norm(wr - el)
        m["skin"] = (t < -0.045 * float(np.linalg.norm(wr - el))) & (st.min(0) > 0.004)
        return m

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        iron = (m["iron"] | m["band"]).astype(F32)
        ham = 0.0008 * NOISE.fbm(P * 50.0, 2) - 0.0018 * np.clip(NOISE2(P * 14.0) - 0.4, 0, 1)
        glove = m["glove"].astype(F32)
        return V + N * (ham * iron + 0.0006 * NOISE3.fbm(P * 90, 2) * glove)[:, None]


# ============================================================================================ CHAINS over the left shoulder
def chain_path():
    """polyline the chain follows: a sash from the right hip (front) up over the left shoulder, down the back to the
    right hip, + two loops round the left upper arm, + a hanging tail with a hook at the right hip."""
    sh, el, wr = arm_pts("l")
    pts_front = []
    for t in np.linspace(0, 1, 12):
        # from right hip front (-0.21, ., 1.0) to the left shoulder top (0.20, -0.05, 1.56)
        x = -0.215 + (0.20 + 0.215) * t
        z = 1.00 + (1.56 - 1.00) * t
        if z > 1.50:
            y = -0.10 + 0.05 * (z - 1.50) / 0.06
        else:
            y = chest_front_y(x, z) - 0.034 - 0.01 * math.sin(t * math.pi)        # over bib + beard gap
        pts_front.append(v3(x, y, z))
    top = [v3(0.215, -0.02, 1.60), v3(0.215, 0.10, 1.575)]
    pts_back = []
    for t in np.linspace(0, 1, 10)[1:]:
        x = 0.21 - (0.21 + 0.22) * t
        z = 1.53 - (1.53 - 1.00) * t
        ys = np.linspace(0.45, 0.0, 200).astype(F32)
        P = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], 1)
        d = mail_d(P)
        ins = np.nonzero(d < 0)[0]
        y = (float(ys[ins[0]]) if len(ins) else 0.2) + 0.030
        pts_back.append(v3(x, y, z))
    return pts_front + top + pts_back


def arm_loops():
    sh, el, wr = arm_pts("l")
    ud = norm(el - sh)
    R = frame_from(ud)
    loops = []
    for i, (tt, rr, tilt) in enumerate(((0.30, 0.142, 8), (0.46, 0.136, -10))):
        c = sh + (el - sh) * tt
        pts = []
        for k in range(22):
            a = 2 * math.pi * k / 22
            off = (R[:, 0] * math.cos(a) + R[:, 2] * math.sin(a)) * rr
            off = off + ud * (math.sin(a + 0.5) * math.radians(tilt) * rr)
            pts.append(c + off)
        loops.append(pts)
    return loops


def hang_path():
    """loose end hanging at the right hip front with a hook."""
    start = v3(-0.215, chest_front_y(-0.215, 1.00) - 0.034, 1.00)
    pts = [start]
    for k in range(1, 7):
        t = k / 6
        pts.append(start + v3(-0.03 * t, -0.03 * math.sin(t * math.pi) - 0.01 * t, -0.27 * t))
    return pts


def links_along(pts, link_len=0.066, closed=False, phase=0):
    """chain link tori along a polyline: alternating link plane orientation."""
    pts = [v3(p) for p in pts]
    if closed:
        pts = pts + [pts[0]]
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + float(np.linalg.norm(b - a)))
    n = max(2, int(L[-1] / (link_len * 0.78)))
    out = []
    for i in range(n):
        s = L[-1] * (i + 0.5) / n
        k = min(int(np.searchsorted(L, s, side='right')) - 1, len(pts) - 2)
        u = (s - L[k]) / max(L[k + 1] - L[k], 1e-6)
        p = pts[k] * (1 - u) + pts[k + 1] * u
        tng = norm(pts[k + 1] - pts[k])
        out.append((p, tng, (i + phase) % 2))
    return out


def link_prim(p, tng, alt, size=0.066, wire=0.0115):
    # elongated link: torus stretched along the chain (use two tori + straight bars via RoundCones)
    side = norm(np.cross(tng, v3(0, 0, 1))) if abs(tng[2]) < 0.9 else norm(np.cross(tng, v3(1, 0, 0)))
    nrm = norm(np.cross(tng, side))
    if alt:
        side, nrm = nrm, side
    hl = size * 0.5 - wire
    hw = size * 0.30 - wire
    a = p - tng * (hl - hw)
    b = p + tng * (hl - hw)
    def d(P, a=a, b=b, side=side, nrm=nrm, hw=hw):
        q = P - p
        u = q @ tng
        v = q @ side
        w = q @ nrm
        uu = np.maximum(np.abs(u) - (hl - hw), 0)
        rho = np.sqrt(uu * uu + v * v)
        return np.sqrt((rho - hw) ** 2 + w * w) - wire
    lo = p - size * 0.6
    hi = p + size * 0.6
    return Func(d, lo, hi)


class Chains(Part):
    name = "chains"
    h = 0.0018
    tris = 3600
    texel = 0.9

    def __init__(self):
        self.lo = (-0.36, -0.44, 0.55)
        self.hi = (0.50, 0.40, 1.66)

    def all_links(self):
        out = links_along(chain_path())
        for lp in arm_loops():
            out += links_along(lp, closed=True)
        out += links_along(hang_path(), phase=1)
        return out

    def hook_prims(self):
        end = hang_path()[-1]
        pr = []
        # shackle ring + J hook
        pr.append(Torus(end + v3(0, 0, -0.03), 0.03, 0.011, R=rot_axis((1, 0, 0), 90)))
        pts = [end + v3(0, 0, -0.06), end + v3(0, -0.005, -0.16), end + v3(0.0, -0.025, -0.23), end + v3(0.0, -0.075, -0.25),
               end + v3(0.0, -0.12, -0.22), end + v3(0.0, -0.128, -0.17)]
        pr.append(Tube(pts, [0.022, 0.024, 0.022, 0.019, 0.015, 0.008]))
        return pr

    def build(self, g):
        for p, tng, alt in self.all_links():
            g.union(link_prim(p, tng, alt), 0.0)
        for pr in self.hook_prims():
            g.union(pr, 0.004)

    def masks(self, P, N):
        dh = None
        for pr in self.hook_prims():
            d = pr.d(P)
            dh = d if dh is None else np.minimum(dh, d)
        return {"hook": dh < 0.002}

    def post(self, V, N):
        P = V
        return V + N * (0.0006 * NOISE.fbm(P * 90.0, 2) - 0.0008 * np.clip(NOISE2(P * 40) - 0.5, 0, 1))[:, None]


# ============================================================================================ BELT + apron straps
BELT_Z = 1.0


def belt_d(P):
    q = P - v3(0, 0.0, BELT_Z)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    ax, ay = 0.262, 0.248
    yc = -0.012
    rr = np.sqrt((x / ax) ** 2 + ((y - yc) / ay) ** 2)
    d = (rr - 1.0) * min(ax, ay)
    d = np.maximum(np.abs(d) - 0.012, np.abs(z + 0.012 * (y < 0) * np.clip(-y / 0.25, 0, 1)) - 0.034)
    return d


class Belt(Part):
    name = "belt"
    h = 0.0018
    tris = 1500
    texel = 1.0

    lo = (-0.32, -0.32, 0.90)
    hi = (0.32, 0.30, 1.08)

    def buckle_c(self):
        return v3(0, -0.262, BELT_Z - 0.01)

    def prims(self):
        c = self.buckle_c()
        pr = [("leather", Func(belt_d, self.lo, self.hi), 0.0)]
        # big iron buckle: rounded frame + prong
        def frame(P):
            q = P - c
            b = np.maximum(np.abs(q[..., 0]) - 0.058, np.abs(q[..., 2]) - 0.046)
            inner = np.maximum(np.abs(q[..., 0]) - 0.040, np.abs(q[..., 2]) - 0.028)
            d2 = np.maximum(b, -inner)
            return np.maximum(d2, np.abs(q[..., 1] + 0.006) - 0.008) - 0.002
        pr.append(("iron", Func(frame, c - 0.08, c + 0.08), 0.0))
        pr.append(("iron", RoundCone(c + v3(0, -0.012, 0.0), c + v3(0.038, -0.012, 0.0), 0.006, 0.005), 0.002))
        # tool loops: a pair of tongs hanging at the left hip
        hip = v3(0.24, -0.08, BELT_Z - 0.01)
        pr.append(("iron", Torus(hip + v3(0.012, 0, -0.035), 0.02, 0.006, R=frame_from(v3(1, 0.3, 0))[:, [0, 2, 1]]), 0.0))
        for s in (1, -1):
            a = hip + v3(0.02, s * 0.012, -0.05)
            pr.append(("iron", Tube([a, a + v3(0.012, s * 0.004, -0.14), a + v3(0.02, s * 0.01, -0.26), a + v3(0.012, s * 0.03, -0.33)],
                                    [0.0075, 0.0078, 0.0075, 0.009]), 0.003))
        pr.append(("iron", Sphere(hip + v3(0.032, 0, -0.19), 0.013), 0.003))
        return pr

    def build(self, g):
        for grp, pr, k in self.prims():
            g.union(pr, k)

    def masks(self, P, N):
        dg = {}
        for grp, pr, k in self.prims():
            d = pr.d(P)
            dg[grp] = d if grp not in dg else np.minimum(dg[grp], d)
        return {"iron": dg["iron"] < dg["leather"]}

    def post(self, V, N):
        P = V
        return V + N * (0.0007 * NOISE.fbm(P * 70.0, 2))[:, None]


class Straps(Part):
    """apron neck strap (behind the beard, round the bull neck) + waist ties (tint2)."""
    name = "straps"
    h = 0.0016
    tris = 900
    texel = 1.0
    mat = "trim"

    lo = (-0.30, -0.36, 0.95)
    hi = (0.30, 0.30, 1.60)

    def prims(self):
        pr = []
        # neck strap: from the bib's top corners up and round the back of the neck
        for s in (1, -1):
            a = v3(s * 0.145, chest_front_y(s * 0.145, 1.42) + 0.002, 1.425)
            b = v3(s * 0.13, -0.10, 1.53)
            c = v3(s * 0.11, 0.02, 1.58)
            d = v3(s * 0.05, 0.11, 1.555)
            e = v3(0.0, 0.125, 1.545)
            pr.append(Tube([a, b, c, d, e], [0.010, 0.010, 0.010, 0.010, 0.010]))
        return pr

    def build(self, g):
        for pr in self.prims():
            g.union(pr, 0.004)
        # flatten the round tubes into straps by intersecting with a slab around the body
        g.apply(lambda f, P: np.maximum(f, -(torso_body_d(P) - 0.004)), self.lo, self.hi)

    def post(self, V, N):
        return V + N * (0.0005 * NOISE.fbm(V * 80.0, 2))[:, None]


# ============================================================================================ SKIRT: mail skirt + apron front
def mskirt_axes(z):
    t = np.clip((0.96 - z) / 0.38, 0, 1.3)
    ax = 0.272 + 0.07 * t
    ay = 0.235 + 0.035 * t
    yc = 0.02 + 0.01 * t
    return ax, ay, yc, t


def mskirt_hem(th):
    return 0.60 + 0.02 * np.cos(th) + 0.005 * np.abs(np.sin(th * 34.0)) + 0.01 * NOISE(np.stack([np.cos(th) * 2, np.sin(th) * 2, th * 0 + 0.5], -1))


def mskirt_d(P):
    x, y, z = X(P), Y(P), Z(P)
    ax, ay, yc, t = mskirt_axes(z)
    qx, qy = x, y - yc
    th = np.arctan2(qx, -qy)
    phi = np.arctan2(qy, qx)
    re = ax * ay / np.sqrt((ay * np.cos(phi)) ** 2 + (ax * np.sin(phi)) ** 2)
    fold = (0.002 + 0.012 * t) * np.sin(th * 8.0 + 1.2 * NOISE2(np.stack([np.cos(th) * 1.5, np.sin(th) * 1.5, z * 2.0], -1)))
    rho = np.sqrt(qx * qx + qy * qy)
    d = (np.abs(rho - (re + fold)) - 0.007) * 0.92
    d = np.maximum(d, z - 1.0)
    d = np.maximum(d, mskirt_hem(th) - z)
    # slits front and back (front hidden by the apron) so the legs can stride
    w = 0.008 + 0.06 * np.clip(t, 0, 1)
    d = np.maximum(d, w - np.abs(th) * re)
    d = np.maximum(d, w - np.abs(np.pi - np.abs(th)) * re)
    return d


APRON_CY = 0.10
APRON_R0 = 0.378


def apron_d(P):
    x, y, z = X(P), Y(P), Z(P)
    rho = np.sqrt(x * x + (y - APRON_CY) ** 2)
    sway = 0.03 * np.clip((0.98 - z) / 0.6, 0, 1) ** 1.3
    th = np.arctan2(x, -(y - APRON_CY))
    wav = 0.006 * np.sin(th * 7.0 + 1.0) * np.clip((0.98 - z) / 0.6, 0, 1)
    d = np.abs(rho - (APRON_R0 + sway + wav)) - 0.0065
    hw = 0.235 + 0.04 * np.clip((0.98 - z) / 0.6, 0, 1)
    d = np.maximum(d, np.abs(x) - hw)
    bottom = 0.46 + 0.03 * (np.abs(x) / 0.25) ** 2 + 0.012 * NOISE(np.stack([x * 9, z * 0 + 1.1, z * 0], -1)) \
        + 0.045 * np.clip(np.sin(x * 23.0 + 1.0) - 0.75, 0, 1)                   # burnt bite out of the hem
    d = np.maximum(d, bottom - z)
    d = np.maximum(d, z - 0.99)
    d = np.maximum(d, y - APRON_CY + 0.05)
    return d


def apron_holes():
    """burnt-through holes in the lower apron (x, z, r)."""
    return [(0.13, 0.64, 0.016), (-0.09, 0.545, 0.012), (0.04, 0.78, 0.009)]


class ApronSkirt(Part):
    name = "apron"
    h = 0.003
    lo = (-0.32, -0.38, 0.34)
    hi = (0.32, -0.10, 1.00)
    tris = 1700
    texel = 1.0
    aset = "gear"
    mat = "apron"
    smooth_iters = 2

    def build(self, g):
        g.union(Func(apron_d, self.lo, self.hi))
        for x, z, r in apron_holes():
            g.sub(Func(lambda P, x=x, z=z, r=r: np.sqrt((X(P) - x) ** 2 + (Z(P) - z) ** 2)
                       - r * (1 + 0.3 * NOISE(P * 90.0)), (x - 0.05, -0.4, z - 0.05), (x + 0.05, -0.1, z + 0.05)), 0.002)
        # stitched hem binding
        def hem(P):
            d0 = apron_d(P)
            x, y, z = X(P), Y(P), Z(P)
            hw = 0.235 + 0.04 * np.clip((0.98 - z) / 0.6, 0, 1)
            edge = np.minimum(hw - np.abs(x), z - 0.46 - 0.03 * (np.abs(x) / 0.25) ** 2)
            return np.maximum(d0 - 0.0018, edge - 0.013)
        g.union(Func(hem, self.lo, self.hi), 0.002)

    def masks(self, P, N):
        x, z = X(P), Z(P)
        hw = 0.235 + 0.04 * np.clip((0.98 - z) / 0.6, 0, 1)
        edge = np.minimum(hw - np.abs(x), z - 0.46 - 0.03 * (np.abs(x) / 0.25) ** 2)
        holes = np.zeros(P.shape[:-1], F32)
        for hx, hz, r in apron_holes():
            dd = np.sqrt((x - hx) ** 2 + (z - hz) ** 2) - r
            holes = np.maximum(holes, smoothstep(0.03, 0.0, dd))
        inner = Y(P) - APRON_CY > -np.sqrt(np.maximum(0, (APRON_R0 + 0.0) ** 2 - x * x)) + 0.002
        return {"edge": edge < 0.014, "holes": holes, "inner": inner}

    def post(self, V, N):
        P = V
        crease = 0.003 * NOISE.fbm(P * np.array([5, 5, 2.5], F32), 3) + 0.0012 * NOISE2.fbm(P * 20.0, 2)
        return V + N * crease[:, None]


class MailSkirt(Part):
    name = "mskirt"
    h = 0.0032
    lo = (-0.40, -0.36, 0.55)
    hi = (0.40, 0.38, 1.02)
    tris = 2400
    texel = 0.9
    aset = "gear"
    mat = "gear"
    smooth_iters = 2

    def build(self, g):
        g.union(Func(mskirt_d, self.lo, self.hi))

    def post(self, V, N):
        P = V
        return V + N * (0.003 * NOISE.fbm(P * 7.0, 2))[:, None]


# ============================================================================================ LEGS / BOOTS
def leg_prims(side):
    s = side
    sx = 1 if s == "l" else -1
    hip, knee, ankle = H("thigh_" + s), H("calf_" + s), H("foot_" + s)
    x = float(ankle[0])
    pr = []
    pr.append(("trousers", RoundCone(hip + v3(0, 0, 0.02), knee, 0.135, 0.098), 0.0))
    pr.append(("trousers", RoundCone(knee, ankle + v3(0, 0, 0.16), 0.098, 0.088), 0.04))
    pr.append(("trousers", Ellipsoid(knee + (ankle - knee) * 0.22 + v3(0, 0.02, 0), (0.092, 0.092, 0.12)), 0.04))   # calf
    # knee guard (leather, strapped)
    kc = knee + v3(sx * 0.005, -0.075, 0.01)
    pr.append(("knee", Ellipsoid(kc, (0.075, 0.045, 0.085), R=rot_axis((1, 0, 0), 8)), 0.012))
    # boot: shaft + gaiter, foot box, steel toe cap, thick sole
    pr.append(("boot", RoundCone(ankle + v3(0, 0.0, -0.01), ankle + v3(0, 0.005, 0.20), 0.088, 0.096), 0.0))
    pr.append(("boot", Torus(ankle + v3(0, 0.005, 0.205), 0.094, 0.015), 0.008))
    fb = RBox(v3(x, -0.045, 0.08), (0.084, 0.14, 0.07), 0.055)
    tc = Ellipsoid(v3(x + sx * 0.006, -0.205, 0.072), (0.092, 0.11, 0.074))
    pr.append(("boot", fb, 0.04))
    pr.append(("toe", Ellipsoid(v3(x + sx * 0.006, -0.212, 0.078), (0.094, 0.104, 0.07)), 0.01))
    pr.append(("boot", tc, 0.04))

    def sole(P, fb=fb, tc=tc):
        d = np.minimum(fb.d(P), tc.d(P)) - 0.012
        return np.maximum(d, Z(P) - 0.038)
    pr.append(("sole", Func(sole, v3(x - 0.13, -0.36, -0.01), v3(x + 0.13, 0.15, 0.06)), 0.003))
    pr.append(("sole", RBox(v3(x, 0.05, 0.035), (0.078, 0.055, 0.035), 0.012), 0.004))
    return pr


def strap_prims(side):
    s = side
    hip, knee, ankle = H("thigh_" + s), H("calf_" + s), H("foot_" + s)
    x = float(ankle[0])
    out = [Torus(v3(x, 0.006, 0.17), 0.097, 0.009, R=rot_axis((1, 0, 0), -4)),
           Torus(v3(x, 0.004, 0.25), 0.099, 0.009),
           Torus(v3(x, -0.03, 0.115), 0.084, 0.0095, R=rot_axis((1, 0, 0), 58))]
    kc = knee + v3(0, -0.02, 0.0)
    out.append(Torus(kc + v3(0, 0.0, 0.05), 0.104, 0.008, R=rot_axis((1, 0, 0), -6)))
    out.append(Torus(kc + v3(0, 0.0, -0.045), 0.098, 0.008, R=rot_axis((1, 0, 0), 6)))
    return out


class Legs(Part):
    name = "legs"
    h = 0.003
    lo = (-0.34, -0.37, -0.01)
    hi = (0.34, 0.22, 0.98)
    tris = 4200
    texel = 1.0
    aset = "gear"
    mat = "gear"

    def build(self, g):
        for side in ("l", "r"):
            for grp, pr, k in leg_prims(side):
                g.union(pr, k)
            for pr in strap_prims(side):
                g.union(pr, 0.003)
        g.apply(lambda f, P: np.maximum(f, -Z(P)), (-0.4, -0.4, -0.02), (0.4, 0.25, 0.01))

    def masks(self, P, N):
        dg = {}
        for side in ("l", "r"):
            for grp, pr, k in leg_prims(side):
                d = pr.d(P)
                dg[grp] = d if grp not in dg else np.minimum(dg[grp], d)
        ds = None
        for side in ("l", "r"):
            for pr in strap_prims(side):
                d = pr.d(P)
                ds = d if ds is None else np.minimum(ds, d)
        strap = ds < 0.0012
        sole = (dg["sole"] < np.minimum(dg["boot"], dg["toe"]) - 0.001) | (Z(P) < 0.014)
        toe = (dg["toe"] < dg["boot"] + 0.0015) & ~sole & (Z(P) > 0.02)
        knee = (dg["knee"] < dg["trousers"] + 0.002) & ~strap
        trous = (dg["trousers"] < np.minimum(dg["boot"], dg["knee"])) & ~sole & (Z(P) > 0.26) & ~strap
        return {"sole": sole, "trousers": trous, "strap": strap, "toe": toe & ~strap, "knee": knee}

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        cloth = m["trousers"].astype(F32)
        d = cloth * (0.0045 * NOISE.fbm(P * 8.0, 3)) + (1 - cloth) * (0.0014 * NOISE2.fbm(P * 25.0, 2))
        z = P[:, 2]
        crease = -0.0016 * smoothstep(0.07, 0.11, z) * smoothstep(0.22, 0.16, z) * np.abs(np.sin(z * 75 + 2.5 * NOISE(P * 8)))
        bunch = 0.004 * np.sin(z * 55.0 + 2 * NOISE(P * 5)) * smoothstep(0.30, 0.36, z) * smoothstep(0.50, 0.40, z)
        d = d + (1 - cloth) * crease + cloth * bunch
        return V + N * d[:, None]


def all_parts():
    return [Torso(), Bib(), Mask(), Hardhat(), Flap(), Beard(), ArmR(), Gauntlet(), Chains(), Belt(), Straps(),
            ApronSkirt(), MailSkirt(), Legs()]

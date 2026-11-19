"""SDF sculpt definitions for The Landlord (modeling pose, UAL1 space before the ~1.10 armature scale, metres,
-Y = front, +X = his left).  The face is the Quaternius UBC male head (s0b_head.py), everything else is sculpted.

Each Part: name, h, lo/hi, tris, texel, aset (atlas), mat (material), build(g) / mesh_source(), post(V, N), masks(P, N)
"""
import math
import os
import numpy as np
import jb_lib as L
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


_HEAD = None


def head_data():
    global _HEAD
    if _HEAD is None:
        _HEAD = dict(np.load(os.path.join(L.WORK, "ubc_head.npz")))
        V = _HEAD["V"]
        ez = float(_HEAD["eye"][0][2])
        sk = V[V[:, 2] > ez + 0.012]
        c = np.array([0.0, (sk[:, 1].min() + sk[:, 1].max()) * 0.5 + 0.004, ez + 0.012], np.float32)
        q = sk - c
        ax = np.array([np.abs(q[:, 0]).max(), np.abs(q[:, 1]).max(), np.abs(q[:, 2]).max()], np.float32)
        k = float(np.sqrt(((q / ax) ** 2).sum(1)).max())
        _HEAD["cran_c"] = c
        _HEAD["cran_r"] = ax * k
    return _HEAD


# ============================================================================================ SUIT (torso part)
def body_prims():
    """the waistcoat/shirt surface (jacket is a layer on top): slim, V-shaped, square padded shoulders."""
    pr = [(Ellipsoid((0, 0.015, 0.975), (0.162, 0.122, 0.13)), 0.0),
          (Ellipsoid((0, 0.004, 1.10), (0.146, 0.110, 0.13)), 0.08),
          (Ellipsoid((0, -0.004, 1.30), (0.180, 0.118, 0.16)), 0.08),
          (Ellipsoid((0, 0.022, 1.40), (0.198, 0.108, 0.10)), 0.07),
          (RoundCone((0, 0.022, 1.42), (0, 0.004, 1.56), 0.060, 0.052), 0.04)]
    for s in (1, -1):
        side = "l" if s > 0 else "r"
        sh, el, wr = arm_pts(side)
        pr.append((RoundCone((s * 0.06, 0.024, 1.468), (s * 0.228, 0.03, 1.462), 0.05, 0.062), 0.05))   # padded shoulder line
        pr.append((Ellipsoid(sh + v3(s * 0.012, 0.0, 0.004), (0.070, 0.074, 0.068)), 0.04))           # roped sleeve head
    return pr


def sleeve_prims(side):
    sh, el, wr = arm_pts(side)
    fv = wr - el
    return [RoundCone(sh, el, 0.064, 0.056), RoundCone(el, wr - norm(fv) * 0.012, 0.056, 0.047)]


def body_d(P):
    d = None
    for pr, k in body_prims():
        x = pr.d(P)
        d = x if d is None else smin(d, x, k)
    return d


JACKET_T = 0.009
BUTTON_Z = 1.095
HEM_Z = 0.80


def open_w(z):
    """half width of the jacket front opening (V above the button, cutaway below)."""
    up = np.interp(z, [BUTTON_Z, 1.20, 1.32, 1.42, 1.50], [0.0, 0.012, 0.042, 0.068, 0.07])
    dn = 0.004 + 0.14 * np.clip((BUTTON_Z - z) / (BUTTON_Z - HEM_Z), 0, 1) ** 1.6
    return np.where(z >= BUTTON_Z, up, dn).astype(F32)


def lapel_w(z):
    """lapel width beyond the opening edge: peak lapel, widest at the peak (z 1.37)."""
    w = np.interp(z, [BUTTON_Z, 1.15, 1.30, 1.37, 1.395], [0.0, 0.035, 0.066, 0.085, 0.07])
    return w.astype(F32)


GORGE_Z = 1.395


def front_region(P):
    return (Y(P) < 0.0)


def jacket_open_d(P):
    """>0 inside the front opening (vest visible), <0 on the jacket."""
    x, z = X(P), Z(P)
    d = open_w(z) - np.abs(x)
    d = np.where(Y(P) < -0.02, d, -1.0)
    d = np.where(z > 1.50, -1.0, d)
    return d


def lapel_region(P):
    x, z = X(P), Z(P)
    ax = np.abs(x)
    ow = open_w(z)
    inside = (ax > ow) & (ax < ow + lapel_w(z)) & (z > BUTTON_Z) & (z < GORGE_Z + 0.004) & (Y(P) < -0.02)
    return inside


def lapel_d(P):
    x, z = X(P), Z(P)
    ax = np.abs(x)
    ow = open_w(z)
    lw = lapel_w(z)
    d = np.maximum(ow - ax, ax - (ow + lw))
    d = np.maximum(d, BUTTON_Z - z)
    # gorge: top edge slants down to the notch, the peak points up/out
    top = GORGE_Z + 0.03 * np.clip((ax - ow - 0.03) / 0.05, 0, 1) - 0.006
    d = np.maximum(d, z - top)
    d = np.maximum(d, Y(P) + 0.02)
    return d


def vest_open_d(P):
    """>0 inside the waistcoat V-neck (shirt visible)."""
    x, z = X(P), Z(P)
    w = np.interp(z, [1.25, 1.33, 1.42, 1.50], [0.0, 0.026, 0.05, 0.06]).astype(F32)
    d = w - np.abs(x)
    return np.where((Y(P) < -0.02) & (z > 1.25), d, -1.0)


def vest_buttons():
    return [v3(0, 0, z) for z in (1.135, 1.172, 1.209, 1.246)]


def pocket_c():
    return v3(0.105, 0.0, 1.335)


def sleeve_factor(P):
    db = None
    for pr, k in body_prims():
        x = pr.d(P)
        db = x if db is None else np.minimum(db, x)
    da = None
    for side in ("l", "r"):
        for pr in sleeve_prims(side):
            x = pr.d(P)
            da = x if da is None else np.minimum(da, x)
    return smoothstep(-0.03, 0.03, db - da)


def surf_y(x, z, fn=body_d, y0=-0.30, y1=0.0):
    ys = np.linspace(y0, y1, 300).astype(F32)
    Pp = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], 1)
    d = fn(Pp)
    ins = np.nonzero(d < 0)[0]
    return float(ys[ins[0]]) if len(ins) else y1


def skirt_axes(z):
    t = np.clip((1.02 - z) / (1.02 - HEM_Z), 0, 1.2)
    ax = 0.168 + 0.028 * t
    ay = 0.132 + 0.022 * t
    yc = 0.016 + 0.004 * t
    return ax, ay, yc, t


def skirt_d(P):
    """jacket skirt below the waist: smooth flare to the hem, centre back vent, cutaway front."""
    x, y, z = X(P), Y(P), Z(P)
    ax, ay, yc, t = skirt_axes(z)
    qx, qy = x, y - yc
    rr = np.sqrt((qx / ax) ** 2 + (qy / ay) ** 2)
    d = (rr - 1.0) * np.minimum(ax, ay)
    d = np.abs(d + JACKET_T * 0.5) - JACKET_T * 0.5 - 0.001
    d = np.maximum(d, HEM_Z - z)
    d = np.maximum(d, z - 1.06)
    # back vent: a narrow gap from the hem up 18 cm (left panel overlaps a touch)
    vent = np.maximum(0.004 - np.abs(x + 0.003), np.maximum(z - (HEM_Z + 0.18), -qy))
    d = np.maximum(d, -vent * 3)
    return d


class Torso(Part):
    """jacket (body, lapels, collar, sleeves, skirt with vent), waistcoat in the opening, shirt front."""
    name = "torso"
    h = 0.0032
    lo = (-0.46, -0.24, HEM_Z - 0.02)
    hi = (0.46, 0.22, 1.60)
    tris = 9000
    texel = 1.15
    aset = "suit"
    mat = "suit"

    def build(self, g):
        for pr, k in body_prims():
            g.union(pr, k)
        for side in ("l", "r"):
            a, b = sleeve_prims(side)
            g.union(a, 0.045)
            g.union(b, 0.02)
        # jacket layer everywhere except the front opening (+ not on the neck above the collar)
        def jacket_region(P):
            r = -jacket_open_d(P)
            r = np.where(Z(P) > 1.505, -0.0 + (Z(P) - 1.505) * 10, r)
            return -r
        g.layer(Func(jacket_region, self.lo, self.hi), JACKET_T, 0.002)
        # jacket skirt (below the waist)
        g.union(Func(lambda P: np.maximum(skirt_d(P), jacket_skirt_cut(P)), (-0.3, -0.24, HEM_Z - 0.01), (0.3, 0.24, 1.08)), 0.01)
        # lapels: raised, crisp
        g.layer(Func(lapel_d, (-0.2, -0.24, BUTTON_Z - 0.01), (0.2, 0.0, 1.43)), 0.0055, 0.0015)
        # jacket collar: band round the back of the neck, rolled
        def collar(P):
            c = v3(0, 0.026, 1.48)
            q = P - c
            rho = np.sqrt(q[..., 0] ** 2 + (q[..., 1] * 1.1) ** 2)
            d = np.abs(rho - 0.072) - 0.0075
            d = np.maximum(d, np.abs(q[..., 2] - 0.0) - 0.032)
            d = np.maximum(d, -q[..., 1] - 0.03)
            return d
        g.union(Func(collar, (-0.15, -0.1, 1.40), (0.15, 0.15, 1.56)), 0.006)
        # vest buttons + jacket button
        for p in vest_buttons():
            y = surf_y(0.0, float(p[2])) - 0.002
            g.union(Ellipsoid((0, y, p[2]), (0.0062, 0.004, 0.0062)), 0.0015)
        yb = surf_y(0.0, BUTTON_Z) - JACKET_T - 0.002
        g.union(Ellipsoid((0.0, yb, BUTTON_Z), (0.0105, 0.005, 0.0105)), 0.002)
        # breast pocket welt + hip pocket flaps
        pc = pocket_c()
        yp = surf_y(pc[0], pc[2]) - JACKET_T
        Rn = frame_from(norm(v3(0.35, -1, 0.1)), (0, 0, 1))
        g.layer(RBox((pc[0], yp, pc[2]), (0.048, 0.03, 0.009), 0.002, R=Rn), 0.0025, 0.001)
        for s in (1, -1):
            zz = 0.975
            xx = s * 0.125
            ypk = -0.03 - math.sqrt(max(0.0, 1 - (xx / 0.18) ** 2)) * 0.143
            Rf = frame_from(norm(v3(s * 0.55, -1, 0)), (0, 0, 1))
            g.layer(RBox((xx, ypk, zz), (0.062, 0.04, 0.022), 0.003, R=Rf), 0.004, 0.001)
        # sleeve cuff buttons (4 kissing buttons on each sleeve)
        for side in ("l", "r"):
            sh, el, wr = arm_pts(side)
            fd = norm(wr - el)
            s = 1 if side == "l" else -1
            outv = norm(np.cross(fd, v3(0, 0, 1))) * (-s)
            for i in range(4):
                p = wr - fd * (0.03 + 0.016 * i) + outv * 0.0
                c = p + norm(v3(s * 0.2, 0.9, 0.0)) * 0.05
                g.union(Sphere(c, 0.0048), 0.001)
        g.apply(lambda f, P: np.maximum(f, HEM_Z - Z(P)), (-0.5, -0.3, HEM_Z - 0.03), (0.5, 0.3, HEM_Z + 0.01))

    def masks(self, P, N):
        m = {}
        lap = lapel_d(P) < 0.0012
        vest = (jacket_open_d(P) > 0.0) & (Z(P) > BUTTON_Z - 0.01) & ~lap
        shirt = (vest_open_d(P) > 0.0) & vest
        m["lapel"] = lap
        m["vest"] = vest & ~shirt
        m["shirt"] = shirt
        bt = np.zeros(P.shape[:-1], bool)
        for p in vest_buttons():
            bt |= (np.abs(X(P)) < 0.008) & (np.abs(Z(P) - p[2]) < 0.008) & (Y(P) < -0.05)
        bt |= (np.abs(X(P)) < 0.013) & (np.abs(Z(P) - BUTTON_Z) < 0.013) & (Y(P) < -0.1)
        m["button"] = bt
        m["sleeve"] = sleeve_factor(P) > 0.5
        return m

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        # a very good suit: almost no wrinkles; soft drape at the elbows, slight pull lines at the button
        fold = np.zeros(len(P), F32)
        for side in ("l", "r"):
            sh, el, wr = arm_pts(side)
            dd = np.linalg.norm(P - el, axis=1)
            fold += -0.0015 * smoothstep(0.07, 0.02, dd) * np.abs(np.sin(P[:, 2] * 110 + 2 * NOISE(P * 8)))
        b = v3(0, surf_y(0.0, BUTTON_Z) - JACKET_T, BUTTON_Z)
        rb = np.linalg.norm((P - b) * v3(1, 1, 1.6), axis=1)
        ang = np.arctan2(P[:, 2] - b[2], P[:, 0])
        fold += -0.0008 * smoothstep(0.12, 0.03, rb) * np.abs(np.sin(ang * 5.0))
        soft = 0.0006 * NOISE.fbm(P * 9.0, 2)
        return V + N * (fold + soft)[:, None]


def jacket_skirt_cut(P):
    """the cutaway front of the skirt: remove where the opening is (below the button)."""
    x, z = X(P), Z(P)
    return np.where((Y(P) < -0.02) & (z < BUTTON_Z), open_w(z) - np.abs(x), -1.0)


# ============================================================================================ TIE + POCKET SQUARE (tint2)
def tie_path():
    pts = []
    for z in (1.445, 1.42, 1.38, 1.33, 1.28, 1.24):
        y = surf_y(0.0, z) - 0.004
        pts.append(v3(0.0, y, z))
    return pts


class Silk(Part):
    name = "silk"
    h = 0.0012
    lo = (-0.10, -0.24, 1.20)
    hi = (0.20, -0.04, 1.48)
    tris = 1300
    texel = 1.5
    mat = "silk"

    def tie_d(self, P):
        pts = tie_path()
        d = None
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            t, dd = seg_t(P, a, b)
            zz = Z(P)
            w = np.interp(zz, [1.24, 1.40, 1.43], [0.034, 0.024, 0.018]).astype(F32)
            q = P - (a + np.clip(t, 0, 1)[..., None] * (b - a))
            e = np.maximum(np.abs(q[..., 0]) - w, np.abs(q[..., 1]) - 0.003 - 0.002 * (1 - np.abs(q[..., 0]) / 0.04))
            e = np.maximum(e, np.maximum(-t * float(np.linalg.norm(b - a)), (t - 1) * float(np.linalg.norm(b - a))))
            d = e if d is None else np.minimum(d, e)
        return d

    def knot(self):
        y = surf_y(0.0, 1.455) - 0.012
        return v3(0.0, y, 1.452)

    def square_prims(self):
        pc = pocket_c()
        yp = surf_y(pc[0], pc[2]) - JACKET_T - 0.004
        base = v3(pc[0], yp, pc[2] + 0.004)
        out = []
        for i, (dx, h, tilt) in enumerate(((-0.022, 0.036, -14), (0.0, 0.046, 4), (0.022, 0.032, 18))):
            R = rot_axis((0, 1, 0), tilt) @ rot_axis((0, 0, 1), -18)
            c = base + v3(dx, 0.0, h * 0.5)
            out.append(Ellipsoid(c, (0.016, 0.006, h * 0.55), R=R))
        out.append(RBox(base + v3(0, 0, -0.004), (0.045, 0.006, 0.008), 0.003, R=frame_from(norm(v3(0.35, -1, 0.1)), (0, 0, 1))))
        return out

    def build(self, g):
        g.union(Func(self.tie_d, self.lo, self.hi))
        k = self.knot()
        g.union(Ellipsoid(k, (0.021, 0.013, 0.021), R=rot_axis((1, 0, 0), 15)), 0.006)
        g.union(RoundCone(k + v3(0, 0.0, 0.0), k + v3(0, 0.006, -0.03), 0.017, 0.021), 0.006)
        # dimple under the knot
        g.sub(Ellipsoid(k + v3(0, -0.012, -0.036), (0.004, 0.006, 0.008)), 0.003)
        for pr in self.square_prims():
            g.union(pr, 0.004)

    def masks(self, P, N):
        pc = pocket_c()
        sq = (np.abs(X(P) - pc[0]) < 0.06) & (Z(P) > pc[2] - 0.02)
        return {"square": sq & (X(P) > 0.05)}

    def post(self, V, N):
        P = V
        m = self.masks(P, N)
        sq = m["square"].astype(F32)
        return V + N * (0.0008 * NOISE.fbm(P * 60.0, 2) * sq)[:, None]


# ============================================================================================ SHIRT COLLAR (body)
class Collar(Part):
    """crisp white shirt collar: band round the neck + two points over the tie."""
    name = "collar"
    h = 0.0012
    lo = (-0.10, -0.12, 1.39)
    hi = (0.10, 0.10, 1.53)
    tris = 900
    texel = 1.2

    def build(self, g):
        def band(P):
            c = v3(0, 0.012, 1.46)
            q = P - c
            rho = np.sqrt(q[..., 0] ** 2 + (q[..., 1] * 1.08) ** 2)
            r = 0.058 + 0.06 * np.clip(-q[..., 2], 0, 1)
            d = np.abs(rho - r) - 0.0028
            d = np.maximum(d, np.abs(q[..., 2] - 0.006 + 0.012 * (q[..., 1] < 0) * np.clip(-q[..., 1] / 0.06, 0, 1)) - 0.024)
            # gap at the front for the tie knot
            d = np.maximum(d, 0.012 - np.abs(q[..., 0]) - 2.0 * np.clip(q[..., 1] + 0.03, 0, 1))
            return d
        g.union(Func(band, self.lo, self.hi))
        for s in (1, -1):
            a = v3(s * 0.014, -0.062, 1.47)
            b = v3(s * 0.046, surf_y(s * 0.046, 1.405) - 0.004, 1.405)
            c = v3(s * 0.05, -0.04, 1.47)
            def wing(P, a=a, b=b, c=c):
                # triangle plate a-b-c, 2.5 mm thick
                n = norm(np.cross(b - a, c - a))
                dp = np.abs((P - a) @ n) - 0.0025
                e = None
                for p0, p1 in ((a, b), (b, c), (c, a)):
                    ed = norm(p1 - p0)
                    nn = norm(np.cross(n, ed))
                    s_ = (P - p0) @ nn
                    e = s_ if e is None else np.maximum(e, s_)
                cen = (a + b + c) / 3
                sgn = 1.0 if ((cen - a) @ norm(np.cross(n, norm(b - a)))) < 0 else -1.0
                return np.maximum(dp, e * sgn if sgn > 0 else np.maximum(dp, -e))
            g.union(Func(lambda P, a=a, b=b, c=c: tri_plate(P, a, b, c, 0.0026), self.lo, self.hi), 0.003)

    def post(self, V, N):
        return V


def tri_plate(P, a, b, c, th):
    n = norm(np.cross(b - a, c - a))
    d = np.abs((P - a) @ n) - th
    for p0, p1, p2 in ((a, b, c), (b, c, a), (c, a, b)):
        ed = norm(p1 - p0)
        nn = norm(np.cross(n, ed))
        if (p2 - p0) @ nn > 0:
            nn = -nn
        d = np.maximum(d, (P - p0) @ nn)
    return d


# ============================================================================================ HEAD (UBC face), EYES, HAIR
class Head(Part):
    """Quaternius UBC male head (CC0) on the Head joint, x1.06, subdivided; textures re-baked from its own UVs."""
    name = "head"
    tris = 3600
    texel = 2.4
    src_texture = os.path.join(L.UBC_DIR, "..", "Textures", "T_Superhero_Male_Ligh.png")

    def mesh_source(self):
        d = head_data()
        return d["V"], d["F"], d["UV"]

    def masks(self, P, N):
        d = head_data()
        Vb = d["V"][np.unique(d["F"][d["brow"] == 1])]
        from scipy_free_knn import nearest_dist
        return {}

    def post(self, V, N):
        return V


class Eyes(Part):
    """pure black glossy eyeballs; violet static is painted (emissive)."""
    name = "eyes"
    h = 0.0006
    tris = 600
    texel = 1.6

    def __init__(self):
        e = head_data()["eye"]
        c = (e[0][:3] + e[1][:3]) * 0.5
        self.lo = tuple(c - v3(0.07, 0.03, 0.03))
        self.hi = tuple(c + v3(0.07, 0.03, 0.03))

    def build(self, g):
        for e in head_data()["eye"]:
            g.union(Sphere(e[:3], float(e[3]) * 1.02))

    def masks(self, P, N):
        return {}


def hair_d(P):
    d = head_data()
    c, r = d["cran_c"], d["cran_r"]
    q = P - c
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    # slicked back: volume rises at the front, sleek over the crown, tapered nape
    lift = 0.012 * np.exp(-((y + r[1] * 0.75) / 0.05) ** 2) * np.clip(z / r[2] + 0.2, 0, 1)
    grooves = 0.0018 * np.sin(x * 140.0 + 4.0 * NOISE(np.stack([x * 8, y * 3, z * 8], -1))) * np.clip(z / r[2], 0, 1)
    rr = np.sqrt((x / (r[0] + 0.006)) ** 2 + (y / (r[1] + 0.006)) ** 2 + (z / (r[2] + 0.010)) ** 2)
    shell = (rr - 1.0) * float(min(r)) - lift - grooves
    # hairline: forehead (front), temples, sideburns, nape
    th = np.arctan2(x, -y)                                   # 0 = front
    front_line = -0.020 + 0.018 * np.abs(np.sin(th)) ** 2    # z of the hairline relative to c, front
    side_line = -0.045 - 0.02 * np.clip(np.abs(th) - 1.2, 0, 1)
    back_line = -0.080
    hl = np.where(np.abs(th) < 0.9, front_line + 0.012 * np.cos(th * 3.0),
                  np.where(np.abs(th) < 2.2, side_line, back_line))
    # keep ears free
    ear = np.exp(-((np.abs(th) - 1.57) / 0.28) ** 2) * 0.04
    d_ = np.maximum(shell, (hl + ear) - z)
    return d_


class Hair(Part):
    name = "hair"
    h = 0.0013
    tris = 2200
    texel = 1.3
    smooth_iters = 2

    def __init__(self):
        d = head_data()
        c, r = d["cran_c"], d["cran_r"]
        self.lo = tuple(c - r - 0.04)
        self.hi = tuple(c + r + 0.04)

    def build(self, g):
        g.union(Func(hair_d, self.lo, self.hi))

    def post(self, V, N):
        P = V
        return V + N * (0.0004 * NOISE(P * np.array([300, 60, 300], F32)))[:, None]


# ============================================================================================ HANDS + SHIRT CUFFS
FINGER_R = {"index": (0.0102, 0.0094, 0.0087, 0.0079), "middle": (0.0106, 0.0098, 0.009, 0.0081),
            "ring": (0.0100, 0.0092, 0.0085, 0.0077), "pinky": (0.0088, 0.0081, 0.0075, 0.0068)}


def hand_frame(s):
    w0 = H("hand_" + s)
    mid = H("middle_01_" + s)
    hd = norm(mid - w0)
    across = norm(H("index_01_" + s) - H("pinky_01_" + s))
    up = norm(np.cross(hd, across)) * (1 if s == "l" else -1)
    return w0, hd, across, up


def hand_prims(side):
    s = side
    pr = []
    w0, hd, across, up = hand_frame(s)
    R = np.stack([across, hd, up], 1)
    knuck = H("middle_01_" + s)
    plen = float(np.linalg.norm(knuck - w0))
    pr.append(("skin", Ellipsoid(w0 + hd * plen * 0.55 + up * 0.001, (0.040, plen * 0.6, 0.017), R=R), 0.0))
    pr.append(("skin", RoundCone(w0 - hd * 0.05, w0 + hd * 0.02, 0.026, 0.030), 0.02))
    for f, rads in FINGER_R.items():
        pts = [H("%s_0%d_%s" % (f, i, s)) for i in (1, 2, 3)] + [H("%s_04_leaf_%s" % (f, s))]
        tip = pts[-1] + norm(pts[-1] - pts[-2]) * 0.002
        pts = pts[:-1] + [tip]
        pts[0] = pts[0] - hd * 0.01
        pr.append(("skin", Tube(pts, list(rads)), 0.004))
        for kj in (1, 2):
            pr.append(("skin", Sphere(pts[kj] + up * 0.0025, rads[kj] * 1.05), 0.004))
        pr.append(("nail", Ellipsoid(tip - norm(tip - pts[2]) * 0.008 + up * rads[3] * 0.62,
                                     (rads[3] * 0.78, 0.010, 0.003), R=frame_from(norm(tip - pts[2]), up)), 0.0015))
    tp = [H("thumb_0%d_%s" % (i, s)) for i in (1, 2, 3)] + [H("thumb_04_leaf_" + s)]
    ttip = tp[-1] + norm(tp[-1] - tp[-2]) * 0.004
    pr.append(("skin", Tube(tp[:-1] + [ttip], [0.016, 0.0135, 0.0118, 0.0102]), 0.01))
    return pr


class Hand(Part):
    h = 0.0011
    tris = 2000
    texel = 1.5

    def __init__(self, side):
        self.side = side
        self.name = "hand_" + side
        c = H("hand_" + side)
        self.lo = tuple(c - 0.26)
        self.hi = tuple(c + 0.26)

    def cuff(self):
        sh, el, wr = arm_pts(self.side)
        fd = norm(wr - el)
        return RoundCone(wr - fd * 0.06, wr + fd * 0.004, 0.043, 0.043), RoundCone(wr - fd * 0.10, wr - fd * 0.03, 0.036, 0.034)

    def build(self, g):
        for grp, pr, k in hand_prims(self.side):
            g.union(pr, k)
        c1, wrist = self.cuff()
        g.union(wrist, 0.012)
        # shirt cuff: hollow band showing past the sleeve
        sh, el, wr = arm_pts(self.side)
        fd = norm(wr - el)
        g.union(c1, 0.003)
        g.sub(RoundCone(wr - fd * 0.03, wr + fd * 0.02, 0.031, 0.031), 0.002)
        g.union(RoundCone(wr - fd * 0.02, wr + fd * 0.01, 0.027, 0.028), 0.008)          # wrist inside the cuff
        # cufflink
        s = 1 if self.side == "l" else -1
        out = norm(np.cross(fd, v3(0, 0, 1))) * (-s)
        cl = wr - fd * 0.03 + norm(out * 0.3 + v3(0, 0.0, -1)) * 0.0
        w0, hd, across, up = hand_frame(self.side)
        p = wr - fd * 0.028 - up * 0.0
        p = p + norm(across) * (-0.044)
        g.union(RBox(p, (0.0065, 0.0065, 0.004), 0.0015, R=frame_from(norm(across), fd)), 0.001)
        # signet ring on the right ring finger (violet stone)
        if self.side == "r":
            a, b = H("ring_01_r"), H("ring_02_r")
            c = a + (b - a) * 0.45
            dd = norm(b - a)
            g.union(Torus(c, 0.0118, 0.0026, R=frame_from(dd)[:, [0, 2, 1]]), 0.001)
            g.union(Ellipsoid(c + up * 0.012, (0.0065, 0.0065, 0.0035), R=frame_from(up, dd)[:, [0, 2, 1]]), 0.001)
        g.apply(lambda f, P: np.maximum(f, -((P - wr) @ fd) - 0.075), self.lo, self.hi)

    def masks(self, P, N):
        sh, el, wr = arm_pts(self.side)
        fd = norm(wr - el)
        t = (P - wr) @ fd
        cuff = (t < 0.006) & (t > -0.07) & (np.linalg.norm(P - (wr + np.outer(t, fd)), axis=1) > 0.033)
        w0, hd, across, up = hand_frame(self.side)
        p = wr - fd * 0.028 - norm(across) * 0.044
        link = np.linalg.norm(P - p, axis=1) < 0.010
        ring = np.zeros(len(P), bool)
        stone = np.zeros(len(P), bool)
        if self.side == "r":
            a, b = H("ring_01_r"), H("ring_02_r")
            c = a + (b - a) * 0.45
            ring = (np.linalg.norm(P - c, axis=1) < 0.0175)
            stone = np.linalg.norm(P - (c + up * 0.012), axis=1) < 0.0085
        dn = None
        for grp, pr, k in hand_prims(self.side):
            if grp == "nail":
                d = pr.d(P)
                dn = d if dn is None else np.minimum(dn, d)
        return {"cuff": cuff & ~link, "link": link, "ring": ring & ~stone, "stone": stone, "nail": dn < 0.001}

    def post(self, V, N):
        P = V
        return V + N * (0.0003 * NOISE.ridged(P * 120.0, 2))[:, None]


# ============================================================================================ GOLD: pen + watch chain
def chain_pts():
    """double albert: from the vest buttonhole (fob bar) swagging to the left vest pocket."""
    a = v3(0.0, surf_y(0.0, 1.172) - 0.004, 1.172)
    b = v3(0.115, surf_y(0.115, 1.12) - 0.004, 1.12)
    pts = []
    for t in np.linspace(0, 1, 14):
        p = a + (b - a) * t
        p[2] -= 0.045 * math.sin(math.pi * t)
        p[1] = surf_y(float(p[0]), float(p[2])) - 0.005
        pts.append(p)
    return pts


class Gold(Part):
    name = "gold"
    h = 0.0007
    tris = 1600
    texel = 1.0

    lo = (-0.04, -0.20, 1.05)
    hi = (0.16, -0.02, 1.42)

    def pen_prims(self):
        pc = pocket_c()
        yp = surf_y(pc[0] + 0.035, pc[2]) - JACKET_T - 0.002
        base = v3(pc[0] + 0.036, yp + 0.002, pc[2] - 0.01)
        top = base + v3(-0.004, -0.004, 0.072)
        out = [("pen", RoundCone(base, top, 0.0062, 0.0058), 0.0),
               ("pen", Sphere(top + v3(0, 0, 0.002), 0.0058), 0.002),
               ("pen", Torus(base + (top - base) * 0.62, 0.0063, 0.0012, R=frame_from(norm(top - base))[:, [0, 2, 1]]), 0.0005),
               ("pen", RoundCone(top + v3(0, -0.006, -0.004), top + v3(0, -0.0085, -0.05), 0.0018, 0.0016), 0.0008)]
        return out

    def build(self, g):
        for grp, pr, k in self.pen_prims():
            g.union(pr, k)
        pts = chain_pts()
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            n = 4
            for j in range(n):
                c = a + (b - a) * (j + 0.5) / n
                d = norm(b - a)
                R = frame_from(d) if (i * n + j) % 2 else frame_from(d) @ rot_axis((0, 1, 0), 90)
                g.union(Torus(c, 0.0034, 0.0011, R=R[:, [0, 2, 1]]), 0.0)
        # T-bar fob at the buttonhole + a tiny seal fob in the middle
        a = pts[0]
        g.union(RoundCone(a + v3(-0.012, -0.002, 0), a + v3(0.012, -0.002, 0), 0.0022, 0.0022), 0.0005)
        m = pts[7]
        g.union(Ellipsoid(m + v3(0, -0.003, -0.016), (0.006, 0.003, 0.008)), 0.0)
        g.union(RoundCone(m, m + v3(0, -0.002, -0.009), 0.0012, 0.0012), 0.0005)

    def masks(self, P, N):
        dp = None
        for grp, pr, k in self.pen_prims():
            d = pr.d(P)
            dp = d if dp is None else np.minimum(dp, d)
        pc = pocket_c()
        base_z = pc[2] - 0.01
        return {"pen": dp < 0.001, "pen_body": (dp < 0.001) & (Z(P) < base_z + 0.040)}

    def post(self, V, N):
        return V


# ============================================================================================ LEGS: trousers + oxfords
def leg_prims(side):
    s = side
    sx = 1 if s == "l" else -1
    hip, knee, ankle = H("thigh_" + s), H("calf_" + s), H("foot_" + s)
    x = float(ankle[0])
    pr = []
    pr.append(("trousers", RoundCone(hip + v3(0, 0.005, 0.03), knee, 0.092, 0.068), 0.0))
    pr.append(("trousers", RoundCone(knee, ankle + v3(0, 0.0, 0.035), 0.068, 0.060), 0.03))
    # break: a slight fold where the hem meets the shoe
    pr.append(("trousers", Torus(ankle + v3(0, -0.004, 0.05), 0.058, 0.007, R=rot_axis((1, 0, 0), -12)), 0.012))
    # oxford: long sleek last, chisel toe, stacked heel
    fb = RBox(v3(x, -0.04, 0.052), (0.046, 0.115, 0.044), 0.038)
    tc = Ellipsoid(v3(x + sx * 0.004, -0.175, 0.040), (0.047, 0.092, 0.036))
    pr.append(("shoe", fb, 0.03))
    pr.append(("shoe", tc, 0.03))
    pr.append(("shoe", RoundCone(ankle + v3(0, 0.005, -0.02), ankle + v3(0, 0.0, 0.05), 0.043, 0.048), 0.02))

    def sole(P, fb=fb, tc=tc):
        d = np.minimum(fb.d(P), tc.d(P)) - 0.004
        return np.maximum(d, Z(P) - 0.014)
    pr.append(("sole", Func(sole, v3(x - 0.1, -0.30, -0.01), v3(x + 0.1, 0.12, 0.04)), 0.002))
    pr.append(("sole", RBox(v3(x, 0.04, 0.016), (0.040, 0.034, 0.016), 0.006), 0.003))
    return pr


def crease_d(P, side):
    """sharp front/back trouser creases: thin raised ridges along the leg line."""
    hip, knee, ankle = H("thigh_" + side), H("calf_" + side), H("foot_" + side)
    out = None
    for a, b, ra, rb in ((hip + v3(0, 0.005, 0.03), knee, 0.092, 0.068), (knee, ankle + v3(0, 0, 0.035), 0.068, 0.060)):
        t, d = seg_t(P, a, b)
        r = ra + (rb - ra) * np.clip(t, 0, 1)
        c = a + np.clip(t, 0, 1)[..., None] * (b - a)
        q = P - c
        fr = np.abs(q[..., 0]) - 0.0014                                  # front & back creases: x = leg centre
        dd = np.maximum(fr, np.abs(np.sqrt((q ** 2).sum(-1)) - r) - 0.0035)
        dd = np.maximum(dd, np.maximum(-t, t - 1))
        out = dd if out is None else np.minimum(out, dd)
    return out


class Legs(Part):
    name = "legs"
    h = 0.0022
    lo = (-0.26, -0.30, -0.01)
    hi = (0.26, 0.17, 1.04)
    tris = 4200
    texel = 1.0
    aset = "suit"
    mat = "suit"

    def build(self, g):
        for side in ("l", "r"):
            for grp, pr, k in leg_prims(side):
                g.union(pr, k)
            g.union(Func(lambda P, side=side: crease_d(P, side), self.lo, self.hi), 0.004)
        g.apply(lambda f, P: np.maximum(f, -Z(P)), (-0.3, -0.35, -0.02), (0.3, 0.2, 0.01))

    def masks(self, P, N):
        dg = {}
        for side in ("l", "r"):
            for grp, pr, k in leg_prims(side):
                d = pr.d(P)
                dg[grp] = d if grp not in dg else np.minimum(dg[grp], d)
        sole = (dg["sole"] < dg["shoe"] - 0.0008) | (Z(P) < 0.008)
        trous = (dg["trousers"] < dg["shoe"] - 0.001) & ~sole & (Z(P) > 0.07)
        return {"sole": sole, "trousers": trous, "shoe": ~trous & ~sole}

    def post(self, V, N):
        return V + N * (0.0004 * NOISE.fbm(V * 12.0, 2))[:, None]


def all_parts():
    return [Torso(), Silk(), Collar(), Head(), Eyes(), Hair(), Hand("l"), Hand("r"), Gold(), Legs()]

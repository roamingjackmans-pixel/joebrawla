"""Archmagister Tock: SDF sculpt definitions (modeling pose, metres, faces -Y, left = +X, Z up).

Atlas sets / materials:
  body  -> tock_body   : brass-and-walnut automaton (chest, clock, head, beard, arms, hands, legs), gear crown,
                         the two clock hands
  robe  -> tint1_robe  : deep blue academic robe with bell sleeves and standing collar, cap + mortarboard
  trim  -> tint2_trim  : brass trim bands (front edges, hem, cuffs, collar, belt + buckle, board edge), tassel
  staff -> tock_staff  : walnut staff with clock head + pendulum (pendulum on extra bone `staff_pendulum`)

Multi-material parts list their primitives with a material tag (prims()); the painter picks, per texel, the tag
of the nearest primitive.
"""
import math
import numpy as np
import fblib as L
from fblib import (F32, v3, norm, rot_axis, frame_from, smoothstep, Sphere, Ellipsoid, RoundCone, Tube, RBox,
                   Torus, Func, NOISE, NOISE2, NOISE3, smin, smax, H, T, wdist)
from sdfx import (X, Y, Z, SIDES, spline, arclen, taper, twisted, dseg, flow_field, dist_polys, aniso, GridXf, Xf)


# ============================================================================================ extra primitives
class Cog(L.Prim):
    """gear: centre c, local frame R (columns x, y, z; z = axle), outer radius r0, n teeth of height th,
    thickness t, optional hole r_in and spokes."""

    def __init__(self, c, R, r0, n, th, t, r_in=0.0, spokes=0, hub=0.0):
        self.c, self.R = v3(c), np.asarray(R, F32)
        self.r0, self.n, self.th, self.t, self.r_in, self.spokes, self.hub = r0, n, th, t, r_in, spokes, hub
        m = r0 + th + t
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = (P - self.c) @ self.R
        x, y, z = q[..., 0], q[..., 1], q[..., 2]
        rho = np.sqrt(x * x + y * y)
        th = np.arctan2(y, x)
        tooth = np.clip(np.cos(th * self.n) * 2.2, -1, 1) * 0.5 + 0.5
        d = np.maximum((rho - self.r0 - self.th * tooth) * 0.8, np.abs(z) - self.t * 0.5)
        if self.r_in > 0:
            ring = np.maximum(d, self.r_in - rho)
            inner = None
            if self.spokes:
                a = (th % (2 * np.pi / self.spokes)) - np.pi / self.spokes
                sp = np.maximum.reduce([np.abs(rho * np.sin(a)) - self.t * 0.35, rho - self.r_in - 0.003,
                                        np.abs(z) - self.t * 0.35])
                inner = sp
            if self.hub > 0:
                hb = np.maximum(rho - self.hub, np.abs(z) - self.t * 0.6)
                inner = hb if inner is None else np.minimum(inner, hb)
            d = ring if inner is None else np.minimum(ring, inner)
        return d.astype(F32)


class Disc(L.Prim):
    """flat cylinder: centre c, axis n, radius r, half thickness t, edge rounding e."""

    def __init__(self, c, n, r, t, e=0.002):
        self.c, self.R = v3(c), frame_from(n)[:, [0, 2, 1]]
        self.r, self.t, self.e = r, t, e
        m = r + t
        self.bbox = (self.c - m, self.c + m)

    def d(self, P):
        q = (P - self.c) @ self.R
        rho = np.sqrt(q[..., 0] ** 2 + q[..., 1] ** 2)
        dx = rho - (self.r - self.e)
        dz = np.abs(q[..., 2]) - (self.t - self.e)
        return (np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dz, 0) ** 2) + np.minimum(np.maximum(dx, dz), 0) - self.e).astype(F32)


def axis_frame(ax, hint=(0, 0, 1)):
    """columns (x, y, z) with z = ax."""
    return frame_from(ax, hint)[:, [0, 2, 1]]


class Part:
    name = "part"
    atlas = "body"
    h = 0.003
    lo = (-1, -1, 0)
    hi = (1, 1, 2)
    tris = 2000
    texel = 1.0
    smooth_iters = 2

    def prims(self):
        return []          # [(prim, k, mat)]

    def subs(self):
        return []          # [(prim, k)]

    def prims2(self):
        return []          # unions after the subtractions

    def build(self, g):
        for pr, k, m in self.prims():
            g.union(pr, k)
        for pr, k in self.subs():
            g.sub(pr, k)
        for pr, k, m in self.prims2():
            g.union(pr, k)

    def post(self, V, N):
        return V

    def mat_ids(self, P):
        allp = self.prims() + self.prims2()
        if not allp:
            return np.zeros(len(P), np.int32), []
        names = []
        best = np.full(len(P), 9.0, F32)
        mid = np.zeros(len(P), np.int32)
        for pr, k, m in allp:
            lo, hi = pr.bb()
            sel = np.nonzero(np.all((P > lo - 0.02) & (P < hi + 0.02), axis=1))[0]
            if len(sel) == 0:
                continue
            d = pr.d(P[sel])
            if m not in names:
                names.append(m)
            upd = d < best[sel]
            best[sel] = np.where(upd, d, best[sel])
            mid[sel] = np.where(upd, names.index(m), mid[sel])
        return mid, names

    def masks(self, P, N):
        mid, names = self.mat_ids(P)
        return {n: mid == i for i, n in enumerate(names)}

    def flow(self):
        return [np.array([[0, 0, 0], [0, 0, 1]], F32)]

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


# ============================================================================================ CHEST + CLOCK
CLOCK_C = v3(0.0, -0.112, 1.29)
CLOCK_N = norm(v3(0, -1, 0.12))
CLOCK_R = 0.074


def chest_weights(P):
    z, x = P[:, 2], P[:, 0]
    spec = [("pelvis", 0.15, v3(0, 0.03, 0.92), v3(0, 0.03, 1.06)), ("spine_01", 0.13), ("spine_02", 0.13),
            ("spine_03", 0.15), ("neck_01", 0.06), ("Head", 0.05, H("Head"), H("Head") + v3(0, 0, 0.05)),
            ("clavicle_l", 0.08), ("clavicle_r", 0.08), ("upperarm_l", 0.05), ("upperarm_r", 0.05)]
    W = wdist(P, spec, 5.0)
    cage = smoothstep(1.16, 1.22, z) * smoothstep(1.52, 1.46, z)
    t = smoothstep(1.2, 1.4, z)
    for b in list(W):
        W[b] = W[b] * (1 - cage)
    W["spine_03"] = W["spine_03"] + cage * (0.75 + 0.25 * t)
    W["spine_02"] = W["spine_02"] + cage * (0.25 - 0.25 * t)
    for s, sg in SIDES:
        for b in ("clavicle_", "upperarm_"):
            W[b + s] = W[b + s] * (sg * x > 0.02)
    return W


class Chest(Part):
    name = "chest"
    atlas = "body"
    h = 0.0032
    lo = (-0.27, -0.16, 0.86)
    hi = (0.27, 0.16, 1.70)
    tris = 4400
    texel = 0.6

    def prims(self):
        out = []
        out.append((Ellipsoid((0, 0.0, 1.34), (0.132, 0.104, 0.165)), 0.0, "walnut"))                  # barrel
        for z, r in ((1.215, 0.122), (1.445, 0.118)):                                                    # hoops
            out.append((Func(lambda P, z=z, r=r: np.maximum(Ellipsoid((0, 0.0, 1.34), (0.137, 0.109, 0.17)).d(P),
                                                            np.abs(Z(P) - z) - 0.011), (-0.2, -0.2, z - 0.03), (0.2, 0.2, z + 0.03)),
                        0.003, "brass"))
        out.append((RoundCone((0, 0.04, 1.47), (0, 0.022, 1.66), 0.032, 0.026), 0.015, "brass"))          # neck
        out.append((Cog((0, 0.035, 1.528), np.eye(3), 0.052, 14, 0.008, 0.016), 0.006, "brass"))       # collar gear
        for s, sg in SIDES:
            sh = H("upperarm_" + s)
            out.append((RoundCone((sg * 0.03, 0.02, 1.49), sh + v3(-sg * 0.02, 0, 0.0), 0.03, 0.028), 0.02, "brass"))
            out.append((Sphere(sh, 0.044), 0.01, "brass"))
        out.append((RoundCone((0, 0.04, 1.03), (0, 0.03, 1.21), 0.05, 0.06), 0.03, "brass"))              # waist column
        for z in (1.08, 1.13):
            out.append((Cog((0, 0.02, z), np.eye(3), 0.07, 18, 0.007, 0.012), 0.004, "steel"))
        out.append((Ellipsoid((0, 0.025, 0.975), (0.118, 0.088, 0.075)), 0.03, "walnut"))                 # pelvis
        out.append((Disc(CLOCK_C - CLOCK_N * 0.018, CLOCK_N, CLOCK_R + 0.012, 0.009), 0.01, "brass"))   # clock seat (behind the dial)
        return out

    def flow(self):
        return [np.array([[0, 0, 0.9], [0, 0, 1.7]], F32)]

    def post(self, V, N):
        return V
    def weights(self, P):
        return chest_weights(P)


def clock_frame():
    R = axis_frame(CLOCK_N, (0, 0, 1))
    return R          # columns: x (right), y (up on the dial), z (= CLOCK_N, out of the face)


class Clock(Part):
    name = "clock"
    atlas = "body"
    h = 0.0012
    lo = CLOCK_C - 0.1
    hi = CLOCK_C + 0.1
    tris = 1600
    texel = 3.0

    def prims(self):
        n = CLOCK_N
        c = CLOCK_C
        R = clock_frame()
        Rt = np.stack([R[:, 0], R[:, 1], R[:, 2]], 1)
        return [(Disc(c - n * 0.004, n, CLOCK_R + 0.006, 0.006), 0.0, "dial"),
                (Torus(c + n * 0.003, CLOCK_R + 0.004, 0.0085, R=Rt), 0.002, "brass"),
                (Cog(c - n * 0.006, Rt, CLOCK_R + 0.012, 36, 0.006, 0.008), 0.002, "brass"),
                (Disc(c + n * 0.006, n, 0.0085, 0.004), 0.001, "brass")]                   # hub cap

    def weights(self, P):
        return {"spine_03": np.ones(len(P), F32)}


def clock_hand_pts(kind):
    """hand polygon outline in dial coords (u right, v up), pointing up; rotated to its time later."""
    if kind == "hour":
        return 0.044, 0.0042
    return 0.062, 0.0032


class ClockHand(Part):
    atlas = "body"
    h = 0.0006
    tris = 160
    texel = 2.0
    smooth_iters = 1

    def __init__(self, kind):
        self.kind = kind
        self.name = "clock_" + kind
        self.lo = CLOCK_C - 0.08
        self.hi = CLOCK_C + 0.08
        # 10:10 -> hour hand at 305 deg, minute hand at 60 deg (clockwise from 12)
        self.angle = -55.0 if kind == "hour" else 60.0
        self.off = 0.0105 if kind == "hour" else 0.0135

    def build(self, g):
        R = clock_frame()
        ln, w = clock_hand_pts(self.kind)
        a = math.radians(self.angle)
        dirv = R[:, 1] * math.cos(a) + R[:, 0] * math.sin(a)
        side = np.cross(CLOCK_N, dirv)
        c = CLOCK_C + CLOCK_N * self.off
        t = 0.0011

        def fn(P):
            q = P - c
            u = q @ side
            v = q @ dirv
            z = q @ CLOCK_N
            # shaft + spade tip + counterweight tail + ring
            wv = w * (1.0 - 0.55 * np.clip(v / ln, 0, 1))
            shaft = np.maximum.reduce([np.abs(u) - wv, v - ln * 0.82, -v - ln * 0.22])
            tip = np.maximum(np.abs(u) * 1.6 + (v - ln * 0.8) - ln * 0.2, ln * 0.62 - v)
            ring = np.abs(np.sqrt(u * u + (v - ln * 0.5) ** 2) - w * 1.5) - w * 0.35
            tail = np.sqrt(u * u + (v + ln * 0.2) ** 2) - w * 1.6
            hub = np.sqrt(u * u + v * v) - w * 2.0
            d2 = np.minimum.reduce([shaft, tip, ring, tail, hub])
            return np.maximum(d2, np.abs(z) - t)
        g.union(Func(fn, c - ln - 0.01, c + ln + 0.01))

    def masks(self, P, N):
        return {"steel": np.ones(len(P), bool)}

    def weights(self, P):
        return {"spine_03": np.ones(len(P), F32)}


# ============================================================================================ HEAD
EYES = [v3(s * 0.032, -0.09, 1.703) for s in (1, -1)]          # [left (monocle), right]
MONO_C = v3(0.033, -0.106, 1.703)


class Head(Part):
    name = "head"
    atlas = "body"
    h = 0.0016
    lo = (-0.12, -0.17, 1.55)
    hi = (0.12, 0.12, 1.82)
    tris = 4200
    texel = 1.5

    def prims(self):
        out = [(Ellipsoid((0, 0.008, 1.70), (0.084, 0.094, 0.09)), 0.0, "brass"),                       # cranium
               (Ellipsoid((0, -0.046, 1.668), (0.066, 0.058, 0.086)), 0.03, "walnut"),                  # face mask
               (Ellipsoid((0, -0.058, 1.605), (0.034, 0.04, 0.034)), 0.025, "walnut"),                  # chin
               (RoundCone((0, -0.097, 1.716), (0, -0.146, 1.672), 0.0125, 0.0065), 0.012, "walnut")]   # nose
        for s, sg in SIDES:
            out.append((RoundCone((sg * 0.054, -0.083, 1.73), (sg * 0.006, -0.099, 1.724), 0.0125, 0.011), 0.012, "walnut"))  # brow
            out.append((Ellipsoid((sg * 0.048, -0.079, 1.674), (0.022, 0.02, 0.017)), 0.015, "walnut"))                      # cheek
            out.append((Cog((sg * 0.084, 0.006, 1.682), axis_frame(v3(sg, 0, 0), (0, 0, 1)), 0.03, 10, 0.006, 0.011), 0.004, "brass"))
            out.append((Disc((sg * 0.092, 0.006, 1.682), v3(sg, 0, 0), 0.011, 0.006), 0.002, "steel"))
        # rivet band where face meets cranium
        out.append((Func(lambda P: np.maximum(Ellipsoid((0, 0.008, 1.70), (0.087, 0.097, 0.093)).d(P), np.abs(Z(P) - 1.745) - 0.006),
                         (-0.1, -0.11, 1.73), (0.1, 0.11, 1.76)), 0.002, "brass"))
        return out

    def subs(self):
        return [(Sphere(e, 0.0165), 0.004) for e in EYES] + \
               [(RBox((0, -0.098, 1.628), (0.026, 0.02, 0.0022), 0.0015), 0.002)]          # mouth slit

    def prims2(self):
        R = axis_frame(v3(0, -1, 0), (0, 0, 1))
        return [(Sphere(EYES[0] + v3(0, 0.002, 0), 0.0118), 0.003, "glow"),
                (Sphere(EYES[1] + v3(0, 0.002, 0), 0.0105), 0.003, "eye"),
                (Torus(MONO_C, 0.021, 0.0036, R=R), 0.002, "brass"),
                (Disc(MONO_C + v3(0, 0.001, 0), v3(0, -1, 0), 0.0195, 0.0012), 0.0, "lens")]

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


# ============================================================================================ BEARD (brass wire)
def beard_locks():
    rng = np.random.default_rng(4)
    out = []
    n = 15
    for i in range(n):
        a = math.radians(-78 + 156 * i / (n - 1))
        p0 = v3(0.064 * math.sin(a), -0.024 - 0.07 * math.cos(a), 1.662 - 0.05 * math.cos(a))
        side = abs(math.sin(a))
        p3 = v3(0.3 * p0[0] + rng.normal() * 0.006, -0.11 + 0.035 * side + rng.normal() * 0.006,
                1.405 + 0.12 * side ** 1.5 + rng.normal() * 0.01)
        p1 = p0 + v3(0.15 * p0[0], -0.03, -0.055)
        p2 = p1 * 0.45 + p3 * 0.55 + v3(rng.normal() * 0.008, -0.022, 0)
        r0 = 0.0115 - 0.003 * side
        out.append(([p0, p1, p2, p3], r0, 0.0025))
    for s, sg in SIDES:                                                   # mustache
        out.append(([v3(sg * 0.006, -0.124, 1.648), v3(sg * 0.03, -0.12, 1.638), v3(sg * 0.056, -0.105, 1.622),
                     v3(sg * 0.07, -0.092, 1.6), v3(sg * 0.079, -0.087, 1.612)], 0.0085, 0.0025))
        for j in range(3):                                                # brows
            b0 = v3(sg * (0.016 + 0.017 * j), -0.104 + 0.004 * j, 1.735)
            out.append(([b0, b0 + v3(sg * 0.014, 0.004, 0.012), b0 + v3(sg * 0.026, 0.012, 0.016)], 0.0055, 0.0018))
    return [(spline(p, 4), r0, r1) for p, r0, r1 in out]


class Beard(Part):
    name = "beard"
    atlas = "body"
    h = 0.0014
    lo = (-0.11, -0.17, 1.36)
    hi = (0.11, 0.0, 1.78)
    tris = 3200
    texel = 3.0

    def build(self, g):
        for p, r0, r1 in beard_locks():
            g.union(Tube(p, taper(p, r0, r1, 1.2)), 0.004)

    def flow(self):
        return [p for p, r0, r1 in beard_locks()]

    def post(self, V, N):
        M = flow_field(V, self.flow(), 0.006)
        s = NOISE.ridged(aniso(V, M, 20.0, 700.0), 2)
        return V + N * (0.0008 * (s - 0.5))[:, None]

    def masks(self, P, N):
        return {"wire": np.ones(len(P), bool)}

    def weights(self, P):
        t = smoothstep(1.63, 1.42, P[:, 2]) * (P[:, 2] < 1.72)
        return {"Head": 1 - 0.55 * t, "neck_01": 0.3 * t, "spine_03": 0.25 * t}


# ============================================================================================ ARMS + HANDS
FING = ("index", "middle", "ring", "pinky")


def finger_chain(f, side):
    return [H("%s_01_%s" % (f, side)), H("%s_02_%s" % (f, side)), H("%s_03_%s" % (f, side)),
            H("%s_04_leaf_%s" % (f, side)), T("%s_04_leaf_%s" % (f, side))]


class Arm(Part):
    atlas = "body"
    h = 0.003
    tris = 1300
    texel = 0.45

    def __init__(self, side):
        self.side, self.s = side, (1.0 if side == "l" else -1.0)
        self.name = "arm_" + side
        S, E, W = H("upperarm_" + side), H("lowerarm_" + side), H("hand_" + side)
        self.lo = np.minimum.reduce([S, E, W]) - 0.08
        self.hi = np.maximum.reduce([S, E, W]) + 0.08

    def prims(self):
        S, E, W = H("upperarm_" + self.side), H("lowerarm_" + self.side), H("hand_" + self.side)
        f = norm(W - E)
        out = [(RoundCone(S, E, 0.034, 0.03), 0.0, "walnut"),
               (Sphere(E, 0.036), 0.01, "brass"),
               (Cog(E, axis_frame(norm(np.cross(norm(E - S), f) + v3(0, 0, 1e-4))), 0.04, 12, 0.006, 0.014), 0.004, "brass"),
               (RoundCone(E, W, 0.03, 0.027), 0.006, "walnut")]
        for t in (0.55, 0.8):
            c = E + (W - E) * t
            out.append((Torus(c, 0.03, 0.0055, R=axis_frame(f)), 0.003, "brass"))
        return out

    def weights(self, P):
        s = self.side
        spec = [("clavicle_" + s, 0.06), ("upperarm_" + s, 0.05), ("lowerarm_" + s, 0.05),
                ("hand_" + s, 0.04, H("hand_" + s), H("middle_01_" + s))]
        W = wdist(P, spec, 6.0)
        W["clavicle_" + s] = W["clavicle_" + s] * 0.5
        return W


class Hand(Part):
    atlas = "body"
    h = 0.0015
    tris = 2300
    texel = 1.6

    def __init__(self, side):
        self.side, self.s = side, (1.0 if side == "l" else -1.0)
        self.name = "hand_" + side
        pts = [H("hand_" + side)] + [p for f in FING for p in finger_chain(f, side)] + \
              [H("thumb_0%d_%s" % (k, side)) for k in (1, 2, 3)] + [T("thumb_04_leaf_" + side)]
        pts = np.array(pts)
        self.lo = pts.min(0) - 0.035
        self.hi = pts.max(0) + 0.035

    def prims(self):
        s = self.side
        W = H("hand_" + s)
        knuck = [H("%s_01_%s" % (f, s)) for f in FING]
        hd = norm(np.mean(knuck, 0) - W)
        across = norm(knuck[0] - knuck[3])
        palm_n = norm(np.cross(hd, across)) * (1 if s == "l" else -1)
        out = [(RoundCone(W - hd * 0.03, W + hd * 0.005, 0.026, 0.024), 0.0, "walnut")]
        for k in knuck:
            out.append((RoundCone(W + hd * 0.004, k, 0.017, 0.012), 0.02, "walnut"))
        out.append((Func(lambda P: np.maximum(RoundCone(W + hd * 0.01, np.mean(knuck, 0) - hd * 0.005, 0.03, 0.028).d(P),
                                              np.abs(((P - (W + np.mean(knuck, 0)) * 0.5) @ palm_n)) - 0.0045 - 0.012),
                         W - 0.08, W + 0.12), 0.003, "brass"))                                          # back plate
        out.append((Cog(W, axis_frame(across), 0.026, 12, 0.005, 0.01), 0.003, "brass"))             # wrist gear
        for f in FING:
            ch = finger_chain(f, s)
            for j in range(3):
                out.append((RoundCone(ch[j], ch[j + 1], 0.0085 - 0.001 * j, 0.0078 - 0.001 * j), 0.003, "walnut"))
            for j in range(3):
                out.append((Cog(ch[j], axis_frame(across), 0.0128 - 0.0012 * j, 8, 0.0036, 0.0078), 0.0015, "brass"))
            tip = ch[3] + (ch[4] - ch[3]) * 0.7
            out.append((RoundCone(ch[3], tip, 0.0068, 0.0035), 0.002, "brass"))                      # fingertip cap
        th = [H("thumb_0%d_%s" % (k, s)) for k in (1, 2, 3)] + [H("thumb_04_leaf_" + s), T("thumb_04_leaf_" + s)]
        out.append((RoundCone(W + hd * 0.005, th[1], 0.02, 0.011), 0.02, "walnut"))
        for j in (1, 2):
            out.append((RoundCone(th[j], th[j + 1], 0.0095, 0.0085), 0.003, "walnut"))
            out.append((Cog(th[j], axis_frame(norm(np.cross(norm(th[j + 1] - th[j]), palm_n))), 0.0135, 8, 0.0036, 0.008), 0.0015, "brass"))
        out.append((RoundCone(th[3], th[3] + (th[4] - th[3]) * 0.7, 0.0078, 0.004), 0.002, "brass"))
        return out

    def weights(self, P):
        s = self.side
        spec = [("lowerarm_" + s, 0.04, H("lowerarm_" + s), H("hand_" + s) - norm(H("hand_" + s) - H("lowerarm_" + s)) * 0.02),
                ("hand_" + s, 0.035, H("hand_" + s), H("middle_01_" + s) * 0.75 + H("hand_" + s) * 0.25)]
        for f in FING:
            ch = finger_chain(f, s)
            for seg in (1, 2, 3):
                tail = ch[seg] if seg < 3 else ch[4]
                spec.append(("%s_0%d_%s" % (f, seg, s), 0.011, ch[seg - 1], tail))
        th = [H("thumb_0%d_%s" % (k, s)) for k in (1, 2, 3)] + [H("thumb_04_leaf_" + s), T("thumb_04_leaf_" + s)]
        for seg in (1, 2, 3):
            spec.append(("thumb_0%d_%s" % (seg, s), 0.014, th[seg - 1], th[seg] if seg < 3 else th[4]))
        return wdist(P, spec, 6.0)


# ============================================================================================ LEGS + SHOES
class Leg(Part):
    atlas = "body"
    h = 0.003
    tris = 1400
    texel = 0.35

    def __init__(self, side):
        self.side, self.s = side, (1.0 if side == "l" else -1.0)
        self.name = "leg_" + side
        hip, knee, ank, ball = H("thigh_" + side), H("calf_" + side), H("foot_" + side), H("ball_" + side)
        self.lo = np.minimum.reduce([hip, knee, ank, ball]) - v3(0.08, 0.16, 0.0)
        self.hi = np.maximum.reduce([hip, knee, ank, ball]) + 0.09
        self.lo[2] = -0.01

    def prims(self):
        sd = self.side
        hip, knee, ank, ball, toe = H("thigh_" + sd), H("calf_" + sd), H("foot_" + sd), H("ball_" + sd), T("ball_" + sd)
        out = [(RoundCone(hip + v3(0, 0, 0.02), knee, 0.058, 0.04), 0.0, "walnut"),
               (Sphere(knee, 0.038), 0.01, "brass"),
               (Cog(knee + v3(self.s * 0.03, 0, 0), axis_frame(v3(1, 0, 0)), 0.036, 12, 0.006, 0.012), 0.003, "brass"),
               (RoundCone(knee, ank, 0.036, 0.027), 0.008, "walnut")]
        for t in (0.3, 0.7):
            c = knee + (ank - knee) * t
            out.append((Torus(c, 0.035 - 0.006 * t, 0.005, R=axis_frame(norm(ank - knee))), 0.003, "brass"))
        out.append((Sphere(ank, 0.03), 0.01, "brass"))
        # pointed academic shoe with curled toe
        tipp = v3(ball[0], toe[1] - 0.07, 0.05)

        def shoe(P):
            body = RoundCone(v3(ank[0], ank[1] + 0.02, 0.045), v3(ball[0], ball[1], 0.035), 0.045, 0.04).d(P)
            front = RoundCone(v3(ball[0], ball[1], 0.032), tipp, 0.036, 0.006).d(P)
            d = smin(body, front, 0.03)
            return np.maximum(d, -Z(P))
        out.append((Func(shoe, v3(ball[0] - 0.08, tipp[1] - 0.03, -0.01), v3(ball[0] + 0.08, ank[1] + 0.09, 0.12)), 0.01, "walnut"))
        out.append((Func(lambda P: np.maximum(RoundCone(v3(ball[0], ball[1] - 0.02, 0.03), tipp, 0.039, 0.0075).d(P),
                                              Y(P) - (ball[1] - 0.045)), v3(ball[0] - 0.08, tipp[1] - 0.03, -0.01),
                         v3(ball[0] + 0.08, ball[1] + 0.02, 0.12)), 0.004, "brass"))                       # toe cap
        out.append((Func(lambda P: np.maximum(np.abs(Z(P) - 0.006) - 0.006,
                                              RoundCone(v3(ank[0], ank[1] + 0.02, 0.045), tipp, 0.047, 0.01).d(P)),
                         v3(ball[0] - 0.08, tipp[1] - 0.03, -0.01), v3(ball[0] + 0.08, ank[1] + 0.09, 0.03)), 0.003, "steel"))  # sole
        return out

    def weights(self, P):
        s = self.side
        hip, knee, ank, ball, toe = H("thigh_" + s), H("calf_" + s), H("foot_" + s), H("ball_" + s), T("ball_" + s)
        spec = [("pelvis", 0.1, v3(0, 0.03, 0.95), v3(0, 0.03, 1.08)), ("thigh_" + s, 0.06), ("calf_" + s, 0.045),
                ("foot_" + s, 0.045, ank, ball), ("ball_" + s, 0.04, ball, toe + v3(0, -0.08, 0.03))]
        return wdist(P, spec, 6.0)


# ============================================================================================ ROBE (tint1)
def skirt_d(P):
    z = Z(P)
    rx = np.interp(z, [0.05, 0.5, 0.95, 1.2], [0.31, 0.255, 0.19, 0.17]).astype(F32)
    ry = np.interp(z, [0.05, 0.5, 0.95, 1.2], [0.285, 0.23, 0.16, 0.14]).astype(F32)
    yc = np.interp(z, [0.05, 1.2], [0.035, 0.005]).astype(F32)
    x, y = X(P), Y(P) - yc
    th = np.arctan2(x, -y)
    fold = 1.0 + 0.045 * np.sin(11 * th + 1.5 * NOISE(P * np.array([3, 3, 0.8], F32))) * smoothstep(1.05, 0.45, z)
    q = np.sqrt((x / rx) ** 2 + (y / ry) ** 2)
    d = (q - fold) * np.minimum(rx, ry) * 0.92
    return np.maximum(d, z - 1.25).astype(F32)


def robe_env(P):
    d = Ellipsoid((0, 0.0, 1.33), (0.172, 0.142, 0.215)).d(P)
    for s, sg in SIDES:
        d = smin(d, RoundCone((sg * 0.05, 0.03, 1.505), (sg * 0.2, 0.05, 1.47), 0.064, 0.066).d(P), 0.05)
    d = smin(d, skirt_d(P), 0.1)
    return d


def open_w(z):
    return np.interp(z, [0.0, 0.3, 0.9, 1.0, 1.06, 1.12, 1.2, 1.3, 1.42, 1.5, 1.6],
                     [0.15, 0.12, 0.05, 0.042, 0.05, 0.06, 0.105, 0.122, 0.11, 0.075, 0.075]).astype(F32)


HEM = 0.095


def hem_z(P):
    return HEM + 0.012 * np.sin(np.arctan2(X(P), -Y(P)) * 11 + 0.6)


def robe_cuts(P):
    """>0 where the robe is cut away (neck hole, front opening, below the hem)."""
    dxy = np.sqrt(X(P) ** 2 + (Y(P) - 0.03) ** 2)
    neck = np.minimum(0.085 - dxy, Z(P) - 1.47)
    front = np.minimum(open_w(Z(P)) - np.abs(X(P)), -0.0 - Y(P))
    hem = hem_z(P) - Z(P)
    return np.maximum.reduce([neck, front, hem])


def sleeve_geo(side):
    S, E, W = H("upperarm_" + side), H("lowerarm_" + side), H("hand_" + side)
    f = norm(W - E)
    C = W + f * 0.012
    Cl = C + v3(0, 0, -0.035)
    return S, E, W, f, C, Cl


def sleeve_env(P, side):
    S, E, W, f, C, Cl = sleeve_geo(side)
    return smin(RoundCone(S, E, 0.074, 0.068).d(P), RoundCone(E, Cl, 0.068, 0.122).d(P), 0.04)


def sleeve_cut(P, side):
    S, E, W, f, C, Cl = sleeve_geo(side)
    return (P - C) @ f                       # >0 beyond the cuff


def collar_geo(P):
    dxy = np.sqrt(X(P) ** 2 + (Y(P) - 0.035) ** 2)
    r = 0.088 + 0.42 * np.clip(Z(P) - 1.47, 0, None)
    th = np.arctan2(X(P), Y(P) - 0.035)              # 0 = back
    fr = (1 - np.cos(th)) * 0.5                     # 0 back .. 1 front
    top = 1.665 - 0.1 * fr ** 1.5
    return dxy, r, fr, top


def collar_d(P):
    dxy, r, fr, top = collar_geo(P)
    d = np.abs(dxy - r) - 0.0055
    return np.maximum.reduce([d, Z(P) - top, 1.465 - Z(P), fr - 0.78]).astype(F32)


T_ROBE = 0.0052


def robe_shell(P):
    d = np.abs(robe_env(P)) - T_ROBE
    d = np.maximum(d, robe_cuts(P))
    return d


def sleeve_shell(P, side):
    d = np.abs(sleeve_env(P, side)) - T_ROBE
    return np.maximum(d, sleeve_cut(P, side))


def robe_weights(P):
    z, x, y = P[:, 2], P[:, 0], P[:, 1]
    W = chest_weights(P)
    for b in ("Head", "neck_01"):
        W[b] = W.get(b, 0) * 0.3
    # sleeves: nearest of the arm chains
    for s, sg in SIDES:
        S, E, Wr, f, C, Cl = sleeve_geo(s)
        de = sleeve_env(P, s)
        on = smoothstep(0.03, -0.01, de - np.minimum(robe_env(P), 0.5)) * (sg * x > 0.12)
        u = np.clip(((P - S) @ norm(E - S)) / np.linalg.norm(E - S), 0, 1)
        past = np.clip(((P - E) @ f) / max(np.linalg.norm(Cl - E), 1e-6), 0, 1.2)
        elbow = (P - E) @ f > -0.03
        wu = np.where(elbow, smoothstep(0.08, -0.04, (P - E) @ f), 1.0) * (0.35 + 0.65 * smoothstep(0.0, 0.35, u))
        wl = np.where(elbow, 1 - smoothstep(0.08, -0.04, (P - E) @ f), 0.0)
        wc = (1 - smoothstep(0.0, 0.35, u)) * np.where(elbow, 0, 1)
        for b in list(W):
            W[b] = W[b] * (1 - on)
        W["upperarm_" + s] = W.get("upperarm_" + s, 0) + on * wu * 0.85
        W["clavicle_" + s] = W.get("clavicle_" + s, 0) + on * (wc * 0.6 + wu * 0.15)
        W["lowerarm_" + s] = W.get("lowerarm_" + s, 0) + on * wl * (1 - 0.15 * np.clip(past, 0, 1))
        W["hand_" + s] = W.get("hand_" + s, 0) + on * wl * 0.15 * np.clip(past, 0, 1)
    # skirt follows the thighs
    hang = smoothstep(1.02, 0.7, z)
    sd = smoothstep(-0.07, 0.07, x)
    back = smoothstep(0.0, 0.12, y)
    legw = hang * (0.85 - 0.35 * back)
    for b in list(W):
        W[b] = W[b] * (1 - legw)
    W["thigh_l"] = W.get("thigh_l", 0) + legw * sd
    W["thigh_r"] = W.get("thigh_r", 0) + legw * (1 - sd)
    low = smoothstep(0.42, 0.15, z) * (1 - back) * 0.25
    for s, sdx in (("l", sd), ("r", 1 - sd)):
        W["thigh_" + s] = W["thigh_" + s] - low * sdx
        W["calf_" + s] = W.get("calf_" + s, 0) + low * sdx
    # collar: neck at the top
    cz = smoothstep(1.5, 1.66, z) * (np.abs(x) < 0.2)
    for b in list(W):
        W[b] = W[b] * (1 - cz * 0.5)
    W["neck_01"] = W.get("neck_01", 0) + cz * 0.5
    return W


class Robe(Part):
    name = "robe"
    atlas = "robe"
    h = 0.0036
    lo = (-0.62, -0.36, 0.06)
    hi = (0.62, 0.36, 1.70)
    tris = 8500
    texel = 1.0
    smooth_iters = 2

    def build(self, g):
        g.union(Func(robe_shell, (-0.36, -0.34, 0.06), (0.36, 0.34, 1.62)))
        for s, sg in SIDES:
            S, E, W, f, C, Cl = sleeve_geo(s)
            lo = np.minimum.reduce([S, E, Cl]) - 0.15
            hi = np.maximum.reduce([S, E, Cl]) + 0.15
            g.union(Func(lambda P, s=s: sleeve_shell(P, s), lo, hi), 0.01)
        g.union(Func(collar_d, (-0.2, -0.2, 1.44), (0.2, 0.25, 1.7)), 0.006)

    def post(self, V, N):
        w = 0.0012 * NOISE.fbm(V * np.array([30, 30, 6], F32), 2)
        return V + N * w[:, None]

    def masks(self, P, N):
        env = robe_env(P)
        lining = env < -T_ROBE * 0.2
        for s, sg in SIDES:
            lining = np.where(sg * P[:, 0] > 0.17, sleeve_env(P, s) < -T_ROBE * 0.2, lining)
        return {"lining": lining, "collar": collar_d(P) < 0.003}

    def weights(self, P):
        return robe_weights(P)


class Hat(Part):
    """skullcap + mortarboard (robe cloth)."""
    name = "hat"
    atlas = "robe"
    h = 0.0022
    lo = (-0.24, -0.24, 1.70)
    hi = (0.24, 0.24, 1.86)
    tris = 1300
    texel = 1.0

    @staticmethod
    def board_R():
        return rot_axis((1, 0, 0), 7) @ rot_axis((0, 0, 1), 45)

    BOARD_C = v3(0, 0.0, 1.812)

    def build(self, g):
        g.union(Func(lambda P: np.maximum(Ellipsoid((0, 0.008, 1.712), (0.092, 0.102, 0.09)).d(P), 1.728 - Z(P)),
                     (-0.11, -0.12, 1.7), (0.11, 0.12, 1.82)))
        g.union(RBox(self.BOARD_C, (0.148, 0.148, 0.0075), 0.003, R=self.board_R()), 0.012)

    def masks(self, P, N):
        return {"board": RBox(self.BOARD_C, (0.148, 0.148, 0.0075), 0.003, R=self.board_R()).d(P) < 0.003}


# ============================================================================================ TRIM (tint2)
def trim_front_d(P):
    """brass band along both front edges of the robe opening (robe side of the edge)."""
    z, ax = Z(P), np.abs(X(P))
    w = open_w(z)
    band = np.maximum.reduce([w - ax, ax - w - 0.032, Y(P), z - 1.5, HEM - z])
    shell = np.abs(robe_env(P)) - T_ROBE - 0.0035
    return np.maximum(np.maximum(shell, band), robe_cuts(P))


def trim_hem_d(P):
    band = np.abs(Z(P) - (hem_z(P) + 0.02)) - 0.02
    shell = np.abs(robe_env(P)) - T_ROBE - 0.0035
    return np.maximum(np.maximum(shell, band), robe_cuts(P))


def belt_d(P):
    env = robe_env(P)
    return np.maximum(np.abs(env + 0.002) - T_ROBE - 0.005, np.abs(Z(P) - 1.05) - 0.021)


BUCKLE_C = v3(0, -0.163, 1.05)


def collar_trim_d(P):
    dxy, r, fr, top = collar_geo(P)
    d = np.abs(dxy - r) - 0.0055 - 0.0025
    return np.maximum.reduce([d, Z(P) - top - 0.002, top - 0.03 - Z(P), fr - 0.785])


def cuff_trim_d(P, side):
    S, E, W, f, C, Cl = sleeve_geo(side)
    d = np.abs(sleeve_env(P, side)) - T_ROBE - 0.0025
    u = (P - C) @ f
    return np.maximum.reduce([d, u + 0.0005, -u - 0.035])


class Trim(Part):
    name = "trim"
    atlas = "trim"
    h = 0.003
    lo = (-0.62, -0.36, 0.06)
    hi = (0.62, 0.36, 1.70)
    tris = 5600
    texel = 1.0
    smooth_iters = 3

    def build(self, g):
        g.union(Func(trim_front_d, (-0.2, -0.34, 0.06), (0.2, 0.01, 1.52)))
        g.union(Func(trim_hem_d, (-0.36, -0.34, 0.06), (0.36, 0.34, 0.17)), 0.0)
        g.union(Func(belt_d, (-0.3, -0.3, 1.0), (0.3, 0.3, 1.1)), 0.003)
        g.union(RBox(BUCKLE_C, (0.03, 0.009, 0.026), 0.006), 0.004)
        g.union(Func(collar_trim_d, (-0.2, -0.2, 1.5), (0.2, 0.25, 1.7)), 0.0)
        for s, sg in SIDES:
            S, E, W, f, C, Cl = sleeve_geo(s)
            g.union(Func(lambda P, s=s: cuff_trim_d(P, s), Cl - 0.16, Cl + 0.16), 0.0)
        # mortarboard edge band
        Rb = Hat.board_R()
        g.union(Func(lambda P: np.maximum(RBox(Hat.BOARD_C, (0.151, 0.151, 0.0062), 0.003, R=Rb).d(P),
                                          -RBox(Hat.BOARD_C, (0.135, 0.135, 0.02), 0.0, R=Rb).d(P)),
                     Hat.BOARD_C - 0.23, Hat.BOARD_C + 0.23), 0.0)
        # cap band
        g.union(Func(lambda P: np.maximum(Ellipsoid((0, 0.008, 1.712), (0.095, 0.105, 0.093)).d(P), np.abs(Z(P) - 1.737) - 0.009),
                     (-0.12, -0.12, 1.72), (0.12, 0.12, 1.76)), 0.0)

    def masks(self, P, N):
        return {"buckle": RBox(BUCKLE_C, (0.034, 0.013, 0.03), 0.006).d(P) < 0.002,
                "belt": np.abs(P[:, 2] - 1.05) < 0.024}

    def weights(self, P):
        W = robe_weights(P)
        hat = P[:, 2] > 1.69
        for b in list(W):
            W[b] = np.where(hat, 0, W[b])
        W["Head"] = W.get("Head", 0) + hat
        return W


TASSEL_TOP = v3(0, 0.0, 1.85)


def tassel_pts():
    corner = Hat.BOARD_C + Hat.board_R() @ v3(0.148, -0.148, 0.0)
    return corner


class Tassel(Part):
    name = "tassel"
    atlas = "trim"
    h = 0.0015
    lo = (-0.05, -0.2, 1.62)
    hi = (0.25, 0.08, 1.87)
    tris = 600
    texel = 1.0

    def build(self, g):
        cr = tassel_pts()
        top = Hat.BOARD_C + Hat.board_R() @ v3(0, 0, 0.012)
        p = spline([top + v3(0, 0, 0.01), (top + cr) * 0.5 + v3(0, 0, 0.012), cr + v3(0, 0, 0.004), cr + v3(0.012, -0.004, -0.05),
                    cr + v3(0.014, -0.006, -0.085)], 4)
        g.union(Tube(p, [0.0032] * len(p)))
        end = cr + v3(0.014, -0.006, -0.085)
        g.union(RoundCone(end, end + v3(0.002, -0.001, -0.07), 0.009, 0.019), 0.006)
        g.union(Sphere(end + v3(0, 0, 0.004), 0.0085), 0.004)

    def masks(self, P, N):
        cr = tassel_pts()
        return {"fringe": P[:, 2] < cr[2] - 0.09}

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


# ============================================================================================ GEAR CROWN (body atlas)
class Crown(Part):
    name = "crown"
    atlas = "body"
    h = 0.0012
    lo = (-0.11, -0.11, 1.80)
    hi = (0.11, 0.11, 1.89)
    tris = 1700
    texel = 1.2

    @staticmethod
    def frame():
        R = Hat.board_R()
        return R

    @staticmethod
    def centre():
        return Hat.BOARD_C + Hat.board_R() @ v3(0, 0, 0.0075 + 0.008)

    def prims(self):
        R = self.frame()
        c = self.centre()
        up = R[:, 2]
        R2 = R @ rot_axis((0, 0, 1), 9)
        return [(Cog(c, R, 0.072, 18, 0.011, 0.014, r_in=0.05, spokes=5, hub=0.016), 0.0, "brass"),
                (Cog(c + up * 0.016, R2, 0.034, 10, 0.008, 0.011, r_in=0.018, spokes=4, hub=0.008), 0.002, "brass"),
                (RoundCone(c, c + up * 0.034, 0.0065, 0.004), 0.002, "steel"),
                (Sphere(c + up * 0.037, 0.0075), 0.002, "glow")]

    def weights(self, P):
        return {"Head": np.ones(len(P), F32)}


# ============================================================================================ STAFF + PENDULUM
STAFF_TILT = 20.0      # degrees the staff is swung from the grip channel toward the forearm


def staff_frame():
    """grip centre and staff axis in the modeling pose (right hand).  Axis: the grip channel (knuckle line,
    pinky -> index) swung STAFF_TILT deg toward the forearm (a compromise: raised forward when the arm hangs,
    near-vertical in punches, never through the body in the UAL test clips)."""
    s = "r"
    W = H("hand_" + s)
    knuck = [H("%s_01_%s" % (f, s)) for f in FING]
    mids = [H("%s_02_%s" % (f, s)) for f in FING]
    hd = norm(np.mean(knuck, 0) - W)
    kl = norm(knuck[0] - knuck[3])
    ax = norm(kl * math.cos(math.radians(STAFF_TILT)) - hd * math.sin(math.radians(STAFF_TILT)))
    grip = np.mean(knuck, 0) * 0.45 + np.mean(mids, 0) * 0.55
    # side vector (perpendicular to the staff, roughly the palm normal)
    side = norm(np.cross(ax, kl) + v3(0, 0, 1e-4))
    return grip, ax, side


STAFF_TOP = 0.98        # from the grip along the axis
STAFF_BOT = -0.62


def staff_pts():
    g, ax, sd = staff_frame()
    return g, ax, sd, g + ax * STAFF_TOP, g + ax * STAFF_BOT


def pendulum_pivot():
    g, ax, sd, top, bot = staff_pts()
    arm_dir = norm(np.cross(ax, sd))
    return top - ax * 0.17 + arm_dir * 0.075, arm_dir


class Staff(Part):
    name = "staff"
    atlas = "staff"
    h = 0.0018
    tris = 2100
    texel = 1.0

    def __init__(self):
        g, ax, sd, top, bot = staff_pts()
        allp = np.array([top, bot, g])
        self.lo = allp.min(0) - 0.12
        self.hi = allp.max(0) + 0.12

    def prims(self):
        g, ax, sd, top, bot = staff_pts()
        arm_dir = norm(np.cross(ax, sd))
        ring_c = top - ax * 0.07
        Rr = np.stack([ax, arm_dir, sd], 1)                # torus z = sd: ring in the (ax, arm) plane
        out = [(RoundCone(bot, top - ax * 0.15, 0.0145, 0.0165), 0.0, "walnut"),
               (RoundCone(bot - ax * 0.01, bot + ax * 0.05, 0.012, 0.0175), 0.004, "brass")]           # ferrule
        for t in (0.18, 0.62, 0.95):
            c = bot + (top - bot) * t
            out.append((Torus(c, 0.0175, 0.0045, R=axis_frame(ax)), 0.003, "brass"))
        out.append((Torus(ring_c, 0.07, 0.0085, R=Rr), 0.004, "brass"))                                # head ring
        out.append((Cog(ring_c, Rr, 0.05, 20, 0.006, 0.01, r_in=0.0, spokes=0), 0.003, "brass"))      # clock backplate
        out.append((Disc(ring_c + sd * 0.006, sd, 0.044, 0.002), 0.001, "dial"))
        out.append((Disc(ring_c - sd * 0.006, -sd, 0.044, 0.002), 0.001, "dial"))
        out.append((RoundCone(top - ax * 0.15, ring_c - ax * 0.065, 0.016, 0.012), 0.006, "brass"))     # collar
        out.append((RoundCone(ring_c + ax * 0.068, top + ax * 0.06, 0.011, 0.002), 0.004, "brass"))     # finial spike
        out.append((Sphere(ring_c + ax * 0.08, 0.012), 0.004, "glow"))
        pv, ad = pendulum_pivot()
        out.append((RoundCone(top - ax * 0.17, pv + ad * 0.008, 0.0075, 0.006), 0.004, "brass"))        # gallows arm
        out.append((Torus(pv, 0.008, 0.003, R=np.stack([ad, ax, sd], 1)), 0.002, "steel"))
        return out

    def weights(self, P):
        return {"hand_r": np.ones(len(P), F32)}


class Pendulum(Part):
    name = "pendulum"
    atlas = "staff"
    h = 0.0012
    tris = 900
    texel = 1.2

    def __init__(self):
        pv, ad = pendulum_pivot()
        self.lo = pv - 0.36
        self.hi = pv + 0.36

    def geo(self):
        g, ax, sd, top, bot = staff_pts()
        pv, ad = pendulum_pivot()
        down = -ax
        bob = pv + down * 0.29
        return pv, down, bob, sd

    def prims(self):
        pv, down, bob, sd = self.geo()
        return [(Torus(pv, 0.0065, 0.0022, R=np.stack([sd, down, norm(np.cross(sd, down))], 1)), 0.0, "steel"),
                (RoundCone(pv + down * 0.006, bob, 0.0032, 0.0032), 0.002, "brass"),
                (Disc(bob, sd, 0.042, 0.0055, 0.003), 0.003, "brass"),
                (Torus(bob, 0.042, 0.004, R=axis_frame(sd)), 0.002, "brass"),
                (Disc(bob + sd * 0.004, sd, 0.016, 0.004, 0.003), 0.002, "glow"),
                (Disc(bob - sd * 0.004, -sd, 0.016, 0.004, 0.003), 0.002, "glow")]

    def weights(self, P):
        return {"hand_r": np.ones(len(P), F32)}


# ============================================================================================
def all_parts():
    ps = [Chest(), Clock(), ClockHand("hour"), ClockHand("min"), Head(), Beard(), Crown()]
    for side, s in SIDES:
        ps += [Arm(side), Hand(side), Leg(side)]
    ps += [Robe(), Hat(), Trim(), Tassel(), Staff(), Pendulum()]
    return ps


def parts(atlas):
    return [p for p in all_parts() if p.atlas == atlas]


ATLAS_SIZE = {"body": 2048, "robe": 2048, "trim": 1024, "staff": 1024}


# grain lines (walnut) per part
def _limb_flow(self):
    if isinstance(self, Arm):
        s = self.side
        return [np.array([H("upperarm_" + s), H("lowerarm_" + s), H("hand_" + s)], F32)]
    if isinstance(self, Leg):
        s = self.side
        return [np.array([H("thigh_" + s), H("calf_" + s), H("foot_" + s), H("ball_" + s), T("ball_" + s)], F32)]
    if isinstance(self, Hand):
        s = self.side
        out = [np.array([H("lowerarm_" + s), H("hand_" + s)], F32)]
        for f in FING:
            out.append(np.array([H("hand_" + s)] + finger_chain(f, s), F32))
        out.append(np.array([H("hand_" + s)] + [H("thumb_0%d_%s" % (k, s)) for k in (1, 2, 3)] + [T("thumb_04_leaf_" + s)], F32))
        return out
    if isinstance(self, (Staff, Pendulum)):
        g, ax, sd, top, bot = staff_pts()
        return [np.array([bot, top], F32)]
    return [np.array([[0, 0, 0.5], [0, 0, 1.9]], F32)]


for _cls in (Arm, Leg, Hand, Staff, Pendulum):
    _cls.flow = _limb_flow


def _staff_bins(self):
    g, ax, sd, top, bot = staff_pts()
    return (ax, 0.2)


Staff.chart_bins = _staff_bins

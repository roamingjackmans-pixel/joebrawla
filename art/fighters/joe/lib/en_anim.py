"""Pose-to-pose animation engine for the enemy rigs (generalised from the Caretaker's ct_anim / s7_anim).

Works on any armature (UAL 65-bone humanoids and our own creature skeletons).

Pose = dict of channels (missing channels = rest):
  'hip_off'          (x,y,z) metres, armature space, offset of the rig's hip bone (UAL: pelvis)
  '<bone>'           (rx,ry,rz) degrees, rotation in ARMATURE REST AXES relative to the parent (character faces -Y,
                     his left = +X; +rx bends a bone forward/down, +rz turns it to his left, +ry leans it to his left)
  '<bone>@loc'       (x,y,z) extra translation of a bone in armature axes (leaf bones: bowstring nock, arrow ...)
  '<bone>@scl'       uniform scale of a bone (e.g. 0 hides an arrow)
  Humanoid helpers (UAL names):
  'L_foot','R_foot'  (x,y,z,yaw,pitch) ankle target + foot yaw/pitch (deg); 'L_ball','R_ball' toe bend (deg)
  'R_wrist','L_wrist' (x,y,z) IK wrist target (world); 'R_hand','L_hand' (rx,ry,rz) hand rel. forearm (rest axes)
  'R_pole','L_pole'  elbow pole directions
  'R_item','L_item'  (x,y,z,yaw,pitch,roll) world grip point + direction of the item held in that hand
                     (item local frame: -Z from grip toward the tip, +Y = face normal, X = Y x Z); the hand is
                     solved from it (overrides R_wrist / R_hand)
  'L_on','R_on'      0..1 blend that free hand onto the OTHER hand's item, at 'L_on_s'/'R_on_s' metres along it
  'fist_l','fist_r'  0..1 finger curl; 'spread_l','spread_r' 0..1 open hand; 'claw_l','claw_r' 0..1 hooked claw
  'shake'            strain tremble amplitude while holding a telegraph
Keys: (frame, pose, opts) with opts 'flow' (0 = ease to a stop, 1 = pass through), 'tin'/'tout' tangent scales.
"""
import math
import numpy as np
from mathutils import Quaternion, Vector, Matrix, Euler

FPS = 30
FINGERS = ("index", "middle", "ring", "pinky")


def E(e):
    return Euler([math.radians(a) for a in e], 'XYZ').to_quaternion()


def item_frame(yaw, pitch, roll):
    """3x3 world rotation of an item frame (X across, Y face normal, Z toward the grip) and its tip direction d.
    yaw 0 = forward (-Y), +90 = his left (+X); pitch +90 = up; roll turns the face normal about d."""
    yw, pt = math.radians(yaw), math.radians(pitch)
    d = Vector((math.cos(pt) * math.sin(yw), -math.cos(pt) * math.cos(yw), math.sin(pt)))
    n = Vector((-math.sin(pt) * math.sin(yw), math.sin(pt) * math.cos(yw), math.cos(pt)))
    n = Quaternion(d, math.radians(roll)) @ n
    Zs = -d
    Ys = n
    Xs = Ys.cross(Zs)
    return Matrix((Xs, Ys, Zs)).transposed(), d


def aim_yp(a, b):
    """yaw, pitch (deg) of the direction a -> b."""
    d = (Vector(b) - Vector(a)).normalized()
    return math.degrees(math.atan2(d.x, -d.y)), math.degrees(math.asin(max(-1, min(1, d.z))))


class Item:
    """a rigid item held in a hand: grip_rot maps item-local axes -> hand bone-local axes, grip_pos = grip point
    in hand bone-local space (inside the closed fist)."""

    def __init__(self, name, bone, grip_rot, grip_pos, off_grip_pos=None):
        self.name, self.bone = name, bone
        self.grip_rot = Matrix(np.asarray(grip_rot, np.float64).tolist())
        self.grip_pos = Vector(grip_pos)
        self.off_grip_pos = Vector(off_grip_pos) if off_grip_pos is not None else Vector(grip_pos)


class Rig:
    def __init__(self, arm, items=(), hip="pelvis"):
        self.arm = arm
        bones = list(arm.data.bones)
        depth = {b.name: len(b.parent_recursive) for b in bones}
        self.order = sorted([b.name for b in bones], key=lambda n: depth[n])
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.R = {b.name: b.matrix_local.to_3x3() for b in bones}
        self.Q = {b.name: b.matrix_local.to_quaternion() for b in bones}
        self.head = {b.name: b.head_local.copy() for b in bones}
        self.tail = {b.name: b.tail_local.copy() for b in bones}
        self.hip = hip
        self.items = {it.name: it for it in items}
        self.humanoid = "upperarm_l" in self.head and "thigh_l" in self.head
        if self.humanoid:
            self.ulen = (self.head["lowerarm_l"] - self.head["upperarm_l"]).length
            self.flen = (self.head["hand_l"] - self.head["lowerarm_l"]).length
            self.thl = (self.head["calf_l"] - self.head["thigh_l"]).length
            self.cal = (self.head["foot_l"] - self.head["calf_l"]).length

    # ---------------------------------------------------------------- FK
    def fk(self, loc, hip_off, tloc=None):
        """loc: bone -> accumulated-delta quaternion (armature axes, relative to parent); tloc: bone -> extra
        translation (armature axes, applied in the parent's rotated frame). Returns (world delta quats, heads)."""
        Qa, pos = {}, {}
        for b in self.order:
            p = self.parent[b]
            q = loc.get(b, Quaternion())
            if p is None:
                Qa[b] = q.copy()
                pos[b] = self.head[b].copy()
            else:
                Qa[b] = Qa[p] @ q
                pos[b] = pos[p] + Qa[p] @ (self.head[b] - self.head[p])
            if b == self.hip:
                pos[b] = pos[b] + Vector(hip_off)
            if tloc and b in tloc:
                pp = Qa[p] if p else Quaternion()
                pos[b] = pos[b] + pp @ Vector(tloc[b])
        return Qa, pos

    def set_world(self, loc, Qa, b, Qw):
        p = self.parent[b]
        loc[b] = Qa[p].inverted() @ Qw if p else Qw

    def world_matrix(self, Qa, pos, b):
        M = (Qa[b].to_matrix() @ self.R[b]).to_4x4()
        M.translation = pos[b]
        return M

    # ---------------------------------------------------------------- IK
    def two_bone(self, S, W, l1, l2, pole, n_rest, u_rest):
        S, W = Vector(S), Vector(W)
        dv = W - S
        d = min(max(dv.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
        dirv = dv.normalized()
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0))
        pv = Vector(pole) - dirv * Vector(pole).dot(dirv)
        if pv.length < 1e-6:
            pv = Vector((0, 0, -1)) - dirv * (-dirv.z)
        pv.normalize()
        Ep = S + dirv * a + pv * h
        u1 = (Ep - S).normalized()
        Wp = S + dirv * d
        f1 = (Wp - Ep).normalized()
        n1 = u1.cross(f1)
        if n1.length < 1e-6:
            n1 = u1.cross(pv).cross(u1) * -1
        n1.normalize()
        u0 = Vector(u_rest).normalized()
        n0 = Vector(n_rest) - u0 * Vector(n_rest).dot(u0)
        n0.normalize()
        M0 = Matrix((u0, n0, u0.cross(n0))).transposed()
        M1 = Matrix((u1, n1, u1.cross(n1))).transposed()
        Mf = Matrix((f1, n1, f1.cross(n1))).transposed()
        return (M1 @ M0.transposed()).to_quaternion(), (Mf @ M0.transposed()).to_quaternion()

    def chain_ik(self, loc, hip_off, upper, lower, end, target, pole, n_rest, tloc=None):
        """generic 2-bone IK: rotates `upper` and `lower` so that the head of `end` reaches target."""
        Qa, pos = self.fk(loc, hip_off, tloc)
        l1 = (self.head[lower] - self.head[upper]).length
        l2 = (self.head[end] - self.head[lower]).length
        u_rest = self.head[lower] - self.head[upper]
        Qu, Qf = self.two_bone(pos[upper], target, l1, l2, pole, n_rest, u_rest)
        # the rest pose may already be bent: measure the rest bend and keep it relative
        f_rest = (self.head[end] - self.head[lower]).normalized()
        u0 = u_rest.normalized()
        n0 = Vector(n_rest) - u0 * Vector(n_rest).dot(u0)
        n0.normalize()
        # rotation of the lower bone in its rest frame is already included by two_bone (it maps u0 frame to f1
        # frame); correct for a bent rest lower segment
        bend_rest = u0.rotation_difference(f_rest)
        Qf = Qf @ bend_rest.inverted()
        self.set_world(loc, Qa, upper, Qu)
        loc[lower] = Qu.inverted() @ Qf
        return Qu, Qf

    reach_log = None

    def arm_ik(self, loc, hip_off, side, wrist, pole, hand_world_q=None):
        Qa, pos = self.fk(loc, hip_off)
        up, lo, ha = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
        over = (Vector(wrist) - pos[up]).length - (self.ulen + self.flen)
        if over > 0.01:
            if self.reach_log is None:
                self.reach_log = []
            self.reach_log.append((side, round(over, 3)))
        u_rest = self.head[lo] - self.head[up]
        n_rest = Vector((0, 0, -1)) if side == "l" else Vector((0, 0, 1))
        Qu, Qf = self.two_bone(pos[up], wrist, self.ulen, self.flen, pole, n_rest, u_rest)
        self.set_world(loc, Qa, up, Qu)
        loc[lo] = Qu.inverted() @ Qf
        if hand_world_q is not None:
            loc[ha] = Qf.inverted() @ hand_world_q
        return Qu, Qf

    def leg_ik(self, loc, hip_off, side, ankle, yaw, pitch, ball):
        Qa, pos = self.fk(loc, hip_off)
        th, ca, fo = "thigh_" + side, "calf_" + side, "foot_" + side
        u_rest = self.head[ca] - self.head[th]
        fwd = Quaternion((0, 0, 1), math.radians(yaw)) @ Vector((0, -1, 0))
        out = Vector((0.25 if side == "l" else -0.25, 0, 0))
        Qt, Qc = self.two_bone(pos[th], ankle, self.thl, self.cal, fwd + out, Vector((1, 0, 0)), u_rest)
        self.set_world(loc, Qa, th, Qt)
        loc[ca] = Qt.inverted() @ Qc
        Qfoot = Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(-pitch))
        loc[fo] = Qc.inverted() @ Qfoot
        if "ball_" + side in self.head:
            loc["ball_" + side] = E((ball, 0, 0))

    # ---------------------------------------------------------------- hands and items
    def hand_q_from_item(self, it, Rs):
        Mw = Rs @ it.grip_rot.transposed()
        return (Mw @ self.R[it.bone].transposed()).to_quaternion()

    def wrist_for_item(self, it, Rs, grip_world, use_off=False):
        Mh = Rs @ it.grip_rot.transposed()
        gp = it.off_grip_pos if use_off else it.grip_pos
        return Vector(grip_world) - Mh @ gp

    def fingers(self, loc, side, fist, spread=0.0, claw=0.0, preset="sword"):
        """fist 0..1 blends from the open rest hand to a closed grip taken from the UAL clips (Sword_Idle right
        hand, mirrored for the left; 'torch' = Idle_Torch_Loop left hand, a looser grip for thick handles).
        claw hooks the finger tips (swipes), spread opens and fans the fingers."""
        sg = 1 if side == "l" else -1
        G = GRIPS[preset]
        o = spread
        for f in FINGERS + ("thumb",):
            for k in ("01", "02", "03"):
                b = "%s_%s_%s" % (f, k, side)
                if b not in self.head:
                    continue
                e = G[f + "_" + k]
                e = (e[0], sg * e[1], sg * e[2])          # presets are stored for the LEFT hand
                q = Quaternion().slerp(E(e), max(0.0, min(1.0, fist)))
                extra = (0.0, 0.0, 0.0)
                if f != "thumb":
                    sp = {"index": 6, "middle": 0, "ring": -6, "pinky": -12}[f] * o
                    hook = {"01": -10.0, "02": 55.0, "03": 45.0}[k] * claw
                    extra = (0.0, sg * (hook - (10 * o if k == "01" else 0)), -sg * sp if k == "01" else 0.0)
                else:
                    extra = (0.0, sg * {"01": 0.0, "02": 15.0, "03": 25.0}[k] * claw, 0.0)
                loc[b] = E(extra) @ q

    _gc = None

    def grip_centre(self, side, preset="sword", fist=1.0):
        key = (side, preset, round(fist, 3))
        if self._gc is None:
            self._gc = {}
        if key in self._gc:
            return self._gc[key]
        self._gc[key] = self._grip_centre(side, preset, fist)
        return self._gc[key]

    def _grip_centre(self, side, preset="sword", fist=1.0):
        """(x, y) in hand bone-local space of the axis the closed fist wraps (handle axis = local Z), and the
        radius from that axis to the finger joint centres."""
        loc = {}
        self.fingers(loc, side, fist, preset=preset)
        Qa, pos = self.fk(loc, (0, 0, 0))
        Mh = self.world_matrix(Qa, pos, "hand_" + side).inverted()
        pts = []
        for f in ("index", "middle", "ring"):
            for k in ("01", "02", "03", "04_leaf"):
                b = "%s_%s_%s" % (f, k, side)
                if b in pos:
                    pts.append(list(Mh @ pos[b])[:2])
        P = np.array(pts)
        A_ = np.c_[2 * P, np.ones(len(P))]
        c = np.linalg.lstsq(A_, (P ** 2).sum(1), rcond=None)[0]
        return (float(c[0]), float(c[1])), float(np.sqrt(c[2] + c[0] ** 2 + c[1] ** 2))


# closed-hand presets (rest-axes eulers, LEFT hand; the right hand mirrors ry, rz), sampled from UAL1 clips
GRIPS = {
    "sword": {  # UAL1 Sword_Idle (right hand, mirrored): a hammer grip around a ~4 cm handle, thumb over the fingers
        "index_01": (0.0, 78.0, 0.0), "index_02": (0.0, 77.1, 0.0), "index_03": (0.0, 77.1, 0.0),
        "middle_01": (-12.6, 77.7, -10.1), "middle_02": (-10.9, 76.9, -8.7), "middle_03": (-11.5, 76.9, -9.1),
        "ring_01": (-9.5, 77.9, -7.7), "ring_02": (-8.8, 77.0, -7.0), "ring_03": (-9.4, 76.9, -7.4),
        "pinky_01": (-54.5, 78.4, -56.9), "pinky_02": (-27.7, 75.4, -23.9), "pinky_03": (-16.4, 76.6, -13.0),
        "thumb_01": (7.4, 3.8, 8.8), "thumb_02": (13.8, -4.2, 20.6), "thumb_03": (32.3, -23.7, 72.1)},
    "torch": {  # UAL1 Idle_Torch_Loop left hand: looser grip around a ~6 cm handle
        "index_01": (12.9, 64.1, 20.5), "index_02": (8.4, 47.4, 5.9), "index_03": (0.0, 43.6, 0.0),
        "middle_01": (4.0, 65.4, 11.7), "middle_02": (4.4, 47.5, 3.4), "middle_03": (-3.7, 54.4, -1.9),
        "ring_01": (2.3, 65.9, 7.6), "ring_02": (-0.3, 47.5, -0.1), "ring_03": (-2.8, 52.6, -1.4),
        "pinky_01": (2.2, 67.1, 11.1), "pinky_02": (-1.7, 47.4, -0.8), "pinky_03": (-19.3, 52.8, -13.8),
        "thumb_01": (37.4, 32.9, 26.4), "thumb_02": (44.3, -41.4, -6.5), "thumb_03": (7.0, -26.9, 30.4)},
}


# -------------------------------------------------------------------- key interpolation
def _vec(v):
    return np.array(v if isinstance(v, (list, tuple, np.ndarray)) else [v], np.float64)


def interp_channel(keys, ch, f, cyclic=False, default=None):
    fr = [k[0] for k in keys]
    vals = [_vec(k[1].get(ch, default)) for k in keys]
    n = len(keys)
    if f <= fr[0]:
        return vals[0]
    if f >= fr[-1]:
        return vals[-1]
    i = max(j for j in range(n - 1) if fr[j] <= f)
    t0, t1 = fr[i], fr[i + 1]

    def slope(a, b):
        return (vals[b] - vals[a]) / max(fr[b] - fr[a], 1e-6)

    def tangents(j):
        o = keys[j][2] if len(keys[j]) > 2 else {}
        flow = o.get("flow", 0.0)
        if 0 < j < n - 1:
            sl, sr = slope(j - 1, j), slope(j, j + 1)
        elif cyclic and n > 2:
            if j == 0:
                sl = (vals[-1] - vals[-2]) / max(fr[-1] - fr[-2], 1e-6)
                sr = slope(0, 1)
            else:
                sl = slope(n - 2, n - 1)
                sr = (vals[1] - vals[0]) / max(fr[1] - fr[0], 1e-6)
        else:
            return np.zeros_like(vals[j]), np.zeros_like(vals[j])
        avg = 0.5 * (sl + sr)
        same = np.sign(sl) == np.sign(sr)
        m = np.where(same, avg, 0.0) * flow
        tin = o.get("tin", None)
        tout = o.get("tout", None)
        mi = sl * tin if tin is not None else m
        mo = sr * tout if tout is not None else m
        return mi, mo

    _, m0 = tangents(i)
    m1, _ = tangents(i + 1)
    h = t1 - t0
    t = (f - t0) / h
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    return h00 * vals[i] + h10 * h * m0 + h01 * vals[i + 1] + h11 * h * m1


def sample_pose(keys, f, cyclic=False):
    chans = set()
    for k in keys:
        chans |= set(k[1].keys())
    out = {}
    for c in chans:
        missing = [k for k in keys if c not in k[1]]
        if missing:
            raise KeyError("channel %s missing in some keys (use P() bases)" % c)
        v = interp_channel(keys, c, f, cyclic)
        out[c] = v if len(v) > 1 else float(v[0])
    return out


def add(p, k, e):
    p[k] = tuple(a + b for a, b in zip(p[k], e))


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def lerpv(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# -------------------------------------------------------------------- pendulum (chains, lanterns)
class Pendulum:
    def __init__(self, length=0.30, damping=0.985, substeps=8, g=9.81):
        self.Lp = length
        self.damp = damping
        self.sub = substeps
        self.g = g
        self.x = None
        self.xp = None

    def reset(self, pivot, direction=(0, 0, -1)):
        self.x = Vector(pivot) + Vector(direction).normalized() * self.Lp
        self.xp = self.x.copy()

    def step(self, piv0, piv1, dt):
        piv0, piv1 = Vector(piv0), Vector(piv1)
        h = dt / self.sub
        for k in range(self.sub):
            pv = piv0.lerp(piv1, (k + 1) / self.sub)
            v = (self.x - self.xp) * (self.damp ** (1.0 / self.sub))
            self.xp = self.x.copy()
            self.x = self.x + v + Vector((0, 0, -self.g)) * h * h
            d = self.x - pv
            self.x = pv + d.normalized() * self.Lp
        return (self.x - piv1).normalized()


# -------------------------------------------------------------------- humanoid pose solver
EULER_SKIP = {"hip_off", "L_foot", "R_foot", "L_ball", "R_ball", "R_wrist", "L_wrist", "R_hand", "L_hand", "R_pole",
              "L_pole", "R_item", "L_item", "L_on", "R_on", "L_on_s", "R_on_s", "fist_l", "fist_r", "spread_l",
              "spread_r", "claw_l", "claw_r", "shake", "L_on_roll", "R_on_roll", "L_on_flip", "R_on_flip"}


class Solver:
    """turns a pose dict into local quaternions (+ translations / scales) for a Rig."""

    def __init__(self, rig, hold=None, post=None):
        self.rig = rig
        self.hold = hold or {}            # side -> item name held in that hand ('r': 'sword')
        self.post = post                  # post(solver, p, loc, tloc, scl, po) hook for extras
        self.presets = {}                 # side -> grip preset name ('sword' default, 'torch')

    def build(self, p):
        rig = self.rig
        loc, tloc, scl = {}, {}, {}
        for k, v in p.items():
            if k in EULER_SKIP:
                continue
            if k.endswith("@loc"):
                tloc[k[:-4]] = Vector(v)
            elif k.endswith("@scl"):
                scl[k[:-4]] = float(v) if not isinstance(v, (tuple, list)) else float(v[0])
            elif k in rig.head:
                loc[k] = E(v)
        po = Vector(p.get("hip_off", (0, 0, 0)))
        if rig.humanoid:
            for s in ("l", "r"):
                on = p.get(s.upper() + "_on", 0.0)
                fist = p.get("fist_" + s, 0.0)
                rig.fingers(loc, s, fist, p.get("spread_" + s, 0.0), p.get("claw_" + s, 0.0), self.presets.get(s, "sword"))
            for s in ("l", "r"):
                f = p.get(s.upper() + "_foot")
                if f is not None:
                    rig.leg_ik(loc, po, s, Vector(f[:3]), f[3], f[4], p.get(s.upper() + "_ball", 0.0))
            Rs = {}
            # item hands first (they define where a supporting hand goes)
            for s in ("r", "l"):
                key = s.upper() + "_item"
                if key in p and s in self.hold:
                    it = rig.items[self.hold[s]]
                    v = p[key]
                    R, d = item_frame(v[3], v[4], v[5])
                    Rs[s] = (it, R, Vector(v[:3]))
                    qh = rig.hand_q_from_item(it, R)
                    wrist = rig.wrist_for_item(it, R, v[:3])
                    rig.arm_ik(loc, po, s, wrist, Vector(p.get(s.upper() + "_pole", (0, 0, -1))), qh)
            for s in ("r", "l"):
                if s in Rs:
                    continue
                o = "l" if s == "r" else "r"
                t = max(0.0, min(1.0, p.get(s.upper() + "_on", 0.0)))
                key_w = s.upper() + "_wrist"
                if key_w not in p and t <= 0:
                    continue
                pole = Vector(p.get(s.upper() + "_pole", (0, 0, -1)))
                wf = Vector(p.get(key_w, (0, 0, 1)))
                if t > 0 and o in Rs:
                    it, R, grip = Rs[o]
                    wh, qhs = self.on_item(s, it, R, grip, p.get(s.upper() + "_on_s", 0.3),
                                           p.get(s.upper() + "_on_roll", 0.0), p.get(s.upper() + "_on_flip", 0.0) > 0.5)
                    if key_w not in p:
                        wf = wh
                    rig.arm_ik(loc, po, s, wf.lerp(wh, t), pole)
                    Qa, pos = rig.fk(loc, po)
                    qfree = Qa["lowerarm_" + s] @ E(p.get(s.upper() + "_hand", (0, 0, 0)))
                    loc["hand_" + s] = Qa["lowerarm_" + s].inverted() @ qfree.slerp(qhs, t)
                else:
                    rig.arm_ik(loc, po, s, wf, pole)
                    if s.upper() + "_hand" in p:
                        loc["hand_" + s] = E(p[s.upper() + "_hand"])
            self.Rs = Rs
        if self.post:
            self.post(self, p, loc, tloc, scl, po)
        return loc, tloc, scl, po

    def on_item(self, s, it, R, grip, dist, roll=0.0, flip=False):
        """wrist target + accumulated world hand rotation for the supporting fist closed around the item axis
        `dist` metres from the main grip toward the tip. Default: overhand, palm on the item's face-normal side,
        index finger toward the main grip; roll turns the hand about the item axis, flip points the index finger
        toward the tip (underhand)."""
        rig = self.rig
        d = -R.col[2]
        Ys = R.col[1]
        pnt = Vector(grip) + d * dist
        zl = d.copy() if flip else -d
        palm = Quaternion(d, math.radians(roll)) @ Ys
        xl = palm if s == "l" else -palm
        xl = (xl - zl * xl.dot(zl)).normalized()
        yl = zl.cross(xl)
        Mw = Matrix((xl, yl, zl)).transposed()
        (cx, cy), _ = rig.grip_centre(s, self.presets.get(s, "sword"))
        gp = Vector((cx, cy, -0.005))
        wrist = pnt - Mw @ gp
        return wrist, (Mw @ rig.R["hand_" + s].transposed()).to_quaternion()


def make_item(rig, name, side, preset="sword", roll=0.0, z=-0.005):
    """Item gripped in a closed fist: item tip direction (-Z) leaves the fist on the index/thumb side, the item's
    face normal (+Y) points along the palm normal turned by roll about the handle."""
    (cx, cy), r = rig.grip_centre(side, preset)
    zi = Vector((0, 0, -1))                       # item +Z (toward the grip end) -> hand -Z (pinky side)
    palm = Vector((1, 0, 0)) if side == "l" else Vector((-1, 0, 0))
    yi = Quaternion((0, 0, 1), math.radians(roll)) @ palm
    xi = yi.cross(zi)
    G = Matrix((xi, yi, zi)).transposed()         # columns = images of item X, Y, Z in hand-local axes
    it = Item(name, "hand_" + side, np.array(G), (cx, cy, z))
    rig.items[name] = it
    return it, r


def to_basis(rig, loc, tloc, scl, po):
    out = {}
    for b in rig.order:
        q = loc.get(b, Quaternion())
        Qr = rig.Q[b]
        out[b] = Qr.inverted() @ q @ Qr
    locs = {}
    hp = Vector(po)
    locs[rig.hip] = rig.R[rig.hip].inverted() @ hp
    for b, t in tloc.items():
        # tloc is expressed in the parent's (delta-rotated) armature axes -> bone-local basis translation
        locs[b] = locs.get(b, Vector()) + rig.R[b].inverted() @ Vector(t)
    return out, locs, dict(scl)


class Clip:
    """keys: [(frame, pose, opts)] or posefn(f) -> pose; layer(p, f) adds procedural motion; shake adds tremble."""

    def __init__(self, name, length, keys=None, posefn=None, cyclic=False, layer=None, events=None, shake_bones=None):
        self.name, self.n, self.keys, self.posefn = name, length, keys, posefn
        self.cyclic, self.layer = cyclic, layer
        self.events = events or {}
        self.shake_bones = shake_bones or ("spine_02", "spine_03", "Head")

    def pose_at(self, f):
        p = self.posefn(f) if self.posefn else sample_pose(self.keys, f, self.cyclic)
        for k, v in list(p.items()):
            if isinstance(v, np.ndarray):
                p[k] = tuple(float(x) for x in v)
        if self.layer:
            self.layer(p, f)
        s = p.get("shake", 0.0)
        if s > 1e-3:
            t = f / FPS
            a = s * math.sin(t * 2 * math.pi * 9.0) * 0.6 + s * math.sin(t * 2 * math.pi * 13.0 + 1.3) * 0.4
            for i, b in enumerate(self.shake_bones):
                if b in p:
                    add(p, b, (0.9 * a, 0.4 * a * (i % 2), 0.5 * a))
        return p

    def bake(self, solver, extra=None):
        """-> list of (basis quats, basis locs, scales) per frame. extra(frames_built) may post-process (pendulums)."""
        frames = list(range(self.n + 1))
        poses = [self.pose_at(f) for f in frames]
        built = []
        for f, p in zip(frames, poses):
            solver.rig.reach_log = None
            built.append(solver.build(p))
            if solver.rig.reach_log:
                print("WARN reach %s f%d: wrist target beyond arm length by %s" % (self.name, f, solver.rig.reach_log))
        if extra:
            extra(self, poses, built)
        return [to_basis(solver.rig, *b) for b in built]

    def write_action(self, rig, frames, loc_bones=None):
        import bpy
        if self.name in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[self.name])
        act = bpy.data.actions.new(self.name)
        act.use_fake_user = True
        slot = act.slots.new(id_type='OBJECT', name="Armature")
        lay = act.layers.new("Layer")
        strip = lay.strips.new(type='KEYFRAME')
        cb = strip.channelbag(slot, ensure=True)
        n = len(frames)
        fr = np.arange(n, dtype=np.float32)

        def put(path, idx, vals, grp):
            fc = cb.fcurves.new(path, index=idx)
            if grp is not None:
                fc.group = grp
            fc.keyframe_points.add(n)
            fc.keyframe_points.foreach_set("co", np.stack([fr, np.asarray(vals, np.float32)], 1).ravel())
            fc.keyframe_points.foreach_set("interpolation", np.full(n, 1, np.int32))

        for b in rig.order:
            qs = [fq[0][b] for fq in frames]
            for i in range(1, n):
                if qs[i].dot(qs[i - 1]) < 0:
                    qs[i] = -qs[i]
            arr = np.array([[q.w, q.x, q.y, q.z] for q in qs], np.float32)
            grp = cb.groups.new(b) if hasattr(cb, "groups") else None
            for c in range(4):
                put('pose.bones["%s"].rotation_quaternion' % b, c, arr[:, c], grp)
            locs = np.array([list(fq[1].get(b, (0, 0, 0))) for fq in frames], np.float32)
            for c in range(3):
                put('pose.bones["%s"].location' % b, c, locs[:, c], grp)
            sc = np.array([fq[2].get(b, 1.0) for fq in frames], np.float32)
            for c in range(3):
                put('pose.bones["%s"].scale' % b, c, sc, grp)
        act.use_frame_range = True
        act.frame_start = 0
        act.frame_end = self.n
        act.use_cyclic = self.cyclic
        return act


def tau(f, n):
    return 2 * math.pi * f / n


def bake_all(arm, rig, clips, solver_for, report, extra_for=None, only=None):
    """bake + write every clip; report[name] gets frames/seconds/events. solver_for(clip) -> Solver."""
    import bpy
    for c in clips:
        if only and c.name not in only:
            continue
        frames = c.bake(solver_for(c), extra_for(c) if extra_for else None)
        c.write_action(rig, frames)
        r = dict(c.events)
        r["frames"] = c.n + 1
        r["seconds"] = round(c.n / FPS, 3)
        if c.cyclic:
            r["loop"] = True
        report[c.name] = r
        print("ANIM %-28s frames=%d (%.2fs)" % (c.name, c.n + 1, c.n / FPS))
    if arm.animation_data is None:
        arm.animation_data_create()
    return report

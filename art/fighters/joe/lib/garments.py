"""Garment / gear geometry for the JoeBrawla human fighters (fitted to the UBC male body, rest = T-pose).

Character faces -Y, his left = +X, arms along +-X in the rest pose. Everything is world space, identity transform.
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.kdtree import KDTree
import djlib as dj
import djarmor as ar
import aggeo as G
from djlib import MB
from agcore import smooth01, lerp, LR

TORSO = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01'}
ARM_UP = {'upperarm_l', 'upperarm_r'}
ARM_LO = {'lowerarm_l', 'lowerarm_r'}
LEG_UP = {'thigh_l', 'thigh_r'}
LEG_LO = {'calf_l', 'calf_r'}
FEET = {'foot_l', 'foot_r', 'ball_l', 'ball_r'}


# ----------------------------------------------------------------------------------------------
# glyph strokes -> image (patch lettering, badges)
# ----------------------------------------------------------------------------------------------
GLYPHS = {
    '3': [[(0.18, 0.88), (0.38, 1), (0.66, 1), (0.82, 0.84), (0.8, 0.62), (0.55, 0.52), (0.82, 0.4), (0.84, 0.16), (0.65, 0), (0.36, 0), (0.16, 0.12)]],
    'C': [[(0.85, 0.85), (0.65, 1), (0.35, 1), (0.15, 0.8), (0.15, 0.2), (0.35, 0), (0.65, 0), (0.85, 0.15)]],
    'M': [[(0.12, 0), (0.12, 1), (0.5, 0.45), (0.88, 1), (0.88, 0)]],
    'F': [[(0.82, 1), (0.2, 1), (0.2, 0)], [(0.2, 0.52), (0.65, 0.52)]],
    'A': [[(0.1, 0), (0.5, 1), (0.9, 0)], [(0.28, 0.42), (0.72, 0.42)]],
    'N': [[(0.15, 0), (0.15, 1), (0.85, 0), (0.85, 1)]],
    'G': [[(0.85, 0.85), (0.65, 1), (0.35, 1), (0.15, 0.8), (0.15, 0.2), (0.35, 0), (0.65, 0), (0.85, 0.18), (0.85, 0.45), (0.55, 0.45)]],
    'E': [[(0.82, 1), (0.2, 1), (0.2, 0), (0.82, 0)], [(0.2, 0.52), (0.7, 0.52)]],
    'T': [[(0.1, 1), (0.9, 1)], [(0.5, 1), (0.5, 0)]],
    '-': [[(0.25, 0.5), (0.75, 0.5)]],
}


def text_strokes(text, x, y, h, width_frac=0.13, spacing=0.8, center=True):
    w = h * spacing
    total = w * len(text)
    x0 = x - total / 2 if center else x
    out = []
    for i, ch in enumerate(text):
        for poly in GLYPHS.get(ch, []):
            pts = [(x0 + i * w + px * w * 0.9, y + py * h) for px, py in poly]
            for a, b in zip(pts[:-1], pts[1:]):
                out.append((a, b, h * width_frac))
    return out


def stroke_image(name, w, h, strokes, res=512):
    rx = res
    ry = max(16, int(res * h / w))
    xs = (np.arange(rx) + 0.5) / rx * w
    ys = (np.arange(ry) + 0.5) / ry * h
    X, Y = np.meshgrid(xs, ys)
    out = np.zeros((ry, rx), np.float32)
    for (a, b, wd) in strokes:
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy + 1e-12
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        v = np.clip(1 - d / wd, 0, 1)
        v = v * v * (3 - 2 * v)
        np.maximum(out, v, out=out)
    img = bpy.data.images.new(name, rx, ry, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    px = np.ones((ry, rx, 4), np.float32)
    px[:, :, 0] = out
    px[:, :, 1] = out
    px[:, :, 2] = out
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


# ----------------------------------------------------------------------------------------------
# surface helpers
# ----------------------------------------------------------------------------------------------
def patch_on(bvh, center, U, V, hu, hv, toward, off, nu=8, nv=8, round_r=0.0, name='patch', far=0.25, uv_name='aux'):
    """Rounded-rectangle patch draped on the outermost surface (rays along `toward`), lifted by off; 'aux' UV:
    u along U, v along V (0..1)."""
    c, U, V, T = Vector(center), Vector(U).normalized(), Vector(V).normalized(), Vector(toward).normalized()

    def squash(x, y):
        if round_r <= 0:
            return x, y
        ax_, ay_ = abs(x) * hu, abs(y) * hv
        cx_, cy_ = hu - round_r, hv - round_r
        if ax_ > cx_ and ay_ > cy_:
            dx, dy = ax_ - cx_, ay_ - cy_
            d = math.hypot(dx, dy)
            if d > 1e-9:
                # map the square corner onto a quarter circle
                k = max(dx, dy) / d
                ax_ = cx_ + dx * k
                ay_ = cy_ + dy * k
        return math.copysign(ax_ / hu, x), math.copysign(ay_ / hv, y)

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new(uv_name)
    rows = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            x = (i / nu - 0.5) * 2
            y = (j / nv - 0.5) * 2
            sx, sy = squash(x, y)
            p = c + U * (sx * hu) + V * (sy * hv)
            loc, nrm, idx, dist = bvh.ray_cast(p - T * far, T, far * 2)
            q = (loc - T * off) if loc is not None else p
            row.append((bm.verts.new(q), (sx * 0.5 + 0.5, sy * 0.5 + 0.5)))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            quad = (rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
            f = bm.faces.new([q[0] for q in quad])
            for l, q in zip(f.loops, quad):
                l[uvl].uv = q[1]
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    dj.link(ob)
    me.shade_smooth()
    return ob


def thicken(ob, t, offset=1.0, rim=True):
    m = ob.modifiers.new('sol', 'SOLIDIFY')
    m.thickness = t
    m.offset = offset
    m.use_even_offset = True
    m.use_rim = rim
    dj.apply_mods(ob)
    ob.data.shade_smooth()
    return ob


def ring_sweep(pts, width, thick, name, axis, sides=8, exp=3.5):
    """closed loop pts swept with a rounded-box section: `width` along axis, `thick` radial."""
    P = pts + pts[:2]
    mb = MB()
    mb.sweep(P, [(width * 0.5, thick * 0.5)] * len(P), sides=sides, exp=exp, up=axis, cap0=None, cap1=None)
    return mb.to_object(name)


def limb_loop(bvh, center, axis, up, off, n=28, smooth=2, maxd=0.2):
    pts = G.band_loop(bvh, Vector(center), Vector(axis), Vector(up), n, off, inside=True, maxd=maxd)
    return G.smooth_loop(pts, smooth)


def roll_cuff(bvh, center, axis, up=(0, 0, 1), width=0.05, thick=0.016, off=0.004, n=30, name='cuff', bulge=0.004,
              seed=0.0):
    """rolled-up sleeve / trouser cuff: a fat band (two stacked rolls) round the limb."""
    a = Vector(axis).normalized()
    c = Vector(center)
    out = []
    for k, (dz, w, t) in enumerate(((0.0, width, thick), (-width * 0.42, width * 0.55, thick * 0.75))):
        pts = limb_loop(bvh, c + a * dz, a, up, off + t * 0.5, n)
        pts = [p + (p - (c + a * dz)).normalized() * (bulge * (0.5 + 0.5 * noise.noise(p * 40 + Vector((seed, k, 0)))))
               for p in pts]
        out.append(ring_sweep(pts, w, t, name + str(k), a, sides=6))
    return dj.join(out, name)


# ----------------------------------------------------------------------------------------------
# shirt collar (spread collar on an open shirt)
# ----------------------------------------------------------------------------------------------
def shirt_collar(body, bvh, name, z_back=None, z_front=None, gap=0.62, stand=0.026, fall=0.045, point=0.045, off=0.012,
                 nu=44, nv=8, thick=0.003, flare=0.018, stand_tilt=0.0):
    """Collar round the neck from the right front tip, around the back, to the left front tip.
    gap: half-angle (rad) of the open front measured from straight ahead."""
    L = body.L
    nc = Vector((0, L['neck'].y + 0.004, 0))
    z_back = z_back if z_back is not None else L['neck'].z + 0.005
    z_front = z_front if z_front is not None else L['neck'].z - 0.06

    def base(th):
        # th = 0 front (-Y), +-pi back
        zf = smooth01(abs(th), 0.0, math.pi)       # 0 front .. 1 back
        z = lerp(z_front, z_back, zf ** 0.7)
        d = Vector((math.sin(th), -math.cos(th), 0))
        st = Vector((nc.x, nc.y, z)) + d * 0.35
        loc, n, i, dist = bvh.ray_cast(st, -d, 0.35)
        r = (0.35 - dist) if loc is not None else 0.07
        # hug the neck at the sides and back (a ray there would land on the trapezius / shoulders)
        frontk = max(0.0, math.cos(th)) ** 2
        r = min(r, r_neck + 0.045 * frontk)
        return Vector((nc.x, nc.y, z)) + d * (r + off), d
    # neck radius just above the shirt line
    rs = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        d = Vector((math.sin(a), -math.cos(a), 0))
        st = Vector((nc.x, nc.y, L['neck'].z + 0.02)) + d * 0.3
        loc, n, i, dist = bvh.ray_cast(st, -d, 0.3)
        if loc is not None:
            rs.append(0.3 - dist)
    r_neck = (sum(rs) / len(rs) if rs else 0.06) + 0.006

    def fn(u, v):
        # u: 0 = front-left tip (his left = +X), around the back, 1 = front-right tip
        th = gap + (2 * math.pi - 2 * gap) * u
        th = th if th <= math.pi else th - 2 * math.pi
        B, d = base(th)
        up = Vector((0, 0, 1))
        frontk = max(0.0, math.cos(th)) ** 1.5
        fl = fall + point * frontk
        # profile: stand up, fold over, fall down/out
        if v <= 0.35:
            s = v / 0.35
            p = B + up * (stand * s) + d * (stand_tilt * s)
        elif v <= 0.5:
            s = (v - 0.35) / 0.15
            p = B + up * (stand + 0.004 * math.sin(math.pi * s)) + d * (0.006 * s + stand_tilt)
        else:
            s = (v - 0.5) / 0.5
            p = B + up * (stand + 0.004 - (stand + 0.004 + fl * 0.55) * s) + d * (0.006 + stand_tilt + (flare + fl * 0.35) * s)
            # the points flare forward and outward at the front
            p += Vector((math.sin(th), 0, 0)) * (0.012 * frontk * s)
        return p
    mb = MB()
    mb.grid(lambda a, b: fn(b, a), nv, nu)      # rows = profile (v), columns = around the neck (u)
    ob = mb.to_object(name)
    ob.data.update()
    if thick > 0:
        thicken(ob, thick, offset=0.0)
    return ob


# ----------------------------------------------------------------------------------------------
# work boot
# ----------------------------------------------------------------------------------------------
def boot_upper(body, side, name, sole_h=0.03, off=0.013, toe_h=0.072, shaft_top=0.2, shaft_off=0.012, toe_len=0.012,
               n=22, exp=2.6, shaft_flare=0.006):
    """Boot upper as a designed shape: a lofted foot (superellipse arch over a flat bottom, measured from the body's
    foot and smoothed: one round toe box, no toes) + a shaft tube round the ankle / shin up to shaft_top."""
    sg = 1 if side == 'l' else -1
    fb = (LR('foot_l', side), LR('ball_l', side))
    P = np.array([list(c) for c, d in zip(body.co, body.dom) if d in fb and c.x * sg > 0])
    y_heel = P[:, 1].max() + off * 0.7
    y_toe = P[:, 1].min() - off - toe_len
    ys = np.linspace(y_heel, y_toe, n)
    cx, hw, zt = [], [], []
    for y in ys:
        sl = P[np.abs(P[:, 1] - y) < 0.016]
        if len(sl) < 3:
            sl = P[np.argsort(np.abs(P[:, 1] - y))[:6]]
        cx.append((sl[:, 0].min() + sl[:, 0].max()) / 2)
        hw.append((sl[:, 0].max() - sl[:, 0].min()) / 2 + off)
        zt.append(sl[:, 2].max() + off)
    cx, hw, zt = np.array(cx), np.array(hw), np.array(zt)
    for _ in range(3):
        cx[1:-1] = (cx[:-2] + cx[1:-1] * 2 + cx[2:]) / 4
        hw[1:-1] = (hw[:-2] + hw[1:-1] * 2 + hw[2:]) / 4
        zt[1:-1] = (zt[:-2] + zt[1:-1] * 2 + zt[2:]) / 4
    ball = body.h(LR('ball_l', side))
    length = y_heel - y_toe
    rings = []
    mb = MB()
    m_up, m_lo = 12, 5
    for i, y in enumerate(ys):
        d_toe = y - y_toe
        d_heel = y_heel - y
        # plan-view rounding of both ends (quarter ellipses)
        rt, rh = 0.05, 0.035
        kt = math.sqrt(max(0.0, 1 - max(0.0, 1 - d_toe / rt) ** 2)) if d_toe < rt else 1.0
        kh = math.sqrt(max(0.0, 1 - max(0.0, 1 - d_heel / rh) ** 2)) if d_heel < rh else 1.0
        k = max(0.04, min(kt, kh))
        toe_k = smooth01(ball.y + 0.03 - y, 0.0, 0.07)
        zb = sole_h + 0.012 * smooth01(ball.y - y, 0.0, 0.07) ** 2
        h = max(zt[i], toe_h) if toe_k > 0.5 else max(zt[i], lerp(zt[i], toe_h, toe_k * 2))
        w = max(hw[i], 0.043) * (k ** 0.6)
        zz = zb + (h - zb) * (k ** 0.35)
        ring = []
        for j in range(m_up + 1):
            a = math.pi * j / m_up
            c, s = math.cos(a), math.sin(a)
            ex = 2.0 / exp
            xx = cx[i] + w * math.copysign(abs(c) ** ex, c)
            zq = zb + (zz - zb) * (abs(s) ** ex)
            ring.append(mb.v(Vector((xx, y, zq))))
        for j in range(1, m_lo):
            xx = cx[i] - w + 2 * w * j / m_lo
            ring.append(mb.v(Vector((xx, y, zb))))
        rings.append(ring)
    for a, b_ in zip(rings[:-1], rings[1:]):
        mb.ring_bridge(a, b_)
    mb.fan(rings[0], sum((v.co for v in rings[0]), Vector()) / len(rings[0]), flip=True)
    mb.fan(rings[-1], sum((v.co for v in rings[-1]), Vector()) / len(rings[-1]))
    foot = mb.to_object(name + "_foot")
    # shaft: loops round the ankle / shin from inside the foot up to the top (rays from outside onto the leg)
    kn, an = body.h(LR('calf_l', side)), body.h(LR('foot_l', side))
    zs = list(np.linspace(0.075, shaft_top, max(6, int((shaft_top - 0.075) / 0.045) + 1)))
    loops = []
    for z in zs:
        t = (z - an.z) / (kn.z - an.z)
        c = an.lerp(kn, max(0.0, t))
        c = Vector((c.x, c.y - 0.006, z))
        off_z = shaft_off + shaft_flare * smooth01(z, shaft_top - 0.04, shaft_top)
        pts = []
        for k in range(24):
            th = 2 * math.pi * k / 24
            d = Vector((math.sin(th), -math.cos(th), 0))
            # reach far enough for the calf, but not so far toward the other leg that the ray starts inside it
            far = 0.11 if d.x * sg < -0.4 else 0.17
            loc, nrm, idx, dist = body.bvh.ray_cast(c + d * far, -d, far)
            r = (far - dist) if loc is not None else 0.04
            pts.append(c + d * (max(r, 0.035) + off_z))
        loops.append(G.smooth_loop(pts, 3))
    mb2 = MB()
    vl = [[mb2.v(p) for p in lp] for lp in loops]
    for a, b_ in zip(vl[:-1], vl[1:]):
        mb2.ring_bridge(a, b_)
    shaft = mb2.to_object(name + '_shaft')
    up = dj.join([foot, shaft], name)
    up.data.shade_smooth()
    return up


def work_boot(body, stack, side, name, top_z=0.2, off=0.013, sole_h=0.03, heel_h=0.04, welt=0.007, toe=0.012,
              toe_h=0.072, shaft_off=0.012, smooth_iters=None):
    """Chunky lace-up work boot: a designed upper (boot_upper) on an extruded lug sole with a heel block."""
    L = body.L
    sg = 1 if side == 'l' else -1
    ball = body.h(LR('ball_l', side))
    ank = body.h(LR('foot_l', side))
    up = boot_upper(body, side, name + '_upper', sole_h=sole_h, off=off, toe_h=toe_h, shaft_top=top_z, shaft_off=shaft_off,
                    toe_len=toe)
    dj.push_out(up, stack.bvh(), 0.006, iters=3)        # clear of the body and anything tucked in (breeches)
    me = up.data
    me.update()
    # ---- sole outline from the upper's footprint
    co = np.array([list(v.co) for v in me.vertices])
    low = co[co[:, 2] < sole_h + 0.03]
    y0, y1 = low[:, 1].min() - welt * 0.6, low[:, 1].max() + welt * 0.4
    ny = 15
    left, right = [], []
    for i in range(ny + 1):
        y = y0 + (y1 - y0) * i / ny
        sl = low[np.abs(low[:, 1] - y) < (y1 - y0) / ny * 0.9]
        if len(sl) < 2:
            continue
        xa, xb = sl[:, 0].min() - welt, sl[:, 0].max() + welt
        left.append((xa, y))
        right.append((xb, y))
    # round the toe and heel ends
    outline = left + list(reversed(right))
    pts2 = np.array(outline)
    cen = pts2.mean(0)
    # chaikin smoothing
    for _ in range(1):
        P = pts2
        Q = []
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            Q.append(a * 0.75 + b * 0.25)
            Q.append(a * 0.25 + b * 0.75)
        pts2 = np.array(Q)
    heel_y = ank.y - 0.01

    def zt(x, y):
        return heel_h if y > heel_y else sole_h
    bm = bmesh.new()
    top = [bm.verts.new((x, y, zt(x, y))) for x, y in pts2]
    bot = [bm.verts.new((x, y, 0.0)) for x, y in pts2]
    mid = [bm.verts.new((x, y, zt(x, y) * 0.55)) for x, y in pts2]
    n = len(pts2)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top[j], top[i]))
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    me2 = bpy.data.meshes.new(name + '_sole')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me2)
    bm.free()
    sole = bpy.data.objects.new(name + '_sole', me2)
    dj.link(sole)
    # toe spring: lift the front of the sole a little
    for v in me2.vertices:
        k = smooth01(ball.y - v.co.y, 0.0, 0.07)
        v.co.z += 0.012 * k * k
        # mid ring bulges (welt)
    me2.update()
    bev = sole.modifiers.new('bev', 'BEVEL')
    bev.width = 0.004
    bev.segments = 1
    bev.limit_method = 'ANGLE'
    dj.apply_mods(sole)
    me2.shade_smooth()
    # welt: a stitched leather band where the upper meets the sole
    cen = pts2.mean(0)
    wp = []
    for x, y in pts2[::2]:
        d = np.array([x, y]) - cen
        q = np.array([x, y]) - d / max(np.linalg.norm(d), 1e-6) * welt * 0.55
        k = smooth01(ball.y - q[1], 0.0, 0.07)
        wp.append(Vector((q[0], q[1], zt(q[0], q[1]) + 0.004 + 0.012 * k * k)))
    wp = G.smooth_loop(wp, 2)
    welt_ob = ring_sweep(wp, 0.011, 0.007, name + '_welt', Vector((0, 0, 1)), sides=6, exp=3.0)
    return up, sole, welt_ob


def boot_laces(body, bvh, side, name, z0=0.06, z1=0.19, pairs=7, half=0.017):
    """eyelets/hooks + criss-cross laces down the instep (rays from the front)."""
    sg = 1 if side == 'l' else -1
    ank = body.h(LR('foot_l', side))
    ball = body.h(LR('ball_l', side))
    cx = ank.x
    mb_l = MB()
    mb_e = MB()
    holes = []
    for k in range(pairs):
        t = k / (pairs - 1)
        z = lerp(z0, z1, t)
        # the lace line runs from over the ball (low, forward) up the shin front
        yref = lerp(ball.y + 0.035, ank.y - 0.065, smooth01(t, 0.0, 0.55))
        row = []
        for sx in (-1, 1):
            x = cx + sx * half * (1.0 - 0.15 * t)
            st = Vector((x, -0.5, z))
            loc, nrm, idx, d = bvh.ray_cast(st, Vector((0, 1, 0)), 1.0)
            if loc is None:
                loc = Vector((x, yref, z))
                nrm = Vector((0, -1, 0))
            p = loc + nrm * 0.0015
            row.append((p, nrm))
            mb_e.lathe([(0.0045, -0.0008), (0.0042, 0.0016), (0.0018, 0.0016), (0.0018, -0.0008)], 6,
                       dj_frame(p, nrm))
        holes.append(row)
    for k in range(pairs - 1):
        a0, a1 = holes[k][0], holes[k][1]
        b0, b1 = holes[k + 1][0], holes[k + 1][1]
        for (p, n), (q, m) in ((a0, b1), (a1, b0)):
            mid = (p + q) * 0.5 + (n + m).normalized() * 0.004
            mb_l.sweep([p + n * 0.002, mid, q + m * 0.002], [0.0024] * 3, sides=5, cap0='flat', cap1='flat')
    for (p, n), (q, m) in (holes[0],):
        mb_l.sweep([p + n * 0.002, (p + q) * 0.5 + n * 0.004, q + m * 0.002], [0.0024] * 3, sides=5, cap0='flat', cap1='flat')
    return mb_l.to_object(name + '_laces'), mb_e.to_object(name + '_eyelets')


def dj_frame(p, n):
    z = Vector(n).normalized()
    x = z.orthogonal().normalized()
    y = z.cross(x)
    M3 = Matrix((x, y, z)).transposed()
    M4 = M3.to_4x4()
    M4.translation = Vector(p)
    return M4


# ----------------------------------------------------------------------------------------------
# hair
# ----------------------------------------------------------------------------------------------
def scalp_region(body, front_z=0.05, side_z=0.03, nape=0.07, temple=0.0):
    L = body.L
    hc = L['head_c']
    eye_z = (L['eye_l'].z + L['eye_r'].z) * 0.5
    ey = L['eye_l'].y

    def keep(c, b):
        if b not in ('Head', 'neck_01'):
            return False
        ax = abs(c.x)
        front = smooth01(-(c.y - ey), -0.06, 0.02)          # 1 at the face plane, 0 behind the ears
        # hairline height above the eyes: forehead high, temples a bit lower, behind the ears low
        z_line = eye_z + lerp(side_z, front_z + temple * smooth01(ax, 0.02, 0.06), front)
        if c.y > hc.y + 0.02:                               # back of the head: down to the nape
            z_line = min(z_line, L['neck'].z + nape + 0.05 * smooth01(ax, 0.02, 0.07))
        # keep the ears clear
        if ax > 0.058 and abs(c.y - (hc.y + 0.01)) < 0.035 and c.z < eye_z + 0.035:
            return False
        return c.z > z_line
    return keep


def messy_hair(body, stack, name, seed=3, n=95, length=(0.045, 0.095), r=(0.011, 0.017), cap_off=0.009, top_lift=0.016,
               fringe=0.35, sides=5, flat=0.55, front_z=0.055, cap=None, zf_min=-0.45, zf_span=2.2):
    """Short messy hair: a scalp cap with volume + tapered tufts swept from the crown, a few falling over the
    forehead. Returns (cap, tufts). With `cap` given (e.g. a stock hair mesh) only the tufts are made, rooted on it;
    zf_min limits how low on the head they start (sin of the elevation)."""
    L = body.L
    hc = L['head_c']
    eye_z = (L['eye_l'].z + L['eye_r'].z) * 0.5
    keep = scalp_region(body, front_z=front_z)
    if cap is not None:
        return cap, _tufts(body, cap, keep, name, seed, n, length, r, cap_off, fringe, sides, flat, zf_min, zf_span)
    cap = ar.extract_region(body.mesh, keep, name + '_cap')
    ar.smooth_offset(cap, 0.0, smooth_iters=4, factor=0.5)
    me = cap.data
    me.update()
    top = L['top']
    for v in me.vertices:
        h = smooth01(v.co.z, eye_z + 0.02, top)
        v.co += v.normal * (cap_off + top_lift * h + 0.004 * noise.noise(v.co * 35 + Vector((seed, 0, 0))))
    me.update()
    G.relax_boundary(cap, lambda pts: True, iters=4, factor=0.5)
    # hairline: tuck the boundary into the skin a little
    bvh_b = body.bvh
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        if v.is_boundary:
            loc, nrm, idx, d = bvh_b.find_nearest(v.co)
            if loc is not None:
                v.co = loc + nrm * 0.0015
    bm.to_mesh(me)
    bm.free()
    me.update()
    return cap, _tufts(body, cap, keep, name, seed, n, length, r, cap_off, fringe, sides, flat, zf_min, zf_span)


def _tufts(body, cap, keep, name, seed, n, length, r, cap_off, fringe, sides, flat, zf_min, zf_span):
    L = body.L
    hc = L['head_c']
    top = L['top']
    rnd = random.Random(seed)
    crown = Vector((0.0, hc.y + 0.045, top - 0.005))
    bvh_cap = dj.bvh_from([cap])
    mb = MB()
    tries = 0
    made = 0
    golden = math.pi * (3 - math.sqrt(5))
    while made < n and tries < n * 8:
        tries += 1
        # even (Fibonacci) coverage of the upper head, jittered
        k = tries
        zf = 1 - (k + 0.5) / (n * zf_span)
        if zf < zf_min:
            zf = rnd.uniform(zf_min, 1.0)
        el = math.asin(max(-1.0, min(1.0, zf))) + rnd.uniform(-0.06, 0.06)
        th = (k * golden) % (2 * math.pi) - math.pi + rnd.uniform(-0.1, 0.1)
        d = Vector((math.sin(th) * math.cos(el), -math.cos(th) * math.cos(el), math.sin(el)))
        loc, nrm, idx, dist = bvh_cap.ray_cast(hc + d * 0.3, -d, 0.3)
        if loc is None:
            continue
        if not keep(loc - nrm * (cap_off + 0.005), 'Head'):
            continue
        made += 1
        front = max(0.0, math.cos(th)) * smooth01(el, 0.2, 0.9)
        away = (loc - crown)
        away = away - nrm * away.dot(nrm)
        if away.length < 1e-4:
            away = Vector((rnd.uniform(-1, 1), -1, 0))
        away.normalize()
        topk = smooth01(el, 0.55, 1.3)                    # crown / top of the head
        Lh = rnd.uniform(*length) * (0.85 + 0.3 * topk)
        jit = Vector((noise.noise(loc * 14 + Vector((seed, 1, 0))), noise.noise(loc * 14 + Vector((seed, 2, 0))),
                      noise.noise(loc * 14 + Vector((seed, 3, 0))))) * (0.5 + 0.7 * topk)
        fz = math.cos(th)                                  # 1 front .. -1 back
        sz = abs(math.sin(th))
        if rnd.random() < fringe * front:
            # a few locks fall forward over the forehead
            fwd = Vector((rnd.uniform(-0.7, 0.7), -1.0, -0.35 - rnd.uniform(0, 0.4))).normalized()
            lift = rnd.uniform(0.15, 0.35)
            dirv = (fwd * 0.8 + jit * 0.35).normalized()
            Lh *= 0.85
        else:
            # flow field: swept up and back from the hairline, tousled on top, back-and-down on the sides,
            # down at the back
            flow = (Vector((0, 1.0, 0)) * max(0.25, 1 - max(0.0, -fz)) + Vector((0, 0, -1.0)) * max(0.0, -fz) * 1.2
                    + Vector((0, 0, -0.6)) * sz * (1 - topk) + Vector((0, 0, 0.7)) * max(0.0, fz) * (1 - topk))
            dirv = (flow.normalized() + jit * 0.9).normalized()
            lift = rnd.uniform(0.03, 0.15) + topk * rnd.uniform(0.2, 0.6) + max(0.0, fz) * (1 - topk) * 0.35
        dirv = (dirv - nrm * dirv.dot(nrm)).normalized()
        p0 = loc - nrm * 0.008
        p1 = loc + nrm * (Lh * 0.22 * lift + 0.003) + dirv * Lh * 0.3
        p3 = loc + dirv * Lh + nrm * (Lh * 0.42 * lift - 0.004)
        p2 = p3 - dirv * Lh * 0.32 + nrm * (0.004 + Lh * 0.1 * lift)
        pts = bez(p0, p1, p2, p3, 6)
        r0 = rnd.uniform(*r)
        nn = len(pts)
        # flat lock (thin along the scalp normal, wide along the surface), full most of its length, blunt tip
        prof = [r0 * (1 - 0.72 * (i / (nn - 1)) ** 2.2) for i in range(nn)]
        radii = [(q * flat, q) for q in prof]
        mb.sweep(pts, radii, sides=sides, cap0='flat', cap1='round', cap_segs=1, up=nrm,
                 twist=rnd.uniform(-0.5, 0.5))
    tufts = mb.to_object(name + '_tufts')
    dj.push_out(tufts, body.bvh, 0.003, iters=3)
    return tufts


# ----------------------------------------------------------------------------------------------
# hardware
# ----------------------------------------------------------------------------------------------
def buckle(center, normal, up, w=0.06, h=0.05, bar=0.008, depth=0.006, name='buckle'):
    """rectangular frame buckle + centre bar + tongue, facing along normal."""
    n = Vector(normal).normalized()
    u = Vector(up)
    u = (u - n * u.dot(n)).normalized()
    x = u.cross(n)
    M3 = Matrix((x, u, n)).transposed()
    c = Vector(center)
    mb = MB()
    for (cx, cy, sx, sy) in ((0, h / 2 - bar / 2, w, bar), (0, -h / 2 + bar / 2, w, bar),
                             (w / 2 - bar / 2, 0, bar, h), (-w / 2 + bar / 2, 0, bar, h), (0, 0, bar * 0.8, h)):
        M4 = M3.to_4x4()
        M4.translation = c + M3 @ Vector((cx, cy, depth / 2))
        mb.box((0, 0, 0), (sx, sy, depth), M=M4, bevel=0.0015)
    return mb.to_object(name)


def cyl_between(mb, a, b, r, segs=12, r2=None, cap=True):
    a, b = Vector(a), Vector(b)
    d = b - a
    M3 = frame3(d)
    M4 = M3.to_4x4()
    M4.translation = a
    r2 = r if r2 is None else r2
    mb.lathe([(r, 0.0), (r2, d.length)], segs, M4, close_top=cap, close_bot=cap)


def frame3(axis, up=None):
    z = Vector(axis).normalized()
    up = Vector(up) if up is not None else (Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((0, 1, 0)))
    x = up.cross(z)
    if x.length < 1e-6:
        x = z.orthogonal()
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def rounded_box(mb, center, size, M3=None, bevel=0.006, segs=2):
    M4 = (M3 or Matrix.Identity(3)).to_4x4()
    M4.translation = Vector(center)
    mb.box((0, 0, 0), size, M=M4, bevel=bevel, bevel_segs=segs)


def bez(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = Vector(p0), Vector(p1), Vector(p2), Vector(p3)
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / (n - 1) for i in range(n))]


def placed_m(M3, origin):
    M4 = M3.to_4x4()
    M4.translation = Vector(origin)
    return M4


def boot_welt(upper, name, z=None, width=0.012, thick=0.007):
    """leather welt band round the bottom edge of a boot upper (hides the upper/sole join)."""
    loops = ar.boundary_loops(upper)
    lo = min(loops, key=lambda l: sum(p.z for p in l[0]) / len(l[0]))
    pts = lo[0]
    zz = z if z is not None else min(p.z for p in pts)
    c = sum(pts, Vector()) / len(pts)
    pts = [Vector((p.x, p.y, zz + width * 0.35)) + (Vector((p.x, p.y, 0)) - Vector((c.x, c.y, 0))).normalized() * 0.002
           for p in pts]
    pts = G.smooth_loop(pts[::2], 2)
    return ring_sweep(pts, width, thick, name, Vector((0, 0, 1)), sides=6, exp=3.0)


def flatten_hem(ob, zmax, z_fn, iters=6):
    """move the bottom boundary verts (below zmax) to z_fn(co) and relax the rows above."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    hem = [v for v in bm.verts if v.is_boundary and v.co.z < zmax]
    for v in hem:
        v.co.z = z_fn(v.co)
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary and v.co.z < zmax + 0.06],
                              factor=0.4, use_axis_x=False, use_axis_y=False, use_axis_z=True)
        for v in hem:
            v.co.z = z_fn(v.co)
    bm.to_mesh(me)
    bm.free()
    me.update()


def tape_shell(body, stack, side, name, off=0.0022, wrist_len=0.05, knuckle=0.012):
    """the taped part of a hand: palm + back of the hand + wrist, finger bases at the knuckles, thumb base."""
    sg = 1 if side == 'l' else -1
    hb = body.h(LR('hand_l', side))
    el = body.h(LR('lowerarm_l', side))
    ax = (hb - el).normalized()
    kn = {f: body.h('%s_01_%s' % (f, side)) for f in ('index', 'middle', 'ring', 'pinky')}

    def keep(c, b):
        if c.x * sg <= 0:
            return False
        if b == LR('hand_l', side):
            return True
        if b == LR('lowerarm_l', side):
            return (c - hb).dot(ax) > -wrist_len
        for f, k in kn.items():
            if b == '%s_01_%s' % (f, side):
                return (c - k).dot(ax) < knuckle
        if b == LR('thumb_01_l', side):
            return True
        return False
    sh = ar.extract_region(body.mesh, keep, name)
    ar.smooth_offset(sh, off, smooth_iters=2, factor=0.4)
    # clean, straight tape end on the forearm (no staircase from the face selection)
    me = sh.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        a = (v.co - hb).dot(ax)
        if v.is_boundary and a < -wrist_len * 0.6:
            v.co = v.co - ax * (a + wrist_len)
    bm.to_mesh(me)
    bm.free()
    me.update()
    G.relax_boundary(sh, lambda pts: True, iters=4, factor=0.5, ring=0.2)
    dj.push_out(sh, body.bvh, off * 0.8, iters=3)
    return sh


def stock_hair(body, style, name, head_scale=1.08, tousle=0.004, lift=0.008, seed=2):
    """A Quaternius UBC hair (rigged to Head), scaled with the enlarged head and tousled with noise."""
    objs = dj.import_gltf(dj.QUAT + r"\ubc\hair\%s.gltf" % style)
    meshes = [o for o in objs if o.type == "MESH" and not o.name.startswith("Icosphere")]
    for o in objs:
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    objs = [o for o in objs if o.name in bpy.data.objects]
    piv = body.B.h("Head")
    L = body.L
    for o in meshes:
        o.modifiers.clear()
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in objs:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    ob = dj.join(meshes, name)
    me = ob.data
    me.update()
    off = Vector((seed * 3.1, seed * 1.7, 0.4))
    for v in me.vertices:
        p = piv + (v.co - piv) * head_scale
        h = smooth01(p.z, L["eye_l"].z + 0.03, L["top"] + 0.03)
        n_hi = noise.noise(p * 30 + off)
        n_lo = noise.noise(p * 11 + off)
        side = Vector((noise.noise(p * 8 + off + Vector((3, 0, 0))), noise.noise(p * 8 + off + Vector((0, 3, 0))), 0))
        p += v.normal * (tousle * n_hi + lift * h * (0.55 + 0.45 * n_lo))
        p += Vector((0, 0, 1)) * (lift * 0.8 * h * max(0.0, n_lo)) + side * (lift * 0.6 * h)
        v.co = p
    me.update()
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if me.uv_layers:
        me.uv_layers[0].name = "aux"
    me.materials.clear()
    me.shade_smooth()
    dj.push_out(ob, body.bvh, 0.002, iters=2)
    return ob


def overlay(ob, pred, off, name, thick=0.0):
    """copy of the faces of ob whose centre satisfies pred(c), lifted off along the normals (toe caps, heel counters)."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    dj.link(cp)
    cp.name = name
    G.delete_faces(cp, lambda c: not pred(c))
    me = cp.data
    me.update()
    for v in me.vertices:
        v.co += v.normal * off
    me.update()
    G.relax_boundary(cp, lambda pts: True, iters=3, factor=0.5)
    if thick > 0:
        thicken(cp, thick, offset=-1.0)
    return cp

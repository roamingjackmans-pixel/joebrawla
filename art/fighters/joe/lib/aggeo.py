"""Garment geometry primitives fitted to a UBC body (male or female) and to the layers already built.

Layer envelopes (distance from the skin in the rest pose) keep pieces from different slots and sets
compatible (any head + body + legs combination):
  legs slot   waist band and thighs <= ENV_LEGS_HIP, plate on the thighs/shins <= ENV_LEGS_MAX
  body slot   from the waist line down: >= ENV_BODY_HIP; skirts over the thighs >= ENV_BODY_SKIRT
  head slot   drapes over the collar zone sit on ENV_COLLAR + 0.8 cm; body pieces stay under ENV_COLLAR
              there (or declare a high collar and the client hides the head piece's drape node)
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree
import agcore as C
import djlib as dj
import djarmor as ar
from djlib import MB, V
from agcore import smooth01, lerp, LR

ENV_LEGS_HIP = 0.018
ENV_LEGS_MAX = 0.032
ENV_BODY_HIP = 0.026
ENV_BODY_SKIRT = 0.040
ENV_COLLAR = 0.024
ENV_DRAPE = 0.034


# ----------------------------------------------------------------------------------------------
# attributes
# ----------------------------------------------------------------------------------------------
def set_edge_attr(ob, width=0.03, name='edge'):
    """POINT attribute: 1 on open boundaries, falling smoothly to 0 at `width` (Euclidean)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bco = [v.co.copy() for v in bm.verts if v.is_boundary]
    bm.free()
    if bco:
        kd = __import__('mathutils').kdtree.KDTree(len(bco))
        for i, c in enumerate(bco):
            kd.insert(c, i)
        kd.balance()
        vals = []
        for v in me.vertices:
            co, idx, d = kd.find(v.co)
            vals.append(1.0 - smooth01(d, 0.0, width))
    else:
        vals = [0.0] * len(me.vertices)
    a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    a.data.foreach_set('value', vals)
    return ob


def set_attr(ob, name, value):
    me = ob.data
    a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    a.data.foreach_set('value', [value] * len(me.vertices))


def ensure_attrs(ob, prand=None, edge=True, width=0.03):
    if edge:
        set_edge_attr(ob, width)
    else:
        set_attr(ob, 'edge', 0.0)
    set_attr(ob, 'prand', random.random() if prand is None else prand)
    return ob


# ----------------------------------------------------------------------------------------------
# generic mesh helpers
# ----------------------------------------------------------------------------------------------
def grid(fn, nu, nv, name, closed_v=False, mask=None, smooth=True):
    mb = MB()
    mb.grid(fn, nu, nv, closed_v=closed_v, mask=mask)
    return mb.to_object(name, smooth=smooth)


def delete_faces(ob, pred):
    """Delete faces whose centre satisfies pred(center_world)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = [f for f in bm.faces if pred(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob


def displace(ob, fn):
    """v.co += fn(co, normal)"""
    me = ob.data
    me.update()
    for v in me.vertices:
        v.co += fn(v.co.copy(), v.normal.copy())
    me.update()


def subdivide(ob, cuts=1, smooth=0.0):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=cuts, use_grid_fill=True, smooth=smooth)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def solidify(ob, thick, offset=-1.0, rim=True):
    m = ob.modifiers.new('sol', 'SOLIDIFY')
    m.thickness = thick
    m.offset = offset
    m.use_even_offset = True
    m.use_quality_normals = True
    m.use_rim = rim
    dj.apply_mods(ob)
    ob.data.shade_smooth()
    return ob


def smooth_verts(ob, iters=4, factor=0.5, keep_boundary=False, pred=None):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(iters):
        vs = [v for v in bm.verts if not (keep_boundary and v.is_boundary) and (pred is None or pred(v.co))]
        bmesh.ops.smooth_vert(bm, verts=vs, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(me)
    bm.free()
    me.update()


def hem_tube(ob, r=0.006, flat=0.55, sides=6, name=None, pred=None, min_len=4):
    """Rolled hem / rim tubes along the open boundaries of ob (optionally only loops passing pred)."""
    loops = ar.boundary_loops(ob)
    if pred:
        loops = [l for l in loops if pred(l)]
    mb = MB()
    for pts, closed in loops:
        if len(pts) < min_len:
            continue
        P = pts + pts[:2] if closed else pts
        mb.sweep(P, [(r, r * flat)] * len(P), sides=sides, cap0=None if closed else 'flat',
                 cap1=None if closed else 'flat', cap_segs=1)
    if not mb.bm.verts:
        mb.bm.free()
        return None
    return mb.to_object(name or (ob.name + '_hem'))


# ----------------------------------------------------------------------------------------------
# body-derived layers
# ----------------------------------------------------------------------------------------------
TORSO_BONES = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01'}
ARM_UP = {'upperarm_l', 'upperarm_r'}
ARM_LO = {'lowerarm_l', 'lowerarm_r'}
HANDS = {'hand_l', 'hand_r'}
LEG_UP = {'thigh_l', 'thigh_r'}
LEG_LO = {'calf_l', 'calf_r'}
FEET = {'foot_l', 'foot_r', 'ball_l', 'ball_r'}


def body_layer(body, keep, offset, name, smooth=8, factor=0.55, stack=None, clearance=None, iters=6,
               keep_boundary=True):
    """Copy of the body faces keep(center, dominant_bone) -> smoothed, offset along normals, pushed clear of
    the stack."""
    ob = ar.extract_region(body.mesh, keep, name)
    ar.smooth_offset(ob, offset, smooth_iters=smooth, factor=factor, keep_boundary=keep_boundary)
    bvh = stack.bvh() if stack else body.bvh
    dj.push_out(ob, bvh, clearance if clearance is not None else offset * 0.8, iters=iters)
    return ob


def torso_shell(body, stack=None, z0=None, z1=None, harm=4, n_th=40, n_st=14):
    L = body.L
    z0 = z0 if z0 is not None else L['crotch_z'] + 0.04
    z1 = z1 if z1 is not None else L['neck'].z + 0.02
    yc = 0.025
    bvh = stack.bvh() if stack else body.bvh
    # arms are horizontal in the rest pose: cap the radius so side rays that hit an arm don't blow it up
    sh = L['shoulder_l']

    def cap(t, th):
        z = z0 + (z1 - z0) * t
        if z > sh.z - 0.16:
            return 0.17 + 0.05 * abs(math.cos(th))
        return 0.5
    return ar.Shell(bvh, (0, yc, z0), (0, yc, z1), up=(0, -1, 0), n_st=n_st, n_th=n_th, harm=harm, cap=cap), z0, z1


def bridge_torso(ob, body, off, zmin, zmax, stack=None, sector=0.75, soft=0.04):
    """Cloth spans hollows: push verts in the front/back sectors (|sin th| < sector) of the torso out to the
    Fourier-smoothed torso shell + off."""
    S, z0, z1 = torso_shell(body, stack, zmin - 0.05, zmax + 0.05)
    me = ob.data
    for v in me.vertices:
        p = v.co
        if p.z < zmin or p.z > zmax or abs(p.x) > 0.2:
            continue
        t = (p.z - z0) / (z1 - z0)
        c = S.center(t)
        dx, dy = p.x - c.x, p.y - c.y
        th = math.atan2(dx, -dy)
        if abs(math.sin(th)) > sector:
            continue
        r = math.hypot(dx, dy)
        rs = S.radius(t, th) + off
        if r < rs:
            f = smooth01(p.z, zmin, zmin + soft) * (1 - smooth01(p.z, zmax - soft, zmax))
            f *= 1 - smooth01(abs(math.sin(th)), sector - 0.25, sector)
            nr = r + (rs - r) * f
            k = nr / max(r, 1e-6)
            p.x = c.x + dx * k
            p.y = c.y + dy * k
    me.update()


def loosen(ob, fn):
    """Push verts out along their normals by fn(co) metres."""
    displace(ob, lambda co, n: n * fn(co))


# ----------------------------------------------------------------------------------------------
# outer profile rings (skirts, robes, mantles)
# ----------------------------------------------------------------------------------------------
def fourier(vals, harm):
    n = len(vals)
    co = [sum(vals) / n]
    for k in range(1, harm + 1):
        co.append((2 / n * sum(vals[j] * math.cos(2 * math.pi * k * j / n) for j in range(n)),
                   2 / n * sum(vals[j] * math.sin(2 * math.pi * k * j / n) for j in range(n))))

    def f(th):
        r = co[0]
        for k in range(1, harm + 1):
            r += co[k][0] * math.cos(k * th) + co[k][1] * math.sin(k * th)
        return r
    return f


class Profile:
    """Outer radius r(z, th) of the stack around a vertical axis (cx, cy), from rays cast inward from
    outside (th = 0 front (-Y), th = 90deg the character's left (+X)). Fourier-smoothed per height."""

    def __init__(self, bvh, zs, cx=0.0, cy=0.025, harm=3, n=48, far=0.6, xmax=None, floor=0.05):
        self.zs = sorted(zs, reverse=True)
        self.cx, self.cy = cx, cy
        self.f = []
        for z in self.zs:
            vals = []
            for k in range(n):
                th = 2 * math.pi * k / n
                d = Vector((math.sin(th), -math.cos(th), 0))
                st = Vector((cx, cy, z)) + d * far
                loc, nrm, idx, dist = bvh.ray_cast(st, -d, far)
                r = (far - dist) if loc is not None else floor
                if xmax is not None and abs(math.sin(th) * r) > xmax:
                    r = min(r, xmax / max(abs(math.sin(th)), 1e-3))
                vals.append(max(r, floor))
            self.f.append(fourier(vals, harm))

    def r(self, z, th):
        zs = self.zs
        if z >= zs[0]:
            return self.f[0](th)
        for i in range(len(zs) - 1):
            if zs[i] >= z >= zs[i + 1]:
                t = (zs[i] - z) / (zs[i] - zs[i + 1])
                return self.f[i](th) * (1 - t) + self.f[i + 1](th) * t
        return self.f[-1](th)

    def pt(self, z, th, off=0.0):
        r = self.r(z, th) + off
        return Vector((self.cx + math.sin(th) * r, self.cy - math.cos(th) * r, z))


def skirt(body, stack, z_top, z_bot, name, off=ENV_BODY_SKIRT, flare=0.06, nu=10, nv=40, th0=0.0, th1=2 * math.pi,
          tatter=0.0, seed=1.0, front_slit=0.0, back_slit=0.0, side_slit=0.0, closed=True, prof_zs=None,
          hem_wave=0.0, xmax=None, off_top=None, top_band=0.09, front_open=0.0):
    """Ring drape from z_top down to z_bot around the hips/legs. flare = extra radius at the hem.
    tatter (m) = ragged hem length variation. *_slit = half-angle (rad) of an opening up from the hem."""
    zs = prof_zs or [z_top + 0.02] + [z_top - (z_top - z_bot) * k / 5 for k in range(1, 6)]
    P = Profile(stack.bvh(), [max(z, 0.62) for z in zs], harm=3, xmax=xmax)
    full = closed and (th1 - th0) >= 2 * math.pi - 1e-6
    rnd = random.Random(int(seed * 1000))
    hem_var = [rnd.random() for _ in range(nv + 1)]

    def hem_len(v):
        if tatter <= 0:
            return 0.0
        k = v * nv
        i = int(k) % nv
        f = k - int(k)
        a, b = hem_var[i], hem_var[(i + 1) % nv]
        n1 = a * (1 - f) + b * f
        n2 = noise.noise(Vector((v * 23.0, seed, 0.3)))
        return tatter * (0.55 * n1 + 0.45 * (0.5 + 0.5 * n2))

    def hull(zq, th):
        # cloth hangs: never narrower than anything above it (no bulge-and-taper around the thighs)
        r = P.r(zq, th)
        for k in range(1, 5):
            zz = zq + (z_top - zq) * k / 4
            r = max(r, P.r(max(zz, 0.62), th))
        return r

    def fn(u, v):
        th = th0 + (th1 - th0) * v
        hl = hem_len(v)
        zb = z_bot + hl
        z = z_top - (z_top - zb) * u
        zq = max(z, 0.62)
        fl = flare * smooth01(z_top - z, 0.0, max(z_top - z_bot, 0.01)) ** 1.3
        o = off if off_top is None else lerp(off_top, off, smooth01(z_top - z, 0.0, top_band))
        r_off = o + fl + hem_wave * u * math.sin(th * 7 + seed)
        r = hull(zq, th) + r_off
        return Vector((P.cx + math.sin(th) * r, P.cy - math.cos(th) * r, z))
    mask = None
    if front_slit or back_slit or side_slit or front_open:
        def mask(i, j):
            u = (i + 0.5) / nu
            th = th0 + (th1 - th0) * ((j + 0.5) / nv)
            thn = math.atan2(math.sin(th), math.cos(th))
            if front_open and abs(thn) < front_open * (1 + 0.35 * u):
                return False
            for c, w in ((0.0, front_slit), (math.pi, back_slit), (math.pi / 2, side_slit), (-math.pi / 2, side_slit)):
                if w <= 0:
                    continue
                d = abs(math.atan2(math.sin(thn - c), math.cos(thn - c)))
                if d < w * smooth01(u, 0.25, 1.0):
                    return False
            return True
    ob = grid(fn, nu, nv, name, closed_v=full, mask=mask)
    dj.push_out(ob, stack.bvh(), (off_top if off_top is not None else off) * 0.6, iters=4)
    if front_open:
        relax_boundary(ob, lambda pts: min(p.y for p in pts) < -0.05, iters=4, factor=0.5)
    return ob


def skirt_weights(body, softness=0.55, pelvis_min=0.25, calf=0.0):
    """Weights for a skirt / robe / coat tail: side by x between the thighs, with pelvis at the top and the
    centre front/back so a stride doesn't tear the cloth."""
    L = body.L
    z_hip = L['hip_l'].z
    z_knee = L['knee_l'].z

    def fn(co):
        x = co.x
        s = max(-1.0, min(1.0, x / 0.12))
        wl = smooth01(s, -softness, softness)
        wr = 1 - wl
        down = smooth01(co.z, z_hip + 0.05, z_hip - 0.18)
        # pelvis only near the waist band; lower down the cloth follows the thighs (the centre front / back
        # shares both), so a raised knee carries the hem with it instead of pushing through it
        pel = min(1.0, max(pelvis_min * 0.5, 1 - down))
        legs = 1 - pel
        out = {'pelvis': pel}
        if calf > 0 and co.z < z_knee:
            k = calf * smooth01(co.z, z_knee, z_knee - 0.2)
            out['thigh_l'] = legs * wl * (1 - k)
            out['thigh_r'] = legs * wr * (1 - k)
            out['calf_l'] = legs * wl * k
            out['calf_r'] = legs * wr * k
        else:
            out['thigh_l'] = legs * wl
            out['thigh_r'] = legs * wr
        if co.z > L['waist'].z - 0.03:
            f = smooth01(co.z, L['waist'].z - 0.03, L['waist'].z + 0.05)
            out = {k: v * (1 - f) for k, v in out.items()}
            out['spine_01'] = f
        return out
    return fn


# ----------------------------------------------------------------------------------------------
# bands, belts, straps, wraps
# ----------------------------------------------------------------------------------------------
def outer_hit(bvh, c, d, maxd=0.2, gap=0.03):
    """Distance from c (inside a limb) along d to the outermost surface of the contiguous layer stack."""
    loc, nrm, idx, dist = bvh.ray_cast(c, d, maxd)
    if loc is None:
        return None
    last = dist
    while True:
        loc2, nrm2, idx2, d2 = bvh.ray_cast(loc + d * 1e-4, d, gap)
        if loc2 is None:
            break
        loc = loc2
        last = (loc2 - c).length
        if last > maxd:
            break
    return last


def band_loop(bvh, center, axis, up, n=32, off=0.006, far=0.5, rmin=0.02, inside=False, maxd=0.2):
    """Closed loop of points on the outermost surface around an axis line through `center`."""
    a = Vector(axis).normalized()
    u = Vector(up)
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        d = u * math.cos(th) + v * math.sin(th)
        if inside:
            r = outer_hit(bvh, Vector(center), d, maxd) or rmin
        else:
            st = Vector(center) + d * far
            loc, nrm, idx, dist = bvh.ray_cast(st, -d, far)
            r = (far - dist) if loc is not None else rmin
        pts.append(Vector(center) + d * (max(r, rmin) + off))
    return pts


def smooth_loop(pts, iters=2):
    n = len(pts)
    for _ in range(iters):
        pts = [(pts[(i - 1) % n] + pts[i] * 2 + pts[(i + 1) % n]) / 4 for i in range(n)]
    return pts


def belt(bvh, center, name, axis=(0, 0, 1), up=(0, -1, 0), width=0.035, thick=0.007, off=0.006, n=40,
         smooth=2, tilt=None):
    pts = smooth_loop(band_loop(bvh, center, axis, up, n, off), smooth)
    if tilt:
        pts = [p + Vector((0, 0, tilt(p))) for p in pts]
    P = pts + pts[:2]
    mb = MB()
    mb.sweep(P, [(width * 0.5, thick * 0.5)] * len(P), sides=4, rot=math.pi / 4, up=axis, cap0=None, cap1=None)
    return mb.to_object(name), pts


def tube_loop(pts, r, name, sides=6, flat=1.0, up=None):
    P = pts + pts[:2]
    mb = MB()
    mb.sweep(P, [(r, r * flat)] * len(P), sides=sides, cap0=None, cap1=None, up=up)
    return mb.to_object(name)


def strap(pts, width, thick, name, up=None):
    mb = MB()
    mb.sweep(pts, [(width * 0.5, thick * 0.5)] * len(pts), sides=4, rot=math.pi / 4, up=up, cap0='flat', cap1='flat')
    return mb.to_object(name)


def surface_path(bvh, a, b, n, off, center_fn):
    """Points from a to b projected onto the outermost surface (rays from outside toward center_fn(p))."""
    pts = []
    for k in range(n + 1):
        p = a.lerp(b, k / n)
        c = center_fn(p)
        d = (p - c)
        d.z = 0 if abs(d.z) < 1e-9 else d.z
        if d.length < 1e-6:
            pts.append(p)
            continue
        d.normalize()
        st = c + d * 0.6
        loc, nrm, idx, dist = bvh.ray_cast(st, -d, 0.6)
        pts.append((loc + d * off) if loc is not None else p)
    return pts


def wraps(bvh, p0, p1, name, turns=6, width=0.03, thick=0.004, off=0.004, up=(0, -1, 0), n_per_turn=18, phase=0.0,
          jitter=0.004, seed=0.0):
    """Spiral bandage wrapped around a limb segment p0 -> p1 (strips sitting on the outermost surface)."""
    p0, p1 = Vector(p0), Vector(p1)
    a = (p1 - p0).normalized()
    u = Vector(up)
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    L = (p1 - p0).length
    N = max(4, int(abs(turns) * n_per_turn))
    pts = []
    for k in range(N + 1):
        t = k / N
        th = 2 * math.pi * turns * t + phase
        c = p0 + a * (L * t)
        d = u * math.cos(th) + v * math.sin(th)
        r = outer_hit(bvh, c, d, 0.16) or 0.04
        j = jitter * noise.noise(Vector((t * 9, seed, 0)))
        pts.append(c + d * (r + off + j))
    mb = MB()
    mb.sweep(pts, [(width * 0.5, thick * 0.5)] * len(pts), sides=4, rot=math.pi / 4, up=a, cap0='flat', cap1='flat')
    return mb.to_object(name)


# ----------------------------------------------------------------------------------------------
# hood (dome + neck + optional mantle), cylindrical/spherical hybrid around the head / neck axis
# ----------------------------------------------------------------------------------------------
def relax_boundary(ob, pred, iters=8, factor=0.5, ring=0.35):
    """Smooth open-boundary loops (staircase edges from masked grids). pred(loop_points) selects loops.
    The first interior ring follows by `ring`."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    loops = ar.boundary_loops(ob)
    sel = set()
    for pts, closed in loops:
        if pred(pts):
            for p in pts:
                for v in bm.verts:
                    if (v.co - p).length < 1e-7:
                        sel.add(v.index)
                        break
    bnb = {}
    for i in sel:
        v = bm.verts[i]
        bnb[i] = [e.other_vert(v).index for e in v.link_edges if e.is_boundary and e.other_vert(v).index in sel]
    inner = {}
    for i in sel:
        v = bm.verts[i]
        for e in v.link_edges:
            o = e.other_vert(v)
            if o.index not in sel:
                inner.setdefault(o.index, []).append(i)
    for _ in range(iters):
        new = {}
        for i, nb in bnb.items():
            if len(nb) == 2:
                c = (bm.verts[nb[0]].co + bm.verts[nb[1]].co) * 0.5
                new[i] = bm.verts[i].co.lerp(c, factor)
        moves = {}
        for i, p in new.items():
            moves[i] = p - bm.verts[i].co
            bm.verts[i].co = p
        for j, srcs in inner.items():
            d = sum((moves.get(s, Vector()) for s in srcs), Vector()) / len(srcs)
            bm.verts[j].co += d * ring
    bm.to_mesh(me)
    bm.free()
    me.update()


def hood(body, stack, name, off=0.022, back_loose=0.02, peak=0.05, peak_back=0.06, z_hem=None, hem_off=None,
         open_w=0.6, open_top=0.035, open_bot=-0.012, mantle_flare=0.02, tatter=0.0, seed=2.0, nu=26, nv=56,
         drape_z=None, xmax=0.22, brim=0.022, cowl=0.025, top_loose=0.012, side_rise=0.05, folds=0.007, n_folds=13):
    """Returns (hood_obj, drape_split_z). The face opening is an oval cut in the front.
    open_w: half-width (rad around the axis) of the opening at eye height; open_top/bot: opening extents above
    the brow / below the chin (m). brim: the opening's edge stands this far proud of the face. cowl: extra
    looseness in front of the throat. side_rise: the mantle hem rises this much over the shoulders."""
    L = body.L
    hc = Vector((0, L['head_c'].y + 0.01, L['head_c'].z))
    eye_z = L['eye_l'].z
    chin = L['chin']
    sh_z = L['shoulder_l'].z
    z_hem = z_hem if z_hem is not None else sh_z - 0.06
    hem_off = hem_off if hem_off is not None else off + 0.01
    bvh = stack.bvh()
    n_el = 9
    els = [math.radians(90 - 90 * k / (n_el - 1)) for k in range(n_el)]
    dome = []
    for el in els:
        vals = []
        for k in range(48):
            th = 2 * math.pi * k / 48
            d = Vector((math.sin(th) * math.cos(el), -math.cos(th) * math.cos(el), math.sin(el)))
            st = hc + d * 0.4
            loc, nrm, idx, dist = bvh.ray_cast(st, -d, 0.4)
            vals.append((0.4 - dist) if loc is not None else 0.1)
        dome.append(fourier(vals, 4))
    neck_c = L['neck']
    zs = [hc.z - 0.001, hc.z - 0.03, chin.z, chin.z - 0.03, L['neck'].z, sh_z + 0.06, sh_z + 0.02, sh_z - 0.03,
          sh_z - 0.1, sh_z - 0.16]
    zs = sorted(set(round(z, 4) for z in zs if z > z_hem - side_rise - 0.08), reverse=True)
    prof = Profile(bvh, zs, cx=0.0, cy=neck_c.y - 0.005, harm=4, xmax=xmax)
    z_eq = hc.z
    span_dome = 0.115 * math.pi / 2
    span_cyl = max(z_eq - z_hem, 0.05)
    a_ = span_dome / (span_dome + span_cyl)
    zt_open = eye_z + open_top
    zb_open = chin.z + open_bot

    def back_k(th):
        return 0.5 * (1 + math.cos(th - math.pi))

    def front_d(th):
        return abs(math.atan2(math.sin(th), math.cos(th)))

    def brim_k(th, z):
        d = front_d(th)
        kz = smooth01(z, zb_open - 0.06, zb_open) * (1 - smooth01(z, zt_open + 0.02, zt_open + 0.09))
        return (1 - smooth01(d, open_w * 0.8, open_w + 0.55)) * kz

    def hem_z(th):
        # capelet: the hem rises over the shoulders (sides), longest at the front and back
        side = abs(math.sin(th))
        t = 0.0
        if tatter > 0:
            t = tatter * (0.5 + 0.5 * noise.noise(Vector((math.cos(th) * 2.2, math.sin(th) * 2.2, seed))))
            t += tatter * 0.35 * max(0.0, noise.noise(Vector((math.cos(th) * 7.0, math.sin(th) * 7.0, seed + 3.1))))
        return z_hem + side_rise * side ** 2 + t

    def pt(th, v):
        bk = back_k(th)
        if v <= a_:
            s = v / a_
            el = math.radians(90 * (1 - s))
            fi = min(int(s * (n_el - 1)), n_el - 2)
            ft = s * (n_el - 1) - fi
            r = dome[fi](th) * (1 - ft) + dome[fi + 1](th) * ft
            pk = peak * math.exp(-((el - math.radians(55)) / math.radians(28)) ** 2) * bk ** 2
            r += off + back_loose * bk + pk + top_loose * math.sin(el)
            d = Vector((math.sin(th) * math.cos(el), -math.cos(th) * math.cos(el), math.sin(el)))
            p = hc + d * r
            p += d * (brim * brim_k(th, p.z))
            p.y += peak_back * bk ** 3 * math.sin(math.radians(90) * s) * smooth01(el, math.radians(20), math.radians(70))
            return p
        s = (v - a_) / (1 - a_)
        zh = hem_z(th)
        z = z_eq - (z_eq - zh) * s
        r = prof.r(max(z, min(zs)), th)
        r_eq = dome[-1](th) + off + back_loose * bk
        w = smooth01(s, 0.0, 0.35)
        neck_off = off * 0.6 + back_loose * bk * 0.6
        o = lerp(neck_off, hem_off + mantle_flare * smooth01(z, sh_z + 0.05, zh), smooth01(z, L['neck'].z + 0.03, sh_z))
        fr = max(0.0, math.cos(th)) ** 2
        o += cowl * fr * smooth01(z, chin.z + 0.01, chin.z - 0.04) * (1 - smooth01(z, sh_z + 0.02, sh_z - 0.08))
        o += folds * math.sin(n_folds * th + seed) * smooth01(z, sh_z + 0.04, zh)
        rr = lerp(r_eq, r + o, w)
        cx_ = lerp(hc.x, prof.cx, w)
        cy_ = lerp(hc.y, prof.cy, w)
        p = Vector((cx_ + math.sin(th) * rr, cy_ - math.cos(th) * rr, z))
        dd = Vector((math.sin(th), -math.cos(th), 0))
        p += dd * (brim * brim_k(th, z))
        return p

    def fn(u, v):
        return pt(2 * math.pi * v, u)

    def inside_open(th, z):
        if z > zt_open or z < zb_open:
            return False
        zc = (zt_open + zb_open) * 0.5
        hz = (zt_open - zb_open) * 0.5
        q = (z - zc) / hz
        w = open_w * math.sqrt(max(0.0, 1 - q * q)) * (1.0 if q > -0.2 else 0.9)
        return front_d(th) < w

    def mask(i, j):
        u = (i + 0.5) / nu
        th = 2 * math.pi * ((j + 0.5) / nv)
        return not inside_open(th, pt(th, u).z)
    ob = grid(fn, nu, nv, name, closed_v=True, mask=mask)
    relax_boundary(ob, lambda pts: max(p.z for p in pts) > eye_z - 0.02 and min(p.y for p in pts) < hc.y - 0.05,
                   iters=10, factor=0.5)
    relax_boundary(ob, lambda pts: max(p.z for p in pts) < sh_z + 0.03, iters=3, factor=0.4, ring=0.2)
    dj.push_out(ob, bvh, off * 0.7, iters=5)
    split_z = drape_z if drape_z is not None else L['neck'].z - 0.015
    return ob, split_z


def split_by_z(ob, z, name_below):
    """Split ob into (above, below) at height z (faces by centre)."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    dj.link(cp)
    cp.name = name_below
    delete_faces(ob, lambda c: c.z < z)
    delete_faces(cp, lambda c: c.z >= z)
    return ob, cp


def hood_weights(body, split_z):
    L = body.L
    ws = body.ws
    zh = L['chin'].z - 0.01

    def fn(co):
        if co.z > zh + 0.04:
            return {'Head': 1.0}
        w = ws.at(co)
        f = smooth01(co.z, zh - 0.02, zh + 0.04)
        out = {k: v * (1 - f) for k, v in w.items()}
        out['Head'] = out.get('Head', 0) + f
        return out
    return fn


# ----------------------------------------------------------------------------------------------
# panels hanging from the shoulders (tabards, ponchos, cloak backs)
# ----------------------------------------------------------------------------------------------
def hanging_panel(body, stack, name, front=True, width_top=0.14, width_bot=0.17, z_top=None, z_bot=0.75, off=0.012,
                  nu=14, nv=8, tatter=0.0, seed=3.0, curve_w=None, wrap=0.0, hang=0.0):
    """Cloth panel down the front (-Y) or back (+Y). Upper part lies on the stack (ray cast from outside);
    below the chest it falls straight (hang>0 pushes it away at the bottom)."""
    L = body.L
    z_top = z_top if z_top is not None else L['shoulder_l'].z + 0.03
    bvh = stack.bvh()
    sg = -1 if front else 1
    rnd = random.Random(int(seed * 1000))
    hv = [rnd.random() for _ in range(nv + 1)]

    def surf(x, z):
        st = Vector((x, sg * 0.6, z))
        loc, nrm, idx, dist = bvh.ray_cast(st, Vector((0, -sg, 0)), 1.2)
        return loc

    # a smooth "fall line": max y-extent from the shoulders down (cloth drapes over the chest / blades)
    def fn(u, v):
        k = v * nv
        i = min(int(k), nv - 1)
        f = k - i
        hl = tatter * (hv[i] * (1 - f) + hv[i + 1] * f) if tatter else 0.0
        z = z_top - (z_top - (z_bot + hl)) * u
        w = lerp(width_top, width_bot, u) if curve_w is None else curve_w(u)
        x = (v - 0.5) * 2 * w
        loc = surf(x, z)
        y = loc.y if loc is not None else sg * 0.12
        # follow the outermost surface above, but never go back inward below the widest point
        return Vector((x, y + sg * off, z))
    ob = grid(fn, nu, nv, name)
    # make the fall line monotonic below the chest: y never recedes toward the body going down
    me = ob.data
    cols = {}
    for vv in me.vertices:
        cols.setdefault(round(vv.co.x, 4), []).append(vv)
    zc = L['chest'].z
    for col in cols.values():
        col.sort(key=lambda q: -q.co.z)
        ext = None
        for q in col:
            if q.co.z < zc + 0.06:
                if ext is None:
                    ext = q.co.y
                else:
                    if sg < 0:
                        ext = min(ext, q.co.y)
                    else:
                        ext = max(ext, q.co.y)
                    drop = (zc + 0.06 - q.co.z)
                    q.co.y = ext + sg * hang * drop
    me.update()
    if wrap:
        # curl the side edges around the body a little
        for q in me.vertices:
            s = q.co.x / max(width_bot, 1e-3)
            q.co.y -= sg * wrap * (s * s)
        me.update()
    dj.push_out(ob, bvh, off * 0.8, iters=6)
    return ob


# ----------------------------------------------------------------------------------------------
# footwear and gloves
# ----------------------------------------------------------------------------------------------
def boot(body, stack, side, name, top_z=None, off=0.008, cuff=0.012, sole=0.012, toe_extra=0.006, smooth=4,
         cuff_h=0.05):
    """Boot from the body's foot + calf (to top_z) with a thicker sole and a flared cuff."""
    L = body.L
    top_z = top_z if top_z is not None else L['knee_l'].z - 0.12
    sg = 1 if side == 'l' else -1

    def keep(c, b):
        if c.x * sg <= 0:
            return False
        if b in (LR('foot_l', side), LR('ball_l', side)):
            return True
        return b == LR('calf_l', side) and c.z <= top_z
    ob = ar.extract_region(body.mesh, keep, name)
    ar.smooth_offset(ob, off, smooth_iters=smooth, factor=0.5)
    zt = top_z
    # flared cuff, fuller toe, sole
    me = ob.data
    me.update()
    for v in me.vertices:
        p = v.co
        n = v.normal
        f = smooth01(p.z, zt - cuff_h, zt)
        p += n * (cuff * f)
        if p.z < 0.035:
            p.z = max(p.z - sole * smooth01(0.035 - p.z, 0.0, 0.02), -0.002)
        if p.y < L['ball_l'].y + 0.01:
            p += n * toe_extra
    me.update()
    dj.push_out(ob, stack.bvh(), off * 0.7, iters=4)
    return ob


def glove(body, stack, side, name, cuff_x=None, off=0.0035, cuff=0.01, fingerless=False):
    sg = 1 if side == 'l' else -1
    wr = body.h(LR('hand_l', side))
    cuff_x = cuff_x if cuff_x is not None else abs(wr.x) - 0.05
    fingers = set(body.fingers(side))

    def keep(c, b):
        if c.x * sg <= 0:
            return False
        if b == LR('hand_l', side):
            return True
        if b in fingers:
            if fingerless:
                return ('_01_' in b) or b.startswith('thumb_01') or b.startswith('thumb_02')
            return True
        return b == LR('lowerarm_l', side) and abs(c.x) >= cuff_x
    ob = ar.extract_region(body.mesh, keep, name)
    ar.smooth_offset(ob, off, smooth_iters=2, factor=0.4)
    me = ob.data
    for v in me.vertices:
        f = smooth01(abs(cuff_x) + 0.03 - abs(v.co.x), 0.0, 0.03)
        v.co += v.normal * cuff * f
    me.update()
    dj.push_out(ob, stack.bvh(), off * 0.8, iters=4)
    return ob

"""Mother Spore -- geometry builders (world space, rest T-pose of the reshaped UBC female body)."""
import math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler, noise
import fblib as F

V = Vector
TAU = 2 * math.pi


def orient(ob, fn):
    """flip faces so their normals agree with fn(face centre) (a desired outward direction)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    flip = [f for f in bm.faces if f.normal.dot(fn(f.calc_center_median())) < 0]
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def dirp(phi):
    """horizontal direction for angle phi measured from the front (-Y) toward her left (+X)."""
    return V((math.sin(phi), -math.cos(phi), 0.0))


# ------------------------------------------------------------------------------------------------ cap
class CapFrame:
    def __init__(self, L, tilt_deg=7.0, seat_z=None, R=0.46, top=2.0):
        self.seat_z = seat_z if seat_z is not None else L['eye_l'].z + 0.068
        self.C = V((0.0, L['head_c'].y + 0.012, self.seat_z))
        self.Rot = Euler((math.radians(tilt_deg), 0, 0)).to_matrix().to_4x4()
        self.M = Matrix.Translation(self.C) @ self.Rot
        self.R = R
        self.h = top - self.seat_z           # dome height above the seat plane (centre)

    def w(self, p):
        return self.M @ V(p)


def rim_mod(a):
    return 1.0 + 0.030 * math.sin(5 * a + 0.7) + 0.018 * math.sin(11 * a + 2.1) + 0.010 * math.sin(17 * a)


def cap_hole(body_bvh, cf, n=48, clr=0.006):
    """inner ring of the cap: where the seat plane cuts the head (local polar radius per angle)."""
    out = []
    for k in range(n):
        a = TAU * k / n
        d_loc = V((math.cos(a), math.sin(a), 0))
        d = (cf.Rot.to_3x3() @ d_loc).normalized()
        r = F.ray_radius(body_bvh, cf.C, d, 0.3)
        out.append((r or 0.1) + clr)
    # smooth
    for _ in range(3):
        out = [(out[k - 1] + 2 * out[k] + out[(k + 1) % n]) / 4 for k in range(n)]
    return out


def build_cap(cf, hole, segs=96):
    """Returns (top, under, band) objects. Top: the dome (tint1). Under: gills (misc). Band: annulus ring."""
    R, H = cf.R, cf.h
    n = segs
    hole_n = len(hole)

    def hole_r(a):
        x = a / TAU * hole_n
        i = int(x) % hole_n
        f = x - int(x)
        return hole[i] * (1 - f) + hole[(i + 1) % hole_n] * f

    # --- top dome: profile from centre to rim, rim curls down
    top = F.MB()
    rows = 16
    prof = []
    for i in range(rows + 1):
        t = i / rows
        r = R * (t ** 0.85)
        z = H * (1 - t ** 2.3) - 0.028 * (t ** 6)          # flat dome, rim droops
        prof.append((r, z))
    # rim roll: round over to the underside
    prof += [(R * 1.012, -0.032), (R * 1.006, -0.045), (R * 0.985, -0.050)]
    us = [i / (len(prof) - 1) for i in range(len(prof))]

    def mod(a, r, z):
        k = (r / R) ** 3
        f = 1 + (rim_mod(a) - 1) * k
        dz = (0.012 * math.sin(4 * a + 1.3) + 0.008 * math.sin(9 * a)) * k
        return r * f, z + dz
    rings = top.lathe(prof, n, cf.M, close_top=False, close_bot=False, rfn=mod, us=us)
    top.fan(rings[0], cf.M @ V((0, 0, H)), flip=True, u=0.0)
    top_ob = top.to_object('ms_cap_top')
    orient(top_ob, lambda c: c - (cf.C - (cf.Rot.to_3x3() @ V((0, 0, 1))) * 0.3))
    # --- underside: from the rim roll inward to the hole, slight cone
    und = F.MB()
    nu = 7
    G = []
    for i in range(nu + 1):
        t = i / nu                               # 0 = rim, 1 = hole
        row = []
        for k in range(n):
            a = TAU * k / n
            rr_rim = R * 0.985
            r_h = hole_r(a)
            r = rr_rim + (r_h - rr_rim) * t
            kk = (r / R) ** 3
            f = 1 + (rim_mod(a) - 1) * kk
            dz = (0.012 * math.sin(4 * a + 1.3) + 0.008 * math.sin(9 * a)) * kk
            z = -0.050 + 0.052 * (t ** 0.7) + dz
            row.append(und.v(cf.M @ V((r * f * math.cos(a), r * f * math.sin(a), z)), t, k / n))
        G.append(row)
    for i in range(nu):
        und.ring_bridge(G[i + 1], G[i])
    und_ob = und.to_object('ms_cap_under')
    ax = cf.Rot.to_3x3() @ V((0, 0, 1))
    orient(und_ob, lambda c: -ax)
    # --- annulus band hugging the head at the hole (a frilled ring)
    band = F.MB()
    pts = []
    n = 64
    for k in range(n):
        a = TAU * k / n
        r = hole_r(a) + 0.006
        pts.append(cf.M @ V((r * math.cos(a), r * math.sin(a), -0.006 + 0.004 * math.sin(13 * a))))
    rings = []
    for k in range(n):
        p = pts[k]
        tang = (pts[(k + 1) % n] - pts[k - 1]).normalized()
        out = (p - cf.C)
        out = (out - (cf.Rot.to_3x3() @ V((0, 0, 1))) * out.dot(cf.Rot.to_3x3() @ V((0, 0, 1)))).normalized()
        up = cf.Rot.to_3x3() @ V((0, 0, 1))
        ring = []
        for j in range(5):
            ang = TAU * j / 5
            ring.append(band.v(p + out * (0.011 * math.cos(ang)) + up * (0.013 * math.sin(ang)), 0.5, k / n))
        rings.append(ring)
    for k in range(n):
        band.ring_bridge(rings[k], rings[(k + 1) % n])
    band_ob = band.to_object('ms_cap_band')
    return top_ob, und_ob, band_ob


def cap_surface_point(cf, a, t):
    """point + normal on the dome top at angle a and radial fraction t (0 centre, 1 rim)."""
    R, H = cf.R, cf.h
    def P(a, t):
        r = R * (t ** 0.85)
        z = H * (1 - t ** 2.3) - 0.028 * (t ** 6)
        k = (r / R) ** 3
        f = 1 + (rim_mod(a) - 1) * k
        dz = (0.012 * math.sin(4 * a + 1.3) + 0.008 * math.sin(9 * a)) * k
        return V((r * f * math.cos(a), r * f * math.sin(a), z + dz))
    p = P(a, t)
    e = 1e-3
    du = P(a, min(1, t + e)) - P(a, max(1e-4, t - e))
    dv = P(a + e, t) - P(a - e, t)
    n = dv.cross(du).normalized()
    if n.z < 0:
        n = -n
    if t < 0.01:
        n = V((0, 0, 1))
    return cf.M @ p, (cf.Rot.to_3x3() @ n).normalized()


def build_warts(cf, seed=3, count=58):
    rnd = random.Random(seed)
    mb = F.MB()
    placed = []
    tries = 0
    while len(placed) < count and tries < 4000:
        tries += 1
        t = math.sqrt(rnd.uniform(0.0, 0.88))
        a = rnd.uniform(0, TAU)
        rad = rnd.uniform(0.010, 0.030) * (1.25 - 0.5 * t)
        p, n = cap_surface_point(cf, a, max(0.02, t))
        if any((p - q).length < (rad + rq) * 1.25 for q, rq in placed):
            continue
        placed.append((p, rad))
        Mrot = n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        # flattened, slightly irregular wart (hemi-ellipsoid with a lumpy top)
        sq = rnd.uniform(0.75, 1.0)
        rs = mb.ellipsoid(p - n * rad * 0.15, (rad, rad * sq, rad * 0.42), segs=9, rings=4, M=Mrot, hemi=True)
    ob = mb.to_object('ms_warts')
    F.displace(ob, lambda c, nn: 0.0018 * F.nz(c, 160.0))
    return ob


# ------------------------------------------------------------------------------------------------ bodice
def build_bodice(body, L, inflate=0.010):
    """Shell from the body's torso faces: duplicated, welded (glTF splits UV seams), cut by planes, inflated."""
    src = body.mesh
    me = src.data
    dom = body.dominant()
    torso = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01', 'upperarm_l',
             'upperarm_r', 'thigh_l', 'thigh_r'}
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if not all(dom[v.index] in torso for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    z_low = L['thigh_l'].z - 0.06
    z_neck = L['neck_01'].z + 0.004
    x_sleeve = 0.27
    za = L['upperarm_l'].z

    def cut(co, no, keep_pos):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=keep_pos, clear_outer=not keep_pos)
    cut(V((0, 0, z_low)), V((0, 0, 1)), True)
    cut(V((0, 0, z_neck)), V((0, -0.6, 1)).normalized(), False)
    cut(V((x_sleeve, 0, za)), V((1, 0, -0.35)).normalized(), False)
    cut(V((-x_sleeve, 0, za)), V((-1, 0, -0.35)).normalized(), False)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    nm = bpy.data.meshes.new('ms_bodice')
    bm.to_mesh(nm)
    bm.free()
    ob = bpy.data.objects.new('ms_bodice', nm)
    F.link(ob)
    for g in src.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    nm.shade_smooth()
    nm.update()
    F.smooth_verts(ob, 3, 0.3)
    nm.update()
    for v in nm.vertices:
        v.co += v.normal * inflate
    nm.update()
    F.push_out(ob, F.bvh_objs([src]), clearance=inflate * 0.8, iters=4, smooth_iters=2, max_dist=0.08)
    return ob


# ------------------------------------------------------------------------------------------------ skirt
class SkirtSpec:
    def __init__(self, L):
        self.z_top = L['spine_01'].z + 0.01
        self.z_hip = L['thigh_l'].z - 0.02
        self.z_hem = 0.315
        self.z_slit = L['calf_l'].z + 0.24
        self.center = V((0, 0.035, 0))
        self.segs = 64
        self.rows = 18


def build_skirt(body_bvh, sp, seed=1):
    rnd = random.Random(seed)
    n, rows = sp.segs, sp.rows
    zs = []
    for i in range(rows + 1):
        u = i / rows
        zs.append(sp.z_top + (sp.z_hem - sp.z_top) * (u ** 0.92))
    # body radius per row/angle (outermost surface), skirt flare profile
    Rb = np.zeros((rows + 1, n + 1))
    for i, z in enumerate(zs):
        for k in range(n + 1):
            phi = TAU * k / n
            r = F.ray_radius(body_bvh, V((sp.center.x, sp.center.y, z)), dirp(phi), 0.7)
            Rb[i, k] = r if r is not None else 0.0
    R = np.zeros_like(Rb)
    for i, z in enumerate(zs):
        drop = max(0.0, sp.z_hip - z)
        base = 0.150 + 0.27 * (drop ** 1.05)
        for k in range(n + 1):
            phi = TAU * k / n
            ell = 1.0 / math.sqrt((math.sin(phi) / 1.0) ** 2 + (math.cos(phi) / 0.80) ** 2)
            prof = base * ell if z < sp.z_hip + 0.06 else 0.0
            R[i, k] = max(Rb[i, k] + 0.014, prof)
    # circular smoothing + monotone flare (never tucks back in going down)
    for _ in range(3):
        R[:, :n] = (np.roll(R[:, :n], 1, 1) + 2 * R[:, :n] + np.roll(R[:, :n], -1, 1)) / 4
        R[:, n] = R[:, 0]
    for i in range(1, rows + 1):
        R[i] = np.maximum(R[i], R[i - 1] - 0.004)
    for _ in range(2):
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4

    def slit_w(z):
        if z >= sp.z_slit:
            return 0.0
        return math.radians(15.0) * F.sstep(sp.z_slit, sp.z_hem, z) ** 0.8

    def hem_wave(phi):
        return 0.020 * math.sin(7 * phi + 0.4) + 0.012 * math.sin(13 * phi + 1.1)

    mb = F.MB()
    G = []
    for i, z in enumerate(zs):
        u = i / rows
        w = slit_w(z)
        row = []
        for k in range(n + 1):
            v = k / n
            phi = w + (TAU - 2 * w) * v
            kf = phi / TAU * n
            k0 = int(kf) % n
            fr = kf - int(kf)
            r = R[i, k0] * (1 - fr) + R[i, k0 + 1] * fr
            zz = z + hem_wave(phi) * (u ** 3)
            p = V((sp.center.x, sp.center.y, zz)) + dirp(phi) * r
            row.append(mb.v(p, u, v))
        G.append(row)
    for i in range(rows):
        for k in range(n):
            mb.f([G[i][k], G[i][k + 1], G[i + 1][k + 1], G[i + 1][k]])
    ob = mb.to_object('ms_skirt')
    # cloth folds: vertical wave displacement growing toward the hem
    F.displace(ob, lambda c, nn: (0.010 * math.sin(math.atan2(c.x, -(c.y - sp.center.y)) * 14 + F.nz(c, 6) * 2.0)
                                  + 0.004 * F.nz(c, 22)) * F.sstep(sp.z_hip, sp.z_hem, c.z))
    orient(ob, lambda c: V((c.x, c.y - sp.center.y, 0)))
    return ob, (zs, R)


def skirt_r(prof, z, phi):
    zs, R = prof
    n = R.shape[1] - 1
    if z >= zs[0]:
        i0, f = 0, 0.0
    elif z <= zs[-1]:
        i0, f = len(zs) - 2, 1.0
    else:
        i0 = max(i for i in range(len(zs) - 1) if zs[i] >= z)
        f = (zs[i0] - z) / (zs[i0] - zs[i0 + 1])
    kf = (phi % TAU) / TAU * n
    k0 = int(kf) % n
    fr = kf - int(kf)
    a = R[i0, k0] * (1 - fr) + R[i0, k0 + 1] * fr
    b = R[i0 + 1, k0] * (1 - fr) + R[i0 + 1, k0 + 1] * fr
    return a * (1 - f) + b * f


def build_tier(sp, prof, z_a, h, flare, phi0, lobes, seed, name, segs=84, rows=4, ruff=26):
    """A frill (flounce with shelf-fungus lobes) attached to the skirt at z_a over phi in [phi0, TAU - phi0];
    phi0 = 0 makes a closed ring. Thick rounded edge, flounce waves, lobed scalloped hem."""
    rnd = random.Random(seed)
    closed = phi0 <= 1e-6
    span = TAU - 2 * phi0
    mb = F.MB()
    G = []
    lob_ph = rnd.uniform(0, 1)
    ncol = segs if closed else segs + 1
    for i in range(rows + 1):
        t = i / rows                   # 0 attach .. 1 edge
        row = []
        for k in range(ncol):
            v = k / segs
            phi = phi0 + span * v
            s_ = (v * lobes + lob_ph) % 1.0
            lobe = math.sin(math.pi * s_) ** 0.5
            edge_drop = h * (0.62 + 0.38 * lobe)
            z = z_a - edge_drop * (t ** 0.85)
            r0 = skirt_r(prof, z_a, phi) + 0.005
            r1 = skirt_r(prof, z_a - edge_drop, phi) + 0.007
            out = flare * (0.7 + 0.3 * lobe)
            r = r0 + (r1 - r0) * t + out * (t ** 1.6)
            wave = math.sin(phi * ruff + seed) * 0.5 + 0.5 * math.sin(phi * ruff * 1.7 + 2 * seed)
            r += 0.013 * wave * (t ** 1.8)
            z += 0.010 * wave * (t ** 2)
            if not closed:
                endk = F.sstep(0.0, 0.05, v) * F.sstep(1.0, 0.95, v)
                r = r0 + (r - r0) * (0.15 + 0.85 * endk)
                z = z_a + (z - z_a) * (0.25 + 0.75 * endk)
            row.append(mb.v(V((sp.center.x, sp.center.y, z)) + dirp(phi) * r, t, v * lobes))
        G.append(row)
    for i in range(rows):
        for k in range(segs):
            k1 = (k + 1) % ncol if closed else k + 1
            mb.f([G[i][k], G[i][k1], G[i + 1][k1], G[i + 1][k]])
    ob = mb.to_object(name)
    orient(ob, lambda c: V((c.x, c.y - sp.center.y, 0)))
    return ob


def build_roots(sp, prof, seed=5, count=26):
    rnd = random.Random(seed)
    mb = F.MB()
    for j in range(count):
        phi = math.radians(26) + (TAU - math.radians(52)) * (j + rnd.uniform(-0.35, 0.35)) / (count - 1)
        z0 = sp.z_hem + 0.020 * math.sin(7 * phi + 0.4) + 0.012 * math.sin(13 * phi + 1.1) + 0.035
        r0 = skirt_r(prof, z0, phi) - 0.006
        p0 = V((sp.center.x, sp.center.y, z0)) + dirp(phi) * r0
        back = 0.5 - 0.5 * math.cos(phi)
        L = rnd.uniform(0.12, 0.24) + 0.07 * back
        z_end = max(0.06, z0 - L)
        pts, rads = [], []
        nseg = 7
        side = V((math.cos(phi), math.sin(phi), 0)) * rnd.uniform(-1, 1)
        curl = rnd.uniform(0.02, 0.06)
        th = rnd.uniform(0.006, 0.010)
        for s_ in range(nseg + 1):
            t = s_ / nseg
            p = p0 + dirp(phi) * (curl * t ** 1.4) + side * (0.025 * math.sin(t * 3.5 + j))
            p.z = z0 + (z_end - z0) * t + 0.03 * (t ** 3) * back
            p += V((F.nz(p, 12, j) * 0.012, F.nz(p, 12, j + 5) * 0.012, 0)) * t
            pts.append(p)
            rads.append(th * (1 - t) ** 0.8 + 0.0018)
        mb.sweep(pts, rads, sides=5, cap0=None, cap1='round', cap_segs=1)
        if j % 2 == 0:
            b0 = pts[rnd.randint(3, 5)]
            d = dirp(phi + rnd.uniform(-0.6, 0.6)) * 0.035 + V((0, 0, -0.03))
            q = [b0 + d * (s_ / 4) + V((0, 0, -0.01 * (s_ / 4) ** 2)) for s_ in range(5)]
            mb.sweep(q, [0.0045 * (1 - s_ / 5) + 0.0012 for s_ in range(5)], sides=5, cap0=None, cap1='round',
                     cap_segs=1)
    return mb.to_object('ms_roots')



# ------------------------------------------------------------------------------------------------ collar, shoulders
def neckline_z(L, y):
    return L['neck_01'].z + 0.6 * (y - 0.0)


def neck_edge(bodice, c, n=80):
    """z of the bodice's neckline boundary per angle (boundary edges above the shoulders)."""
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(bodice.data)
    pts = []
    for e in bm.edges:
        if e.is_boundary:
            for v in e.verts:
                p = v.co
                if p.z > c.z - 0.08 and abs(p.x) < 0.11:
                    pts.append(p.copy())
    bm.free()
    out = []
    for k in range(n):
        phi = TAU * k / n
        best, bw = None, 1e9
        for p in pts:
            a = math.atan2(p.x - c.x, -(p.y - c.y))
            d = abs((a - phi + math.pi) % TAU - math.pi)
            if d < bw:
                best, bw = p, d
        out.append(best.z if best is not None else c.z)
    for _ in range(2):
        out = [(out[k - 1] + 2 * out[k] + out[(k + 1) % n]) / 4 for k in range(n)]
    return out


def build_collar(bvh, L, bodice, segs=80, waves=22):
    """The mushroom's ring (annulus) worn as a drooping ruffled collar over the bodice's neckline."""
    c = V((0, 0.025, L['neck_01'].z))
    edge = neck_edge(bodice, c, segs)
    mb = F.MB()
    rows = 4
    G = []
    for i in range(rows + 1):
        t = i / rows
        row = []
        for k in range(segs):
            phi = TAU * k / segs
            d = dirp(phi)
            z0 = edge[k] + 0.006
            rb = F.ray_radius(bvh, V((c.x, c.y, z0)), d, 0.3) or 0.065
            back = 0.5 - 0.5 * math.cos(phi)
            wave = math.sin(phi * waves) * 0.6 + 0.4 * math.sin(phi * waves * 1.6 + 1.0)
            width = 0.040 + 0.020 * back
            r = rb + 0.003 + width * (t ** 0.9) + 0.010 * wave * (t ** 1.6)
            z = z0 - (0.036 + 0.010 * back) * (t ** 1.3) + 0.007 * wave * (t ** 2)
            row.append(mb.v(V((c.x, c.y, z)) + d * r, t, phi / TAU * waves))
        G.append(row)
    for i in range(rows):
        mb.ring_bridge(G[i], G[i + 1])
    ob = mb.to_object('ms_collar')
    orient(ob, lambda q: V((q.x, q.y - 0.025, 0.4)))
    return ob


def bracket(mb, base, out, R, thick, lobes, seed, droop=0.35, nr=4, nt=12, span=100):
    """One bracket (shelf) fungus: a lobed half-disc lens, thick at the base, rounded thin edge."""
    rnd = random.Random(seed)
    o = V(out).normalized()
    up = V((0, 0, 1))
    sd = up.cross(o).normalized()
    u = o.cross(sd).normalized()
    ph = rnd.uniform(0, 6)
    rows = []
    for side in (1, -1):                         # top surface out to the rim, then bottom back in
        rng = range(nr + 1) if side == 1 else range(nr - 1, -1, -1)
        for i in rng:
            t = i / nr
            row = []
            for j in range(nt + 1):
                th = math.radians(-span + 2 * span * j / nt)
                lob = 0.86 + 0.14 * math.cos(th * lobes + ph)
                rr = R * t * lob
                dz = -droop * R * (t ** 2) * (0.6 + 0.4 * math.cos(th))
                half = thick * 0.5 * (1 - 0.75 * t ** 1.3)
                p = base + (o * math.cos(th) + sd * math.sin(th)) * rr + u * (dz + side * half)
                row.append(mb.v(p, t, j / nt * 3))
            rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(nt):
            mb.f([rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]])


def build_shoulder_shelves(body_bvh, L, seed=11):
    """Bracket-fungus clusters sitting on both shoulders (epaulettes)."""
    mb = F.MB()
    sh = L['upperarm_l']
    for s in (1, -1):
        for k, (x, y, dz, R, th, ox, oy, oz) in enumerate([
                (0.150, 0.020, 0.010, 0.115, 0.042, 1.0, -0.10, 0.18),
                (0.160, 0.080, -0.010, 0.085, 0.034, 0.8, 0.70, 0.10),
                (0.175, -0.035, -0.030, 0.072, 0.030, 0.9, -0.75, 0.05)]):
            p0 = V((s * x, sh.y + y - 0.03, sh.z + 0.25))
            hit = body_bvh.ray_cast(p0, V((0, 0, -1)), 0.6)
            base = (hit[0] if hit[0] is not None else V((s * x, sh.y + y, sh.z + 0.05))) + V((0, 0, dz + 0.006))
            bracket(mb, base, V((s * ox, oy, oz)), R, th, 5 + k, seed + k * 7 + (s > 0) * 31, droop=0.22)
    return mb.to_object('ms_shoulders')


# ------------------------------------------------------------------------------------------------ hair (mycelium threads)
def build_hood(bvh, L, cf, hole, seed=21, cols=48, rows=10, phi0=math.radians(68)):
    """Mycelium hood: hangs from under the cap around the back and sides of the head down to the shoulders."""
    mb = F.MB()
    axis = V((0.0, L['head_c'].y + 0.012, 0.0))
    hole_n = len(hole)
    span = TAU - 2 * phi0
    colpts = []
    for k in range(cols + 1):
        v = k / cols
        phi = phi0 + span * v
        back = 0.5 - 0.5 * math.cos(phi)
        a_loc = math.atan2(-math.cos(phi), math.sin(phi))
        hr = hole[int((a_loc % TAU) / TAU * hole_n) % hole_n]
        root = cf.M @ V((hr * math.cos(a_loc), hr * math.sin(a_loc), -0.008))
        z_end = L['neck_01'].z + 0.03 - 0.17 * back ** 1.2 + 0.018 * math.sin(phi * 11 + 0.5) * back
        pts = []
        r_prev = prev_z = None
        for i in range(rows + 1):
            t = i / rows
            z = root.z + (z_end - root.z) * t
            rb = F.ray_radius(bvh, V((axis.x, axis.y, z)), dirp(phi), 0.5) or 0.06
            r = rb + 0.012
            if r_prev is not None:
                r = max(r, r_prev - 0.30 * abs(z - prev_z))
            if i == 0:
                r = max(r, (root - V((axis.x, axis.y, root.z))).length)
            r_prev, prev_z = r, z
            fold = 0.006 * math.sin(phi * 9 + 1.0) * t
            r += (0.050 * back + 0.020) * (t ** 2.2) + fold
            pts.append(V((axis.x, axis.y, z)) + dirp(phi) * r)
        colpts.append(pts)
    G = []
    for i in range(rows + 1):
        G.append([mb.v(colpts[k][i], i / rows, k / cols) for k in range(cols + 1)])
    for i in range(rows):
        for k in range(cols):
            mb.f([G[i][k], G[i][k + 1], G[i + 1][k + 1], G[i + 1][k]])
    ob = mb.to_object('ms_hood')
    orient(ob, lambda c: V((c.x, c.y - axis.y, 0)))
    return ob


def build_belt(prof, sp, L, seed=41):
    """Twisted mycelium cord at the waist + a cluster of little mushrooms on her left hip."""
    rnd = random.Random(seed)
    mb = F.MB()
    z = sp.z_top - 0.035
    for strand in range(2):
        pts, rads = [], []
        n = 64
        for k in range(n + 1):
            phi = TAU * k / n
            r = skirt_r(prof, z, phi) + 0.010
            off = 0.007 * math.cos(phi * 14 + strand * math.pi)
            dz = 0.007 * math.sin(phi * 14 + strand * math.pi)
            pts.append(V((sp.center.x, sp.center.y, z + dz)) + dirp(phi) * (r + off))
            rads.append(0.0075)
        mb.sweep(pts, rads, sides=5, cap0=None, cap1=None)
    phi_k = math.radians(62)
    for e in range(2):
        q = []
        for s_ in range(9):
            t = s_ / 8
            zz = z - 0.20 * t - 0.03 * e
            rr = skirt_r(prof, zz, phi_k + 0.06 * e) + 0.02 + 0.03 * t
            q.append(V((sp.center.x, sp.center.y, zz)) + dirp(phi_k + 0.06 * e + 0.05 * math.sin(t * 4)) * rr)
        mb.sweep(q, [0.007] * 8 + [0.009], sides=5, cap0=None, cap1='round', cap_segs=1)
    belt = mb.to_object('ms_belt')
    caps = F.MB()
    for j, (dphi, dz, h, rc) in enumerate([(0.0, 0.0, 0.05, 0.034), (0.16, -0.03, 0.035, 0.024),
                                           (-0.14, -0.02, 0.03, 0.020), (0.07, 0.035, 0.025, 0.016)]):
        phi = math.radians(70) + dphi
        r = skirt_r(prof, z + dz, phi) + 0.012
        base = V((sp.center.x, sp.center.y, z + dz)) + dirp(phi) * r
        d = (dirp(phi) * 0.9 + V((0, 0, 1.0)) + V((rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), 0))).normalized()
        stem = [base + d * (h * s_ / 5) for s_ in range(6)]
        caps.sweep(stem, [rc * 0.28 * (1.15 - 0.25 * s_ / 5) for s_ in range(6)], sides=8, cap0=None, cap1=None,
                   us=[0.9] * 6)
        M = Matrix.Translation(stem[-1]) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        prf, us = [], []
        for i in range(9):
            t = i / 8
            prf.append((rc * math.sin(t * math.pi / 2), rc * 0.55 * math.cos(t * math.pi / 2) ** 0.8))
            us.append(0.8 * t)
        prf.append((rc * 1.02, -rc * 0.06)); us.append(0.85)
        prf.append((rc * 0.25, -rc * 0.10)); us.append(1.0)
        caps.lathe(prf, 16, M, close_top=False, close_bot=True, us=us)
    hip = caps.to_object('ms_hipcaps')
    return belt, hip


def build_cuffs(L, body_bvh):
    """Mycelium thread wraps around both forearms near the wrist."""
    mb = F.MB()
    for s in (1, -1):
        wx = abs(L['hand_l'].x)
        for j in range(4):
            x = s * (wx - 0.035 - 0.022 * j)
            c = V((x, L['hand_l'].y + 0.002, L['hand_l'].z))
            ring = []
            for k in range(17):
                a = TAU * k / 16
                d = V((0, math.cos(a), math.sin(a)))
                r = F.ray_radius(body_bvh, c, d, 0.12) or 0.03
                ring.append(c + d * (r + 0.004) + V((s * 0.006 * math.sin(a + j), 0, 0)))
            mb.sweep(ring, [0.0045] * 17, sides=4, cap0=None, cap1=None)
    return mb.to_object('ms_cuffs')


# ------------------------------------------------------------------------------------------------ staff
def staff_local(seed=31):
    """Staff in its own frame: grip at the origin, +Z = up the staff (toward the index side of the fist)."""
    rnd = random.Random(seed)
    mb = F.MB()
    bottom, top = -0.92, 1.00
    n = 34
    pts, rads = [], []
    for i in range(n + 1):
        t = i / n
        z = bottom + (top - bottom) * t
        bend = V((0.018 * math.sin(t * 7.0 + 0.6) + 0.010 * math.sin(t * 17), 0.014 * math.sin(t * 5.0 + 2.0), 0))
        bend *= F.sstep(0.0, 0.08, abs(z))                      # straight through the fist
        knot = sum(0.006 * math.exp(-((z - kz) / 0.03) ** 2) for kz in (-0.62, -0.28, 0.34, 0.66))
        r = 0.020 + 0.004 * t + knot + (0.006 * F.sstep(0.82, 1.0, t))
        pts.append(V((0, 0, z)) + bend)
        rads.append(r)
    mb.sweep(pts, rads, sides=12, cap0='round', cap1='flat', twist=1.2)
    top_p = pts[-1]
    # bottom roots
    b = pts[0]
    for j in range(5):
        a = TAU * j / 5 + 0.4
        q = [b + V((math.cos(a) * 0.05 * (s / 5) ** 1.3, math.sin(a) * 0.05 * (s / 5) ** 1.3, 0.04 - 0.06 * s / 5))
             for s in range(6)]
        mb.sweep(q, [0.010 * (1 - s / 6) + 0.002 for s in range(6)], sides=6, cap0=None, cap1='round', cap_segs=1,
                 us=[0.0] * 6)
    stalk = mb.to_object('ms_staff_stalk')
    F.displace(stalk, lambda c, nn: 0.0015 * F.nz(c, 90))
    # crown: one mushroom cap + two small ones (pu < 0.85 = cap top, 1 = gills)
    caps = F.MB()

    def mush(base, dirv, h, rc):
        d = dirv.normalized()
        stem = [base + d * (h * s / 5) for s in range(6)]
        caps.sweep(stem, [rc * 0.30 * (1.1 - 0.2 * s / 5) for s in range(6)], sides=10, cap0=None, cap1=None,
                   us=[0.9] * 6)
        M = Matrix.Translation(stem[-1]) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        prof, us = [], []
        for i in range(9):
            t = i / 8
            prof.append((rc * math.sin(t * math.pi / 2) * 1.0, rc * 0.42 * math.cos(t * math.pi / 2) ** 0.8))
            us.append(0.8 * t)
        prof.append((rc * 1.02, -rc * 0.06)); us.append(0.85)
        prof.append((rc * 0.25, -rc * 0.10)); us.append(1.0)
        caps.lathe(prof, 20, M, close_top=False, close_bot=True, us=us)
    mush(top_p - V((0, 0, 0.02)), V((0.05, 0.02, 1)), 0.07, 0.070)
    mush(top_p - V((0, 0, 0.10)), V((1, 0.3, 0.6)), 0.05, 0.040)
    mush(top_p - V((0, 0, 0.15)), V((-0.8, -0.5, 0.5)), 0.04, 0.032)
    caps_ob = caps.to_object('ms_staff_caps')
    # glowing spore bulb cradled under the big cap
    bulb = F.MB()
    bulb.ellipsoid(top_p + V((0.0, -0.035, 0.035)), (0.028, 0.028, 0.030), segs=14, rings=8)
    bulb_ob = bulb.to_object('ms_staff_bulb')
    # mycelium wrap at the grip
    wrap = F.MB()
    for j in range(7):
        z = -0.07 + 0.02 * j
        ring = []
        for k in range(17):
            a = TAU * k / 16
            ring.append(V((math.cos(a) * 0.0235, math.sin(a) * 0.0235, z + 0.008 * math.sin(a))))
        wrap.sweep(ring, [0.0035] * 17, sides=5, cap0=None, cap1=None)
    wrap_ob = wrap.to_object('ms_staff_wrap')
    return [stalk, caps_ob, bulb_ob, wrap_ob], top_p

"""Saint Aurelia the Unthawed -- geometry builders (world space, rest T-pose of the reshaped UBC female body)."""
import math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import fblib as F

V = Vector
TAU = 2 * math.pi


def orient(ob, fn):
    """flip faces so their normals agree with fn(face centre)."""
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
    """horizontal direction for angle phi from the front (-Y) toward her left (+X)."""
    return V((math.sin(phi), -math.cos(phi), 0.0))


def split_faces(ob, pred, name):
    """move the faces whose centre passes pred(centre, face) into a new object (same weights/attributes)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    keep = [f for f in bm.faces if not pred(f.calc_center_median(), f)]
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    kill2 = [f for f in bm2.faces if not pred(f.calc_center_median(), f)]
    bmesh.ops.delete(bm2, geom=kill2, context='FACES')
    bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if not v.link_faces], context='VERTS')
    me = bpy.data.meshes.new(name)
    bm2.to_mesh(me)
    bm2.free()
    o2 = bpy.data.objects.new(name, me)
    F.link(o2)
    for g in ob.vertex_groups:
        o2.vertex_groups.new(name=g.name)
    me.shade_smooth()
    ob.data.update()
    return o2


# ------------------------------------------------------------------------------------------------ shell (alb top)
def build_shell(body, L, name, bones, cuts, inflate=0.010, smooth=3):
    src = body.mesh
    dom = body.dominant()
    bm = bmesh.new()
    bm.from_mesh(src.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(dom[v.index] in bones for v in f.verts)],
                     context='FACES')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for co, no, keep_pos in cuts:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=V(no).normalized(), clear_inner=keep_pos,
                               clear_outer=not keep_pos)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    nm = bpy.data.meshes.new(name)
    bm.to_mesh(nm)
    bm.free()
    ob = bpy.data.objects.new(name, nm)
    F.link(ob)
    for g in src.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    nm.shade_smooth()
    F.smooth_verts(ob, smooth, 0.3)
    nm.update()
    for v in nm.vertices:
        v.co += v.normal * inflate
    nm.update()
    F.push_out(ob, F.bvh_objs([src]), clearance=inflate * 0.8, iters=4, smooth_iters=2, max_dist=0.08)
    return ob


# ------------------------------------------------------------------------------------------------ robe skirt (alb)
class SkirtSpec:
    def __init__(self, L, z_hem=0.115, slit_deg=17.0):
        self.z_top = L['spine_01'].z + 0.01
        self.z_hip = L['thigh_l'].z - 0.02
        self.z_hem = z_hem
        self.z_slit = L['calf_l'].z + 0.22
        self.slit = math.radians(slit_deg)
        self.center = V((0, 0.035, 0))
        self.segs = 64
        self.rows = 22
        self.flare = (0.150, 0.20)
        self.ell_y = 0.82


def build_skirt(body_bvh, sp, name='au_alb'):
    n, rows = sp.segs, sp.rows
    zs = [sp.z_top + (sp.z_hem - sp.z_top) * ((i / rows) ** 0.95) for i in range(rows + 1)]
    Rb = np.zeros((rows + 1, n + 1))
    for i, z in enumerate(zs):
        for k in range(n + 1):
            r = F.ray_radius(body_bvh, V((sp.center.x, sp.center.y, z)), dirp(TAU * k / n), 0.7)
            Rb[i, k] = r if r is not None else 0.0
    R = np.zeros_like(Rb)
    for i, z in enumerate(zs):
        drop = max(0.0, sp.z_hip - z)
        base = sp.flare[0] + sp.flare[1] * (drop ** 1.1)
        for k in range(n + 1):
            phi = TAU * k / n
            ell = 1.0 / math.sqrt(math.sin(phi) ** 2 + (math.cos(phi) / sp.ell_y) ** 2)
            prof = base * ell if z < sp.z_hip + 0.06 else 0.0
            R[i, k] = max(Rb[i, k] + 0.014, prof)
    for _ in range(3):
        R[:, :n] = (np.roll(R[:, :n], 1, 1) + 2 * R[:, :n] + np.roll(R[:, :n], -1, 1)) / 4
        R[:, n] = R[:, 0]
    for i in range(1, rows + 1):
        R[i] = np.maximum(R[i], R[i - 1] - 0.004)
    for _ in range(2):
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4

    def slit_w(z):
        return 0.0 if z >= sp.z_slit else sp.slit * F.sstep(sp.z_slit, sp.z_hem, z) ** 0.8

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
            zz = z + (0.010 * math.sin(5 * phi + 0.4)) * (u ** 3)
            row.append(mb.v(V((sp.center.x, sp.center.y, zz)) + dirp(phi) * r, u, v))
        G.append(row)
    for i in range(rows):
        for k in range(n):
            mb.f([G[i][k], G[i][k + 1], G[i + 1][k + 1], G[i + 1][k]])
    ob = mb.to_object(name)
    F.displace(ob, lambda c, nn: (0.011 * math.sin(math.atan2(c.x, -(c.y - sp.center.y)) * 11 + F.nz(c, 5) * 1.6)
                                  + 0.003 * F.nz(c, 20)) * F.sstep(sp.z_hip, sp.z_hem + 0.2, c.z))
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


# ------------------------------------------------------------------------------------------------ chasuble
def build_chasuble(bvh_up, bvh_hang, L, W=0.185, ncol=30, n_arc=14, n_front=18, n_back=18, clr=0.016,
                   neck_r=0.082):
    """Gothic chasuble: an arc over the shoulders (rays in each column's YZ plane) continued by front and back
    panels that hang (monotone) from the chest/shoulder blades to below the knees. Returns the mesh; face
    attribute-free classification is done by the caller via (x, z) and the stored per-vertex params."""
    za = L['upperarm_l'].z
    cols = []
    for j in range(ncol + 1):
        u = j / ncol
        x = -W + 2 * W * u
        ax = abs(x)
        zc = za - 0.13 + 0.06 * F.sstep(0.08, 0.18, ax)
        c = V((x, 0.035, zc))
        arc = []
        for i in range(n_arc + 1):
            t = math.radians(-28 + 236 * i / n_arc)
            d = V((0, -math.cos(t), math.sin(t)))
            r = F.ray_radius(bvh_up, c, d, 0.45)
            arc.append([t, d, r])
        known = [a[2] for a in arc if a[2] is not None]
        for i, a in enumerate(arc):            # fill the neck gap
            if a[2] is None:
                prev = next((arc[k][2] for k in range(i, -1, -1) if arc[k][2] is not None), None)
                nxt = next((arc[k][2] for k in range(i, len(arc)) if arc[k][2] is not None), None)
                a[2] = ((prev or nxt or 0.14) + (nxt or prev or 0.14)) * 0.5
        pts_arc = [c + d * (r + clr) for t, d, r in arc]
        # front panel (hang downward from the arc's front end)
        p0 = pts_arc[0]
        z_bot = 0.50 + 0.17 * (ax / W) ** 2
        front, y_prev = [], p0.y
        for k in range(1, n_front + 1):
            z = p0.z + (z_bot - p0.z) * (k / n_front) ** 0.9
            hit = bvh_hang.ray_cast(V((x, -1.5, z)), V((0, 1, 0)), 3.0)
            y = (hit[0].y - clr) if hit[0] is not None else y_prev
            y = min(y, y_prev + 0.0015)
            y_prev = y
            front.append(V((x, y, z)))
        p1 = pts_arc[-1]
        zb_back = 0.46 + 0.17 * (ax / W) ** 2
        back, y_prev = [], p1.y
        for k in range(1, n_back + 1):
            z = p1.z + (zb_back - p1.z) * (k / n_back) ** 0.9
            hit = bvh_hang.ray_cast(V((x, 1.5, z)), V((0, -1, 0)), 3.0)
            y = (hit[0].y + clr) if hit[0] is not None else y_prev
            y = max(y, y_prev - 0.0015)
            y_prev = y
            back.append(V((x, y, z)))
        cols.append(list(reversed(front)) + pts_arc + back)
    nrow = len(cols[0])
    mb = F.MB()
    G = [[mb.v(cols[j][i], i / (nrow - 1), j / ncol) for j in range(ncol + 1)] for i in range(nrow)]
    i_arc0, i_arc1 = n_front, n_front + n_arc
    for i in range(nrow - 1):
        for j in range(ncol):
            xm = abs(-W + 2 * W * (j + 0.5) / ncol)
            ia = i - i_arc0
            if xm < neck_r and 0 <= ia and i + 1 <= i_arc1:
                t = math.radians(-28 + 236 * (ia + 0.5) / n_arc)
                if math.radians(28) < t < math.radians(160):
                    continue
            mb.f([G[i][j], G[i][j + 1], G[i + 1][j + 1], G[i + 1][j]])
    ob = mb.to_object('au_chasuble')
    F.smooth_verts(ob, 2, 0.35)
    F.displace(ob, lambda c, nn: 0.006 * math.sin(c.x * 60 + F.nz(c, 6) * 2) * F.sstep(1.0, 0.6, c.z))
    orient(ob, lambda c: V((c.x * 0.3, c.y - 0.035, max(0.0, c.z - 1.35) * 2.0)))
    return ob


# ------------------------------------------------------------------------------------------------ sleeves, collar
def build_bell_sleeves(L, segs=18, rows=9):
    mb = F.MB()
    for s in (1, -1):
        x0 = s * (abs(L['lowerarm_l'].x) - 0.01)
        x1 = s * (abs(L['hand_l'].x) - 0.035)
        cy, cz = L['hand_l'].y + 0.004, L['hand_l'].z
        G = []
        for i in range(rows + 1):
            t = i / rows
            x = x0 + (x1 - x0) * t
            r = 0.050 + 0.068 * t ** 1.7
            dz = -0.030 * t ** 2
            row = []
            for k in range(segs):
                a = TAU * k / segs
                y = cy + math.cos(a) * r
                z = cz + dz + math.sin(a) * r * (1.0 + 0.25 * t * max(0.0, -math.sin(a)))
                row.append(mb.v(V((x, y, z)), t, k / segs))
            G.append(row)
        for i in range(rows):
            mb.ring_bridge(G[i], G[i + 1])
    ob = mb.to_object('au_sleeves')
    orient(ob, lambda c: V((0, c.y - L['hand_l'].y, c.z - L['hand_l'].z)))
    return ob


def build_collar(body_bvh, L, segs=56, rows=3):
    """gold stand-up collar (amice) around the neck base."""
    c = V((0, L['neck_01'].y - 0.005, L['neck_01'].z))
    mb = F.MB()
    G = []
    for i in range(rows + 1):
        t = i / rows
        row = []
        for k in range(segs):
            phi = TAU * k / segs
            z = c.z - 0.035 + 0.075 * t + 0.012 * (0.5 - 0.5 * math.cos(phi)) * t
            rb = F.ray_radius(body_bvh, V((c.x, c.y, z)), dirp(phi), 0.3) or 0.06
            r = rb + 0.012 + 0.012 * t
            row.append(mb.v(V((c.x, c.y, z)) + dirp(phi) * r, t, k / segs))
        G.append(row)
    for i in range(rows):
        mb.ring_bridge(G[i], G[i + 1])
    ob = mb.to_object('au_collar')
    orient(ob, lambda q: V((q.x, q.y - c.y, 0)))
    F.solidify(ob, 0.006, 1.0)
    return ob


# ------------------------------------------------------------------------------------------------ stole
def build_stole(chas_bvh, skirt_bvh, L, half_w=0.029, end_w=0.040, z_end=0.36):
    mb = F.MB()
    for s in (1, -1):
        path = []
        # over the shoulder, beside the collar
        for (x, y) in ((0.105, 0.075), (0.105, 0.040), (0.100, 0.005)):
            hit = chas_bvh.ray_cast(V((s * x, y, 2.2)), V((0, 0, -1)), 2.0)
            if hit[0] is not None:
                path.append((hit[0] + hit[1] * 0.007, hit[1]))
        ztop = path[-1][0].z if path else L['spine_03'].z + 0.12
        z = ztop - 0.03
        while z > z_end:
            x = s * (0.098 - 0.008 * F.sstep(ztop, ztop - 0.25, z))
            hit = chas_bvh.ray_cast(V((x, -1.5, z)), V((0, 1, 0)), 3.0)
            h2 = skirt_bvh.ray_cast(V((x, -1.5, z)), V((0, 1, 0)), 3.0)
            cand = [h for h in (hit, h2) if h[0] is not None]
            if cand:
                h = min(cand, key=lambda h: h[0].y)
                p = h[0] + V((0, -0.007, 0))
                prev_y = path[-1][0].y if path else p.y
                p.y = min(p.y, prev_y + 0.004)
                path.append((p, V((0, -1, 0))))
            z -= 0.035
        rows = []
        n = len(path)
        for i, (p, nrm) in enumerate(path):
            tng = (path[min(i + 1, n - 1)][0] - path[max(i - 1, 0)][0]).normalized()
            w = tng.cross(nrm).normalized()
            if w.x * s < 0:
                w = -w
            t = i / (n - 1)
            hw = half_w + (end_w - half_w) * F.sstep(0.85, 1.0, t)
            rows.append([mb.v(p - w * hw, t, 0.0), mb.v(p + w * hw, t, 1.0)])
        for i in range(n - 1):
            mb.f([rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]])
    ob = mb.to_object('au_stole')
    orient(ob, lambda c: V((0, -1, 0.2)) if c.z < 1.40 else V((0, 0, 1)))
    F.solidify(ob, 0.004, -1.0)
    return ob


# ------------------------------------------------------------------------------------------------ frost
def shard(mb, base, d, length, rad, sides=5, twist=0.0):
    d = d.normalized()
    M = d.to_track_quat('Z', 'Y').to_matrix()
    pts = [base, base + d * length * 0.55, base + d * length]
    rings = []
    for i, (p, rr) in enumerate(zip(pts[:2], (rad, rad * 0.8))):
        ring = []
        for k in range(sides):
            a = TAU * k / sides + twist
            ring.append(mb.v(p + M @ V((math.cos(a) * rr, math.sin(a) * rr, 0)), i * 0.5, k / sides))
        rings.append(ring)
    mb.ring_bridge(rings[0], rings[1])
    mb.fan(rings[1], pts[2], u=1.0)
    mb.fan(rings[0], base - d * 0.002, flip=True, u=0.0)


def build_frost(sp, prof, chas, seed=7, count=70):
    rnd = random.Random(seed)
    mb = F.MB()
    for j in range(count):
        phi = sp.slit + 0.05 + (TAU - 2 * sp.slit - 0.1) * rnd.random()
        z = sp.z_hem + 0.010 * math.sin(5 * phi + 0.4) + rnd.uniform(0.0, 0.05)
        r = skirt_r(prof, z, phi) + 0.002
        base = V((sp.center.x, sp.center.y, z)) + dirp(phi) * r
        d = dirp(phi) * rnd.uniform(0.3, 0.9) + V((0, 0, -1.0 + rnd.uniform(-0.2, 0.5)))
        d += V((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), 0))
        shard(mb, base, d, rnd.uniform(0.025, 0.07), rnd.uniform(0.005, 0.010), twist=rnd.random())
        if rnd.random() < 0.5:
            shard(mb, base + V((0, 0, 0.01)), dirp(phi) + V((rnd.uniform(-.5, .5), 0, rnd.uniform(-0.2, 0.4))),
                  rnd.uniform(0.015, 0.035), 0.004, twist=rnd.random())
    # crust along the chasuble's lower edge
    me = chas.data
    bm = bmesh.new()
    bm.from_mesh(me)
    edge_pts = []
    for e in bm.edges:
        if e.is_boundary:
            m = (e.verts[0].co + e.verts[1].co) / 2
            if m.z < 0.75:
                edge_pts.append(m.copy())
    bm.free()
    rnd.shuffle(edge_pts)
    for p in edge_pts[:28]:
        out = V((0, -1 if p.y < 0.035 else 1, 0))
        shard(mb, p, out * 0.4 + V((rnd.uniform(-.3, .3), 0, -1)), rnd.uniform(0.02, 0.05), rnd.uniform(0.004, 0.008),
              twist=rnd.random())
    return mb.to_object('au_frost')


# ------------------------------------------------------------------------------------------------ halo
def build_halo(L, back_y, seed=3, n=20):
    rnd = random.Random(seed)
    c = V((0, back_y + 0.075, L['head_c'].z + 0.065))
    R = 0.205
    mb = F.MB()
    ring = [c + V((math.cos(TAU * k / 72) * R, 0, math.sin(TAU * k / 72) * R)) for k in range(73)]
    mb.sweep(ring, [0.0065] * 73, sides=6, cap0=None, cap1=None)
    ring2 = [c + V((math.cos(TAU * k / 72) * R * 0.86, 0.004, math.sin(TAU * k / 72) * R * 0.86)) for k in range(73)]
    mb.sweep(ring2, [0.003] * 73, sides=5, cap0=None, cap1=None)
    for k in range(n):
        a = TAU * k / n + math.pi / 2
        o = V((math.cos(a), 0, math.sin(a)))
        top = 0.5 + 0.5 * math.sin(a)
        long = (k % 2 == 0)
        Ln = (0.075 + 0.075 * top) * (1.0 if long else 0.55) * rnd.uniform(0.9, 1.1)
        base = c + o * (R - 0.004)
        shard(mb, base, o + V((0, rnd.uniform(-0.08, 0.08), 0)), Ln, 0.011 if long else 0.008, sides=6,
              twist=rnd.random())
        if long:
            shard(mb, c + o * (R * 0.86), -o, 0.028, 0.005, sides=5)
    ob = mb.to_object('au_halo')
    return ob, c


# ------------------------------------------------------------------------------------------------ crozier
def crozier_local():
    """Crozier in its own frame: grip at the origin, +Z up the staff. Returns parts (shaft, gold, sun, ice)."""
    shaft = F.MB()
    pts = [V((0, 0, z)) for z in np.linspace(-0.95, 1.00, 28)]
    shaft.sweep(pts, [0.0165 - 0.002 * (p.z + 0.95) / 1.95 for p in pts], sides=12, cap0='round', cap1=None)
    shaft_ob = shaft.to_object('au_croz_shaft')
    gold = F.MB()
    for z, r, h in ((-0.95, 0.021, 0.05), (-0.10, 0.021, 0.025), (0.10, 0.021, 0.025), (0.55, 0.024, 0.04),
                    (0.98, 0.034, 0.07)):
        prof = [(r * 0.8, -h / 2), (r, -h / 4), (r * 1.08, 0), (r, h / 4), (r * 0.8, h / 2)]
        gold.lathe(prof, 16, Matrix.Translation(V((0, 0, z))), close_top=False, close_bot=False)
    # the crook: rises then curls (in the local XZ plane) into a spiral around the sun
    ctr = V((0.115, 0, 1.29))
    crook = []
    for i in range(41):
        t = i / 40
        if t < 0.18:
            p = V((0.0, 0, 1.02 + 0.15 * t / 0.18))
        else:
            u = (t - 0.18) / 0.82
            ang = math.pi - u * 1.55 * TAU * 0.80
            rr = 0.128 * (1 - 0.40 * u)
            p = ctr + V((math.cos(ang) * rr, 0, math.sin(ang) * rr))
        crook.append(p)
    gold.sweep(crook, [0.0145 * (1 - 0.35 * i / 40) for i in range(41)], sides=10, cap0=None, cap1='round')
    for i in range(10, 38, 4):       # crockets on the outside of the curl
        p = crook[i]
        o = (p - ctr).normalized()
        shard(gold, p + o * 0.010, o + V((0, 0.0, 0.25)), 0.035, 0.007, sides=5)
    gold_ob = gold.to_object('au_croz_gold')
    sun = F.MB()
    sun.ellipsoid(ctr, (0.046, 0.020, 0.046), segs=16, rings=8)
    sun_ob = sun.to_object('au_croz_sun')
    ice = F.MB()
    for k in range(14):
        a = TAU * k / 14
        o = V((math.cos(a), 0, math.sin(a)))
        shard(ice, ctr + o * 0.040, o + V((0, 0.05 * (k % 3 - 1), 0)), 0.085 if k % 2 == 0 else 0.050, 0.010, sides=4,
              twist=0.4)
    for k in range(5):                # ice crust encasing the sun front and back
        a = TAU * k / 5 + 0.3
        for sy in (1, -1):
            shard(ice, ctr + V((math.cos(a) * 0.02, sy * 0.010, math.sin(a) * 0.02)),
                  V((math.cos(a) * 0.6, sy * 1.0, math.sin(a) * 0.6)), 0.04, 0.011, sides=5, twist=a)
    ice_ob = ice.to_object('au_croz_ice')
    return [shaft_ob, gold_ob, sun_ob, ice_ob], ctr


# ------------------------------------------------------------------------------------------------ eyes, hair
def eye_spheres(eyes_ob):
    ev = [v.co.copy() for v in eyes_ob.data.vertices]
    out = []
    for s in (1, -1):
        side = [p for p in ev if p.x * s > 0]
        mn = V((min(p.x for p in side), min(p.y for p in side), min(p.z for p in side)))
        mx = V((max(p.x for p in side), max(p.y for p in side), max(p.z for p in side)))
        out.append(((mn + mx) / 2, (mx.x - mn.x) / 2))
    return out


def build_lids(spheres, ang=72, rings=10, segs=22):
    mb = F.MB()
    for c, R in spheres:
        f = V((0, -1, 0))
        M = Matrix.Translation(c) @ f.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        prof = []
        for i in range(rings + 1):
            th = math.radians(ang) * i / rings
            prof.append((math.sin(th) * (R + 0.0011), math.cos(th) * (R + 0.0011)))
        rs = mb.lathe(prof[1:], segs, M, close_top=False, close_bot=False)
        mb.fan(rs[0], M @ V((0, 0, R + 0.0011)), flip=True)
    ob = mb.to_object('au_lids')
    orient(ob, lambda q: V((0, -1, 0)))
    return ob


def build_icicle_hair(hair_ob, L, seed=13, count=40):
    """icicle strands hanging from the lower edge of the hair at the back and sides."""
    rnd = random.Random(seed)
    hv = [v.co.copy() for v in hair_ob.data.vertices]
    cy = L['head_c'].y + 0.01
    mb = F.MB()
    for j in range(count):
        phi = math.radians(76) + math.radians(208) * (j + rnd.uniform(-0.3, 0.3)) / (count - 1)
        d = dirp(phi)
        ph = phi if phi <= math.pi else phi - TAU
        cand = [p for p in hv if abs((math.atan2(p.x, -(p.y - cy)) - ph + math.pi) % TAU - math.pi) < 0.09]
        if not cand:
            continue
        root = min(cand, key=lambda p: p.z)
        back = 0.5 - 0.5 * math.cos(phi)
        Ln = rnd.uniform(0.07, 0.14) + 0.18 * back ** 1.5 * rnd.uniform(0.55, 1.0)
        pts, rads = [], []
        r0 = rnd.uniform(0.0065, 0.0105)
        for s_ in range(7):
            t = s_ / 6
            p = root + V((0, 0, 0.012)) + d * (0.006 + 0.03 * t ** 2 * back) + V((0, 0, -Ln * t))
            pts.append(p)
            rads.append(r0 * (1 - t) ** 1.5 + 0.0005)
        mb.sweep(pts, rads, sides=5, cap0=None, cap1='round', cap_segs=1, twist=0.7)
    return mb.to_object('au_icicles')

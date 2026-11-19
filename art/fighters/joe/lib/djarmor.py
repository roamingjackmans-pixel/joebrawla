"""Armour-fitting helpers: conformal shells sampled from a body mesh, body-derived cloth layers,
plate solidify with rolled rims."""
import bpy, bmesh, math
from mathutils import Vector, Matrix
import djlib as dj
from djlib import MB, V


def frame(axis, up_hint=None):
    a = Vector(axis).normalized()
    u = Vector(up_hint) if up_hint is not None else (Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((0, -1, 0)))
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    return a, u, v


class Shell:
    """Radius field around an axis segment p0->p1 sampled from a body BVH.
    pt(t, th, off): point on the smoothed surface (Fourier low-pass in th, moving average in t) + off.
    th = 0 along `up`, th = 90deg along axis x up."""

    def __init__(self, bvh, p0, p1, up=None, n_st=11, n_th=32, harm=4, t0=0.0, t1=1.0, maxd=0.3, cap=None,
                 recenter=True, smooth_t=1, centers=None, gap=0.03):
        self.gap = gap
        self.p0, self.p1 = Vector(p0), Vector(p1)
        self.a, self.u, self.v = frame(self.p1 - self.p0, up)
        self.ts = [t0 + (t1 - t0) * i / (n_st - 1) for i in range(n_st)]
        self.n_th = n_th
        self.harm = harm
        rows = []
        for t in self.ts:
            c = centers(t) if centers else self.p0.lerp(self.p1, t)
            for _ in range(2 if recenter else 1):
                hits = self._cast(bvh, c, maxd)
                good = [h for h in hits if h is not None]
                if recenter and len(good) > n_th // 2:
                    cen = sum(good, Vector()) / len(good)
                    c = cen - self.a * (cen - c).dot(self.a)
            hits = self._cast(bvh, c, maxd)
            r = [((h - c).length if h is not None else None) for h in hits]
            good = [x for x in r if x is not None]
            fill = sum(good) / len(good) if good else 0.05
            r = [x if x is not None else fill for x in r]
            if cap:
                r = [min(x, cap(t, 2 * math.pi * k / n_th)) for k, x in enumerate(r)]
            rows.append((c, self._fourier(r)))
        # smooth along t (coefficients and centres)
        for _ in range(smooth_t):
            new = []
            for i in range(len(rows)):
                j0, j1 = max(0, i - 1), min(len(rows) - 1, i + 1)
                c = (rows[j0][0] + rows[i][0] * 2 + rows[j1][0]) / 4
                co = [(rows[j0][1][k] + rows[i][1][k] * 2 + rows[j1][1][k]) / 4 for k in range(len(rows[i][1]))]
                new.append((c, co))
            rows = new
        self.rows = rows

    def _cast(self, bvh, c, maxd):
        out = []
        for k in range(self.n_th):
            th = 2 * math.pi * k / self.n_th
            d = self.u * math.cos(th) + self.v * math.sin(th)
            # outermost surface of the contiguous layer stack (body + cloth layers) along the ray
            loc, nrm, idx, dist = bvh.ray_cast(c, d, maxd)
            last = loc
            while loc is not None:
                st = loc + d * 1e-4
                loc2, nrm2, idx2, dist2 = bvh.ray_cast(st, d, self.gap)
                if loc2 is None or (loc2 - c).length > maxd:
                    break
                last = loc = loc2
            out.append(last)
        return out

    def _fourier(self, r):
        n = len(r)
        co = [sum(r) / n]
        for k in range(1, self.harm + 1):
            a = 2 / n * sum(r[j] * math.cos(2 * math.pi * k * j / n) for j in range(n))
            b = 2 / n * sum(r[j] * math.sin(2 * math.pi * k * j / n) for j in range(n))
            co += [a, b]
        return co

    def _interp(self, t):
        ts = self.ts
        if t <= ts[0]:
            i, f = 0, (t - ts[0]) / (ts[1] - ts[0])
        elif t >= ts[-1]:
            i, f = len(ts) - 2, 1 + (t - ts[-1]) / (ts[-1] - ts[-2])
        else:
            i = max(k for k in range(len(ts) - 1) if ts[k] <= t)
            f = (t - ts[i]) / (ts[i + 1] - ts[i])
        c0, k0 = self.rows[i]
        c1, k1 = self.rows[i + 1]
        return c0.lerp(c1, f), [a + (b - a) * f for a, b in zip(k0, k1)]

    def radius(self, t, th):
        c, co = self._interp(t)
        r = co[0]
        for k in range(1, self.harm + 1):
            r += co[2 * k - 1] * math.cos(k * th) + co[2 * k] * math.sin(k * th)
        return r

    def center(self, t):
        return self._interp(t)[0]

    def dirv(self, th):
        return self.u * math.cos(th) + self.v * math.sin(th)

    def pt(self, t, th, off=0.0, scale=1.0):
        c, co = self._interp(t)
        r = co[0]
        for k in range(1, self.harm + 1):
            r += co[2 * k - 1] * math.cos(k * th) + co[2 * k] * math.sin(k * th)
        return c + self.dirv(th) * (r * scale + off)


# ----------------------------------------------------------------------------------------------
def extract_region(body, keep_fn, name):
    """Copy of body faces for which keep_fn(face_center_world, dominant_bone) is True (merged seams)."""
    W = dj.read_weights(body)
    dom = [max(w.items(), key=lambda kv: kv[1])[0] if w else '' for w in W]
    me = body.data.copy()
    ob = bpy.data.objects.new(name, me)
    dj.link(ob)
    ob.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    mw = body.matrix_world
    kill = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        bones = [dom[v.index] for v in f.verts]
        b = max(set(bones), key=bones.count)
        if not keep_fn(c, b):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me)
    bm.free()
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    # bake transform: body is at identity already in our scenes
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    me.materials.clear()
    return ob


def smooth_offset(ob, offset, smooth_iters=8, factor=0.6, keep_boundary=True):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(smooth_iters):
        verts = [v for v in bm.verts if not (keep_boundary and v.is_boundary)]
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm.to_mesh(me)
    bm.free()
    me.update()
    me.shade_smooth()


def solidify(ob, thick, rim=True):
    """Give a single-sided plate thickness (inwards along normals); returns object."""
    m = ob.modifiers.new('sol', 'SOLIDIFY')
    m.thickness = thick
    m.offset = -1.0
    m.use_even_offset = True
    m.use_quality_normals = True
    m.use_rim = rim
    dj.apply_mods(ob)
    ob.data.shade_smooth()
    return ob


def boundary_loops(ob):
    """Ordered boundary vertex loops (world coords) of a mesh."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    edges = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a.index, []).append(b.index)
        adj.setdefault(b.index, []).append(a.index)
    co = {v.index: v.co.copy() for v in bm.verts}
    seen = set()
    loops = []
    for s in list(adj):
        if s in seen:
            continue
        loop = [s]
        seen.add(s)
        prev, cur = None, s
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        closed = s in adj[cur] and len(loop) > 2
        loops.append(([co[i] for i in loop], closed))
    bm.free()
    return loops


def rim_tubes(mb, loops, r, sides=6, min_len=3):
    for pts, closed in loops:
        if len(pts) < min_len:
            continue
        if closed:
            pts = pts + pts[:2]
        mb.sweep(pts, [r] * len(pts), sides=sides, cap0='flat' if not closed else None,
                 cap1='flat' if not closed else None, cap_segs=1)


def plate(name, fn, nu, nv, thick=0.006, rim_r=0.006, rim_sides=6, mask=None, rim_filter=None):
    """Parametric plate: grid fn(u, v) -> point, solidified, with rolled rims along its boundary."""
    mb = MB()
    mb.grid(fn, nu, nv, mask=mask)
    ob = mb.to_object(name + '_srf')
    loops = boundary_loops(ob)
    if rim_filter:
        loops = [l for l in loops if rim_filter(l)]
    if thick > 0:
        solidify(ob, thick)
    if rim_r > 0 and loops:
        mbr = MB()
        rim_tubes(mbr, loops, rim_r, rim_sides)
        rim = mbr.to_object(name + '_rim')
        ob = dj.join([ob, rim], name)
    else:
        ob.name = name
    return ob


def weights_lerp_axis(p0, p1, b0, b1, w0=(1.0, 0.0), w1=(0.0, 1.0)):
    """Weight fn blending b0->b1 along segment p0->p1 (projected), with end weights."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L2 = d.length_squared

    def fn(co):
        t = max(0.0, min(1.0, (co - p0).dot(d) / L2))
        t = t * t * (3 - 2 * t)
        a = w0[0] * (1 - t) + w1[0] * t
        b = w0[1] * (1 - t) + w1[1] * t
        out = {}
        if a > 0:
            out[b0] = a
        if b > 0:
            out[b1] = out.get(b1, 0) + b
        return out
    return fn


def fixed(weights):
    def fn(co):
        return dict(weights)
    return fn


def bone_centers(body, dom, bones, p0, p1, slab=0.02):
    """t -> centroid of body vertices (dominant bone in `bones`) within a slab around p0 + (p1-p0) t."""
    p0, p1 = Vector(p0), Vector(p1)
    a = (p1 - p0)
    L = a.length
    a = a / L
    mw = body.matrix_world
    pts = [mw @ v.co for v, b in zip(body.data.vertices, dom) if b in bones]

    def fn(t):
        c = p0 + a * (L * t)
        sel = [p for p in pts if abs((p - c).dot(a)) < slab]
        if len(sel) < 6:
            return c
        cen = sum(sel, Vector()) / len(sel)
        return cen - a * (cen - c).dot(a)
    return fn


def trim_covered(ob, bvh, dist=0.08, need=3):
    """Delete faces of ob that are fully hidden under the obstacle (rays along the normal + 4 tilted
    directions hit the obstacle within dist)."""
    import bmesh as _bm
    me = ob.data
    bm = _bm.new()
    bm.from_mesh(me)
    bm.normal_update()
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal
        hits = 0
        for d in (n, (n + Vector((0.4, 0, 0))).normalized(), (n + Vector((-0.4, 0, 0))).normalized(),
                  (n + Vector((0, 0, 0.4))).normalized(), (n + Vector((0, 0, -0.4))).normalized()):
            loc, nrm, idx, dd = bvh.ray_cast(c + d * 0.001, d, dist)
            if loc is not None:
                hits += 1
        if hits >= 5 - (5 - need):
            kill.append(f)
    _bm.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    _bm.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(kill)

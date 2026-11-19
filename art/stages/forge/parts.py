"""Reusable stage parts built from the DJ3D bmesh helpers (Blender coords, Z up, metres).
Every function returns a mesh object in world space (data transformed, object at identity) unless noted."""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
import dj_common as dj


def _orient(ob, p0, p1, up=(0, 0, 1)):
    """Object built along +X from the origin: rotate/translate so it spans p0 -> p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    x = d.normalized()
    u = Vector(up)
    if abs(x.dot(u)) > 0.98:
        u = Vector((0, 1, 0)) if abs(x.y) < 0.9 else Vector((1, 0, 0))
    y = u.cross(x).normalized()
    z = x.cross(y).normalized()
    R = Matrix((x, y, z)).transposed().to_4x4()
    ob.data.transform(Matrix.Translation(p0) @ R)
    ob.data.update()
    return ob


def ibeam(name, p0, p1, h=0.45, w=0.28, t=0.05, mat=None, up=(0, 0, 1)):
    L = (Vector(p1) - Vector(p0)).length
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, -h / 2 + t), (t / 2, -h / 2 + t), (t / 2, h / 2 - t), (w / 2, h / 2 - t),
           (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, h / 2 - t), (-t / 2, h / 2 - t), (-t / 2, -h / 2 + t), (-w / 2, -h / 2 + t)]
    bm = bmesh.new()
    vs = [bm.verts.new((0, y, z)) for (y, z) in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(L, 0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = dj.mesh_obj(name, bm, mat)
    return _orient(ob, p0, p1, up)


def bar(name, p0, p1, w=0.1, h=None, mat=None, up=(0, 0, 1)):
    """Rectangular bar from p0 to p1."""
    h = h or w
    L = (Vector(p1) - Vector(p0)).length
    ob = dj.box(name, L, w, h, loc=(L / 2, 0, -h / 2), mat=mat)
    return _orient(ob, p0, p1, up)


def rod(name, p0, p1, r=0.05, segs=8, mat=None):
    L = (Vector(p1) - Vector(p0)).length
    ob = dj.cyl(name, r, L, segs, mat=mat, rot=(0, 90, 0))
    return _orient(ob, p0, p1)


def catenary(p0, p1, sag, n=24):
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


def _link_mesh(bm, L, W, r, segs, M):
    """One stadium-shaped chain link (length L along local X, width W) swept with a ring of radius r."""
    path = []
    n = 6
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        path.append(Vector((L / 2 - W / 2 + W / 2 * math.cos(a), W / 2 * math.sin(a), 0)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        path.append(Vector((-L / 2 + W / 2 + W / 2 * math.cos(a), W / 2 * math.sin(a), 0)))
    rings = []
    m = len(path)
    for i in range(m):
        p = path[i]
        t = (path[(i + 1) % m] - path[i - 1]).normalized()
        nrm = Vector((0, 0, 1))
        b = t.cross(nrm).normalized()
        ring = [bm.verts.new(M @ (p + (nrm * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r)) for k in range(segs)]
        rings.append(ring)
    for i in range(m):
        a, b = rings[i], rings[(i + 1) % m]
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((a[k], a[j], b[j], b[k]))


def chain(name, pts, link=0.16, wire=0.022, mat=None, segs=5):
    """Chain links along a polyline (alternating 90 degrees)."""
    pts = [Vector(p) for p in pts]
    # resample at link pitch
    pitch = link * 0.72
    seg = []
    acc = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    total = acc[-1]
    bm = bmesh.new()
    n = max(1, int(total / pitch))
    def at(s):
        for i in range(len(pts) - 1):
            if acc[i + 1] >= s:
                t = (s - acc[i]) / max(1e-6, acc[i + 1] - acc[i])
                return pts[i].lerp(pts[i + 1], t), (pts[i + 1] - pts[i]).normalized()
        return pts[-1], (pts[-1] - pts[-2]).normalized()
    W = link * 0.62
    for i in range(n):
        p, d = at((i + 0.5) * pitch)
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        y = up.cross(d).normalized()
        z = d.cross(y)
        R = Matrix((d, y, z)).transposed()
        if i % 2:
            R = R @ Matrix.Rotation(math.pi / 2, 3, 'X')
        M = Matrix.Translation(p) @ R.to_4x4()
        _link_mesh(bm, link, W, wire, segs, M)
    return dj.mesh_obj(name, bm, mat)


def hook(name, top, size=0.35, mat=None):
    """A crane hook hanging from `top` (open toward +X)."""
    p = Vector(top)
    path = [p, p + Vector((0, 0, -size * 0.6))]
    for i in range(9):
        a = math.pi - math.pi * 1.25 * i / 8
        path.append(p + Vector((size * 0.32 * (1 + math.cos(a)) - 0.0, 0, -size * 0.6 - size * 0.32 + size * 0.32 * math.sin(a) * -1)))
    radii = [size * 0.07] * 2 + [size * (0.09 - 0.05 * i / 8) for i in range(9)]
    return dj.tube(name, path, size * 0.08, 8, mat, radii=radii)


def stairs(name, x0, x1, y0, y1, z0, z1, n, mat=None, along='y', nosing=0.03):
    """Solid stair: n steps rising from (y0, z0) to (y1, z1) (or along x)."""
    parts = []
    for i in range(n):
        za = z0 + (z1 - z0) * (i + 1) / n
        if along == 'y':
            ya = y0 + (y1 - y0) * i / n
            parts.append(dj.box(f'{name}_{i}', x1 - x0, abs(y1 - ya) + nosing, za - z0,
                                loc=((x0 + x1) / 2, (ya + y1) / 2 - math.copysign(nosing / 2, y1 - y0), z0), mat=mat))
        else:
            xa = x0 + (x1 - x0) * i / n
            parts.append(dj.box(f'{name}_{i}', abs(x1 - xa) + nosing, y1 - y0, za - z0,
                                loc=((xa + x1) / 2 - math.copysign(nosing / 2, x1 - x0), (y0 + y1) / 2, z0), mat=mat))
    return dj.join(parts, name)


def railing(name, pts, h=1.0, post=1.4, r=0.035, mat=None, mid=True):
    pts = [Vector(p) for p in pts]
    parts = []
    acc = 0.0
    parts.append(dj.tube(name + '_top', [p + Vector((0, 0, h)) for p in pts], r, 8, mat))
    if mid:
        parts.append(dj.tube(name + '_mid', [p + Vector((0, 0, h * 0.5)) for p in pts], r * 0.8, 6, mat))
    for a, b in zip(pts[:-1], pts[1:]):
        L = (b - a).length
        k = max(1, int(round(L / post)))
        for i in range(k + (1 if b is pts[-1] else 0)):
            p = a.lerp(b, i / k)
            parts.append(dj.cyl(name + '_p', r * 1.1, h, 8, loc=tuple(p), mat=mat))
    return dj.join(parts, name)


def arch_outline(cx, w, spring, segs=16, bottom=0.0):
    """XZ outline of an opening: vertical jambs from `bottom` to `spring`, semicircle on top (w = width)."""
    r = w / 2
    pts = [(cx - r, bottom), (cx + r, bottom), (cx + r, spring)]
    for i in range(1, segs):
        a = math.pi * i / segs
        pts.append((cx + r * math.cos(a), spring + r * math.sin(a)))
    pts.append((cx - r, spring))
    return pts


def cutter_xz(name, pts, y0, y1):
    """Prism from an XZ outline between y0 and y1 (for booleans)."""
    ob = dj.extrude_xz(name, pts, abs(y1 - y0), y=(y0 + y1) / 2)
    return ob


def boolean(ob, cutter, op='DIFFERENCE', remove=True):
    m = ob.modifiers.new('B', 'BOOLEAN')
    m.operation = op
    m.solver = 'EXACT'
    m.object = cutter
    dj.apply_mods(ob)
    if remove:
        bpy.data.objects.remove(cutter)
    return ob


def ring_xz(name, cx, cz, r0, r1, a0, a1, depth, y, segs=24, mat=None):
    """Arched band (annulus sector in the XZ plane) extruded along Y, centred on y."""
    outer = [(cx + r1 * math.cos(a0 + (a1 - a0) * i / segs), cz + r1 * math.sin(a0 + (a1 - a0) * i / segs)) for i in range(segs + 1)]
    inner = [(cx + r0 * math.cos(a1 - (a1 - a0) * i / segs), cz + r0 * math.sin(a1 - (a1 - a0) * i / segs)) for i in range(segs + 1)]
    bm = bmesh.new()
    pts = outer + inner
    vs0 = [bm.verts.new((x, y - depth / 2, z)) for x, z in pts]
    vs1 = [bm.verts.new((x, y + depth / 2, z)) for x, z in pts]
    n = len(pts)
    m = segs + 1
    for i in range(segs):
        # front and back quads between outer[i], outer[i+1], inner
        a, b = i, i + 1
        c, d = n - 1 - (i + 1), n - 1 - i
        bm.faces.new((vs0[a], vs0[b], vs0[c], vs0[d]))
        bm.faces.new((vs1[d], vs1[c], vs1[b], vs1[a]))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vs0[i], vs1[i], vs1[j], vs0[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return dj.mesh_obj(name, bm, mat)


def gear(name, r, teeth=16, depth=0.2, tooth=0.12, hole=0.0, spokes=0, rim=0.0, mat=None, axis='Y'):
    """Spur gear in the XZ plane (axis Y) centred on the origin; extruded along the axis."""
    pts = []
    for i in range(teeth):
        a0 = 2 * math.pi * i / teeth
        da = 2 * math.pi / teeth
        for f, rr in ((0.0, r), (0.12, r + tooth), (0.38, r + tooth), (0.5, r)):
            a = a0 + da * f
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        pts.append((r * math.cos(a0 + da * 0.75), r * math.sin(a0 + da * 0.75)))
    bm = bmesh.new()
    vs = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]
    f = bm.faces.new(vs)
    rr = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in rr['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = dj.mesh_obj(name, bm, mat)
    if spokes and rim > 0:
        cut = []
        inner_r = r - rim
        hub = max(hole + 0.06 * r, 0.22 * r)
        for k in range(spokes):
            a0 = 2 * math.pi * k / spokes
            da = 2 * math.pi / spokes
            sw = 0.16 * r / max(inner_r, 1e-3)
            pts2 = []
            n = 6
            for i in range(n + 1):
                a = a0 + sw + (da - 2 * sw) * i / n
                pts2.append((inner_r * math.cos(a), inner_r * math.sin(a)))
            for i in range(n + 1):
                a = a0 + da - sw - (da - 2 * sw) * i / n
                pts2.append((hub * math.cos(a), hub * math.sin(a)))
            c = dj.extrude_xz(name + '_cut', pts2, depth * 3, y=0)
            cut.append(c)
        cj = dj.join(cut, name + '_cutj')
        boolean(ob, cj)
    if hole > 0:
        c = dj.cyl(name + '_hole', hole, depth * 3, 16, loc=(0, depth * 1.5, 0), rot=(90, 0, 0))
        boolean(ob, c)
    if axis == 'Z':
        dj.xform(ob, rot=(90, 0, 0))
    elif axis == 'X':
        dj.xform(ob, rot=(0, 0, 90))
    return ob


def key_obj(name, L=0.5, mat=None):
    """A big old-fashioned key lying along +X (flat, on z=0)."""
    parts = []
    rb = L * 0.18
    bow = dj.tube(name + '_bow', [(rb * math.cos(2 * math.pi * i / 12) - rb, 0, rb * math.sin(2 * math.pi * i / 12)) for i in range(13)], L * 0.035, 6, mat)
    parts.append(bow)
    parts.append(dj.cyl(name + '_shaft', L * 0.03, L * 0.78, 8, loc=(0, 0, 0), rot=(0, 90, 0), mat=mat))
    parts.append(dj.box(name + '_bit1', L * 0.07, L * 0.03, L * 0.16, loc=(L * 0.7, 0, -L * 0.16), mat=mat))
    parts.append(dj.box(name + '_bit2', L * 0.05, L * 0.03, L * 0.11, loc=(L * 0.6, 0, -L * 0.11), mat=mat))
    parts.append(dj.cyl(name + '_collar', L * 0.05, L * 0.04, 8, loc=(L * 0.02, 0, 0), rot=(0, 90, 0), mat=mat))
    ob = dj.join(parts, name)
    dj.xform(ob, rot=(90, 0, 0))   # lie flat: bow ring in the XY plane
    mn = min(v.co.z for v in ob.data.vertices)
    dj.xform(ob, loc=(0, 0, -mn))
    return ob


def padlock(name, s=0.4, body=None, shackle=None):
    """Padlock standing on z=0, facing -Y."""
    parts = []
    b = dj.box(name + '_body', s, s * 0.35, s * 0.8, loc=(0, 0, 0), mat=body, cuts=1)
    dj.bevel(b, s * 0.08, 3, 35)
    parts.append(b)
    path = [(s * 0.3 * math.cos(math.pi * i / 10), 0, s * 0.8 + s * 0.12 + s * 0.3 * math.sin(math.pi * i / 10)) for i in range(11)]
    path = [(path[0][0], 0, s * 0.7)] + path + [(path[-1][0], 0, s * 0.7)]
    parts.append(dj.tube(name + '_sh', path, s * 0.055, 8, shackle or body))
    parts.append(dj.cyl(name + '_kh', s * 0.06, s * 0.02, 10, loc=(0, -s * 0.18, s * 0.38), rot=(90, 0, 0), mat=shackle or body))
    return dj.join(parts, name)


def sign_board(name, text, w, h, board_mat, depth=0.06):
    """Board facing -Y with its bottom centre at the origin (text via the material)."""
    b = dj.box(name, w, depth, h, loc=(0, 0, 0), mat=board_mat, cuts=1)
    dj.bevel(b, min(w, h) * 0.03, 2, 35)
    return b


def lathe_obj(name, prof, segs=24, mat=None, loc=(0, 0, 0)):
    return dj.lathe(name, prof, segs, mat, loc=loc)


def blob_cluster(name, center, radius, n=8, seed=0, subdiv=1, squash=1.0, mat=None, spread=1.0):
    """Lumpy stylised cloud/smoke/rock cluster of icospheres around center."""
    r = random.Random(seed)
    parts = []
    c = Vector(center)
    for i in range(n):
        rr = radius * r.uniform(0.45, 1.0)
        off = Vector((r.uniform(-1, 1), r.uniform(-1, 1) * 0.6, r.uniform(-0.4, 1))) * radius * spread
        s = dj.ico(f'{name}_{i}', rr, subdiv, loc=tuple(c + off), scale=(1, 1, squash), mat=mat)
        dj.warp(s, rr * 0.18, 1.2 / max(rr, 0.1), seed=seed * 31 + i)
        parts.append(s)
    return dj.join(parts, name)


def terrain(name, x0, x1, y0, y1, nx, ny, fn):
    """Height field grid: fn(x, y) -> z."""
    def f(u, v):
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * v
        return (x, y, fn(x, y))
    ob = dj.grid(name, nx, ny, f, uv=False)
    return ob

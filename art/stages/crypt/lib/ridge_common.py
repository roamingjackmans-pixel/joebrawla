"""Natural rock ridge for the WallPanel slot (template glyph 'P', src/Zone/ZonePlacer.cs Wall()): shared by
fungal_kit.py (fungal_ridge) and crypt_ridge.py (crypt_ridge).

Slot contract: origin at the base centre on the ground, length along X ~2.0 m with rounded ends overlapping to about
+-1.12 m (neighbours merge into one continuous ridge), height 3.12 m (the placer sinks it 0.6-1.2 m, so the crest
detail lives in the top ~2.5 m and the visible foot is around z 0.6-1.4), depth along Y ~+-0.2 m core with the foot
flaring to ~+-0.34 m (the placer scales depth by ~1.5). No flat top, no vertical flat faces, no straight edges: a
union of overlapping, tilted, warped boulders (tall ones along the spine, smaller ones leaning on the crest, wide
ones at the foot), terraced into one set of dipping strata across the whole piece, voxel-remeshed into one skin.

Helpers return plain mesh objects (with the 'rest' attribute stored) for the caller to join and finish()."""
import math, random
import bpy, bmesh
import dj_common as dj
from mathutils import Vector, Matrix, Quaternion, noise as mnoise
from mathutils.bvhtree import BVHTree

L_HALF = 1.12      # rounded ends reach this far along X
HEIGHT = 3.12
FOOT_Y = 0.34


def _chunk(name, centre, size, rot, seed, warp=0.2):
    """One boulder: a warped icosphere, base at centre.z - size.z/2 ... (ellipsoid of half-sizes `size`)."""
    o = dj.ico(name, 1.0, 3)
    dj.xform(o, scale=size)
    m = min(size)
    off = Vector((seed * 5.3, seed * 2.9, seed * 1.7))
    for v in o.data.vertices:
        n = mnoise.noise_vector(v.co * (1.3 / max(m, 0.15)) + off)
        n2 = mnoise.noise_vector(v.co * (4.0 / max(m, 0.15)) + off * 2.0)
        # facet it a little: pull towards a slightly squarer superellipse so it reads as stone, not a blob
        v.co.x += (n.x * 0.5 + n2.x * 0.15) * warp * size[0]
        v.co.y += (n.y * 0.35 + n2.y * 0.1) * warp * size[1]
        v.co.z += (n.z * 0.5 + n2.z * 0.15) * warp * size[2] * 0.6
    o.data.update()
    dj.xform(o, rot=rot, loc=centre)
    return o


def _union(name, parts, voxel):
    ob = dj.join(parts, name)
    rm = ob.modifiers.new('Remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    dj.apply_mods(ob)
    return ob


def _cut(ob, zcut=-0.25):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = [f for f in bm.faces if all(v.co.z < zcut for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def ridge_body(name, mat, seed, lobes=4, crest=(2.4, 3.12), strata_step=0.3, strata_tilt=0.14, terrace=0.45,
               voxel=0.04, target_tris=3800):
    """The rock: tall tilted boulders along the spine (varying height, one at full height, one end lower), smaller
    boulders leaning on the crest, wide boulders at the visible foot, rounded lower ends past +-1.0; terraced into
    dipping strata (one bedding plane set for the whole piece), unioned by a voxel remesh, decimated to target_tris."""
    R = random.Random(seed)
    P = []
    xs = [-0.78 + 1.56 * i / (lobes - 1) for i in range(lobes)]
    hs = [R.uniform(*crest) for _ in xs]
    hs[R.randrange(1, lobes - 1)] = crest[1]
    hs[R.choice([0, lobes - 1])] *= R.uniform(0.72, 0.85)
    for i, (x, h) in enumerate(zip(xs, hs)):
        x += R.uniform(-0.05, 0.05)
        sx = R.uniform(0.36, 0.46)
        sy = R.uniform(0.2, 0.24)
        sz = h * 0.56
        rot = (R.uniform(-6, 6), R.uniform(-12, 12), R.uniform(-10, 10))
        P.append(_chunk(f'sp{i}', (x, (0.07 if i % 2 else -0.07) + R.uniform(-0.03, 0.03), h - sz), (sx, sy, sz), rot, seed + i))
    # smaller boulders leaning on / poking out of the crest
    for k in range(R.randint(3, 4)):
        i = R.randrange(lobes)
        x = xs[i] + R.uniform(-0.25, 0.25)
        s = (R.uniform(0.2, 0.3), R.uniform(0.15, 0.19), R.uniform(0.25, 0.4))
        P.append(_chunk(f'cr{k}', (x, R.uniform(-0.05, 0.05), hs[i] * R.uniform(0.78, 0.88)), s,
                        (R.uniform(-15, 15), R.uniform(-35, 35), R.uniform(-30, 30)), seed + 20 + k, warp=0.16))
    # wide foot boulders where the sunk piece meets the ground
    for k in range(R.randint(4, 5)):
        x = -0.9 + 1.8 * (k + 0.5) / 5 + R.uniform(-0.12, 0.12)
        side = 1 if k % 2 else -1
        s = (R.uniform(0.32, 0.45), R.uniform(0.26, 0.32), R.uniform(0.45, 0.6))
        P.append(_chunk(f'ft{k}', (x, side * R.uniform(0.04, 0.08), R.uniform(0.45, 0.75)), s,
                        (R.uniform(-10, 10), R.uniform(-15, 15), R.uniform(-25, 25)), seed + 40 + k))
    # rounded, lower ends that overlap the neighbours
    for sgn in (-1, 1):
        s = (0.3, R.uniform(0.2, 0.24), R.uniform(0.7, 0.95))
        P.append(_chunk(f'end{sgn}', (sgn * 0.84, R.uniform(-0.04, 0.04), s[2] * R.uniform(0.6, 0.9)), s,
                        (R.uniform(-6, 6), sgn * R.uniform(8, 20), R.uniform(-10, 10)), seed + 60 + sgn))
    ob = _union(name, P, voxel)
    # one set of dipping strata across the whole outcrop (beds line up through every boulder): terraced in Z and
    # stepped as ledges across the face (a Y scale that depends only on X/Z, so the thin rock can't be pierced),
    # with a crack groove at each bedding plane and a few vertical joints; then a second remesh irons out folds
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    joints = [R.uniform(-0.8, 0.8) for _ in range(R.randint(2, 3))]
    dj.warp(ob, 0.05, 1.2, seed=seed + 5, axes=(1, 0, 1))
    for v in ob.data.vertices:
        c = v.co
        bed = c.z + strata_tilt * c.x + 0.07 * mnoise.noise(Vector((c.x * 1.2, 0.0, c.z * 0.3)) + off)
        if 0.25 < c.z < HEIGHT * 0.97:
            fr = bed / strata_step
            d = fr - math.floor(fr)                      # 0 at a bed's foot .. 1 at its top
            amp = 0.6 + 0.4 * mnoise.noise(Vector((c.x * 1.7, 2.1, math.floor(fr) * 1.3)) + off)
            c.z += (round(fr) - fr) * strata_step * terrace
            groove = math.exp(-(d * d) / 0.005) + math.exp(-((d - 1.0) ** 2) / 0.005)
            f = 1.0 + (d ** 1.6 - 0.35) * 0.34 * amp - 0.22 * groove * amp
            for j, xj in enumerate(joints):
                f -= 0.14 * math.exp(-((c.x - xj - 0.08 * math.sin(c.z * 3.0 + j)) ** 2) / 0.0015)
            c.y *= max(0.6, f)
    ob.data.update()
    rm = ob.modifiers.new('Remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel * 1.1
    dj.apply_mods(ob)
    # scale to the slot: x span to +-L_HALF, the top at HEIGHT
    vs = ob.data.vertices
    xs_ = [v.co.x for v in vs]
    cx = (max(xs_) + min(xs_)) * 0.5
    kx = L_HALF / ((max(xs_) - min(xs_)) * 0.5)
    kz = HEIGHT / max(v.co.z for v in vs)
    for v in vs:
        v.co.x = (v.co.x - cx) * kx
        v.co.z *= kz
    ob.data.update()
    _cut(ob)
    ym = max(abs(v.co.y) for v in ob.data.vertices if v.co.z > 0.3)
    if ym > FOOT_Y:                                   # keep the visible foot inside the slot depth
        for v in ob.data.vertices:
            v.co.y *= FOOT_Y / ym
        ob.data.update()
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if n > target_tris:
        dj.decimate(ob, target_tris / n)
    print(f'ridge body {name}: {sum(len(p.vertices) - 2 for p in ob.data.polygons)} tris (from {n})')
    dj.set_mat(ob, mat)
    dj.store_rest(ob)
    return ob


def bvh_of(ob):
    me = ob.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def surf(bvh, x, phi, zc=1.4):
    """Surface point/normal of the ridge at X=x, angle phi around a horizontal axis at height zc (phi=0 straight
    up, -90 front (-Y), +90 back)."""
    d = Vector((0.0, math.sin(math.radians(phi)), math.cos(math.radians(phi))))
    o = Vector((x, 0.0, zc)) + d * 4.0
    hit = bvh.ray_cast(o, -d)
    if hit[0] is None:
        return None, None
    return hit[0], hit[1]


def crest_points(bvh, xs, y=0.0):
    """Highest surface point at each x (ray straight down)."""
    out = []
    for x in xs:
        hit = bvh.ray_cast(Vector((x, y, 6.0)), Vector((0, 0, -1)))
        if hit[0] is not None:
            out.append((hit[0], hit[1]))
    return out


def side_hit(bvh, x, z, side=-1):
    """Surface point on the front (side=-1) or back (+1) face at (x, z)."""
    hit = bvh.ray_cast(Vector((x, side * 3.0, z)), Vector((0, -side, 0)))
    return (hit[0], hit[1]) if hit[0] is not None else (None, None)


def drape_root(name, bvh, x, mat, seed, phi0=-35, phi1=-115, back=25, rad=0.05, n=11, zc=1.4, lift=0.6, wig=0.2, drift=0.0):
    """A root/vine draped over the rock at X~x: from slightly behind the crest over the top and down the front face,
    hugging the surface (ray-cast), thinning as it goes."""
    R = random.Random(seed)
    pts, radii = [], []
    for k in range(n):
        t = k / (n - 1)
        phi = back + (phi1 - back) * t
        xx = max(-0.95, min(0.95, x + drift * t + wig * math.sin(t * 4.0 + seed) + R.uniform(-0.03, 0.03)))
        p, nr = surf(bvh, xx, phi, zc)
        if p is None:
            continue
        r = rad * (1.0 - 0.6 * t) * R.uniform(0.85, 1.15)
        pts.append(p + nr * r * lift)
        radii.append(r)
    if len(pts) < 3:
        return None
    o = dj.tube(name, pts, rad, 6, mat, radii=radii)
    dj.store_rest(o)
    return o


def rubble(prefix, mat, seed, n=10, x_half=1.05, ymin=0.22, ymax=0.42, rmin=0.07, rmax=0.2, sides=(-1, 1)):
    """Tumbled stones half-buried along the foot on both sides."""
    R = random.Random(seed)
    out = []
    for i in range(n):
        s = R.uniform(rmin, rmax)
        side = sides[i % len(sides)]
        x = R.uniform(-x_half, x_half)
        y = side * R.uniform(ymin, ymax)
        o = dj.ico(f'{prefix}{i}', s, 1, loc=(0, 0, 0), scale=(R.uniform(1.0, 1.5), R.uniform(0.8, 1.1), R.uniform(0.55, 0.8)), mat=mat)
        dj.warp(o, s * 0.25, 2.5 / s, seed=seed + i)
        dj.store_rest(o)
        dj.xform(o, rot=(R.uniform(-15, 15), R.uniform(-15, 15), R.uniform(0, 360)), loc=(x, y, s * 0.15))
        out.append(o)
    return out


def talus(prefix, mat, bvh, seed, n=12, zlo=0.45, zhi=1.4, rmin=0.08, rmax=0.15, sides=(-1, 1)):
    """Tumbled stones seated against the faces at the heights where the sunk piece meets the ground (the placer sinks
    it 0.6-1.2 m), half sunk into the rock so there's always a rubbly foot showing. Returns (objects, hits)."""
    R = random.Random(seed)
    out, hits = [], []
    for i in range(n):
        side = sides[i % len(sides)]
        x = R.uniform(-0.9, 0.9)
        z = R.uniform(zlo, zhi)
        p, nr = side_hit(bvh, x, z, side)
        if p is None:
            continue
        s = R.uniform(rmin, rmax)
        o = dj.ico(f'{prefix}{i}', s, 1, scale=(R.uniform(1.0, 1.5), R.uniform(0.8, 1.1), R.uniform(0.55, 0.8)), mat=mat)
        dj.warp(o, s * 0.25, 2.5 / s, seed=seed + i)
        dj.store_rest(o)
        dj.xform(o, rot=(R.uniform(-15, 15), R.uniform(-15, 15), R.uniform(0, 360)), loc=p - nr * s * 0.15)
        out.append(o)
        hits.append((p + nr * s * 0.6, nr))
    return out, hits


def leaf_spray(prefix, mat, pts_normals, seed, per=3, size=(0.06, 0.1), jitter=0.07):
    """Small ivy leaves around points, each facing roughly along the surface normal (pid varies the tint)."""
    R = random.Random(seed)
    out = []
    for p, nrm0 in pts_normals:
        for _ in range(per):
            o = p + Vector((R.uniform(-jitter, jitter), R.uniform(-jitter, jitter), R.uniform(-jitter, jitter))) + nrm0 * 0.03
            nrm = (nrm0 + Vector((R.uniform(-0.5, 0.5), R.uniform(-0.5, 0.5), R.uniform(0.0, 0.6)))).normalized()
            sz = R.uniform(*size)
            tang = nrm.cross(Vector((0, 0, 1)))
            if tang.length < 1e-3:
                tang = Vector((1, 0, 0))
            tang = Matrix.Rotation(R.uniform(-0.8, 0.8), 3, nrm) @ tang.normalized()
            tip = -nrm.cross(tang).normalized()
            bm = bmesh.new()
            c0 = bm.verts.new(o + tip * sz * 0.9)
            c1 = bm.verts.new(o + tang * sz * 0.5)
            c2 = bm.verts.new(o - tip * sz * 0.35)
            c3 = bm.verts.new(o - tang * sz * 0.5)
            cc = bm.verts.new(o + nrm * sz * 0.18)
            for a_, b_ in ((c0, c1), (c1, c2), (c2, c3), (c3, c0)):
                bm.faces.new((a_, b_, cc))
            bm.faces.new((c3, c2, c1, c0))
            lf = dj.mesh_obj(f'{prefix}leaf', bm, mat)
            dj.pid(lf, R.random())
            dj.store_rest(lf)
            out.append(lf)
    return out


def moss_on(prefix, mat, hits, seed, r=(0.12, 0.26), h=(0.04, 0.08)):
    """Moss cushions seated on surface hits, tilted to the surface normal."""
    R = random.Random(seed)
    out = []
    for i, (p, nr) in enumerate(hits):
        if p is None:
            continue
        c = dj.cushion(f'{prefix}{i}', R.uniform(*r), R.uniform(*h), (0, 0, 0), mat, seed=seed + i)
        dj.store_rest(c)
        q = Vector((0, 0, 1)).rotation_difference(nr)
        c.data.transform(Matrix.Translation(p - nr * 0.015) @ q.to_matrix().to_4x4())
        c.data.update()
        out.append(c)
    return out

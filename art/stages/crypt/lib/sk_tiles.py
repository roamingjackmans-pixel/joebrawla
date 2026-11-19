"""Seamless procedural tile materials (sk.TileM: noise on a 4D torus) for stage ground and big surfaces.
Each returns a TileM ready for sk.bake_tile(m, name, size). Coordinates: P = rest position on an L x L plane."""
import math
import sk
from sk import TileM


def _h(m, a, b, c=None):
    s = m.add(a, b)
    return m.add(s, c) if c is not None else s


def grass(name, L=3.0, base='#4c7a2c', light='#86a83e', dark='#2c4f1e', dry='#a3a05a', speck='#efe9c2',
          speck2='#e9c93c', specks=0.55, seed=0.0):
    """Stylised lawn: broad light/dark patches, clover-like clumps, sparse tiny flower specks."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 3.1, seed * 1.7, 0))
    n1 = m.noise(P, 0.9, 3.0, 0.55)
    n2 = m.noise(P, 3.2, 4.0, 0.6)
    n3 = m.noise(P, 11.0, 3.0, 0.55)
    d, cc = m.voronoi(P, 9.0)
    clump = m.inv(m.mr(d, 0.0, 0.42))
    c = m.mix(m.mr(n1, 0.38, 0.62), dark, base)
    c = m.mix(m.mul(m.mr(n2, 0.5, 0.78), 0.85), c, light)
    c = m.mix(m.mul(clump, m.mr(m.sep(cc)[0], 0.4, 0.9)), c, dark)
    c = m.mix(m.mul(m.mr(n1, 0.6, 0.78), 0.55), c, dry)
    c = m.mix(m.mul(m.mr(n3, 0.55, 0.75), 0.35), c, light)
    ds, cs = m.voronoi(P, 34.0)
    r, g, _ = m.sep(cs)
    sp = m.mul(m.inv(m.mr(ds, 0.06, 0.13)), m.mr(r, 1.0 - 0.12 * specks, 1.0 - 0.1 * specks))
    sp2 = m.mul(m.inv(m.mr(ds, 0.05, 0.11)), m.mr(g, 1.0 - 0.06 * specks, 1.0 - 0.05 * specks))
    c = m.mix(sp, c, speck)
    c = m.mix(sp2, c, speck2)
    h = _h(m, m.mul(n2, 0.5), m.mul(clump, 0.35), m.mul(n3, 0.25))
    m.set(color=c, rough=m.lin(n2, 0, 1, 0.82, 0.95), height=h, bump=0.6, bump_dist=0.02)
    return m


def dirt(name, L=2.5, base='#7a5a3a', dark='#4a3423', light='#a2805a', pebble='#9a9284', pebble2='#6f675c',
         grassy='#5a6a2e', grass_amt=0.0, wet=0.0, seed=0.0, pebbles=0.6, cracks=0.5):
    """Packed earth path: mottled browns, embedded pebbles, fine cracks, optional grass tufts / damp patches."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.3, seed * 4.1, 0))
    n1 = m.noise(P, 1.2, 4.0, 0.55)
    n2 = m.noise(P, 5.0, 4.0, 0.6)
    n3 = m.noise(P, 16.0, 3.0, 0.6)
    c = m.mix(m.mr(n1, 0.35, 0.65), dark, base)
    c = m.mix(m.mul(m.mr(n2, 0.52, 0.8), 0.8), c, light)
    c = m.mix(m.mul(m.mr(n3, 0.6, 0.8), 0.3), c, dark)
    # cracks (voronoi edges)
    de = m.N.new('ShaderNodeTexVoronoi')
    v, w = m._torus(P)
    de.voronoi_dimensions = '4D'
    de.feature = 'DISTANCE_TO_EDGE'
    m.inp(de.inputs['Vector'], v)
    m.inp(de.inputs['W'], w)
    m.inp(de.inputs['Scale'], 2.6)
    crack = m.mul(m.inv(m.mr(de.outputs['Distance'], 0.0, 0.035)), cracks)
    crack = m.mul(crack, m.mr(n2, 0.35, 0.6))
    c = m.mix(m.mul(crack, 0.7), c, dark)
    # pebbles
    dp, cp = m.voronoi(P, 7.0)
    pr = m.sep(cp)[0]
    peb = m.mul(m.inv(m.mr(dp, 0.16, 0.26)), m.mr(pr, 1.0 - 0.45 * pebbles, 1.0 - 0.4 * pebbles))
    dq, cq = m.voronoi(P, 19.0)
    peb2 = m.mul(m.inv(m.mr(dq, 0.12, 0.22)), m.mr(m.sep(cq)[1], 0.7, 0.75))
    pc = m.mix(m.mr(m.sep(cp)[1], 0.2, 0.8), pebble2, pebble)
    c = m.mix(peb2, c, pebble2)
    c = m.mix(peb, c, pc)
    h = _h(m, m.mul(n2, 0.25), m.mul(peb, 0.7), m.mul(peb2, 0.35))
    h = m.sub(h, m.mul(crack, 0.4))
    rough = m.lin(n2, 0, 1, 0.8, 0.95)
    if grass_amt > 0:
        gm = m.mul(m.mr(n1, 0.72 - 0.2 * grass_amt, 0.82 - 0.2 * grass_amt), m.inv(peb))
        c = m.mix(gm, c, grassy)
        h = m.add(h, m.mul(gm, 0.2))
    if wet > 0:
        wm = m.mul(m.mr(n1, 0.25, 0.4), wet)
        c = m.mix(m.mul(wm, 0.5), c, dark)
        rough = m.lerp(wm, rough, 0.35)
    m.set(color=c, rough=rough, height=h, bump=0.7, bump_dist=0.02)
    return m


def flagstone(name, L=4.0, base='#9c9688', light='#bdb6a4', dark='#5f5a50', moss='#5f7a34', grout='#3e3a32',
              moss_amt=0.5, seed=0.0, cells=3.2, warm='#a99474'):
    """Irregular flagstones (voronoi cells), mossy grout, worn tops."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    de = m.N.new('ShaderNodeTexVoronoi')
    v, w = m._torus(P)
    de.voronoi_dimensions = '4D'
    de.feature = 'DISTANCE_TO_EDGE'
    m.inp(de.inputs['Vector'], v)
    m.inp(de.inputs['W'], w)
    m.inp(de.inputs['Scale'], cells)
    m.inp(de.inputs['Randomness'], 0.85)
    edge = de.outputs['Distance']
    d1, c1 = m.voronoi(P, cells, rand=0.85)
    n1 = m.noise(P, 1.5, 3.0, 0.55)
    n2 = m.noise(P, 7.0, 4.0, 0.6)
    n3 = m.noise(P, 22.0, 3.0, 0.6)
    gr = m.inv(m.mr(edge, 0.012, 0.045))
    stone_tone = m.sep(c1)[0]
    c = m.mix(m.mr(stone_tone, 0.0, 1.0), dark, base)
    c = m.mix(m.mul(m.mr(m.sep(c1)[1], 0.4, 1.0), 0.6), c, light)
    c = m.mix(m.mul(m.mr(m.sep(c1)[2], 0.6, 1.0), 0.5), c, warm)
    c = m.mix(m.mul(m.mr(n2, 0.45, 0.75), 0.4), c, light)
    c = m.mix(m.mul(m.mr(n3, 0.55, 0.75), 0.35), c, dark)
    mo = m.mul(m.mr(m.add(m.mul(gr, 0.6), m.mul(n1, 0.7)), 0.75 - 0.25 * moss_amt, 0.95 - 0.25 * moss_amt), moss_amt * 1.2)
    c = m.mix(gr, c, grout)
    c = m.mix(m.clamp01(mo), c, moss)
    bevel = m.mr(edge, 0.0, 0.12)
    h = _h(m, m.mul(bevel, 0.6), m.mul(n2, 0.15), m.mul(n3, 0.08))
    m.set(color=c, rough=m.lerp(gr, m.lin(n2, 0, 1, 0.72, 0.9), 0.95), height=h, bump=0.8, bump_dist=0.03)
    return m


def cobble(name, L=2.0, base='#7d7a74', light='#a39e94', dark='#4c4a46', grout='#2e2c28', wet=0.0, moss='#4f6a34',
           moss_amt=0.2, seed=0.0, cells=7.0):
    """Rounded cobbles (voronoi F1 domes) with dark gaps; wet darkens and smooths."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    d1, c1 = m.voronoi(P, cells, rand=0.9)
    de = m.N.new('ShaderNodeTexVoronoi')
    v, w = m._torus(P)
    de.voronoi_dimensions = '4D'
    de.feature = 'DISTANCE_TO_EDGE'
    m.inp(de.inputs['Vector'], v)
    m.inp(de.inputs['W'], w)
    m.inp(de.inputs['Scale'], cells)
    m.inp(de.inputs['Randomness'], 0.9)
    edge = de.outputs['Distance']
    n2 = m.noise(P, 9.0, 4.0, 0.6)
    n1 = m.noise(P, 1.3, 3.0, 0.5)
    dome = m.mr(edge, 0.0, 0.16)
    gap = m.inv(m.mr(edge, 0.01, 0.05))
    c = m.mix(m.mr(m.sep(c1)[0], 0, 1), dark, base)
    c = m.mix(m.mul(m.mr(m.sep(c1)[1], 0.5, 1), 0.7), c, light)
    c = m.mix(m.mul(m.mr(n2, 0.5, 0.8), 0.3), c, dark)
    mo = m.mul(m.mul(gap, m.mr(n1, 0.55, 0.7)), moss_amt * 2)
    c = m.mix(gap, c, grout)
    c = m.mix(m.clamp01(mo), c, moss)
    rough = m.lin(n2, 0, 1, 0.65, 0.85)
    if wet > 0:
        rough = m.lerp(m.mul(m.add(gap, 0.6), wet), rough, 0.18)
    h = m.add(m.mul(dome, 0.8), m.mul(n2, 0.1))
    m.set(color=c, rough=rough, height=h, bump=0.9, bump_dist=0.03)
    return m


def planks(name, L=2.0, base='#7a5534', dark='#3e2a1a', light='#a77d52', grey='#8b8274', weather=0.3, n=8, seed=0.0):
    """Boards along X (n boards per tile), grain streaks, dark seams, weathered grey."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    x, y, z = m.sep(P)
    k = n / L
    row = m.math('FLOOR', m.mul(y, k))
    fr = m.math('FRACT', m.mul(y, k))
    seam = m.add(m.inv(m.mr(fr, 0.0, 0.05)), m.mr(fr, 0.95, 1.0))
    rr = m.math('FRACT', m.mul(m.math('SINE', m.mul(row, 12.9898)), 43758.5))
    stretched = m.comb(x, m.add(m.mul(y, 6.0), m.mul(rr, 13.0)), 0)
    g = m.noise(stretched, 3.0, 6.0, 0.6)
    n1 = m.noise(P, 1.5, 3.0, 0.5)
    c = m.mix(m.mr(g, 0.35, 0.7), dark, base)
    c = m.mix(m.mul(m.mr(g, 0.6, 0.8), 0.6), c, light)
    c = m.mix(m.mul(rr, 0.35), c, dark)
    c = m.mix(m.mul(m.mr(n1, 0.4, 0.7), weather), c, grey)
    c = m.mix(m.clamp01(seam), c, dark)
    h = m.sub(m.mul(g, 0.2), m.mul(m.clamp01(seam), 0.6))
    m.set(color=c, rough=m.lin(g, 0, 1, 0.7, 0.9), height=h, bump=0.6, bump_dist=0.02)
    return m


def leaf_litter(name, L=3.0, base='#6a4a2a', cols=('#c8641e', '#e09a2a', '#a8381c', '#d8b040', '#7a3a1a'),
                ground='#4a3824', density=0.8, seed=0.0):
    """Autumn leaf litter: layered voronoi 'leaves' in oranges / reds / golds over dark soil."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    n1 = m.noise(P, 1.1, 3.0, 0.55)
    c = m.mix(m.mr(n1, 0.3, 0.7), ground, base)
    h = m.mul(n1, 0.1)
    for i, (sc, th) in enumerate(((11.0, 0.32), (17.0, 0.3), (25.0, 0.28), (8.0, 0.36))):
        Pi = m.vm('ADD', P, (i * 1.7, i * 2.3, 0))
        di, ci = m.voronoi(Pi, sc, rand=1.0)
        r, g, b = m.sep(ci)
        leaf = m.mul(m.inv(m.mr(di, th * 0.7, th)), m.mr(r, 1.0 - density * 0.8, 1.0 - density * 0.75))
        lc = m.mix(m.mr(g, 0.0, 0.5), cols[i % len(cols)], cols[(i + 1) % len(cols)])
        lc = m.mix(m.mr(b, 0.6, 1.0), lc, cols[(i + 2) % len(cols)])
        vein = m.mul(m.inv(m.mr(di, 0.0, 0.05)), 0.4)
        lc = m.mix(vein, lc, '#5a2a10')
        c = m.mix(leaf, c, lc)
        h = m.add(h, m.mul(leaf, 0.25 + 0.05 * i))
    m.set(color=c, rough=0.88, height=h, bump=0.6, bump_dist=0.015)
    return m


def water(name, L=4.0, deep='#1c3038', shallow='#3a5a5e', foam='#a8b8b0', seed=0.0):
    """Rippled water surface: dark, glossy, normal-mapped rings (rain) and slow swell."""
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    n1 = m.noise(P, 1.0, 3.0, 0.5)
    n2 = m.noise(P, 4.0, 3.0, 0.5)
    d, cc = m.voronoi(P, 6.0)
    ring = m.mul(m.math('SINE', m.mul(d, 40.0)), m.inv(m.mr(d, 0.1, 0.5)))
    d2, _ = m.voronoi(m.vm('ADD', P, (0.37, 0.71, 0)), 9.0)
    ring2 = m.mul(m.math('SINE', m.mul(d2, 55.0)), m.inv(m.mr(d2, 0.08, 0.4)))
    c = m.mix(m.mr(n1, 0.3, 0.7), deep, shallow)
    h = _h(m, m.mul(n2, 0.4), m.mul(ring, 0.12), m.mul(ring2, 0.1))
    m.set(color=c, rough=0.08, height=h, bump=0.35, bump_dist=0.02)
    return m


def moss(name, L=2.0, a='#3d6a2a', b='#86a548', dark='#24401a', seed=0.0):
    m = TileM(name, L)
    P = m.vm('ADD', m.rest, (seed * 2.9, seed * 1.3, 0))
    n1 = m.noise(P, 2.0, 4.0, 0.6)
    n2 = m.noise(P, 12.0, 4.0, 0.6)
    d, _ = m.voronoi(P, 24.0)
    c = m.mix(m.mr(n1, 0.3, 0.7), a, b)
    c = m.mix(m.mul(m.mr(d, 0.3, 0.6), 0.4), c, dark)
    h = m.add(m.mul(n2, 0.5), m.mul(m.inv(m.mr(d, 0.0, 0.5)), 0.4))
    m.set(color=c, rough=0.95, height=h, bump=0.6, bump_dist=0.02)
    return m

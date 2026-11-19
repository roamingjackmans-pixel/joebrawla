"""Procedural (bake-only) materials for the zone 2 kit, The Fungal Hollows (sinkhole cave open to the sky).
Palette from the original zone (floor #2a2236, wallTop #5a3f7a, accent #5fd3c0, hazard #3a5a20, #8b5a3c, #c58cff):
violet-grey cave stone, blue-green cave moss, ivory stalks, violet / ochre / rust caps, teal and violet bioluminescence.
Every function returns a dj_common.M; glowing ones set an `emit` channel (bake with finish(..., emission=True))."""
import math
from dj_common import M, col
import dj_common as dj
import dj_mats as mats

STONE = '#5d5866'
STONE_LIGHT = '#8a8496'
STONE_DARK = '#28232f'
STONE_WARM = '#8a7a72'
MOSS_A = '#2f5a45'
MOSS_B = '#6f9a5c'
TEAL = '#5fd3c0'
VIOLET_GLOW = '#c58cff'
LIME = '#c8f06a'


def _P(m, seed=0.0, scale=1.0):
    P = m.vm('ADD', m.rest, (seed * 5.31, seed * 2.17, seed * 3.73))
    if scale != 1.0:
        P = m.vm('SCALE', P, scale=scale)
    return P


def _glow_dots(m, P, density=0.5, scale=14.0, colour=TEAL, strength=2.5):
    """Bioluminescent lichen specks, gathered in shaded crevices and under overhangs. Returns (mask, emit colour)."""
    d, _ = m.voronoi(P, scale)
    dots = m.mr(d, 0.16, 0.07)
    clump = m.mr(m.noise(m.vm('ADD', P, (7.3, 1.1, 4.4)), 1.6, 3), 0.62 - density * 0.25, 0.7 - density * 0.25)
    nz = m.sep(m.normal)[2]
    shade = m.add(m.mr(nz, 0.2, -0.6), m.mul(m.cavity_mask(0.25, 0.05, 0.55), 0.8))
    mask = m.mul(m.mul(dots, clump), m.clamp01(m.add(shade, 0.35)))
    c = col(colour)
    emit = m.mix(mask, (0, 0, 0, 1), c)
    return mask, emit


def cave_stone(name, seed=0, moss=0.45, glow=0.5, base=STONE, light=STONE_LIGHT, dark=STONE_DARK, warm=STONE_WARM,
               strata=0.6, scale=1.0, rough=0.88, bump=0.5, glow_col=TEAL):
    """Violet-grey limestone of the sinkhole walls: banded strata, damp dark streaks, blue-green moss on the tops
    and in the cracks, and teal glowing lichen specks in the shade."""
    m = M(name, glow=False)
    P = _P(m, seed, scale)
    nz = m.sep(m.normal)[2]
    pz = m.sep(m.rest)[2]
    big = m.noise(P, 0.9, 3, 0.55)
    mid = m.noise(P, 3.2, 4, 0.55)
    fine = m.noise(P, 13, 3, 0.6)
    c = m.mix(m.mr(big, 0.32, 0.7), base, light)
    c = m.mix(m.mul(m.mr(mid, 0.5, 0.75), 0.35), c, warm)
    # strata bands (horizontal, wobbly)
    band = m.wave(m.vm('ADD', P, m.vm('SCALE', m.noisec(P, 0.8, 2), scale=0.6)), 1.7, 3.0, 2.0, 'BANDS', 'Z')
    c = m.mix(m.mul(m.mr(band, 0.55, 0.9), 0.35 * strata), c, dark)
    # damp streaks running down
    stk = m.noise(m.vm('MULTIPLY', P, (5.0, 5.0, 0.35)), 1.0, 3, 0.5)
    c = m.mix(m.mul(m.mr(stk, 0.55, 0.72), 0.5), c, '#1f1a26')
    cav = m.cavity_mask(0.25, 0.05, 0.55)
    c = m.mix(m.mul(cav, 0.65), c, dark)
    ed = m.mul(m.edge_mask(0.03, 0.15, 0.5), m.mr(fine, 0.3, 0.6))
    c = m.mix(m.mul(ed, 0.4), c, '#b9b2bd')
    height = m.add(m.mul(fine, 0.35), m.mul(mid, 0.45))
    height = m.sub(height, m.mul(m.mr(band, 0.6, 0.95), 0.5 * strata))
    # moss on the tops and in the cracks, blue-green
    mn = m.noise(P, 2.0, 4, 0.6)
    up = m.mr(nz, 0.35, 0.9)
    score = m.add(m.add(m.mul(up, 0.9), m.mul(cav, 0.5)), m.mul(m.sub(mn, 0.5), 1.6))
    t = 1.05 - moss * 0.7
    mm = m.mr(score, t, t + 0.12)
    mcol = m.mix(m.mr(m.noise(P, 7, 3), 0.35, 0.7), MOSS_A, MOSS_B)
    mcol = m.mix(m.mul(m.mr(m.noise(P, 24, 2), 0.55, 0.75), 0.4), mcol, '#8fb36a')
    c = m.mix(mm, c, mcol)
    height = m.add(height, m.mul(mm, m.add(0.4, m.mul(m.noise(P, 30, 2), 0.6))))
    r = m.lerp(mm, rough, 0.96)
    emit = None
    if glow > 0:
        gm, emit = _glow_dots(m, P, glow, 16.0 / max(scale, 0.3), glow_col)
        c = m.mix(gm, c, glow_col)
        height = m.add(height, m.mul(gm, 0.3))
    m.set(color=c, rough=r, metal=0.0, height=height, emit=emit, bump=bump, bump_dist=0.012)
    return m


def cap(name, top='#7a4a8a', top2='#a46bb4', rim='#3a2440', gill='#e9dcc8', spots=None, spot_col='#efe6d2',
        spot_glow=0.0, gill_glow=0.0, glow_col=TEAL, seed=0, rough=0.55, sheen=0.25, under_axis=-0.15):
    """Mushroom cap: top colour graded to a darker rim, optional raised warts/spots (glowing if spot_glow),
    underside gills (glowing if gill_glow) chosen by normal.z < under_axis."""
    m = M(name, glow=False)
    P = _P(m, seed)
    nz = m.sep(m.normal)[2]
    n = m.noise(P, 2.5, 3)
    c = m.mix(m.mr(n, 0.3, 0.75), top, top2)
    # radial streaks
    x, y, z = m.sep(m.rest)
    ang = m.math('ARCTAN2', y, x)
    streak = m.noise(m.comb(m.mul(ang, 6.0), m.mul(z, 2.0), seed), 1.0, 3, 0.6)
    c = m.mix(m.mul(m.mr(streak, 0.5, 0.75), 0.35), c, rim)
    edge = m.mr(nz, 0.75, 0.15)
    c = m.mix(m.mul(edge, 0.55), c, rim)
    height = m.mul(streak, 0.3)
    emit = (0, 0, 0, 1)
    gc = col(glow_col)
    if spots:
        d, _ = m.voronoi(P, spots)
        sp = m.mul(m.mr(d, 0.24, 0.12), m.mr(nz, 0.0, 0.4))
        c = m.mix(sp, c, spot_col)
        height = m.add(height, m.mul(sp, 1.2))
        if spot_glow > 0:
            emit = m.mix(sp, emit, (gc[0] * min(spot_glow, 1), gc[1] * min(spot_glow, 1), gc[2] * min(spot_glow, 1), 1))
    under = m.mr(nz, under_axis, under_axis - 0.3)
    gl = m.math('SINE', m.mul(ang, 70.0))
    gills = m.mix(m.mr(gl, -0.2, 0.9), m.mix(0.5, gill, '#4a3a3a'), gill)
    c = m.mix(under, c, gills)
    height = m.lerp(under, height, m.mul(gl, 0.5))
    if gill_glow > 0:
        ge = m.mul(under, m.mr(gl, 0.0, 0.9, 0.35, 1.0))
        emit = m.mix(ge, emit, (gc[0] * min(gill_glow, 1), gc[1] * min(gill_glow, 1), gc[2] * min(gill_glow, 1), 1))
    cav = m.cavity_mask(0.12, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.5), c, '#1b1220')
    r = m.lerp(under, rough, 0.8)
    m.set(color=c, rough=r, metal=0.0, height=height, emit=emit if (spots and spot_glow > 0) or gill_glow > 0 else None,
          bump=0.35, bump_dist=0.008)
    return m


def stalk(name, base='#ddd2bd', dark='#9c8f7c', seed=0, moss=0.0, ring=None):
    """Fibrous ivory stalk: vertical fibres, a darker foot, optional moss at the base."""
    m = M(name)
    P = _P(m, seed)
    x, y, z = m.sep(m.rest)
    fib = m.noise(m.vm('MULTIPLY', P, (14.0, 14.0, 0.6)), 1.0, 3, 0.6)
    c = m.mix(m.mr(fib, 0.35, 0.75), dark, base)
    foot = m.mr(z, 0.6, 0.0)
    c = m.mix(m.mul(foot, 0.55), c, '#5b4b3c')
    cav = m.cavity_mask(0.1, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.5), c, '#3a2e26')
    height = m.mul(fib, 0.6)
    r = m.S(0.75)
    if moss > 0:
        mm = m.mul(m.mr(z, 0.5 * moss, 0.0), m.mr(m.noise(P, 4, 3), 0.4, 0.6))
        c = m.mix(mm, c, m.mix(m.noise(P, 9), MOSS_A, MOSS_B))
        r = m.lerp(mm, 0.75, 0.95)
    m.set(color=c, rough=r, metal=0.0, height=height, bump=0.4, bump_dist=0.006)
    return m


def shelf(name, top='#b8642c', band='#e2a35a', under='#e8dcc0', seed=0, glow=0.0, glow_col=VIOLET_GLOW):
    """Bracket / shelf fungus: concentric growth bands on top, pale pored underside (optionally glowing edge)."""
    m = M(name)
    P = _P(m, seed)
    nz = m.sep(m.normal)[2]
    x, y, z = m.sep(m.rest)
    d = m.vm('LENGTH', m.comb(x, y, 0))
    w = m.math('SINE', m.mul(m.add(d, m.mul(m.noise(P, 4.0), 0.05)), 70.0))
    c = m.mix(m.mr(w, -0.4, 0.8), top, band)
    c = m.mix(m.mul(m.mr(m.noise(P, 3.0), 0.5, 0.8), 0.4), c, '#5a2f1a')
    und = m.mr(nz, -0.1, -0.5)
    c = m.mix(und, c, under)
    emit = None
    if glow > 0:
        gc = col(glow_col)
        ed = m.mul(m.edge_mask(0.02, 0.1, 0.5), m.add(und, 0.4))
        emit = m.mix(m.clamp01(ed), (0, 0, 0, 1), (gc[0] * min(glow, 1), gc[1] * min(glow, 1), gc[2] * min(glow, 1), 1))
    m.set(color=c, rough=m.lerp(und, 0.6, 0.85), metal=0.0, height=m.mul(w, 0.25), emit=emit, bump=0.3, bump_dist=0.004)
    return m


def roots(name, base='#5a3a2c', dark='#2e1d16', light='#8a6650', seed=0, moss=0.35):
    m = mats.wood(name, base=base, dark=dark, light=light, grey='#6f6466', weather=0.25, moss=0.0, seed=seed, rough=0.86)
    # blue-green moss on the upper sides of the roots
    P = _P(m, seed)
    nz = m.sep(m.normal)[2]
    mn = m.noise(P, 3.0, 4)
    sc = m.add(m.mul(m.mr(nz, 0.3, 0.95), 0.8), m.mul(m.sub(mn, 0.5), 1.6))
    tt = 1.05 - moss * 0.6
    mm = m.mr(sc, tt, tt + 0.12)
    c = m.mix(mm, m.ch['color'], m.mix(m.noise(P, 8), MOSS_A, MOSS_B))
    m.set(color=c, rough=m.lerp(mm, 0.86, 0.96))
    return m


def glowcap(name, colour=TEAL, strength=4.0, base=None, seed=0):
    """Small bioluminescent cap: bright translucent-looking cap, glow strongest at the rim and underside."""
    m = M(name, glow=False)
    P = _P(m, seed)
    nz = m.sep(m.normal)[2]
    gc = col(colour)
    bc = col(base) if base else (gc[0] * 0.6 + 0.08, gc[1] * 0.6 + 0.08, gc[2] * 0.6 + 0.08, 1)
    n = m.noise(P, 18.0, 2)
    c = m.mix(m.mul(m.mr(n, 0.4, 0.7), 0.4), bc, '#f2fff8')
    rimm = m.add(m.mr(nz, 0.6, -0.2), 0.35)
    emit = m.mix(m.clamp01(rimm), (gc[0] * 0.35, gc[1] * 0.35, gc[2] * 0.35, 1), gc)
    m.set(color=c, rough=0.35, metal=0.0, height=n, emit=emit, bump=0.2, bump_dist=0.003)
    return m


def cave_moss(name, seed=0):
    return mats.moss_mat(name, seed=seed, a=MOSS_A, b=MOSS_B)


def puffball(name, base='#e6dccb', dark='#a59580', seed=0, spores=True):
    """Puffball skin: pale, warty, a dusty spore-brown crown where it has split."""
    m = M(name)
    P = _P(m, seed)
    nz = m.sep(m.normal)[2]
    d, _ = m.voronoi(P, 28.0)
    wart = m.mr(d, 0.3, 0.1)
    c = m.mix(m.mr(m.noise(P, 4, 3), 0.3, 0.7), dark, base)
    c = m.mix(m.mul(wart, 0.35), c, '#f7f1e6')
    if spores:
        crown = m.mul(m.mr(nz, 0.75, 0.98), m.mr(m.noise(P, 3), 0.45, 0.6))
        c = m.mix(crown, c, '#6a5038')
    cav = m.cavity_mask(0.1, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.5), c, '#4a3c30')
    m.set(color=c, rough=0.9, metal=0.0, height=wart, bump=0.4, bump_dist=0.004)
    return m


def sludge(name, seed=0):
    """Slow terrain (D126/D160 'spore sludge'): sticky brown-mauve goo, glossy rim, glowing violet spores stuck in it
    (the original's caverns Slow colours: deep #3a1a1e, mid #6a3a30, hi #e0a070, rim #d89060, glow #c060ff)."""
    m = M(name, glow=False)
    P = _P(m, seed)
    x, y, z = m.sep(m.rest)
    n = m.noise(P, 3.0, 4)
    c = m.mix(m.mr(n, 0.3, 0.7), '#3a1a1e', '#6a3a30')
    rimz = m.mr(z, 0.0, 0.05)
    c = m.mix(m.mul(m.mr(m.noise(P, 9.0, 3), 0.55, 0.75), 0.6), c, '#e0a070')
    d, _ = m.voronoi(P, 9.0)
    sp = m.mul(m.mr(d, 0.12, 0.05), m.mr(m.noise(m.vm('ADD', P, (3, 1, 2)), 2.0), 0.45, 0.55))
    c = m.mix(sp, c, '#f0c0ff')
    gc = col('#c060ff')
    emit = m.mix(sp, (0, 0, 0, 1), gc)
    m.set(color=c, rough=m.lerp(rimz, 0.12, 0.3), metal=0.0, height=m.add(n, m.mul(sp, 0.6)), emit=emit, bump=0.5,
          bump_dist=0.01)
    return m


def spike(name, body='#b8d860', tip='#f4ffc0', ground='#2a4a06'):
    """Hurt terrain (D167 spike field, caverns lime): dark ground, pale-lime spikes with bright glowing tips."""
    m = M(name, glow=False)
    P = _P(m, 0)
    x, y, z = m.sep(m.rest)
    t = m.mr(z, 0.02, 0.32)
    c = m.mix(t, ground, body)
    c = m.mix(m.mr(z, 0.22, 0.34), c, tip)
    gc = col('#d8ff60')
    tipm = m.mr(z, 0.2, 0.34)
    gnd = m.mr(z, 0.03, 0.0)
    emit = m.mix(tipm, (0, 0, 0, 1), gc)
    m.set(color=c, rough=0.45, metal=0.0, height=m.noise(P, 20.0), emit=emit, bump=0.3, bump_dist=0.004)
    return m

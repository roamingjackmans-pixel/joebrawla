"""Procedural (bake-only) materials for Dungeon Joe props. Palette: moss #4f7a38, sage #9db9a7,
bone #e8e1c8, sun #f6e2b3, grey-green stone #6c8471. Every function returns a dj_common.M."""
import math
from dj_common import M, col
import dj_common as dj

MOSS = '#4f7a38'
MOSS_LIGHT = '#86a548'
MOSS_DARK = '#2f5124'
SAGE = '#9db9a7'
BONE = '#e8e1c8'
STONE = '#6c8471'


def _P(m, seed=0.0, scale=1.0):
    P = m.vm('ADD', m.rest, (seed * 5.31, seed * 2.17, seed * 3.73))
    if scale != 1.0:
        P = m.vm('SCALE', P, scale=scale)
    return P


def mixv(m, fac, a, b):
    n = m.N.new('ShaderNodeMix')
    n.data_type = 'VECTOR'
    n.clamp_factor = True
    ins = {s.identifier: s for s in n.inputs}
    m.inp(ins['Factor_Float'], fac)
    m.inp(ins['A_Vector'], a)
    m.inp(ins['B_Vector'], b)
    return [s for s in n.outputs if s.identifier == 'Result_Vector'][0]


def planar_coord(m, P):
    """Pick a 2D projection by dominant normal axis -> vector (u, v, 0)."""
    x, y, z = m.sep(P)
    nx, ny, nz = m.sep(m.normal)
    ax, ay, az = m.math('ABSOLUTE', nx), m.math('ABSOLUTE', ny), m.math('ABSOLUTE', nz)
    cxz = m.comb(x, z, 0)
    cyz = m.comb(y, z, 0)
    cxy = m.comb(x, y, 0)
    s1 = m.math('GREATER_THAN', ax, ay)
    v1 = mixv(m, s1, cxz, cyz)
    s2 = m.math('GREATER_THAN', az, 0.72)
    return mixv(m, s2, v1, cxy)


def carve_mask(m, img, x0, z0, w, h, facing=-1):
    """Image groove mask projected on the XZ plane; only on faces whose normal.y has sign `facing`."""
    x, y, z = m.sep(m.rest)
    u = m.mul(m.sub(x, x0), 1.0 / w)
    v = m.mul(m.sub(z, z0), 1.0 / h)
    c = m.image(img, m.comb(u, v, 0), 'CLIP')
    ny = m.sep(m.normal)[1]
    face = m.mr(m.mul(ny, float(facing)), 0.45, 0.75)
    return m.mul(m.bw(c), face)


def stone(name, base=STONE, light='#83977f', dark='#33402f', warm='#a8a283', moss=0.5, lichen=0.5, edge=0.55,
          streak=0.5, seed=0, carve=None, rough=0.86, scale=1.0, bump=0.45, blocks=None, fade=None,
          edge_dist=0.028, moss_bottom=0.4, cav_dist=0.25, patches='#4c5d49', moss_scale=2.0):
    """Weathered grey-green stone. carve=(img,x0,z0,w,h) adds lettering grooves; blocks=(w,h,mortar)
    adds ashlar coursing; fade=(z_top,z_bottom) darkens to black with depth (crypt)."""
    m = M(name)
    P = _P(m, seed, scale)
    nz = m.sep(m.normal)[2]
    big = m.noise(P, 1.1, 3, 0.55)
    mid = m.noise(P, 3.5, 4, 0.55)
    fine = m.noise(P, 12, 3, 0.6)
    stk = m.noise(m.vm('MULTIPLY', P, (5.0, 5.0, 0.45)), 1.0, 3, 0.5)
    c = m.mix(m.mr(big, 0.35, 0.68), base, light)
    c = m.mix(m.mul(m.mr(mid, 0.5, 0.74), 0.3), c, warm)
    c = m.mix(m.mul(m.mr(stk, 0.52, 0.7), 0.4 * streak), c, dark)
    big2 = m.noise(m.vm('ADD', P, (17.0, 3.0, 9.0)), 2.2, 3, 0.6)
    c = m.mix(m.mul(m.mr(big2, 0.56, 0.7), 0.6), c, patches)
    height = m.add(m.mul(fine, 0.35), m.mul(mid, 0.45))
    mortar = None
    if blocks:
        bw, bh, ms = blocks
        bn = m.N.new('ShaderNodeTexBrick')
        m.inp(bn.inputs['Vector'], planar_coord(m, P))
        bn.inputs['Color1'].default_value = (0, 0, 0, 1)
        bn.inputs['Color2'].default_value = (1, 1, 1, 1)
        bn.inputs['Mortar'].default_value = (1, 1, 1, 1)
        bn.inputs['Scale'].default_value = 1.0
        bn.inputs['Mortar Size'].default_value = ms
        bn.inputs['Mortar Smooth'].default_value = 0.6
        bn.inputs['Bias'].default_value = 0.0
        bn.inputs['Brick Width'].default_value = bw
        bn.inputs['Row Height'].default_value = bh
        bn.offset = 0.5
        bn.squash = 1.0
        mf = bn.outputs['Fac']
        tint = m.bw(bn.outputs['Color'])
        c = m.mix(m.mul(tint, 0.35), c, light)
        c = m.mix(m.mul(m.inv(tint), 0.25), c, dark)
        rim = m.mul(m.mr(mf, 0.02, 0.35), m.mr(mf, 0.85, 0.5))
        c = m.mix(m.mul(rim, 0.45), c, BONE)
        mortar = m.mr(mf, 0.6, 0.95)
        c = m.mix(m.mul(mortar, 0.75), c, '#3a4236')
        height = m.sub(height, m.mul(m.mr(mf, 0.2, 0.9), 1.4))
    pz = m.sep(m.rest)[2]
    low = m.mr(pz, 0.35, 0.0)
    c = m.mix(m.mul(low, 0.45), c, '#4b5a3c')
    cav = m.cavity_mask(cav_dist, 0.05, 0.55)
    c = m.mix(m.mul(cav, 0.6), c, dark)
    ed = m.mul(m.edge_mask(edge_dist, 0.15, 0.5), m.mr(fine, 0.3, 0.6))
    c = m.mix(m.mul(ed, edge), c, BONE)
    cm = None
    if carve:
        img, x0, z0, w, h = carve[:5]
        cm = carve_mask(m, img, x0, z0, w, h)
        cm = m.mul(cm, m.mr(m.noise(P, 9.0, 3), 0.25, 0.55, 0.45, 1.0))
        c = m.mix(m.mul(cm, 0.8), c, '#2c3629')
        height = m.sub(height, m.mul(cm, 1.6))
    # lichen spots
    ln = m.noise(P, 16.0, 3, 0.6, dist=0.8)
    cl = m.noise(m.vm('ADD', P, (3.1, 7.7, 1.3)), 1.8, 2)
    spot = m.mul(m.mr(ln, 0.64, 0.69), m.mr(cl, 0.72 - lichen * 0.2, 0.76 - lichen * 0.2))
    lc = m.mix(m.mr(m.noise(P, 5.0), 0.45, 0.6), '#b4bf8c', '#c4a964')
    c = m.mix(m.mul(spot, 0.75), c, lc)
    height = m.add(height, m.mul(spot, 0.3))
    # moss: up-facing, crevices, base, lettering, mortar
    mn = m.noise(P, moss_scale, 4, 0.6)
    up = m.mr(nz, 0.3, 0.9)
    score = m.add(m.mul(up, 0.9), m.mul(cav, 0.55))
    score = m.add(score, m.mul(low, moss_bottom))
    if cm is not None:
        score = m.add(score, m.mul(cm, 0.9))
    if mortar is not None:
        score = m.add(score, m.mul(mortar, 0.45))
    score = m.add(score, m.mul(m.sub(mn, 0.5), 1.6))
    t = 1.05 - moss * 0.7
    mm = m.mr(score, t, t + 0.12)
    mcol = m.mix(m.mr(m.noise(P, 7, 3), 0.35, 0.7), '#3a6328', '#6f9640')
    mcol = m.mix(m.mul(m.mr(m.noise(P, 24, 2), 0.55, 0.75), 0.4), mcol, '#93b052')
    mcol = m.mix(m.mul(cav, 0.6), mcol, MOSS_DARK)
    medge = m.mul(m.mr(score, t - 0.06, t + 0.01), m.mr(score, t + 0.1, t + 0.02))
    c = m.mix(m.mul(medge, 0.35), c, '#2f3f27')
    c = m.mix(mm, c, mcol)
    height = m.add(height, m.mul(mm, m.add(0.4, m.mul(m.noise(P, 30, 2), 0.6))))
    r = m.lerp(mm, rough, 0.95)
    if fade:
        z0, z1 = fade
        f = m.mr(pz, z0, z1, 0.0, 1.0)
        c = m.mix(f, c, '#050605')
    m.set(color=c, rough=r, metal=0.0, height=height, bump=bump, bump_dist=0.012)
    return m


def wood(name, base='#8a5a35', dark='#4c301d', light='#b98c5a', grey='#8e8679', weather=0.4, moss=0.0, seed=0,
         rough=0.82, edge=0.45, scale=1.0, cav_dist=0.15, end_grain=False, planks=0.0):
    m = M(name)
    P = _P(m, seed, scale)
    g = m.attr('grain', 'Vector')
    t = m.vm('DOT_PRODUCT', P, g)
    perp = m.vm('SUBTRACT', P, m.vm('SCALE', g, scale=t))
    q = m.vm('ADD', perp, m.vm('SCALE', g, scale=m.mul(t, 0.07)))
    gr = m.noise(q, 8.0, 5, 0.62, dist=0.6)
    gr2 = m.noise(q, 26.0, 2, 0.5)
    c = m.mix(m.mr(gr, 0.3, 0.72), dark, base)
    c = m.mix(m.mul(m.mr(gr2, 0.56, 0.72), 0.45), c, dark)
    pv = m.attr('pid')
    c = m.mix(m.mul(pv, 0.35), c, light)
    wn = m.noise(P, 1.4, 3)
    c = m.mix(m.mul(m.mr(wn, 0.38, 0.7), weather), c, grey)
    ed = m.edge_mask(0.015, 0.08, 0.45)
    c = m.mix(m.mul(ed, edge), c, light)
    cav = m.cavity_mask(cav_dist, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.6), c, '#2a1b10')
    height = m.add(m.mul(gr, 0.5), m.mul(gr2, 0.35))
    if planks > 0:
        nx_, ny_, nz_ = m.sep(m.normal)
        px_, py_, pz_ = m.sep(m.rest)
        pc = m.lerp(m.math('GREATER_THAN', m.math('ABSOLUTE', nz_), 0.7), pz_, px_)
        fr = m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(pc, 1.0 / planks)), 0.5))
        seam = m.lin(fr, 0.46, 0.49)
        c = m.mix(m.mul(seam, 0.8), c, '#24170d')
        height = m.sub(height, m.mul(seam, 1.2))
    if end_grain:
        endm = m.mr(m.math('ABSOLUTE', m.vm('DOT_PRODUCT', m.normal, g)), 0.6, 0.8)
        rel = m.vm('SUBTRACT', m.rest, m.attr('axisc', 'Vector'))
        rd = m.vm('LENGTH', m.vm('SUBTRACT', rel, m.vm('SCALE', g, scale=m.vm('DOT_PRODUCT', rel, g))))
        rings = m.math('SINE', m.mul(m.add(rd, m.mul(m.noise(P, 6.0), 0.01)), 2 * math.pi / 0.014))
        ec = m.mix(m.mr(rings, -0.4, 0.8), '#a8783f', '#e0b77a')
        ec = m.mix(m.mr(rd, 0.02, 0.0), ec, '#7a4f28')
        c = m.mix(endm, c, ec)
        height = m.lerp(endm, height, m.mul(rings, 0.3))
    r = m.S(rough)
    if moss > 0:
        nz = m.sep(m.normal)[2]
        mn = m.noise(P, 2.5, 4)
        sc = m.add(m.mul(m.mr(nz, 0.5, 0.95), 0.8), m.mul(m.sub(mn, 0.5), 1.6))
        tt = 1.05 - moss * 0.6
        mm = m.mr(sc, tt, tt + 0.12)
        c = m.mix(mm, c, m.mix(m.noise(P, 8), '#3d6a2c', MOSS_LIGHT))
        r = m.lerp(mm, rough, 0.95)
    m.set(color=c, rough=r, metal=0.0, height=height, bump=0.5, bump_dist=0.006)
    return m


def canvas(name, base='#e6d3a6', stain='#cdb585', light='#f3e6c6', dirt='#7f6648', stripe='#bf5332',
           stripe_edge='#e3a144', band=(0.56, 0.86), seam=0.55, seed=0, stripes=True, bleach_z=(1.2, 2.3),
           scallop=0.32, inner_glow=0.0, glow_col='#f6c987', glow_center=(0.0, 0.0, 0.9), pin_col='#f0dfb6',
           emblem=None):
    m = M(name)
    P = _P(m, seed)
    x, y, z = m.sep(m.rest)
    nx, ny, nz = m.sep(m.normal)
    sel = m.math('GREATER_THAN', m.math('ABSOLUTE', ny), 0.6)
    along = m.lerp(sel, y, x)
    big = m.noise(P, 0.9, 3)
    mid = m.noise(P, 3.0, 4)
    c = m.mix(m.mul(m.mr(big, 0.4, 0.7), 0.6), base, stain)
    c = m.mix(m.mul(m.mr(mid, 0.55, 0.76), 0.35), c, stain)
    c = m.mix(m.mul(m.mr(z, bleach_z[0], bleach_z[1]), 0.45), c, light)
    if stripes:
        lo, hi = band
        sc_ = m.math('ABSOLUTE', m.math('SINE', m.mul(along, math.pi / scallop)))
        lower = m.add(lo, m.mul(m.inv(sc_), 0.085))
        bm_ = m.mul(m.lin(m.sub(z, lower), -0.005, 0.005), m.lin(z, hi + 0.005, hi - 0.005))
        trim = m.mul(m.lin(m.sub(z, lower), 0.012, 0.004), bm_)
        pin = m.lin(m.math('ABSOLUTE', m.sub(z, hi - 0.055)), 0.014, 0.008)
        sc = m.mix(pin, stripe, pin_col)
        sc = m.mix(trim, sc, stripe_edge)
        sc = m.mix(m.mul(m.mr(big, 0.4, 0.75), 0.3), sc, '#963b22')
        c = m.mix(m.mul(bm_, 0.96), c, sc)
    fr = m.math('FRACT', m.mul(along, 1.0 / seam))
    d = m.math('ABSOLUTE', m.sub(fr, 0.5))
    seamm = m.lin(d, 0.455, 0.485)
    c = m.mix(m.mul(seamm, 0.55), c, '#9c815a')
    stitch = m.mul(m.lin(d, 0.455, 0.462), m.math('GREATER_THAN', m.math('SINE', m.mul(z, 160.0)), 0.2))
    c = m.mix(m.mul(stitch, 0.55), c, '#86714f')
    if emblem:
        img, y0, z0, w, h, ecol, ecol2 = emblem
        ev = m.bw(m.image(img, m.comb(m.mul(m.sub(y, y0), 1.0 / w), m.mul(m.sub(z, z0), 1.0 / h), 0), 'CLIP'))
        sidem = m.mr(m.math('ABSOLUTE', nx), 0.3, 0.5)
        wear = m.mr(m.noise(P, 7.0, 3), 0.3, 0.6, 0.55, 1.0)
        e1 = m.mul(m.mul(m.lin(ev, 0.7, 0.85), sidem), wear)
        e2 = m.mul(m.mul(m.mul(m.lin(ev, 0.3, 0.42), m.inv(m.lin(ev, 0.7, 0.85))), sidem), wear)
        c = m.mix(m.mul(e2, 0.9), c, ecol2)
        c = m.mix(m.mul(e1, 0.92), c, ecol)
    dzn = m.add(z, m.mul(m.sub(m.noise(P, 4.0, 3), 0.5), 0.3))
    c = m.mix(m.mul(m.mr(dzn, 0.34, 0.04), 0.85), c, dirt)
    cav = m.cavity_mask(0.35, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.5), c, '#8a7552')
    folds = m.noise(m.vm('MULTIPLY', P, (1.0, 6.0, 1.0)), 1.6, 3)
    height = m.add(m.mul(mid, 0.35), m.mul(folds, 0.5))
    height = m.sub(height, m.mul(seamm, 0.4))
    emit = None
    if inner_glow > 0:
        rv = m.vm('SUBTRACT', m.rest, glow_center)
        dp = m.vm('DOT_PRODUCT', m.normal, rv)
        inner = m.mr(dp, 0.0, -0.12)
        emit = m.mix(m.mul(inner, inner_glow), (0, 0, 0, 1), m.mix(0.35, glow_col, c))
    m.set(color=c, rough=0.93, metal=0.0, height=height, emit=emit, bump=0.35, bump_dist=0.01)
    return m


def patch(name, base='#9db9a7', dark='#5b4a36', seed=0):
    m = M(name)
    P = _P(m, seed)
    u, v, _ = m.sep(m.uvmap('aux'))
    b = m.mn(m.mn(u, m.inv(u)), m.mn(v, m.inv(v)))
    band = m.mul(m.lin(b, 0.035, 0.05), m.lin(b, 0.09, 0.075))
    dash = m.math('GREATER_THAN', m.math('SINE', m.mul(m.add(u, v), 70.0)), 0.0)
    st = m.mul(band, dash)
    n = m.noise(P, 3.0, 3)
    c = m.mix(m.mul(m.mr(n, 0.4, 0.7), 0.4), base, '#e9dfc1')
    c = m.mix(m.mul(m.lin(b, 0.02, 0.0), 0.5), c, '#6f6250')
    c = m.mix(st, c, dark)
    cav = m.cavity_mask(0.3)
    c = m.mix(m.mul(cav, 0.5), c, '#5c5444')
    m.set(color=c, rough=0.93, height=m.sub(m.mul(n, 0.3), m.mul(st, 0.6)), bump=0.4, bump_dist=0.006)
    return m


def iron(name, base='#4a5054', light='#80878a', rust='#7b4627', rust2='#a7642f', rustamt=0.4, seed=0,
         edge_dist=0.006, metal=0.7, moss=0.0):
    m = M(name)
    P = _P(m, seed)
    n1 = m.noise(P, 3.0, 4)
    n2 = m.noise(P, 9.0, 3)
    c = m.mix(m.mul(m.mr(n1, 0.4, 0.6), 0.5), base, '#3a3f43')
    cav = m.cavity_mask(0.12, 0.05, 0.6)
    score = m.add(n1, m.mul(cav, 0.5))
    score = m.add(score, m.mul(m.sub(n2, 0.5), 0.5))
    t = 1.0 - rustamt * 0.5
    rm = m.mr(score, t, t + 0.12)
    rc = m.mix(m.mr(n2, 0.35, 0.65), rust, rust2)
    c = m.mix(rm, c, rc)
    ed = m.mul(m.edge_mask(edge_dist, 0.1, 0.5), m.inv(rm))
    c = m.mix(m.mul(ed, 0.6), c, light)
    c = m.mix(m.mul(cav, 0.5), c, '#1c1f21')
    mt = m.lerp(rm, metal, 0.05)
    r = m.lerp(rm, 0.48, 0.88)
    if moss > 0:
        nz = m.sep(m.normal)[2]
        sc = m.add(m.mul(m.mr(nz, 0.5, 0.95), 0.8), m.mul(m.sub(m.noise(P, 4.0, 3), 0.5), 1.6))
        tt = 1.05 - moss * 0.6
        mm = m.mr(sc, tt, tt + 0.12)
        c = m.mix(mm, c, MOSS)
        mt = m.lerp(mm, mt, 0.0)
        r = m.lerp(mm, r, 0.95)
    m.set(color=c, rough=r, metal=mt, height=m.add(m.mul(n2, 0.6), m.mul(rm, 0.5)), bump=0.4, bump_dist=0.004)
    return m


def brass(name, base='#c08b3c', dark='#6a4721', light='#f0cf86', verd=0.15, seed=0):
    m = M(name)
    P = _P(m, seed)
    n = m.noise(P, 4.0, 3)
    c = m.mix(m.mul(m.mr(n, 0.4, 0.7), 0.4), base, '#a8752f')
    cav = m.cavity_mask(0.08, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.7), c, dark)
    ed = m.edge_mask(0.006, 0.1, 0.5)
    c = m.mix(m.mul(ed, 0.6), c, light)
    vm_ = m.mr(m.add(m.mul(cav, 0.8), m.mul(m.sub(m.noise(P, 9.0), 0.5), 1.0)), 1.0 - verd, 1.1 - verd)
    c = m.mix(vm_, c, '#5fa58a')
    m.set(color=c, rough=m.lerp(vm_, 0.32, 0.8), metal=m.lerp(vm_, 0.9, 0.0), height=n, bump=0.2,
          bump_dist=0.003)
    return m


def cloth(name, base='#9c3b2e', alt='#e9dcc0', alt2='#2f3f5a', pattern=None, period=0.16, seed=0, rough=0.95):
    m = M(name)
    P = _P(m, seed)
    x, y, z = m.sep(m.rest)
    c = m.S(base)
    if pattern == 'check':
        sx = m.lin(m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(x, 1 / period)), 0.5)), 0.32, 0.36)
        sy = m.lin(m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(y, 1 / period)), 0.5)), 0.32, 0.36)
        c = m.mix(m.mul(sx, 0.55), c, alt2)
        c = m.mix(m.mul(sy, 0.55), c, alt2)
        thin = m.lin(m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(m.add(x, y), 1 / period)), 0.5)), 0.47, 0.49)
        c = m.mix(m.mul(m.mul(sx, sy), 0.7), c, alt)
    elif pattern == 'rug':
        fr = m.math('FRACT', m.mul(y, 1 / period))
        b1 = m.mul(m.lin(fr, 0.08, 0.1), m.lin(fr, 0.22, 0.2))
        b2 = m.mul(m.lin(fr, 0.3, 0.32), m.lin(fr, 0.36, 0.34))
        b3 = m.mul(m.lin(fr, 0.6, 0.62), m.lin(fr, 0.78, 0.76))
        c = m.mix(b1, c, alt)
        c = m.mix(b2, c, alt2)
        c = m.mix(b3, c, '#d6a645')
        zig = m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(x, 6.0)), 0.5))
        dia = m.mul(m.lin(m.math('ABSOLUTE', m.sub(m.add(fr, m.mul(zig, 0.12)), 0.69)), 0.03, 0.015), 1.0)
        c = m.mix(dia, c, alt)
    elif pattern == 'stripe':
        s = m.lin(m.math('ABSOLUTE', m.sub(m.math('FRACT', m.mul(x, 1 / period)), 0.5)), 0.38, 0.41)
        c = m.mix(s, c, alt)
    n = m.noise(P, 6.0, 4)
    c = m.mix(m.mul(m.mr(n, 0.4, 0.75), 0.3), c, '#ffffff')
    cav = m.cavity_mask(0.12, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.6), c, '#2a1d17')
    fz = m.noise(P, 40.0, 2)
    m.set(color=c, rough=rough, height=m.add(m.mul(n, 0.5), m.mul(fz, 0.3)), bump=0.35, bump_dist=0.006)
    return m


def rope(name, base='#c9b287', dark='#7a6645', seed=0):
    m = M(name)
    P = _P(m, seed)
    g = m.attr('grain', 'Vector')
    t = m.vm('DOT_PRODUCT', P, g)
    b = m.math('SINE', m.mul(t, 140.0))
    c = m.mix(m.mr(b, -0.6, 0.8), dark, base)
    n = m.noise(P, 6.0, 3)
    c = m.mix(m.mul(m.mr(n, 0.5, 0.75), 0.3), c, '#7d8f5c')
    m.set(color=c, rough=0.95, height=b, bump=0.4, bump_dist=0.003)
    return m


def moss_mat(name, seed=0, a='#3d6a2a', b=MOSS_LIGHT):
    m = M(name)
    P = _P(m, seed)
    n = m.noise(P, 5.0, 4)
    n2 = m.noise(P, 22.0, 3)
    c = m.mix(m.mr(n, 0.35, 0.7), a, b)
    c = m.mix(m.mul(m.mr(n2, 0.6, 0.8), 0.3), c, '#a7bf5e')
    cav = m.cavity_mask(0.15, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.7), c, '#1f3a18')
    m.set(color=c, rough=0.96, height=m.add(n2, m.mul(n, 0.5)), bump=0.7, bump_dist=0.01)
    return m


def leaves(name, a='#355f27', b='#6f9b3b', seed=0):
    m = M(name)
    P = _P(m, seed)
    pv = m.attr('pid')
    c = m.mix(pv, a, b)
    n = m.noise(P, 8.0, 3)
    c = m.mix(m.mul(m.mr(n, 0.5, 0.8), 0.35), c, '#9cc25a')
    cav = m.cavity_mask(0.1, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.7), c, '#1b3315')
    ed = m.edge_mask(0.006, 0.1, 0.5)
    c = m.mix(m.mul(ed, 0.35), c, '#b5d478')
    m.set(color=c, rough=0.6, height=n, bump=0.2, bump_dist=0.003)
    return m


def soil(name, base='#5f412b', dark='#382519', light='#8a6a4a', seed=0):
    m = M(name)
    P = _P(m, seed)
    d, cc = m.voronoi(P, 14.0)
    n = m.noise(P, 4.0, 4)
    c = m.mix(m.mr(n, 0.35, 0.7), dark, base)
    peb = m.mr(d, 0.22, 0.12)
    pr = m.sep(cc)[0]
    peb = m.mul(peb, m.math('GREATER_THAN', pr, 0.75))
    c = m.mix(m.mul(peb, 0.6), c, '#80766a')
    cav = m.cavity_mask(0.15, 0.05, 0.6)
    c = m.mix(m.mul(cav, 0.6), c, '#22160e')
    nz = m.sep(m.normal)[2]
    c = m.mix(m.mul(m.mr(m.noise(P, 1.5, 3), 0.55, 0.65), 0.3), c, light)
    m.set(color=c, rough=0.97, height=m.add(n, m.mul(peb, 0.8)), bump=0.6, bump_dist=0.01)
    return m


def void(name, c='#060706'):
    m = M(name)
    m.set(color=c, rough=1.0, metal=0.0)
    return m


def plain(name, c, rough=0.8, metal=0.0):
    m = M(name)
    m.set(color=c, rough=rough, metal=metal)
    return m

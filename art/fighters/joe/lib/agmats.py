"""Procedural armour / clothing materials (Cycles node trees baked by agbuild.bake_direct).

Every builder takes `col` (sRGB hex) for a fully coloured surface, or col=None for a NEUTRAL light-grey
version used on the dye and trim slots (the colour then comes from glTF baseColorFactor, so the client can
re-tint: class palettes, rarity). Object coordinates are world metres (parts sit at identity).

Optional mesh attributes read by the materials:
  edge   (POINT float, 1 at a garment's open boundary falling to 0 inside) -> fraying, wear, hem dirt
  prand  (POINT float, per-part random) -> tone variation between parts
"""
import bpy, math, colorsys
from djlib import NB, srgb

NEUTRAL = '#d4d4d4'


def _m(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def shade(hex_, v=1.0, s=1.0, h=0.0):
    """Adjust an sRGB hex in HSV (value / saturation multipliers, hue shift in turns)."""
    hx = hex_.lstrip('#')
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
    H, S, Vv = colorsys.rgb_to_hsv(r, g, b)
    H = (H + h) % 1.0
    S = max(0.0, min(1.0, S * s))
    Vv = max(0.0, min(1.0, Vv * v))
    r, g, b = colorsys.hsv_to_rgb(H, S, Vv)
    return '#%02x%02x%02x' % (int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5))


def pal(col, dv=0.18, ds=0.08):
    """(dark, base, light) linear colours around a hex (or neutral)."""
    c = col or NEUTRAL
    return srgb(shade(c, 1 - dv, 1 + ds)), srgb(c), srgb(shade(c, 1 + dv * 0.8, 1 - ds))


def cavity(nb, dist=0.03, lo=0.5, hi=0.97):
    return nb.mr(nb.ao(dist, 12), hi, lo, 0.0, 1.0)


def upfacing(nb, lo=0.25, hi=0.85):
    z = nb.sep(nb.geo('Normal'))[2]
    return nb.mr(z, lo, hi, 0.0, 1.0)


def edge_attr(nb, lo=0.0, hi=1.0):
    return nb.mr(nb.attr('edge'), lo, hi, 0.0, 1.0)


def _base(nb, co, col, dv=0.18, scale=3.5):
    d, b, l = pal(col, dv)
    n1 = nb.noise(co, scale, 4, 0.55)
    base = nb.ramp(n1, [(0.3, d), (0.5, b), (0.72, l)])
    pr = nb.attr('prand')
    base = nb.mix(nb.mul(nb.sub(pr, 0.5), 0.3), base, d)
    return base, n1


# ----------------------------------------------------------------------------------------------
def fabric(name, col=None, kind='wool', wear=0.5, dirt=0.5, moss=0.0, low_z=0.35, high_z=0.9, glow=None,
           glow_strength=0.0, stripes=None):
    """Woven cloth. kind: wool | linen | burlap | silk | velvet | felt | quilted | canvas.
    dirt darkens toward the ground (below high_z, strongest at low_z); moss adds green stains low down.
    stripes: (hex, period_m, width_frac, axis) woven stripes."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    sc = {'wool': 140.0, 'linen': 190.0, 'burlap': 95.0, 'silk': 260.0, 'velvet': 300.0, 'felt': 60.0,
          'quilted': 160.0, 'canvas': 120.0}[kind]
    base, n1 = _base(nb, co, col, 0.2 if kind in ('burlap', 'wool', 'felt') else 0.14)
    wx = nb.wave(co, sc, 0.0, 0.0, 'BANDS', 'X')
    wz = nb.wave(co, sc, 0.0, 0.0, 'BANDS', 'Z')
    wy = nb.wave(co, sc, 0.0, 0.0, 'BANDS', 'Y')
    weave = nb.mul(nb.mx(wx, wy), wz)
    fuzz = nb.noise(co, 60.0, 6, 0.7)
    c = nb.mix(nb.mul(weave, 0.1 if kind != 'burlap' else 0.22), base, srgb('#1a1612'))
    if stripes:
        shex, per, wfrac, ax = stripes
        sw = nb.wave(co, 1.0 / per, 0.0, 0.0, 'BANDS', ax, 'SAW')
        sm = nb.mr(sw, 1 - wfrac, 1 - wfrac + 0.02, 0.0, 1.0)
        c = nb.mix(sm, c, srgb(shex))
    # slubs and blotches
    c = nb.mix(nb.mr(nb.noise(co, 12.0, 6, 0.6), 0.45, 0.8, 0, 0.22), c, srgb('#fff4e0' if col is None else shade(col, 1.25, 0.8)))
    cav = cavity(nb, 0.035)
    c = nb.mix(nb.mul(cav, 0.55), c, srgb('#141010'))
    up = upfacing(nb, 0.3, 0.95)
    if col is not None:
        c = nb.mix(nb.mul(up, 0.12 * wear), c, srgb('#cbbfa8'))
    # fraying / worn edges
    e = edge_attr(nb, 0.25, 1.0)
    c = nb.mix(nb.mul(e, 0.35 * wear), c, srgb('#e8dcc4' if col is None else shade(col, 1.3, 0.6)))
    # ground grime + moss
    z = nb.sep(co)[2]
    low = nb.mr(z, high_z, low_z, 0.0, 1.0)
    gm = nb.mul(nb.mul(low, nb.mr(nb.noise(co, 8.0, 4, 0.6), 0.3, 0.7, 0.3, 1.0)), dirt)
    c = nb.mix(nb.mul(gm, 0.6), c, srgb('#3a3022'))
    if moss > 0:
        mm = nb.mul(nb.mul(nb.mx(low, nb.mul(cav, 0.6)), nb.mr(nb.noise(co, 7.0, 6, 0.65, 0.4), 0.55, 0.66, 0, 1)), moss)
        c = nb.mix(mm, c, nb.ramp(nb.noise(co, 80.0, 3, 0.6), [(0.4, srgb('#3a5418')), (0.65, srgb('#6c862c'))]))
    rough = {'silk': 0.48, 'velvet': 0.92, 'linen': 0.82}.get(kind, 0.88)
    r = nb.add(rough, nb.mul(nb.sub(fuzz, 0.5), 0.08))
    height = nb.add(nb.mul(weave, 0.35 if kind != 'silk' else 0.08), nb.mul(fuzz, 0.25))
    if kind == 'quilted':
        d1 = nb.wave(nb.mapping(co, rot=(0, 0, 0.785)), 18.0, 0.0, 0.0, 'BANDS', 'X', 'TRI')
        dz = nb.wave(co, 13.0, 0.0, 0.0, 'BANDS', 'Z', 'TRI')
        puff = nb.mn(d1, nb.mx(dz, 0.3))
        seam = nb.mr(puff, 0.0, 0.14, 1.0, 0.0)
        c = nb.mix(nb.mul(seam, 0.45), c, srgb('#2a2018'))
        height = nb.add(height, nb.mul(nb.mr(puff, 0.0, 0.5, 0.0, 1.0), 1.4))
    folds = nb.noise(nb.mapping(co, scale=(9, 9, 2.2)), 4.0, 3, 0.5)
    height = nb.add(height, nb.mul(folds, 1.6))
    nrm = nb.bump(height, 0.35, 0.002)
    emit = None
    if glow:
        gmask = nb.mr(nb.noise(co, 9.0, 4, 0.6), 0.55, 0.7, 0.0, 1.0)
        emit = nb.mix(gmask, srgb('#000000'), srgb(glow))
    nb.finish(c, r, 0.0, nrm, emit=emit, emit_strength=glow_strength)
    return m


def leather(name, col=None, kind='smooth', wear=0.6, dirt=0.4, low_z=0.3, high_z=0.8):
    """Leather: fine grain, creases, lighter scuffed edges, darker cavities. kind: smooth | rough | suede | oiled."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.22, 5.0)
    grain = nb.voronoi(co, 260.0 if kind != 'rough' else 160.0, 'F1', out='Distance')
    crease = nb.noise(nb.mapping(co, scale=(1, 1, 6)), 30.0, 3, 0.6)
    cr = nb.mr(crease, 0.62, 0.7, 0, 1)
    c = nb.mix(nb.mul(cr, 0.3), base, srgb('#1b120b'))
    cav = cavity(nb, 0.03)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#120c08'))
    e = edge_attr(nb, 0.2, 1.0)
    sc = nb.mr(nb.noise(co, 40.0, 4, 0.6), 0.5, 0.75, 0.0, 1.0)
    light = srgb('#e0d2bc') if col is None else srgb(shade(col, 1.45, 0.75))
    c = nb.mix(nb.mul(nb.mx(e, nb.mul(sc, 0.5)), 0.45 * wear), c, light)
    z = nb.sep(co)[2]
    low = nb.mr(z, high_z, low_z, 0.0, 1.0)
    c = nb.mix(nb.mul(nb.mul(low, dirt), 0.5), c, srgb('#2e2418'))
    rough = {'smooth': 0.55, 'oiled': 0.4, 'rough': 0.75, 'suede': 0.92}[kind]
    r = nb.add(rough, nb.mul(nb.sub(sc, 0.5), 0.2))
    height = nb.add(nb.mul(grain, 0.25), nb.mul(cr, -0.5))
    nrm = nb.bump(height, 0.3, 0.0015)
    nb.finish(c, r, 0.0, nrm)
    return m


def mail(name, col=None, ring=170.0, rust=0.3, dirt=0.3, low_z=0.3, high_z=0.8):
    """Riveted mail: ring lattice (lit ring tops, dark gaps), patches of rust, dirt low down."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    p = nb.mapping(co, scale=(1, 1, 1.5))
    rings = nb.voronoi(p, ring, 'F1', out='Distance', rand=0.0)
    rtop = nb.mul(nb.mr(rings, 0.14, 0.28, 0.0, 1.0), nb.mr(rings, 0.5, 0.36, 0.0, 1.0))
    gap = nb.mr(rings, 0.40, 0.55, 0.0, 1.0)
    d, b, l = pal(col or '#8a877f', 0.2)
    n1 = nb.noise(co, 6.0, 4, 0.6)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.75, l)])
    c = nb.mix(nb.mul(gap, 0.85), c, srgb('#100e0c'))
    cav = cavity(nb, 0.03)
    rm = nb.mul(nb.mx(nb.mul(cav, 0.8), nb.mr(nb.noise(co, 7.0, 5, 0.6), 0.6, 0.72, 0, 1)), rust)
    c = nb.mix(rm, c, srgb('#6a3b1c'))
    c = nb.mix(nb.mul(rtop, 0.22), c, srgb('#d8d4cc'))
    z = nb.sep(co)[2]
    low = nb.mr(z, high_z, low_z, 0.0, 1.0)
    c = nb.mix(nb.mul(nb.mul(low, dirt), 0.5), c, srgb('#2a2218'))
    metal = nb.mixf(nb.mx(gap, rm), 0.95, 0.15)
    r = nb.mixf(rm, nb.add(0.38, nb.mul(n1, 0.1)), 0.85)
    nrm = nb.bump(nb.sub(rtop, gap), 0.7, 0.0012)
    nb.finish(c, r, metal, nrm)
    return m


def scales(name, col=None, size=34.0, metal=0.85, rough=0.35, rim_hex=None):
    """Overlapping scale armour (abyssal scale, drowned king): rounded scales in rows, dark seams."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    p = nb.mapping(co, scale=(1.0, 1.0, 1.35))
    v = nb.voronoi(p, size, 'F1', out='Distance', rand=0.15)
    edge = nb.voronoi(p, size, 'DISTANCE_TO_EDGE', out='Distance', rand=0.15)
    dome = nb.mr(v, 0.0, 0.55, 1.0, 0.0)
    seam = nb.mr(edge, 0.0, 0.06, 1.0, 0.0)
    d, b, l = pal(col, 0.25)
    n1 = nb.noise(co, 5.0, 4, 0.6)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.78, l)])
    c = nb.mix(nb.mul(dome, 0.35), c, l)
    c = nb.mix(nb.mul(seam, 0.85), c, srgb('#0a0810'))
    cav = cavity(nb, 0.03)
    c = nb.mix(nb.mul(cav, 0.5), c, srgb('#0a0810'))
    if rim_hex:
        c = nb.mix(nb.mul(nb.mr(edge, 0.06, 0.1, 1.0, 0.0), 0.7), c, srgb(rim_hex))
    mt = nb.mixf(seam, metal, 0.0)
    r = nb.add(rough, nb.mul(nb.sub(n1, 0.5), 0.15))
    nrm = nb.bump(nb.sub(dome, nb.mul(seam, 0.6)), 0.6, 0.002)
    nb.finish(c, r, mt, nrm)
    return m


def plate(name, col=None, kind='steel', rust=0.15, grime=0.6, dents=1.0, moss=0.0, scratches=1.0,
          rough=None, low_z=0.25, high_z=0.7):
    """Worn plate metal. kind: steel | iron | blackened | gilded | bronze | brass | copper | ice | painted.
    col tints the metal (it is the metal's colour, e.g. a greenish steel); None = neutral polished metal."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    defaults = {'steel': '#9a958c', 'iron': '#6a6662', 'blackened': '#3a3836', 'gilded': '#d6a83e',
                'bronze': '#a8743a', 'brass': '#c49a48', 'copper': '#b8683a', 'ice': '#bfe0f2', 'painted': '#8a3030'}
    metalv = {'steel': 1.0, 'iron': 0.9, 'blackened': 0.75, 'gilded': 1.0, 'bronze': 1.0, 'brass': 1.0,
              'copper': 1.0, 'ice': 0.0, 'painted': 0.0}[kind]
    rv = rough if rough is not None else {'steel': 0.34, 'iron': 0.5, 'blackened': 0.45, 'gilded': 0.3, 'bronze': 0.38,
                                          'brass': 0.32, 'copper': 0.36, 'ice': 0.12, 'painted': 0.55}[kind]
    if col == 'default':
        col = defaults[kind]
    d, b, l = pal(col, 0.14, 0.05)
    n1 = nb.noise(co, 2.5, 4, 0.5)
    n2 = nb.noise(co, 45.0, 8, 0.65)
    c = nb.ramp(n1, [(0.3, d), (0.5, b), (0.72, l)])
    ham = nb.voronoi(co, 26.0, 'SMOOTH_F1', out='Distance')
    s1 = nb.noise(nb.mapping(co, rot=(0.3, 0.2, 0.9), scale=(1, 1, 14)), 22.0, 2, 0.5)
    s2 = nb.noise(nb.mapping(co, rot=(1.1, 0.4, -0.5), scale=(14, 1, 1)), 22.0, 2, 0.5)
    scr = nb.mx(nb.mr(s1, 0.675, 0.69, 0, 1), nb.mr(s2, 0.675, 0.69, 0, 1))
    scr = nb.mul(nb.mul(scr, nb.mr(nb.noise(co, 4.0, 2, 0.5), 0.45, 0.6, 0.0, 1.0)), scratches)
    c = nb.mix(nb.mul(scr, 0.35), c, l)
    # big dents (shovel blows): dark-rimmed dimples
    dv = nb.voronoi(co, 7.0, 'F1', out='Distance', rand=1.0)
    dent = nb.mul(nb.mr(dv, 0.22, 0.05, 0.0, 1.0), nb.mr(nb.noise(co, 3.0, 2, 0.5), 0.5, 0.6, 0.0, 1.0))
    dent = nb.mul(dent, dents)
    e = edge_attr(nb, 0.3, 1.0)
    c = nb.mix(nb.mul(e, 0.45), c, l)
    cav = cavity(nb, 0.025)
    gm = nb.mul(cav, grime)
    c = nb.mix(gm, c, srgb('#2c2620'))
    rm = nb.math('MINIMUM', nb.mul(nb.mul(nb.mx(cav, nb.mul(dent, 0.6)), nb.mr(nb.noise(co, 9.0, 5, 0.6), 0.48, 0.64, 0, 1)), rust * 4), 1.0)
    c = nb.mix(rm, c, nb.ramp(n2, [(0.4, srgb('#5e3418')), (0.7, srgb('#9a5a26'))]))
    z = nb.sep(co)[2]
    low = nb.mr(z, high_z, low_z, 0.0, 1.0)
    c = nb.mix(nb.mul(low, 0.35 * grime), c, srgb('#3a3022'))
    met = nb.mixf(nb.mx(nb.mul(gm, 0.7), rm), metalv, 0.0)
    r = nb.add(rv, nb.mul(nb.sub(n2, 0.5), 0.14))
    r = nb.mixf(scr, r, rv * 0.7)
    r = nb.mixf(nb.mx(gm, rm), r, 0.85)
    if moss > 0:
        up = upfacing(nb, 0.3, 0.9)
        mm = nb.mul(nb.mul(nb.mx(up, cav), nb.mr(nb.noise(co, 6.0, 6, 0.65, 0.4), 0.52, 0.63, 0, 1)), moss)
        c = nb.mix(mm, c, nb.ramp(nb.noise(co, 110.0, 4, 0.7), [(0.35, srgb('#2f4a17')), (0.6, srgb('#5c7a28')), (0.8, srgb('#8ea03c'))]))
        met = nb.mixf(mm, met, 0.0)
        r = nb.mixf(mm, r, 0.95)
    height = nb.add(nb.mul(ham, 0.5), nb.mul(scr, -0.25))
    height = nb.add(height, nb.mul(dent, -2.5))
    height = nb.add(height, nb.mul(rm, 0.4))
    nrm = nb.bump(height, 0.25, 0.002)
    if kind == 'ice':
        emit = nb.mix(nb.mr(n1, 0.4, 0.8, 0, 1), srgb('#3a7aa8'), srgb('#9ad0ff'))
        nb.finish(c, r, met, nrm, emit=emit, emit_strength=0.15)
    else:
        nb.finish(c, r, met, nrm)
    return m


def metal_trim(name, col=None, kind='polished', rough=0.3):
    """Rims, buckles, rivets, studs: polished metal (neutral by default -> trim colour via factor)."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = pal(col, 0.15)
    n1 = nb.noise(co, 8.0, 4, 0.55)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.8, l)])
    cav = cavity(nb, 0.012)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#2a2218'))
    r = nb.add(rough, nb.mul(nb.sub(n1, 0.5), 0.15))
    r = nb.mixf(cav, r, 0.7)
    nrm = nb.bump(nb.noise(co, 60.0, 4, 0.6), 0.15, 0.001)
    nb.finish(c, r, nb.mixf(cav, 1.0, 0.4), nrm)
    return m


def fur(name, col=None, length=0.6):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.3, 6.0)
    strands = nb.noise(nb.mapping(co, scale=(40, 40, 6)), 9.0, 6, 0.75)
    c = nb.mix(nb.mr(strands, 0.3, 0.7, 0.4, 0.0), base, srgb('#120d08'))
    tips = nb.mr(strands, 0.55, 0.75, 0.0, 0.5)
    c = nb.mix(tips, c, srgb('#f0e6d6') if col is None else srgb(shade(col, 1.5, 0.6)))
    cav = cavity(nb, 0.04)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#0c0906'))
    nrm = nb.bump(strands, 0.8, 0.004)
    nb.finish(c, 0.95, 0.0, nrm)
    return m


def rope(name, col='#9a8058'):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.25, 9.0)
    tw = nb.wave(nb.mapping(co, rot=(0.6, 0.6, 0.6)), 180.0, 1.5, 2.0, 'BANDS', 'Z', 'SIN')
    c = nb.mix(nb.mul(nb.mr(tw, 0.3, 0.0, 0.0, 1.0), 0.6), base, srgb('#2a2014'))
    nrm = nb.bump(tw, 0.6, 0.002)
    nb.finish(c, 0.9, 0.0, nrm)
    return m


def wood(name, col='#7a5232'):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.25, 3.0)
    g = nb.wave(nb.mapping(co, scale=(1, 1, 0.08)), 40.0, 6.0, 3.0, 'BANDS', 'X', 'SIN')
    c = nb.mix(nb.mul(nb.mr(g, 0.2, 0.7, 0.4, 0.0), 1.0), base, srgb(shade(col, 0.55)))
    nrm = nb.bump(g, 0.3, 0.0015)
    nb.finish(c, 0.7, 0.0, nrm)
    return m


def bone_mat(name, col='#d8c8a2'):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.18, 6.0)
    cav = cavity(nb, 0.02)
    c = nb.mix(nb.mul(cav, 0.7), base, srgb('#4a3622'))
    nrm = nb.bump(nb.noise(co, 50.0, 6, 0.6), 0.3, 0.0015)
    nb.finish(c, 0.6, 0.0, nrm)
    return m


def fungus(name, col=None, spots='#e8e0d0', spot_scale=14.0, glow=None, glow_strength=0.0):
    """Mushroom flesh / cap: soft mottling, pale spots, slight sheen; optional glowing spots."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.22, 4.0)
    sp = nb.voronoi(co, spot_scale, 'F1', out='Distance', rand=1.0)
    spm = nb.mr(sp, 0.2, 0.12, 0.0, 1.0)
    c = nb.mix(spm, base, srgb(spots))
    cav = cavity(nb, 0.03)
    c = nb.mix(nb.mul(cav, 0.5), c, srgb('#140c14'))
    nrm = nb.bump(nb.add(nb.mul(spm, 0.6), nb.mul(nb.noise(co, 30.0, 4, 0.6), 0.3)), 0.4, 0.002)
    emit = None
    if glow:
        emit = nb.mix(spm, srgb('#000000'), srgb(glow))
    nb.finish(c, 0.55, 0.0, nrm, emit=emit, emit_strength=glow_strength)
    return m


def rubber(name, col=None):
    """Oilcloth / waxed waders: smooth with sheen, crinkles."""
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.15, 3.0)
    cr = nb.noise(nb.mapping(co, scale=(4, 4, 1)), 14.0, 5, 0.7)
    c = nb.mix(nb.mul(nb.mr(cr, 0.6, 0.75, 0, 1), 0.3), base, srgb('#101010'))
    cav = cavity(nb, 0.03)
    c = nb.mix(nb.mul(cav, 0.5), c, srgb('#101010'))
    nrm = nb.bump(cr, 0.4, 0.002)
    nb.finish(c, nb.add(0.32, nb.mul(cr, 0.2)), 0.0, nrm)
    return m


def glow(name, col='#ff7a1a', strength=3.0):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    n = nb.noise(co, 20.0, 4, 0.6)
    e = nb.mix(nb.mr(n, 0.3, 0.7, 0, 1), srgb(shade(col, 0.6)), srgb(shade(col, 1.2, 0.8)))
    nb.finish(srgb(shade(col, 0.5)), 0.4, 0.0, None, emit=e, emit_strength=strength)
    return m


def skin_like(name, col='#c89878'):
    m = _m(name)
    nb = NB(m)
    co = nb.coord('Object')
    base, n1 = _base(nb, co, col, 0.12, 8.0)
    nb.finish(base, 0.6, 0.0, None)
    return m

"""Saint Aurelia -- procedural materials (baked into texture sets by fblib.Kit)."""
import math
import bpy
from mathutils import Vector
import fblib as F
from fblib import NB, srgb

V = Vector
ICE = srgb('#a8e4ff')
ICE_HOT = srgb('#d6f4ff')
SUN = srgb('#ffd27a')
SKIN = '#e1e7ef'


def _m(name):
    m = bpy.data.materials.new(name)
    return m, NB(m)


def spots(nb, co, scale, frac=0.25, size=0.35, seed=0.0):
    c = nb.mapping(co, loc=(seed, seed * 1.3, seed * 0.7))
    d = nb.voronoi(c, scale, 'F1', out='Distance')
    rc = nb.voronoi(c, scale, 'F1', out='Color')
    sel = nb.mr(nb.sep(rc)[0], 1.0 - frac - 0.02, 1.0 - frac + 0.02, 0.0, 1.0)
    return nb.mul(nb.mr(d, size, size * 0.6, 0.0, 1.0), sel)


def frost_crystals(nb, co, scale=60.0):
    """crystalline frost: voronoi cells with bright edges and sparkles (0..1)."""
    e = nb.voronoi(co, scale, 'DISTANCE_TO_EDGE', out='Distance')
    edges = nb.mr(e, 0.0, 0.05, 1.0, 0.0)
    sp = spots(nb, co, scale * 3.0, 0.12, 0.25, 3.0)
    return nb.mx(nb.mul(edges, 0.7), sp)


# ================================================================================================ skin
def skin(L, base_img, nrm_img, tips):
    m, nb = _m('au_skin_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    tex = nb.img(base_img, 'UVMap')
    bw = nb.node('ShaderNodeRGBToBW')
    nb.link(tex, bw.inputs[0])
    detail = nb.mr(bw.outputs[0], 0.02, 0.45, 0.35, 1.7, 'LINEAR')
    detail = nb.add(nb.mul(detail, 0.7), 0.3)
    c = nb.mix(1.0, srgb(SKIN), nb.comb(detail, detail, detail), 'MULTIPLY')
    c = nb.mix(nb.mr(nb.noise(co, 7.0, 4, 0.6), 0.4, 0.7, 0.0, 0.30), c, srgb('#c6d2e4'))
    el, er, nose, chin = L['eye_l'], L['eye_r'], L['nose'], L['chin']
    mouth = V((0, nose.y + 0.030, (nose.z + chin.z) * 0.5 + 0.006))
    eye_z = (el.z + er.z) * 0.5
    c = nb.paint(c, nb.ell(co, mouth, (0.023, 0.022, 0.0085), soft=0.45), '#9ea8c8', 0.75)
    for e, sx in ((el, 1), (er, -1)):
        sh = nb.ell(co, (e.x + sx * 0.004, e.y + 0.006, e.z + 0.006), (0.028, 0.03, 0.019), soft=0.8)
        c = nb.paint(c, sh, '#8fa6cf', 0.45)
        ch = nb.ell(co, (sx * 0.046, e.y + 0.014, eye_z - 0.036), (0.026, 0.03, 0.02), soft=0.9)
        c = nb.paint(c, ch, '#e9c9d4', 0.22)
    tipm = None
    for tp in tips:
        mk = nb.ell(co, tp, (0.03, 0.03, 0.03), soft=0.9)
        tipm = mk if tipm is None else nb.mx(tipm, mk)
    c = nb.paint(c, tipm, '#9fb4dc', 0.6)
    toes = nb.mul(nb.mr(s[2], 0.06, 0.0, 0.0, 1.0), nb.mr(s[1], -0.06, -0.12, 0.0, 1.0))
    c = nb.paint(c, toes, '#a8bbe0', 0.5)
    # frost dusting: on the crown of the face, shoulders, hands and feet
    frost = frost_crystals(nb, co, 70.0)
    reg = nb.mr(nb.noise(co, 5.0, 3, 0.55), 0.48, 0.66, 0.0, 1.0)
    face = nb.ell(co, L['head_c'] + V((0, -0.04, 0.0)), (0.10, 0.10, 0.13), soft=0.6)
    reg = nb.mx(nb.mul(reg, 0.8), nb.mul(face, 0.35))
    feet = nb.mr(s[2], 0.16, 0.04, 0.0, 1.0)
    reg = nb.mx(reg, feet)
    fm = nb.mul(frost, reg)
    c = nb.paint(c, fm, '#ffffff', 0.85)
    c = nb.mix(nb.mul(reg, 0.25), c, srgb('#cfe2fb'))
    rough = nb.sub(0.50, nb.mul(fm, 0.25))
    rough = nb.mixf(nb.ell(co, mouth, (0.023, 0.022, 0.0085), soft=0.45), rough, 0.32)
    emit = nb.mix(nb.mul(nb.mul(fm, reg), 0.35), (0, 0, 0, 1), ICE)
    nm = nb.normal_map(nb.img(nrm_img, 'UVMap'), 1.0)
    n = nb.bump(nb.add(nb.mul(frost, 0.5), nb.mul(nb.noise(co, 260.0, 2, 0.5), 0.2)), 0.12, 0.0012, nm)
    nb.finish(c, rough, n, emit)
    return m


def lids(spheres):
    """closed eyelids: skin with a frosty lid shadow, a dark lash seam that glows faintly pale blue."""
    m, nb = _m('au_lids_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    cz = spheres[0][0].z
    R = spheres[0][1]
    seam_z = cz - 0.22 * R
    d = nb.math('ABSOLUTE', nb.sub(s[2], seam_z))
    seam = nb.mr(d, 0.0016, 0.0005, 0.0, 1.0)
    glow = nb.mr(d, 0.0045, 0.0, 0.0, 1.0)
    upper = nb.mr(nb.sub(s[2], seam_z), 0.0, 0.004, 0.0, 1.0)
    c = nb.mix(upper, srgb('#d3dcea'), srgb('#b7c6e2'))
    c = nb.mix(nb.mr(nb.sub(s[2], seam_z), 0.002, 0.012, 0.0, 0.5), c, srgb('#9db1d8'))
    lash = nb.mr(nb.sub(s[2], seam_z), -0.0002, 0.0022, 1.0, 0.0)
    lash = nb.mul(lash, nb.mr(nb.sub(s[2], seam_z), -0.0012, 0.0, 0.0, 1.0))
    c = nb.mix(lash, c, srgb('#3a4a6a'))
    c = nb.mix(nb.mul(seam, 0.6), c, srgb('#eaf6ff'))
    emit = nb.mix(nb.mul(glow, 0.9), (0, 0, 0, 1), ICE_HOT)
    n = nb.bump(nb.mul(lash, -1.0), 0.3, 0.0008)
    nb.finish(c, 0.42, n, emit)
    return m


def brows():
    m, nb = _m('au_brows_proc')
    co = nb.coord('Object')
    c = nb.mix(nb.mr(nb.noise(co, 300.0, 2, 0.5), 0.4, 0.7, 0.0, 1.0), srgb('#dfe9f6'), srgb('#ffffff'))
    nb.finish(c, 0.5, None, nb.mix(0.15, (0, 0, 0, 1), ICE))
    return m


def hair():
    m, nb = _m('au_hair_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    strand = nb.noise(nb.mapping(co, scale=(260, 260, 9)), 1.0, 4, 0.6)
    clump = nb.noise(nb.mapping(co, scale=(40, 40, 3)), 1.0, 3, 0.5)
    c = nb.mix(nb.mr(strand, 0.35, 0.7, 0.0, 1.0), srgb('#b9c8dc'), srgb('#f6f9fd'))
    c = nb.mix(nb.mr(clump, 0.4, 0.6, 0.0, 0.5), c, srgb('#9fb6d4'))
    lower = nb.mr(s[2], 1.75, 1.55, 0.0, 1.0)
    c = nb.mix(nb.mul(lower, 0.5), c, srgb('#bfe6ff'))
    fr = frost_crystals(nb, co, 140.0)
    c = nb.paint(c, fr, '#ffffff', 0.6)
    emit = nb.mix(nb.mul(nb.mul(fr, lower), 0.35), (0, 0, 0, 1), ICE)
    n = nb.bump(nb.add(strand, nb.mul(clump, 0.5)), 0.5, 0.0015)
    nb.finish(c, nb.sub(0.42, nb.mul(fr, 0.2)), n, emit)
    return m


def icicle(glow=0.30):
    m, nb = _m('au_icicle_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    v = nb.noise(nb.mapping(co, scale=(120, 120, 30)), 1.0, 3, 0.5)
    c = nb.mix(nb.mr(v, 0.35, 0.7, 0.0, 1.0), srgb('#9fd6f5'), srgb('#eef9ff'))
    c = nb.mix(nb.mr(pu, 0.6, 1.0, 0.0, 0.6), c, srgb('#ffffff'))
    emit = nb.mix(nb.add(glow, nb.mul(pu, glow)), (0, 0, 0, 1), ICE)
    n = nb.bump(v, 0.4, 0.001)
    nb.finish(c, 0.10, n, emit)
    return m


def halo():
    m, nb = _m('au_halo_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    v = nb.noise(nb.mapping(co, scale=(90, 90, 90)), 1.0, 3, 0.5)
    c = nb.mix(nb.mr(v, 0.35, 0.7, 0.0, 1.0), srgb('#bfe8ff'), srgb('#ffffff'))
    emit = nb.mix(nb.add(0.65, nb.mul(pu, 0.35)), (0, 0, 0, 1), ICE_HOT)
    nb.finish(c, 0.08, nb.bump(v, 0.3, 0.001), emit)
    return m


def croz_shaft():
    m, nb = _m('au_shaft_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    tw = nb.wave(co, 3.0, 2.0, 1.0, 'RINGS', 'Z')
    c = nb.mix(nb.mr(tw, 0.3, 0.8, 0.0, 1.0), srgb('#d8e2ee'), srgb('#f4f7fb'))
    fr = frost_crystals(nb, co, 160.0)
    c = nb.paint(c, fr, '#ffffff', 0.5)
    nb.finish(c, 0.30, nb.bump(nb.add(tw, fr), 0.25, 0.001), nb.mix(nb.mul(fr, 0.25), (0, 0, 0, 1), ICE), metal=0.35)
    return m


def croz_gold():
    m, nb = _m('au_gold_proc')
    co = nb.coord('Object')
    e = nb.noise(co, 140.0, 4, 0.6)
    c = nb.mix(nb.mr(e, 0.3, 0.7, 0.0, 1.0), srgb('#b48a36'), srgb('#f0cf7a'))
    fr = frost_crystals(nb, co, 120.0)
    c = nb.paint(c, fr, '#eef8ff', 0.55)
    metal = nb.sub(1.0, nb.mul(fr, 0.8))
    nb.finish(c, nb.add(0.28, nb.mul(fr, 0.3)), nb.bump(e, 0.3, 0.001), nb.mix(nb.mul(fr, 0.2), (0, 0, 0, 1), ICE),
              metal=metal)
    return m


def croz_sun():
    m, nb = _m('au_sun_proc')
    co = nb.coord('Object')
    v = nb.voronoi(co, 220.0, 'F1', out='Distance')
    c = nb.mix(nb.mr(v, 0.1, 0.4, 0.0, 1.0), srgb('#fff2c8'), srgb('#ffc85a'))
    nb.finish(c, 0.25, None, nb.mix(nb.mr(v, 0.1, 0.45, 1.0, 0.75), (0, 0, 0, 1), SUN), metal=0.4)
    return m


# ================================================================================================ robes (tint1: light, nearly neutral)
def robe(kind='alb', hem_z=0.12, center_y=0.035):
    """white liturgical cloth: fine twill + damask motif; frost-crusted hem (mild blue)."""
    m, nb = _m('au_robe_%s_proc' % kind)
    co = nb.coord('Object')
    s = nb.sep(co)
    twill = nb.wave(nb.mapping(co, rot=(0, 0.6, 0.6)), 160.0, 1.0, 1.0, 'BANDS', 'Z')
    # damask: soft quatrefoil-ish repeat from crossed sines in the horizontal angle / height
    ang = nb.math('ARCTAN2', s[0], nb.sub(center_y, s[1]))
    a1 = nb.math('SINE', nb.mul(ang, 22.0))
    a2 = nb.math('SINE', nb.mul(s[2], 70.0))
    a3 = nb.math('SINE', nb.add(nb.mul(ang, 11.0), nb.mul(s[2], 35.0)))
    dam = nb.mr(nb.add(nb.mul(nb.mul(a1, a2), 0.7), nb.mul(a3, 0.4)), 0.35, 0.9, 0.0, 1.0)
    dam_amt = 0.05 if kind == 'alb' else 0.09
    val = nb.add(0.86, nb.mul(nb.sub(twill, 0.5), 0.05))
    val = nb.sub(val, nb.mul(dam, dam_amt))
    val = nb.sub(val, nb.mul(nb.mr(nb.noise(co, 4.0, 3, 0.5), 0.45, 0.75, 0.0, 1.0), 0.06))
    c = nb.comb(val, nb.mul(val, 0.985), nb.mul(val, 0.96))
    # frost toward the hem: icier, sparkling
    hem = nb.mr(s[2], hem_z + 0.30, hem_z, 0.0, 1.0)
    fr = frost_crystals(nb, co, 90.0)
    c = nb.mix(nb.mul(hem, 0.55), c, nb.comb(nb.mul(val, 0.86), nb.mul(val, 0.95), val))
    c = nb.mix(nb.mul(nb.mul(fr, hem), 0.8), c, (1, 1, 1, 1))
    rough = nb.sub(0.62, nb.mul(nb.mul(fr, hem), 0.35))
    emit = nb.mix(nb.mul(nb.mul(fr, hem), 0.30), (0, 0, 0, 1), ICE)
    n = nb.bump(nb.add(nb.mul(twill, 0.3), nb.add(nb.mul(dam, 0.3), nb.mul(nb.mul(fr, hem), 0.6))), 0.22, 0.0015)
    nb.finish(c, rough, n, emit)
    return m


# ================================================================================================ gold (tint2: light, nearly neutral)
def gold(kind='stole'):
    """gold cloth: woven base, raised embroidery (crosses and sunbursts on the stole, lozenge galloon on trims),
    metallic where embroidered."""
    m, nb = _m('au_gold_%s_proc' % kind)
    co = nb.coord('Object')
    pu = nb.attr('pu')
    pv = nb.attr('pv')
    weave = nb.wave(co, 220.0, 1.0, 1.0, 'BANDS', 'Z')
    if kind == 'stole':
        # embroidery motifs repeating along the stole: a cross inside a sunburst every ~0.12 m
        k = nb.math('FRACT', nb.mul(pu, 9.0))
        dy = nb.sub(k, 0.5)
        dx = nb.sub(pv, 0.5)
        r = nb.math('SQRT', nb.add(nb.mul(nb.mul(dy, dy), 1.0), nb.mul(nb.mul(dx, dx), 0.16)))
        ang = nb.math('ARCTAN2', dy, nb.mul(dx, 0.4))
        rays = nb.mul(nb.mr(nb.math('SINE', nb.mul(ang, 12.0)), 0.3, 0.9, 0.0, 1.0), nb.mr(r, 0.32, 0.22, 0.0, 1.0))
        rays = nb.mul(rays, nb.mr(r, 0.10, 0.14, 0.0, 1.0))
        cross = nb.mx(nb.mul(nb.mr(nb.math('ABSOLUTE', dx), 0.07, 0.05, 0.0, 1.0), nb.mr(nb.math('ABSOLUTE', dy), 0.15, 0.13, 0.0, 1.0)),
                      nb.mul(nb.mr(nb.math('ABSOLUTE', dy), 0.035, 0.025, 0.0, 1.0), nb.mr(nb.math('ABSOLUTE', dx), 0.30, 0.27, 0.0, 1.0)))
        border = nb.mx(nb.mr(pv, 0.12, 0.08, 0.0, 1.0), nb.mr(pv, 0.88, 0.92, 0.0, 1.0))
        emb = nb.mx(nb.mx(rays, cross), border)
        fringe = nb.mul(nb.mr(pu, 0.95, 0.97, 0.0, 1.0), nb.mr(nb.math('SINE', nb.mul(pv, 120.0)), 0.0, 0.6, 0.0, 1.0))
        emb = nb.mx(emb, fringe)
    else:
        # galloon: lozenges between two edge cords
        x = nb.sep(co)
        lz = nb.math('ABSOLUTE', nb.math('SINE', nb.add(nb.mul(x[0], 90.0), nb.mul(x[2], 90.0))))
        lz2 = nb.math('ABSOLUTE', nb.math('SINE', nb.sub(nb.mul(x[0], 90.0), nb.mul(x[2], 90.0))))
        emb = nb.mr(nb.mn(lz, lz2), 0.25, 0.08, 0.0, 1.0)
        emb = nb.mx(emb, nb.mul(nb.mr(nb.noise(co, 80.0, 2, 0.5), 0.55, 0.6, 0.0, 1.0), 0.6))
    val = nb.add(0.58, nb.mul(nb.sub(weave, 0.5), 0.08))
    val = nb.add(val, nb.mul(emb, 0.38))
    c = nb.comb(val, nb.mul(val, 0.97), nb.mul(val, 0.92))
    fr = frost_crystals(nb, co, 120.0)
    lowf = nb.mr(nb.sep(co)[2], 0.75, 0.45, 0.0, 1.0)
    c = nb.mix(nb.mul(nb.mul(fr, lowf), 0.6), c, (1, 1, 1, 1))
    metal = nb.add(0.25, nb.mul(emb, 0.65))
    rough = nb.sub(0.55, nb.mul(emb, 0.25))
    n = nb.bump(nb.add(nb.mul(emb, 1.0), nb.mul(weave, 0.2)), 0.45, 0.0015)
    emit = nb.mix(nb.mul(nb.mul(fr, lowf), 0.25), (0, 0, 0, 1), ICE)
    nb.finish(c, rough, n, emit, metal=metal)
    return m

"""The Instructor -- Management's orientation officer -- JoeBrawla fighter model (art/BRIEF.md, docs/ROSTER.md).

UBC Superhero_Male body (UAL 65-bone rig, UBC rest), head and hands +8 %, armature node scaled to 1.95 m.
Slate-grey Management dress tunic (high stand collar, double row of brass buttons, shoulder boards, flared skirt),
crimson sash with a rosette and fringed tails, black Sam Browne belt, pressed breeches with a crimson seam stripe
tucked into tall polished black boots, white gloves, peaked officer's cap low over the eyes (crimson band, black
patent visor, brass "M" badge, gold chin cord), grey moustache and brows, a brass whistle on a cord, a clipboard
strapped to his back, a black training baton in the right hand (100 % hand_r).

The shared kit (fkit, garments, Dungeon Joe 3D helpers) lives in ../joe/lib.
blender -b --factory-startup --python build_instructor.py -- [--geo]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FIGHTER_WORK'] = r'C:\dev\JoeBrawla\art\_work\instructor'
LIB = os.path.join(os.path.dirname(HERE), 'joe', 'lib')
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'joe'))
import bpy, bmesh, math, random, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
import fkit as K
import garments as GM
import djlib as dj
import djarmor as ar
import aggeo as G
import agmats as M
import en_anim as A
import build_joe as BJ
from agcore import smooth01, lerp, LR
from djlib import MB, NB, srgb

FID = 'instructor'
UNIFORM = '#6e7a8a'        # tint1 base colour factor: slate grey (times the light neutral texture)
SASH = '#b0242a'           # tint2 base colour factor: crimson
HEIGHT = 1.95
ARGS = dj.args_after_dashdash()


def polished(name, col='#121214', rough=0.16):
    """mirror-polished black leather: smooth with soft creases and a sharp sheen."""
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = M.pal(col, 0.3)
    n1 = nb.noise(co, 6.0, 4, 0.55)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.8, l)])
    crease = nb.noise(nb.mapping(co, scale=(1, 1, 7)), 26.0, 3, 0.6)
    cr = nb.mr(crease, 0.6, 0.7, 0.0, 1.0)
    c = nb.mix(nb.mul(cr, 0.25), c, srgb('#2a2a2e'))
    scuff = nb.mr(nb.noise(co, 55.0, 4, 0.6), 0.62, 0.75, 0.0, 1.0)
    r = nb.add(rough, nb.mul(nb.add(scuff, cr), 0.15))
    nrm = nb.bump(nb.mul(cr, -0.5), 0.2, 0.0015)
    nb.finish(c, r, 0.0, nrm)
    return m


def gloves_mat(name, col='#f2efe6'):
    return M.fabric(name, col, kind='linen', wear=0.15, dirt=0.15, low_z=0.5, high_z=0.8)


def build():
    F = K.Fighter(FID, head=1.08, hands=1.08)
    b, L, kit = F.body, F.L, F.kit
    st = kit.stack
    neck, chest = L['neck'], L['chest']
    zw = L['waist'].z

    # ------------------------------------------------------------------ materials
    m_uni = kit.mat('uniform', M.fabric, None, kind='wool', wear=0.25, dirt=0.15, low_z=0.2, high_z=0.6)
    m_sash = kit.mat('sash', M.fabric, '#dcdcdc', kind='silk', wear=0.2, dirt=0.05, low_z=0.5, high_z=0.8)
    m_boot = kit.mat('boot', polished, '#111114', 0.16)
    m_belt = kit.mat('belt', polished, '#16120f', 0.22)
    m_sole = kit.mat('sole', K.rubber_sole, '#1c1a19')
    m_brass = kit.mat('brass', M.plate, '#d2a54a', kind='brass', rust=0.0, grime=0.25, dents=0.1, scratches=0.4, rough=0.24)
    m_glove = kit.mat('glove', gloves_mat, '#f3f0e8')
    m_hair = kit.mat('hair', K.hair_mat, '#8e8c88', light='#d6d4ce', rough=0.55)
    m_visor = kit.mat('visor', polished, '#0c0c0e', 0.1)
    m_cord = kit.mat('cord', M.rope, '#d8b04a')
    m_board = kit.mat('board', M.wood, '#7a5a38')
    m_paper = kit.mat('paper', M.fabric, '#efe9da', kind='linen', wear=0.1, dirt=0.25, low_z=1.0, high_z=1.3)
    m_steel = kit.mat('steel', M.metal_trim, '#c4c2bc', rough=0.25)
    m_baton = kit.mat('baton', polished, '#141416', 0.32)
    m_grip = kit.mat('grip', K.rubber_sole, '#1e1d1c')

    # ------------------------------------------------------------------ breeches (tucked into the boots), crimson seam stripe
    z_wb = zw + 0.005
    knee_z = L['knee_l'].z
    boot_top = knee_z - 0.055

    def keep_tr(c, bn):
        if bn in ('pelvis', 'spine_01'):
            return c.z < z_wb
        if bn in GM.LEG_UP:
            return True
        if bn in GM.LEG_LO:
            return c.z > boot_top - 0.06
        return False
    tr = G.body_layer(b, keep_tr, 0.012, 'breeches', smooth=8, stack=st)
    # jodhpur flare on the outer thigh, pressed crease down the front
    G.loosen(tr, lambda co: 0.022 * smooth01(co.z, knee_z + 0.36, knee_z + 0.2) * (1 - smooth01(co.z, knee_z + 0.06, knee_z - 0.02))
             * (0.4 + 0.6 * smooth01(abs(co.x), 0.08, 0.16)))
    dj.push_out(tr, st.bvh(), 0.008, iters=4)
    kit.add('breeches', tr, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=3)), edge_w=0.03)
    trb = dj.bvh_from([tr])
    for s in 'lr':
        sg = 1 if s == 'l' else -1
        pts = []
        for k in range(14):
            z = lerp(z_wb - 0.02, boot_top + 0.01, k / 13)
            loc, nrm, i, d = trb.ray_cast(Vector((sg * 0.6, b.h(LR('thigh_l', s)).y, z)), Vector((-sg, 0, 0)), 1.0)
            if loc is not None:
                pts.append(loc + nrm * 0.0012)
        if len(pts) > 3:
            mbs = MB()
            ups = [Vector((0, 1, 0))] * len(pts)
            mbs.strip(pts, [0.016] * len(pts), ups)
            stripe = mbs.to_object('stripe_' + s)
            kit.add('stripe_' + s, stripe, m_sash, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=1)),
                    edge=False, collide=False)

    # ------------------------------------------------------------------ tall polished riding boots (over the breeches)
    for s in 'lr':
        up, sole, welt = GM.work_boot(b, st, s, 'boot_' + s, top_z=boot_top, off=0.01, sole_h=0.022, heel_h=0.042,
                                      toe=0.016, toe_h=0.06, welt=0.004, shaft_off=0.024)
        kit.add('boot_' + s, up, m_boot, weight=('transfer', dict(smooth_iters=2)), edge_w=0.015)
        kit.add('sole_' + s, sole, m_sole, weight=('transfer', dict(smooth_iters=1)), edge=False)
        kit.add('welt_' + s, welt, m_sole, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)
        lp = ar.boundary_loops(up)
        topl = max(lp, key=lambda l: sum(p.z for p in l[0]) / len(l[0]))
        pts = G.smooth_loop([p for p in topl[0]][::2], 2)
        rim = GM.ring_sweep(pts, 0.014, 0.007, 'boot_rim_' + s, Vector((0, 0, 1)), sides=6)
        kit.add('boot_rim_' + s, rim, m_boot, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)

    # ------------------------------------------------------------------ tunic
    def keep_tu(c, bn):
        if bn in ('spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'):
            return True
        if bn == 'neck_01':
            return c.z < neck.z - 0.012
        if bn == 'pelvis':
            return c.z > zw - 0.06
        if bn in GM.ARM_UP or bn in GM.ARM_LO:
            return abs(c.x) < abs(L['wrist_l'].x) - 0.035
        return False
    tu = G.body_layer(b, keep_tu, 0.018, 'tunic', smooth=10, stack=st, clearance=0.01)
    G.bridge_torso(tu, b, 0.02, zw - 0.06, chest.z + 0.12, stack=st)
    G.delete_faces(tu, lambda c: c.z > neck.z - 0.03 and abs(c.x) < 0.075 and c.y < 0.07)
    G.relax_boundary(tu, lambda pts: True, iters=6)
    dj.push_out(tu, st.bvh(), 0.01, iters=4)
    kit.add('tunic', tu, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=4)), edge_w=0.02)
    skirt = G.skirt(b, st, zw - 0.03, L['crotch_z'] - 0.05, 'tunic_skirt', off=0.026, off_top=0.02, top_band=0.06, flare=0.012,
                    nu=7, nv=40, back_slit=0.12, front_slit=0.0)
    kit.add('tunic_skirt', skirt, m_uni, atlas='cloth', role='tint1', weight=G.skirt_weights(b, softness=0.6, pelvis_min=0.3),
            edge_w=0.02)
    hem = G.hem_tube(skirt, 0.004, 0.6, sides=4, name='skirt_hem', pred=lambda l: min(p.z for p in l[0]) < zw - 0.1)
    kit.add('skirt_hem', hem, m_uni, atlas='cloth', role='tint1', weight=G.skirt_weights(b, softness=0.6, pelvis_min=0.3),
            edge=False, collide=False)
    # high stand collar: from the tunic's neck opening (no gap) straight up round the neck
    nc = Vector((0, neck.y + 0.004, 0))
    hole = max(ar.boundary_loops(tu), key=lambda l: sum(p.z for p in l[0]) / len(l[0]))[0]
    lp = []
    for k in range(32):
        a = 2 * math.pi * k / 32
        d = Vector((math.sin(a), -math.cos(a), 0))
        hp_ = max(hole, key=lambda p: Vector((p.x - nc.x, p.y - nc.y, 0)).normalized().dot(d))
        zt = neck.z + 0.05 - 0.012 * max(0.0, math.cos(a)) ** 2
        loc, n, i, dist = b.bvh.ray_cast(Vector((nc.x, nc.y, zt - 0.012)) + d * 0.14, -d, 0.14)
        r = (0.14 - dist) if loc is not None else 0.065
        lp.append((d, hp_, r, zt))
    bot = G.smooth_loop([hp_ + d * 0.003 for d, hp_, r, zt in lp], 2)
    top = G.smooth_loop([Vector((nc.x, nc.y, zt)) + d * (r + 0.016) for d, hp_, r, zt in lp], 1)
    mbc = MB()
    rows = [[mbc.v(p.lerp(q, t)) for p, q in zip(bot, top)] for t in (0.0, 0.4, 1.0)]
    for a_, b_ in zip(rows[:-1], rows[1:]):
        mbc.ring_bridge(a_, b_)
    collar = mbc.to_object('collar')
    GM.thicken(collar, 0.005, offset=0.0)
    kit.add('collar', collar, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge_w=0.015)
    collar_rim = GM.ring_sweep(G.smooth_loop([Vector((nc.x, nc.y, zt)) + d * (r + 0.016) for d, hp_, r, zt in lp], 1),
                               0.006, 0.0065, 'collar_rim', Vector((0, 0, 1)), sides=6)
    kit.add('collar_rim', collar_rim, m_sash, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=1)), edge=False,
            collide=False)
    # cuffs at the wrists (crimson piping)
    for s in 'lr':
        el, wr = b.h(LR('lowerarm_l', s)), b.h(LR('hand_l', s))
        a = (wr - el).normalized()
        c = wr - a * 0.05
        cf = GM.ring_sweep(GM.limb_loop(st.bvh(), c, a, (0, 0, 1), 0.006, 26), 0.05, 0.008, 'cuff_' + s, a, sides=6)
        kit.add('cuff_' + s, cf, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=1)), edge=False)
        pp = GM.ring_sweep(GM.limb_loop(st.bvh(), c - a * 0.026, a, (0, 0, 1), 0.006, 26), 0.007, 0.006, 'cuffpipe_' + s, a,
                           sides=6)
        kit.add('cuffpipe_' + s, pp, m_sash, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=1)), edge=False,
                collide=False)
    # shoulder boards (draped on the tunic only, so nothing climbs the neck or the head)
    tub0 = dj.bvh_from([tu])
    for s in 'lr':
        sg = 1 if s == 'l' else -1
        sh = b.h(LR('upperarm_l', s))
        pb = GM.patch_on(tub0, (sg * (abs(sh.x) - 0.03), sh.y - 0.005, sh.z + 0.2), (1, 0, 0), (0, 1, 0), 0.068, 0.034,
                         (0, 0, -1), 0.003, nu=8, nv=4, round_r=0.012, name='board_' + s)
        GM.thicken(pb, 0.006)
        kit.add('board_' + s, pb, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=1)), edge_w=0.01)
        bbv = dj.bvh_from([pb])
        mbb = MB()
        loc, nrm, i, d = bbv.ray_cast(Vector((sg * (abs(sh.x) - 0.08), sh.y - 0.005, sh.z + 0.3)), Vector((0, 0, -1)), 1.0)
        if loc is not None:
            GM.cyl_between(mbb, loc + nrm * 0.0005, loc + nrm * 0.006, 0.0085, segs=10)
        kit.add('board_btn_' + s, mbb.to_object('board_btn_' + s), m_brass, weight=('transfer', dict(smooth_iters=1)), edge=False,
                collide=False)
    # breast pockets with flaps
    tub = dj.bvh_from([tu])
    for sx in (-1, 1):
        pk = GM.patch_on(tub, (sx * 0.1, 0, 1.27), (1, 0, 0), (0, 0, 1), 0.05, 0.06, (0, 1, 0), 0.0028, nu=6, nv=7,
                         round_r=0.006, name='pocket')
        GM.thicken(pk, 0.0025)
        kit.add('pocket', pk, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge_w=0.01, collide=False)
        fl = GM.patch_on(tub, (sx * 0.1, 0, 1.335), (1, 0, 0), (0, 0, 1), 0.054, 0.018, (0, 1, 0), 0.0065, nu=6, nv=3,
                         round_r=0.005, name='flap')
        GM.thicken(fl, 0.003)
        kit.add('flap', fl, m_uni, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge_w=0.01, collide=False)
    # double row of brass buttons
    mbn = MB()
    for z in (1.05, 1.13, 1.21, 1.29, 1.37, 1.44):
        for sx in (-1, 1):
            x = sx * lerp(0.055, 0.075, smooth01(z, 1.05, 1.44))
            loc, nrm, i, d = tub.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)), 1.0)
            if loc is not None:
                mbn.ellipsoid(loc + nrm * 0.003, (0.0085, 0.0085, 0.005), segs=10, rings=5,
                              M=GM.frame3(nrm).to_4x4())
    for sx in (-1, 1):
        loc, nrm, i, d = tub.ray_cast(Vector((sx * 0.1, -0.5, 1.328)), Vector((0, 1, 0)), 1.0)
        if loc is not None:
            mbn.ellipsoid(loc + nrm * 0.0085, (0.0065, 0.0065, 0.004), segs=8, rings=4, M=GM.frame3(nrm).to_4x4())
    kit.add('buttons', mbn.to_object('buttons'), m_brass, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)

    # ------------------------------------------------------------------ Sam Browne belt
    belt, bpts = G.belt(st.bvh(), Vector((0, 0.02, zw - 0.035)), 'belt', width=0.05, thick=0.009, off=0.004, n=56)
    kit.add('belt', belt, m_belt, weight=('transfer', dict(smooth_iters=2)), edge=False)
    front = min(bpts, key=lambda p: p.y + abs(p.x) * 0.8)
    bk = GM.buckle(front + Vector((0, -0.007, 0)), (0, -1, 0), (0, 0, 1), w=0.062, h=0.056, bar=0.009, depth=0.006)
    kit.add('buckle', bk, m_brass, weight={'pelvis': 1.0}, edge=False, collide=False)

    # ------------------------------------------------------------------ crimson sash: right shoulder -> left hip
    sb = st.bvh()
    path = []
    p_sh = Vector((-0.12, 0.0, L['shoulder_l'].z + 0.04))
    p_hip = Vector((0.15, 0.0, zw - 0.06))
    for k in range(17):
        t = k / 16
        q = p_sh.lerp(p_hip, t)
        path.append(q)
    front_pts, back_pts = [], []
    for q in path:
        for sgn, lst in ((-1, front_pts), (1, back_pts)):
            loc, nrm, i, d = sb.ray_cast(Vector((q.x, sgn * 0.6, q.z)), Vector((0, -sgn, 0)), 1.2)
            if loc is not None:
                lst.append(loc + nrm * 0.006)
    # over the shoulder top
    top = []
    for k in range(7):
        y = lerp(front_pts[0].y, back_pts[0].y, k / 6)
        loc, nrm, i, d = sb.ray_cast(Vector((-0.12, y, 2.0)), Vector((0, 0, -1)), 1.0)
        if loc is not None:
            top.append(loc + nrm * 0.006)
    # round the left side of the waist, back hip -> front hip (closes the loop)
    side = []
    hc_ = Vector((0.0, 0.02, p_hip.z))
    for th in np.linspace(math.radians(150), math.radians(30), 7):
        d = Vector((math.sin(th), -math.cos(th), 0))
        loc, nrm, i, dd = sb.ray_cast(hc_ + d * 0.6, -d, 0.6)
        if loc is not None:
            side.append(loc + nrm * 0.006)
    loop = list(reversed(front_pts)) + top[1:-1] + back_pts + side
    ups = []
    nL = len(loop)
    for i, p in enumerate(loop):
        a = loop[(i - 1) % nL]
        c = loop[(i + 1) % nL]
        tng = (c - a).normalized()
        loc, nrm, idx, d = sb.find_nearest(p)
        nn = nrm if nrm is not None else Vector((0, -1, 0))
        ups.append(tng.cross(nn).normalized())
    mbs = MB()
    mbs.strip(loop, [0.085] * len(loop), ups, closed=True)
    sash = mbs.to_object('sash')
    GM.thicken(sash, 0.003, offset=0.0)
    dj.push_out(sash, st.bvh(), 0.004, iters=3)
    kit.add('sash', sash, m_sash, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=3)), edge_w=0.012)
    # rosette knot + fringed tails at the left hip
    kc = front_pts[-1] + Vector((0.01, -0.012, -0.01))
    mbk = MB()
    mbk.ellipsoid(kc, (0.03, 0.022, 0.03), segs=10, rings=6)
    for k, (dx, ln) in enumerate(((-0.018, 0.2), (0.02, 0.24))):
        p0 = kc + Vector((dx, 0.0, -0.02))
        pts = [p0 + Vector((dx * 0.3 * t, -0.008 * math.sin(t * 2), -ln * t)) for t in np.linspace(0, 1, 7)]
        mbk.strip(pts, [0.05 - 0.008 * t for t in np.linspace(0, 1, 7)], [Vector((1, 0, 0))] * 7, thick=0.0)
    knot = mbk.to_object('sash_knot')
    GM.thicken(knot, 0.003, offset=0.0)
    kit.add('sash_knot', knot, m_sash, atlas='cloth', role='tint2', weight={'pelvis': 0.6, 'thigh_l': 0.4}, edge_w=0.01,
            collide=False)
    mbf = MB()
    for dx, ln in ((-0.018, 0.2), (0.02, 0.24)):
        end = kc + Vector((dx * 1.3, 0.0, -0.02 - ln))
        for j in range(7):
            x = end.x + (j - 3) * 0.0065
            mbf.sweep([Vector((x, end.y - 0.002, end.z + 0.004)), Vector((x + 0.001, end.y - 0.003, end.z - 0.045))],
                      [0.0022, 0.0016], sides=4, cap0='flat', cap1='flat')
    fringe = mbf.to_object('fringe')
    kit.add('fringe', fringe, m_cord, weight={'pelvis': 0.5, 'thigh_l': 0.5}, edge=False, collide=False)

    # ------------------------------------------------------------------ white gloves
    for s in 'lr':
        gl = G.glove(b, st, s, 'glove_' + s, off=0.0028, cuff=0.012)
        kit.add('glove_' + s, gl, m_glove, weight=('transfer', dict(smooth_iters=1)), edge_w=0.01)

    # ------------------------------------------------------------------ head: grey hair, brows, moustache, cap
    m_hairtex = kit.mat('hairtex', K.hair_tex, '#8a8884', light='#dcdad4', rough=0.55)
    hair = GM.stock_hair(b, 'Hair_Buzzed', 'hair', head_scale=1.08, tousle=0.0015, lift=0.0, seed=4)
    kit.add('hair', hair, m_hairtex, weight='Head', edge=False)
    brows = b.brows
    brows.parent = None
    brows.modifiers.clear()
    BJ.shape_brows(b, brows, thick=1.5, stern=0.002)          # bushy, inner ends down: stern
    kit.add('brows', brows, m_hair, weight='Head', edge=False, collide=False, uvw=2.0)
    b.meshes = [o for o in b.meshes if o is not brows]
    kit.add('moustache', moustache(b), m_hair, weight='Head', edge=False, collide=False, uvw=2.0)
    for name, ob, mat in officer_cap(b, st, m_uni, m_sash, m_visor, m_brass, m_cord):
        kit.add(name, ob, mat, atlas='cloth' if mat in (m_uni, m_sash) else 'gear',
                role='tint1' if mat is m_uni else ('tint2' if mat is m_sash else 'gear'), weight='Head', edge=False,
                collide=False, uvw=3.0 if name == 'badge' else 1.0)

    # ------------------------------------------------------------------ whistle on a cord (left chest)
    loc, nrm, i, d = tub.ray_cast(Vector((0.1, -0.5, 1.255)), Vector((0, 1, 0)), 1.0)
    wpos = loc + nrm * 0.016
    mbw = MB()
    ax_w = Vector((0.25, -0.15, -1)).normalized()
    GM.cyl_between(mbw, wpos, wpos + ax_w * 0.05, 0.0075, segs=10)
    mbw.ellipsoid(wpos + ax_w * 0.055 + Vector((0.0, -0.004, 0.0)), (0.013, 0.012, 0.012), segs=10, rings=6)
    mbw.lathe([(0.004, -0.001), (0.0055, 0.0), (0.0055, 0.003), (0.004, 0.004)], 8, GM.placed_m(GM.frame3(-ax_w), wpos - ax_w * 0.002))
    whistle = mbw.to_object('whistle')
    kit.add('whistle', whistle, m_brass, weight='spine_03', edge=False, collide=False, uvw=2.0)
    # cord: from the left shoulder board button down to the whistle (lanyard drape)
    sh = b.h('upperarm_l')
    c0 = st.bvh().ray_cast(Vector((abs(sh.x) - 0.08, sh.y - 0.005, sh.z + 0.3)), Vector((0, 0, -1)), 1.0)[0]
    if c0 is not None:
        c1 = c0 + Vector((-0.02, -0.06, -0.06))
        c2 = wpos + Vector((0.01, -0.02, 0.05))
        cpts = GM.bez(c0, c1, c2, wpos + Vector((0, 0, 0.004)), 10)
        cbv = st.bvh()
        cpts2 = []
        for p in cpts:
            l2, n2, i2, d2 = cbv.find_nearest(p)
            if l2 is not None and (p - l2).dot(n2) < 0.004:
                p = l2 + n2 * 0.004
            cpts2.append(p)
        mbc2 = MB()
        mbc2.sweep(cpts2, [0.0022] * len(cpts2), sides=5, cap0='flat', cap1='flat')
        kit.add('whistle_cord', mbc2.to_object('whistle_cord'), m_cord, weight=('transfer', dict(smooth_iters=1)), edge=False,
                collide=False)

    # ------------------------------------------------------------------ clipboard strapped to the back
    # board plane just behind the furthest-back point of the back under its footprint (shoulder blades, sash)
    sbv = st.bvh()

    def back_max(z0, z1):
        m_ = -1.0
        for x in np.linspace(-0.14, 0.16, 7):
            for z in np.linspace(z0, z1, 4):
                l0 = sbv.ray_cast(Vector((x, 0.6, z)), Vector((0, -1, 0)), 1.0)[0]
                if l0 is not None:
                    m_ = max(m_, l0.y)
        return m_
    y_top, y_bot = back_max(1.27, 1.4) + 0.012, back_max(1.12, 1.2) + 0.012
    back_y = max(y_top, y_bot) - 0.012
    lean = math.atan2(y_top - y_bot, 0.25)                       # follows the back: top further out than the waist
    tilt = math.radians(14)
    Rb = Matrix.Rotation(-lean, 3, 'X') @ Matrix.Rotation(tilt, 3, 'Y')
    cc = Vector((0.02, (y_top + y_bot) * 0.5, 1.25))

    def plane_y(z):
        return cc.y + (z - cc.z) * math.tan(lean)
    mbb = MB()
    GM.rounded_box(mbb, cc, (0.23, 0.009, 0.32), Rb, bevel=0.003, segs=1)
    board = mbb.to_object('clipboard')
    kit.add('clipboard', board, m_board, weight='spine_03', edge=False, collide=False)
    mbp = MB()
    GM.rounded_box(mbp, cc + Rb @ Vector((0, 0.006, -0.012)), (0.205, 0.003, 0.27), Rb, bevel=0.0008, segs=1)
    paper = mbp.to_object('paper')
    kit.add('paper', paper, m_paper, weight='spine_03', edge=False, collide=False)
    mbs2 = MB()
    GM.rounded_box(mbs2, cc + Rb @ Vector((0, 0.011, 0.135)), (0.11, 0.012, 0.035), Rb, bevel=0.004, segs=1)
    GM.cyl_between(mbs2, cc + Rb @ Vector((-0.035, 0.017, 0.15)), cc + Rb @ Vector((0.035, 0.017, 0.15)), 0.0045, segs=8)
    clip = mbs2.to_object('clip')
    kit.add('clip', clip, m_steel, weight='spine_03', edge=False, collide=False)
    # two black straps holding it (over the shoulders would fight the sash; a short harness on the back)
    mbt = MB()
    for zz in (1.32, 1.14):
        pts = []
        for x in np.linspace(-0.19, 0.21, 11):
            l3, n3, i3, d3 = sbv.ray_cast(Vector((x, 0.6, zz)), Vector((0, -1, 0)), 1.0)
            y = l3.y + 0.004 if l3 is not None else back_y
            if abs(x - 0.02) < 0.15:
                y = max(y, plane_y(zz) + 0.0045 + 0.006 + 0.004)   # over the board and the paper
            pts.append(Vector((x, y, zz)))
        mbt.strip(pts, [0.03] * len(pts), [Vector((0, 0, 1))] * len(pts))
    straps = mbt.to_object('straps')
    GM.thicken(straps, 0.003, offset=0.0)
    kit.add('straps', straps, m_belt, weight='spine_03', edge=False, collide=False)

    # ------------------------------------------------------------------ training baton in the right fist (100 % hand_r)
    rig = A.Rig(b.arm)
    it, rr = A.make_item(rig, 'baton', 'r', 'sword')
    hb = b.arm.data.bones['hand_r']
    Mi = hb.matrix_local.to_3x3() @ it.grip_rot
    gp = hb.matrix_local @ it.grip_pos
    z_ax = Mi @ Vector((0, 0, 1))         # item +Z = toward the pommel (pinky side); the tip is -Z
    mbbt = MB()
    tip = gp - z_ax * 0.52
    GM.cyl_between(mbbt, gp + z_ax * 0.075, gp - z_ax * 0.06, 0.0165, segs=12)                 # grip
    GM.cyl_between(mbbt, gp - z_ax * 0.06, tip, 0.0145, segs=12, r2=0.0125)                  # shaft
    knob = gp + z_ax * 0.075
    mbbt.ellipsoid(knob + z_ax * 0.008, (0.021, 0.021, 0.014), segs=12, rings=6, M=GM.frame3(z_ax).to_4x4())
    mbbt.ellipsoid(tip, (0.0135, 0.0135, 0.01), segs=12, rings=6, M=GM.frame3(z_ax).to_4x4())
    baton = mbbt.to_object('baton')
    kit.add('baton', baton, m_baton, weight='hand_r', edge=False, collide=False)
    mbg = MB()
    for k in range(6):
        c = gp + z_ax * (0.06 - k * 0.022)
        GM.cyl_between(mbg, c, c - z_ax * 0.012, 0.0172, segs=12)
    kit.add('baton_grip', mbg.to_object('baton_grip'), m_grip, weight='hand_r', edge=False, collide=False)
    mbc3 = MB()
    GM.cyl_between(mbc3, tip + z_ax * 0.03, tip - z_ax * 0.004, 0.0142, segs=12)
    kit.add('baton_cap', mbc3.to_object('baton_cap'), m_steel, weight='hand_r', edge=False, collide=False)
    return F


def moustache(b):
    """thick grey military moustache from under the nose out past the mouth corners, slightly upturned tips."""
    L = b.L
    nose, chin = L['nose'], L['chin']
    mouth_z = (nose.z + chin.z) * 0.5 + 0.004
    mb = MB()
    rnd = random.Random(11)
    for sx in (-1, 1):
        for k in range(9):
            x0 = sx * (0.002 + 0.0042 * k)
            z0 = nose.z - 0.02 - 0.0012 * k + rnd.uniform(-0.002, 0.002)
            st = Vector((x0, -0.4, z0))
            loc, n, i, d = b.bvh.ray_cast(st, Vector((0, 1, 0)), 0.6)
            if loc is None:
                continue
            ln = 0.026 + 0.0035 * k
            e = Vector((sx * (0.03 + 0.0042 * k), loc.y + 0.016 + 0.003 * k, mouth_z - 0.006 - 0.0015 * k + 0.004 * max(0, k - 6)))
            pts = GM.bez(loc - n * 0.002, loc + n * 0.011 + Vector((sx * 0.006, 0, -0.004)),
                         e + Vector((-sx * 0.006, -0.009, 0.01)), e, 7)
            rad = [(lerp(0.0085, 0.0025, t ** 1.4) * 0.8, lerp(0.0085, 0.0025, t ** 1.4)) for t in np.linspace(0, 1, 7)]
            mb.sweep(pts, rad, sides=5, cap0='flat', cap1='round', cap_segs=1, up=n)
    ob = mb.to_object('moustache')
    dj.push_out(ob, b.bvh, 0.0018, iters=3)
    return ob


def officer_cap(b, st, m_crown, m_band, m_visor, m_brass, m_cord):
    """peaked officer's cap worn low: band round the head, wide saucer crown raised in front, black visor over the eyes,
    brass badge and gold chin cord."""
    L = b.L
    hc = L['head_c']
    eye_z = (L['eye_l'].z + L['eye_r'].z) * 0.5
    # head outline at the band height (tilted: low in front, higher at the back)
    zf, zb = eye_z + 0.046, eye_z + 0.088

    def band_z(th):
        return lerp(zf, zb, 0.5 - 0.5 * math.cos(th))

    def head_r(th, z):
        d = Vector((math.sin(th), -math.cos(th), 0))
        loc, n, i, dist = b.bvh.ray_cast(Vector((hc.x, hc.y, z)) + d * 0.3, -d, 0.3)
        r = (0.3 - dist) if loc is not None else 0.1
        return r
    N = 36
    ring = []
    for k in range(N):
        th = 2 * math.pi * k / N
        z = band_z(th)
        ring.append((th, z, max(head_r(th, z), head_r(th, z + 0.03)) + 0.012))
    out = []
    # band (crimson): a short tube
    mb = MB()
    rows = []
    for t in (0.0, 1.0):
        rows.append([mb.v(Vector((hc.x + math.sin(th) * r, hc.y - math.cos(th) * r, z + 0.045 * t))) for th, z, r in ring])
    mb.ring_bridge(rows[0], rows[1])
    band = mb.to_object('cap_band')
    GM.thicken(band, 0.004, offset=-1.0)
    out.append(('cap_band', band, m_band))
    # crown: from the band top flaring out to a wide saucer, raised at the front
    mb = MB()
    rows = []
    prof = [(0.0, 0.045, 1.0), (0.4, 0.075, 1.1), (0.75, 0.108, 1.38), (0.92, 0.124, 1.42), (1.0, 0.13, 1.36)]
    for (_, dz, sc) in prof:
        row = []
        for th, z, r in ring:
            front = max(0.0, math.cos(th))
            rise = 0.03 * front ** 1.5 * smooth01(dz, 0.07, 0.115)
            rr = r * sc + 0.01 * front * smooth01(dz, 0.07, 0.115)
            row.append(mb.v(Vector((hc.x + math.sin(th) * rr, hc.y - math.cos(th) * rr * (1.05 if front > 0 else 1.0), z + dz + rise))))
        rows.append(row)
    for a_, b_ in zip(rows[:-1], rows[1:]):
        mb.ring_bridge(a_, b_)
    # top: domed lid
    topc = sum((v.co for v in rows[-1]), Vector()) / N
    inner = [mb.v(topc + (v.co - topc) * 0.55 + Vector((0, 0, 0.012))) for v in rows[-1]]
    mb.ring_bridge(rows[-1], inner)
    mb.fan(inner, topc + Vector((0, 0, 0.016)))
    crown = mb.to_object('cap_crown')
    GM.thicken(crown, 0.003, offset=-1.0)
    out.append(('cap_crown', crown, m_crown))
    # visor: a curved half-disc sloping down over the eyes
    mb = MB()
    rows = []
    for t in np.linspace(0, 1, 4):
        row = []
        for k in range(15):
            th = math.radians(-78 + 156 * k / 14)
            z0 = band_z(th) + 0.004
            r0 = max(head_r(th, z0), head_r(th, z0 + 0.03)) + 0.012
            reach = 0.062 * math.cos(th) ** 0.7
            d = Vector((math.sin(th), -math.cos(th), 0))
            p = Vector((hc.x, hc.y, z0)) + d * (r0 + reach * t) + Vector((0, 0, -0.022 * t * t - 0.004 * t))
            row.append(mb.v(p))
        rows.append(row)
    for a_, b_ in zip(rows[:-1], rows[1:]):
        mb.ring_bridge(a_, b_, closed=False)
    visor = mb.to_object('cap_visor')
    GM.thicken(visor, 0.004, offset=0.0)
    out.append(('cap_visor', visor, m_visor))
    # badge on the crown front: brass oval with an "M"
    z = band_z(0) + 0.072
    cbv = dj.bvh_from([crown])
    loc, n_, i_, d_ = cbv.ray_cast(Vector((hc.x, hc.y - 0.5, z)), Vector((0, 1, 0)), 1.0)
    nrm = (n_ if n_ is not None and n_.y < 0 else Vector((0, -1, 0.35))).normalized()
    pf = (loc + nrm * 0.001) if loc is not None else Vector((hc.x, hc.y - ring[0][2] * 1.2, z))
    mb = MB()
    mb.lathe([(0.0, 0.0), (0.022, 0.0), (0.024, 0.004), (0.018, 0.007), (0.0, 0.008)], 16, GM.placed_m(GM.frame3(nrm), pf))
    # raised "M" bars
    Mf = GM.frame3(nrm)
    for (a, c) in (((-0.011, -0.01), (-0.011, 0.011)), ((-0.011, 0.011), (0.0, -0.002)), ((0.0, -0.002), (0.011, 0.011)),
                   ((0.011, 0.011), (0.011, -0.01))):
        pa = pf + Mf @ Vector((a[0], a[1], 0.008))
        pc = pf + Mf @ Vector((c[0], c[1], 0.008))
        mb.sweep([pa, pc], [(0.0028, 0.002)] * 2, sides=4, cap0='flat', cap1='flat', up=nrm)
    badge = mb.to_object('badge')
    out.append(('badge', badge, m_brass))
    # gold chin cord above the visor with two side buttons
    mb = MB()
    pts = []
    for k in range(15):
        th = math.radians(-80 + 160 * k / 14)
        z0 = band_z(th) + 0.01
        r0 = max(head_r(th, z0), head_r(th, z0 + 0.03)) + 0.018
        pts.append(Vector((hc.x + math.sin(th) * r0, hc.y - math.cos(th) * r0, z0)))
    mb.sweep(pts, [0.0032] * len(pts), sides=6, cap0='round', cap1='round')
    for p in (pts[0], pts[-1]):
        mb.ellipsoid(p, (0.006, 0.006, 0.006), segs=8, rings=5)
    out.append(('chin_cord', mb.to_object('chin_cord'), m_cord))
    return out


def skin_info():
    return dict(sex='m', skin='#c3906e', feats=[('wrinkles', 0.75), ('eyebags', 0.5), ('rosy', 0.18), ('stubble', '#8a8680', 0.25),
                                              ('kohl', '#2a1e1a', 0.28), ('scar', 'brow_l', 0.55)])


def main():
    F = build()
    kit = F.kit
    kit.report()
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'joe'))
    if '--geo' in ARGS:
        import build_joe as BJ
        K.eye_material(F, hue_sat=(0.58, 0.3), iris_gain=1.1, glow=('#bfe4ff', 2.5))
        BJ.quick_render(F, 'instructor', {'tint1': UNIFORM, 'tint2': SASH})
        K.save_blend(F, 'geo')
        return
    sk = K.skin_texture(F, skin_info())
    K.skin_material(F, sk, name='instructor_skin')
    K.eye_material(F, hue_sat=(0.58, 0.3), iris_gain=1.1, name='instructor_eyes', glow=('#bfe4ff', 2.5))
    covers = [p.ob for p in kit.parts if p.atlas == 'cloth' or p.name.startswith(('boot', 'sole', 'glove'))]

    def protect(co, bn):
        return bn in ('Head',)
    def force(co, bn):             # feet and shins live inside the riding boots
        return bn.startswith(('foot_', 'ball_')) or (bn.startswith('calf_') and co.z < L_boot_top - 0.03)
    L_boot_top = F.L['knee_l'].z - 0.055
    K.trim_body(F, covers, reach=0.12, dilate=2, protect=protect, force=force)
    K.save_blend(F, 'prebake')
    cloth = K.bake_atlas(F, 'cloth', {'tint1': ('tint1_instructor_uniform', UNIFORM, True),
                                      'tint2': ('tint2_instructor_sash', SASH, True)},
                         size=2048, samples=16, extra_occluders=[p.ob for p in kit.parts if p.atlas != 'cloth'])
    gear = K.bake_atlas(F, 'gear', {'gear': ('instructor_gear', None, True)}, size=2048, samples=16, extra_occluders=[cloth])
    F.body.mesh.name = 'instructor_body'
    F.body.eyes.name = 'instructor_eyes'
    cloth.name = 'instructor_cloth'
    gear.name = 'instructor_gear'
    meshes = [F.body.mesh, F.body.eyes, cloth, gear]
    K.save_blend(F, 'final')
    src = os.path.join(F.work, 'instructor_src.glb')
    scale = HEIGHT / F.L['top']
    K.export(F, meshes, src, scale=scale)
    K.node(os.path.join(K.TOOLS, 'post.mjs'), src, json.dumps({'tint1_instructor_uniform': UNIFORM, 'tint2_instructor_sash': SASH}))


if __name__ == '__main__':
    main()

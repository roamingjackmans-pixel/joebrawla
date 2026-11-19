"""Joe -- "Apartment 3C" -- JoeBrawla fighter model (art/BRIEF.md, docs/ROSTER.md).

UBC Superhero_Male body (UAL 65-bone rig, UBC rest), head and hands +8 %; charcoal rolled-sleeve work shirt open
over a torn white tank top, dark work trousers with knee patches, scuffed tan lace-up work boots, leather tool belt
with pouch + tools, ring holster with a flashlight on the right hip (lens glows), brass key on an orange lanyard,
grey duct-tape hand wraps, messy brown hair, stubble, faded orange "3C" shoulder patch.

blender -b --factory-startup --python build_joe.py -- [--geo] (geo = procedural EEVEE look only, no bake/export)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FIGHTER_WORK'] = r'C:\dev\JoeBrawla\art\_work\joe'
sys.path.insert(0, os.path.join(HERE, 'lib'))
import bpy, bmesh, math, random, json
import numpy as np
from mathutils import Vector, Matrix, noise
import fkit as K
import garments as GM
import djlib as dj
import djarmor as ar
import aggeo as G
import agmats as M
from agcore import smooth01, lerp, LR
from djlib import MB

FID = 'joe'
SHIRT = '#4c5058'          # tint1 base colour factor (charcoal once multiplied with the light neutral texture)
TROUSERS = '#4f4532'       # tint2 base colour factor (dark olive-brown work trousers)
ROLL_DX = 0.035            # sleeve roll sits this far past the elbow
ARGS = dj.args_after_dashdash()


def build():
    F = K.Fighter(FID, head=1.08, hands=1.08)
    b, L, kit = F.body, F.L, F.kit
    st = kit.stack
    zw = L['waist'].z
    neck = L['neck']
    chest = L['chest']

    # ------------------------------------------------------------------ materials
    m_tank = kit.mat('tank', M.fabric, '#e6e0d2', kind='linen', wear=0.6, dirt=0.7, low_z=0.95, high_z=1.2)
    m_shirt = kit.mat('shirt', M.fabric, None, kind='canvas', wear=0.75, dirt=0.35, low_z=0.85, high_z=1.1)
    m_trou = kit.mat('trousers', M.fabric, None, kind='canvas', wear=0.6, dirt=0.9, low_z=0.1, high_z=0.65)
    m_knee = kit.mat('knee', M.fabric, '#b4b4b4', kind='canvas', wear=0.9, dirt=0.8, low_z=0.3, high_z=0.7)
    m_boot = kit.mat('boot', M.leather, '#5c4026', kind='rough', wear=0.45, dirt=0.7, low_z=0.0, high_z=0.1)
    m_bootcap = kit.mat('bootcap', M.leather, '#3b2715', kind='smooth', wear=0.9, dirt=0.6, low_z=0.0, high_z=0.08)
    m_welt = kit.mat('welt', M.leather, '#3e2614', kind='smooth', wear=0.5, dirt=0.8, low_z=0.0, high_z=0.06)
    m_sole = kit.mat('sole', K.rubber_sole, '#2e2620')
    m_lace = kit.mat('lace', M.rope, '#6a4a2a')
    m_belt = kit.mat('belt', M.leather, '#5a3820', kind='oiled', wear=0.8, dirt=0.3, low_z=0.7, high_z=0.95)
    m_steel = kit.mat('steel', M.metal_trim, '#b4b0a6', rough=0.32)
    m_brass = kit.mat('brass', M.plate, 'default', kind='brass', rust=0.0, grime=0.5, dents=0.2, scratches=0.6)
    m_tape = kit.mat('tape', K.duct_tape, '#a2a6a9')
    m_hair = kit.mat('hair', K.hair_mat, '#4a3122', light='#8f6a46')
    m_lan = kit.mat('lanyard', M.fabric, '#d9572a', kind='silk', wear=0.3, dirt=0.2, low_z=0.5, high_z=0.8)
    m_flash = kit.mat('flash', M.plate, '#3c3e42', kind='blackened', rust=0.0, grime=0.5, dents=0.3)
    m_lens = kit.mat('lens', K.glass_lens, '#fff0c8', 8.0)
    m_btn = kit.mat('button', M.plate, '#3b2e24', kind='painted', rust=0.0, grime=0.3, dents=0.0, scratches=0.4, rough=0.35)
    m_red = kit.mat('grip_red', M.plate, '#b8261c', kind='painted', rust=0.0, grime=0.4, dents=0.0, rough=0.4)
    m_yel = kit.mat('grip_yel', M.plate, '#e2a822', kind='painted', rust=0.0, grime=0.4, dents=0.0, rough=0.45)

    # ------------------------------------------------------------------ boots (first: the trousers fall over them)
    for s in 'lr':
        up, sole, welt = GM.work_boot(b, st, s, 'boot_' + s, top_z=0.24, off=0.021, sole_h=0.034, heel_h=0.047, toe=0.022,
                                      toe_h=0.092, welt=0.011, shaft_off=0.016)
        ball = b.h(LR('ball_l', s))
        ank = b.h(LR('foot_l', s))
        cap_ = GM.overlay(up, lambda c, by=ball.y: c.y < by - 0.012 and c.z > 0.034, 0.0022, 'toecap_' + s, thick=0.0018)
        heel = GM.overlay(up, lambda c, ay=ank.y: c.y > ay + 0.005 and c.z < 0.1, 0.0022, 'heelcap_' + s, thick=0.0018)
        kit.add('boot_' + s, up, m_boot, weight=('transfer', dict(smooth_iters=2)), edge_w=0.02)
        kit.add('toecap_' + s, cap_, m_bootcap, weight=('transfer', dict(smooth_iters=1)), edge_w=0.008)
        kit.add('heelcap_' + s, heel, m_bootcap, weight=('transfer', dict(smooth_iters=1)), edge_w=0.008)
        kit.add('sole_' + s, sole, m_sole, weight=('transfer', dict(smooth_iters=1)), edge=False)
        kit.add('welt_' + s, welt, m_welt, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)
    for s in 'lr':
        laces, eyelets = GM.boot_laces(b, st.bvh(), s, 'boot_' + s, z0=0.082, z1=0.22, pairs=6, half=0.019)
        kit.add('laces_' + s, laces, m_lace, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)
        kit.add('eyelets_' + s, eyelets, m_brass, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)

    # ------------------------------------------------------------------ tank top (tucked in)
    def keep_tank(c, bn):
        if bn not in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'):
            return False
        if c.z < 0.985:
            return False
        ax = abs(c.x)
        strap = 0.068 < ax < 0.135
        if bn.startswith('clavicle'):
            return strap
        if ax > 0.148 and c.z > 1.26:
            return False
        front = c.y < 0.0
        zline = (1.37 if front else 1.445) + (0.12 if front else 0.05) * min(1.0, ax / 0.125) ** 2
        return c.z <= zline or strap
    tank = G.body_layer(b, keep_tank, 0.0045, 'tank', smooth=6, stack=st)
    G.bridge_torso(tank, b, 0.006, 1.0, chest.z + 0.06)
    # a little torn: two small rips and a nick in the neckline
    for (cx, cz, rx, rz) in ((0.042, 1.115, 0.011, 0.016), (-0.03, 1.035, 0.008, 0.012)):
        G.delete_faces(tank, lambda c, cx=cx, cz=cz, rx=rx, rz=rz: c.y < 0 and ((c.x - cx) / rx) ** 2 + ((c.z - cz) / rz) ** 2 < 1)
    G.relax_boundary(tank, lambda pts: True, iters=5)
    dj.push_out(tank, b.bvh, 0.004, iters=3)
    kit.add('tank', tank, m_tank, weight=('transfer', dict(smooth_iters=3)), edge_w=0.015)

    # ------------------------------------------------------------------ trousers
    z_wb = 1.035

    def keep_tr(c, bn):
        if bn in ('pelvis', 'spine_01'):
            return c.z < z_wb
        if bn in GM.LEG_UP:
            return True
        if bn in GM.LEG_LO:
            return c.z > 0.095
        return False
    tr = G.body_layer(b, keep_tr, 0.013, 'trousers', smooth=8, stack=st)
    knee_z = L['knee_l'].z
    G.loosen(tr, lambda co: 0.009 * smooth01(co.z, z_wb - 0.03, z_wb - 0.16) + 0.006 * smooth01(co.z, knee_z + 0.25, knee_z)
             * (1 - smooth01(co.z, knee_z - 0.1, knee_z - 0.25)))
    straight_legs(b, tr)
    me = tr.data
    me.update()
    for v in me.vertices:          # the break: soft folds bunching over the boots
        k = 1 - smooth01(v.co.z, 0.14, 0.32)
        a = math.atan2(v.co.y, v.co.x - math.copysign(0.114, v.co.x))
        v.co += v.normal * (0.0055 * k * math.sin(v.co.z * 95 + a * 2.0 + 1.3))
    me.update()
    dj.push_out(tr, st.bvh(), 0.009, iters=4)

    def hem_z(co):                 # the break: higher over the instep, lower at the heel
        sg = 1 if co.x > 0 else -1
        cy = b.h(LR('foot_l', 'l' if sg > 0 else 'r')).y - 0.03
        return 0.15 + 0.026 * smooth01(cy - co.y, -0.06, 0.07)
    GM.flatten_hem(tr, 0.2, hem_z)
    dj.push_out(tr, st.bvh(), 0.008, iters=2)
    kit.add('trousers', tr, m_trou, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=3)), edge_w=0.03)
    hems = G.hem_tube(tr, 0.0055, 0.55, sides=4, name='trouser_hems')
    kit.add('trouser_hems', hems, m_trou, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=2)), edge=False,
            collide=False)
    trb = dj.bvh_from([tr])
    for s in 'lr':
        sg = 1 if s == 'l' else -1
        kx = b.h(LR('calf_l', s)).x
        kp = GM.patch_on(trb, (kx + sg * 0.004, 0, knee_z + 0.015), (1, 0, 0), (0, 0, 1), 0.052, 0.072, (0, 1, 0), 0.0025,
                         nu=7, nv=9, round_r=0.018, name='knee_' + s)
        GM.thicken(kp, 0.002, offset=1.0)
        kit.add('knee_' + s, kp, m_knee, atlas='cloth', role='tint2', weight=('transfer', dict(smooth_iters=2)), edge_w=0.012)

    # ------------------------------------------------------------------ work shirt (open, sleeves rolled)
    roll_x = abs(L['elbow_l'].x) + ROLL_DX

    def keep_sh(c, bn):
        if bn in ('spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'):
            return True
        if bn == 'neck_01':
            return c.z < neck.z - 0.01
        if bn == 'pelvis':
            return c.z > 0.985
        if bn in GM.ARM_UP:
            return True
        if bn in GM.ARM_LO:
            return abs(c.x) < roll_x + 0.005
        return False
    sh = G.body_layer(b, keep_sh, 0.021, 'shirt', smooth=10, stack=st, clearance=0.011)
    G.bridge_torso(sh, b, 0.024, 0.99, chest.z + 0.12, stack=st)
    G.loosen(sh, lambda co: 0.007 * smooth01(abs(co.x), 0.26, 0.42) + 0.006 * (1 - smooth01(abs(co.x), 0.16, 0.24)) *
             smooth01(co.z, 1.25, 1.05))

    def open_w(z):
        return lerp(0.088, 0.046, smooth01(z, 1.0, 1.43))
    G.delete_faces(sh, lambda c: c.y < 0 and abs(c.x) < open_w(c.z))
    G.delete_faces(sh, lambda c: c.z > neck.z - 0.028 and abs(c.x) < 0.082 and c.y < 0.07)
    G.relax_boundary(sh, lambda pts: True, iters=8, factor=0.5)
    me = sh.data
    for v in me.vertices:          # open panels hang off the chest
        p = v.co
        if p.y < 0.02 and abs(p.x) < 0.2:
            d = abs(p.x) - open_w(p.z)
            k = 1 - smooth01(d, 0.0, 0.06)
            p.y -= 0.011 * k * smooth01(p.z, 1.45, 1.25)
            p.x += math.copysign(0.005 * k, p.x)
    me.update()
    dj.push_out(sh, st.bvh(), 0.011, iters=5)
    kit.add('shirt', sh, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=4)), edge_w=0.025)
    hem = G.hem_tube(sh, 0.0042, 0.55, sides=4, name='shirt_hem', pred=lambda l: max(abs(p.x) for p in l[0]) < 0.4)
    kit.add('shirt_hem', hem, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge=False,
            collide=False)
    tails = G.skirt(b, st, 1.0, 0.815, 'shirt_tails', off=0.03, off_top=0.022, top_band=0.06, flare=0.016, nu=7, nv=40,
                    tatter=0.0, seed=1.7, front_open=0.42, side_slit=0.1, hem_wave=0.004)
    kit.add('shirt_tails', tails, m_shirt, atlas='cloth', role='tint1', weight=G.skirt_weights(b, softness=0.6, pelvis_min=0.3),
            edge_w=0.03)
    them = G.hem_tube(tails, 0.0042, 0.55, sides=4, name='tails_hem', pred=lambda l: min(p.z for p in l[0]) < 0.9)
    kit.add('tails_hem', them, m_shirt, atlas='cloth', role='tint1', weight=G.skirt_weights(b, softness=0.6, pelvis_min=0.3),
            edge=False, collide=False)
    collar = GM.shirt_collar(b, st.bvh(), 'collar', z_back=neck.z + 0.002, z_front=neck.z - 0.085, gap=0.5, stand=0.026,
                             fall=0.03, point=0.045, off=0.004, thick=0.003, flare=0.008, nu=30, nv=6)
    dj.push_out(collar, st.bvh(), 0.004, iters=3)
    kit.add('collar', collar, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=3)), edge_w=0.02)
    shb = dj.bvh_from([sh])
    for sx in (-1, 1):
        pk = GM.patch_on(shb, (sx * 0.102, 0, 1.285), (1, 0, 0), (0, 0, 1), 0.052, 0.062, (0, 1, 0), 0.0028, nu=6, nv=7,
                         round_r=0.008, name='pocket')
        GM.thicken(pk, 0.0025)
        kit.add('pocket', pk, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge_w=0.01,
                collide=False)
        fl = GM.patch_on(shb, (sx * 0.102, 0, 1.352), (1, 0, 0), (0, 0, 1), 0.056, 0.019, (0, 1, 0), 0.0065, nu=6, nv=3,
                         round_r=0.006, name='flap')
        GM.thicken(fl, 0.003)
        kit.add('flap', fl, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge_w=0.01,
                collide=False)
    # buttons: down the wearer's right panel edge and on the pocket flaps
    mb = MB()
    for z in (1.05, 1.14, 1.23, 1.32, 1.41):
        x = -(open_w(z) + 0.016)
        loc, nrm, i, d = shb.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)), 1.0)
        if loc is not None:
            GM.cyl_between(mb, loc + nrm * 0.0005, loc + nrm * 0.0035, 0.0065, segs=10)
    for sx in (-1, 1):
        loc, nrm, i, d = shb.ray_cast(Vector((sx * 0.102, -0.5, 1.345)), Vector((0, 1, 0)), 1.0)
        if loc is not None:
            GM.cyl_between(mb, loc + nrm * 0.006, loc + nrm * 0.0095, 0.0058, segs=10)
    kit.add('buttons', mb.to_object('buttons'), m_btn, weight=('transfer', dict(smooth_iters=1)), edge=False, collide=False)
    # rolled sleeves
    for s in 'lr':
        el, wr = b.h(LR('lowerarm_l', s)), b.h(LR('hand_l', s))
        t = (roll_x - abs(el.x)) / abs(wr.x - el.x)
        c = el.lerp(wr, t)
        cuff = GM.roll_cuff(st.bvh(), c, (wr - el), up=(0, 0, 1), width=0.052, thick=0.017, off=0.003, n=30,
                            name='cuff_' + s, seed=3 if s == 'l' else 8)
        kit.add('cuff_' + s, cuff, m_shirt, atlas='cloth', role='tint1', weight=('transfer', dict(smooth_iters=2)), edge=False)
    # "3C" patch on the left shoulder (top of the arm in the T-pose rest: text up = toward the neck, reads along +Y)
    hu, hv = 0.036, 0.03
    img = GM.stroke_image('joe_3c', 2 * hu, 2 * hv, GM.text_strokes('3C', hu, 0.2 * 2 * hv, 0.6 * 2 * hv, width_frac=0.16,
                                                                     spacing=0.82), res=256)
    m_patch = kit.mat('patch', K.emblem_fabric, '#d8681c', '#f3e6c6', img, 'aux', '#5e2a0e')
    shoulder_x = abs(L['shoulder_l'].x) + 0.085
    arm_z = L['shoulder_l'].z
    pt = GM.patch_on(st.bvh(), (shoulder_x, L['shoulder_l'].y - 0.012, arm_z + 0.1), (0, 1, 0), (-1, 0, 0), hu, hv,
                     (0, 0, -1), 0.0025, nu=8, nv=8, round_r=0.012, name='patch3c')
    GM.thicken(pt, 0.0022)
    kit.add('patch3c', pt, m_patch, weight=('transfer', dict(smooth_iters=2)), edge=False, collide=False, uvw=6.0)

    # ------------------------------------------------------------------ tool belt over the shirt
    zb = 0.99
    belt, bpts = G.belt(st.bvh(), Vector((0, 0.02, zb)), 'toolbelt', width=0.058, thick=0.011, off=0.004, n=56,
                        tilt=lambda p: -0.012 * smooth01(-p.x, -0.02, 0.16))
    kit.add('toolbelt', belt, m_belt, weight=('transfer', dict(smooth_iters=2)), edge=False)
    front = min(bpts, key=lambda p: p.y + abs(p.x) * 0.8)
    bk = GM.buckle(front + Vector((0, -0.007, 0)), (0, -1, 0), (0, 0, 1), w=0.066, h=0.058, bar=0.009, depth=0.006)
    kit.add('buckle', bk, m_steel, weight={'pelvis': 1.0}, edge=False, collide=False)

    def belt_at(th):            # th: 0 front, +90 his left
        d = Vector((math.sin(math.radians(th)), -math.cos(math.radians(th)), 0))
        best = max(bpts, key=lambda p: Vector((p.x, p.y - 0.02, 0)).normalized().dot(d))
        return best, d
    # pouch on the left hip with a screwdriver and pliers
    pp, pd = belt_at(62)
    tang = Vector((0, 0, 1)).cross(pd).normalized()
    M3 = Matrix((tang, pd, Vector((0, 0, 1)))).transposed()      # x along the belt, y out, z up
    pc = pp + pd * 0.03 + Vector((0, 0, -0.045))
    mbp = MB()
    GM.rounded_box(mbp, pc, (0.105, 0.05, 0.12), M3, bevel=0.012, segs=2)
    GM.rounded_box(mbp, pc + M3 @ Vector((0, 0.006, 0.052)), (0.112, 0.056, 0.03), M3, bevel=0.01, segs=2)
    pouch = mbp.to_object('pouch')
    wpouch = {'pelvis': 0.65, 'thigh_l': 0.35}
    kit.add('pouch', pouch, m_belt, weight=wpouch, edge=False)
    mbt = MB()
    a = pc + M3 @ Vector((-0.03, -0.006, 0.06))
    GM.cyl_between(mbt, a, a + M3 @ Vector((-0.012, 0.004, 0.075)), 0.0115, segs=10, r2=0.01)
    tools_r = mbt.to_object('screwdriver')
    kit.add('screwdriver', tools_r, m_red, weight=wpouch, edge=False, collide=False)
    mbs = MB()
    tip = a + M3 @ Vector((-0.012, 0.004, 0.075))
    GM.cyl_between(mbs, tip, tip + M3 @ Vector((-0.002, 0.0, 0.012)), 0.004, segs=8)
    for k in (-1, 1):
        q0 = pc + M3 @ Vector((0.024 + 0.006 * k, -0.004, 0.055))
        GM.cyl_between(mbs, q0, q0 + M3 @ Vector((0.012 * k + 0.008, 0.002, 0.07)), 0.0055, segs=7, r2=0.0045)
    pl = mbs.to_object('pliers')
    kit.add('pliers', pl, m_yel, weight=wpouch, edge=False, collide=False)
    # ring holster + flashlight on the right hip (lens glows)
    hp, hd = belt_at(-112)
    loc, nrm, i, d = b.bvh.ray_cast(Vector((-0.5, 0.0, 0.9)), Vector((1, 0, 0)), 1.0)
    hip_x = loc.x if loc is not None else -0.19
    fl_c = Vector((hip_x - 0.075, 0.05, 0.86))
    ax = Vector((-0.25, -0.42, 0.87)).normalized()      # head up, tipped out and forward: the lit lens shows
    mbf = MB()
    head_top = fl_c + ax * 0.12
    GM.cyl_between(mbf, fl_c - ax * 0.13, fl_c + ax * 0.045, 0.0175, segs=14)                   # body (knurled)
    GM.cyl_between(mbf, fl_c - ax * 0.145, fl_c - ax * 0.13, 0.0165, segs=14)                   # tail cap
    GM.cyl_between(mbf, fl_c + ax * 0.045, fl_c + ax * 0.08, 0.0185, segs=14, r2=0.025)         # neck flare
    GM.cyl_between(mbf, fl_c + ax * 0.08, head_top, 0.026, segs=16)                             # head
    GM.cyl_between(mbf, head_top - ax * 0.002, head_top + ax * 0.008, 0.0275, segs=16)          # bezel ring
    flash = mbf.to_object('flashlight')
    mbl = MB()
    GM.cyl_between(mbl, head_top + ax * 0.003, head_top + ax * 0.0065, 0.0225, segs=16)
    lens = mbl.to_object('lens')
    whol = {'pelvis': 0.6, 'thigh_r': 0.4}
    kit.add('flashlight', flash, m_flash, weight=whol, edge=False)
    kit.add('lens', lens, m_lens, weight=whol, edge=False, collide=False, uvw=3.0)
    mbh = MB()
    ring_c = fl_c + ax * 0.02
    mbh.lathe([(0.0215, -0.012), (0.0235, -0.012), (0.0235, 0.012), (0.0215, 0.012)], 16, GM.placed_m(GM.frame3(ax), ring_c))
    strap_top = hp + Vector((0, 0, 0.01)) + hd * 0.004
    mbh.sweep([strap_top, strap_top + Vector((0, 0, -0.04)) + hd * 0.012, ring_c + Vector((0.012, 0.012, 0.015)),
               ring_c + Vector((0.02, 0.0, -0.004))], [(0.016, 0.003)] * 4, sides=4, rot=math.pi / 4, cap0='flat', cap1='flat')
    holster = mbh.to_object('holster')
    kit.add('holster', holster, m_belt, weight=whol, edge=False)
    # key on an orange lanyard (left front of the belt)
    kp0, kd0 = belt_at(28)
    ka = kp0 + kd0 * 0.006 + Vector((0, 0, -0.012))
    key_c = ka + kd0 * 0.012 + Vector((0.004, 0, -0.085))
    mbk = MB()
    lpath = [ka, ka + kd0 * 0.01 + Vector((0, 0, -0.03)), key_c + kd0 * 0.004 + Vector((-0.004, 0, 0.03)), key_c + Vector((0, 0, 0.012))]
    mbk.sweep(lpath, [(0.006, 0.0018)] * 4, sides=4, rot=math.pi / 4, up=kd0, cap0='flat', cap1='flat')
    lan = mbk.to_object('lanyard')
    wkey = {'pelvis': 0.6, 'thigh_l': 0.4}
    kit.add('lanyard', lan, m_lan, weight=wkey, edge=False, collide=False)
    mbk2 = MB()
    Mk = GM.frame3(kd0)          # key lies flat facing out
    ring_m = GM.placed_m(Mk, key_c + Vector((0, 0, 0.004)))
    mbk2.lathe([(0.009, -0.0015), (0.013, -0.0015), (0.013, 0.0015), (0.009, 0.0015)], 14, ring_m)
    blade_c = key_c + Vector((0, 0, -0.02))
    GM.rounded_box(mbk2, blade_c, (0.009, 0.0025, 0.034), None, bevel=0.0008, segs=1)
    for k in range(3):
        GM.rounded_box(mbk2, blade_c + Vector((0.006, 0, -0.012 + 0.008 * k)), (0.004, 0.0024, 0.004), None, bevel=0.0005, segs=1)
    key = mbk2.to_object('key')
    kit.add('key', key, m_brass, weight=wkey, edge=False, collide=False)

    # ------------------------------------------------------------------ duct-tape hand wraps
    # a tape shell over palm, back of the hand, wrist and knuckles, with a few overlapping strips on top so the
    # layered tape edges read (fingers and thumb tip stay bare)
    for s in 'lr':
        el = b.h(LR('lowerarm_l', s))
        hb = b.h(LR('hand_l', s))
        kn = b.h(LR('middle_01_l', s))
        a = (hb - el).normalized()
        h_ax = (kn - hb).normalized()
        sd = 1 if s == 'l' else 2
        shell = GM.tape_shell(b, st, s, 'tape_shell_' + s, off=0.0024, wrist_len=0.055, knuckle=0.013)
        kit.add('tape_shell_' + s, shell, m_tape, weight=('transfer', dict(smooth_iters=1)), edge_w=0.008)
        w1 = G.wraps(st.bvh(), hb - a * 0.05, hb + a * 0.004, 'tape_wrist_' + s, turns=2.2, width=0.034, thick=0.0016,
                     off=0.0006, up=(0, 0, 1), phase=0.4 * sd, jitter=0.0008, seed=sd, n_per_turn=22)
        kit.add('tape_wrist_' + s, w1, m_tape, weight=('transfer', dict(smooth_iters=1)), edge=False)
        w2 = G.wraps(st.bvh(), hb + h_ax * 0.01, kn - h_ax * 0.01, 'tape_hand_' + s, turns=1.6, width=0.034, thick=0.0016,
                     off=0.0006, up=(0, 0, 1), phase=1.9 * sd, jitter=0.0008, seed=sd + 4, n_per_turn=22)
        kit.add('tape_hand_' + s, w2, m_tape, weight=('transfer', dict(smooth_iters=1)), edge=False)

    # ------------------------------------------------------------------ hair, brows
    # Quaternius Hair_SimpleParted (Joe's look in Dungeon Joe 3D, its own strand texture), tousled hard with noise
    m_hairtex = kit.mat('hairtex', K.hair_tex, '#4e3322', light='#9a7048', rough=0.5)
    hair = GM.stock_hair(b, 'Hair_SimpleParted', 'hair', head_scale=1.08, tousle=0.01, lift=0.022, seed=3)
    kit.add('hair', hair, m_hairtex, weight='Head', edge=False, uvw=1.6)
    brows = b.brows
    brows.parent = None
    brows.modifiers.clear()
    shape_brows(b, brows, thick=1.35, stern=0.0015)
    kit.add('brows', brows, m_hair, weight='Head', edge=False, collide=False, uvw=2.0)
    b.meshes = [o for o in b.meshes if o is not brows]
    return F


def shape_brows(b, brows, thick=1.35, stern=0.0015):
    """bolder brows: thicken the brow strips vertically (the lashes in the same mesh stay as they are) and pull the
    inner ends down a touch for a determined look."""
    eye_z = (b.L['eye_l'].z + b.L['eye_r'].z) * 0.5
    me = brows.data
    co = np.array([list(v.co) for v in me.vertices])
    is_brow = co[:, 2] > eye_z + 0.011
    for s in (1, -1):
        sel = is_brow & ((co[:, 0] > 0) if s > 0 else (co[:, 0] <= 0))
        if not sel.any():
            continue
        cz = co[sel, 2].mean()
        for i in np.nonzero(sel)[0]:
            v = me.vertices[int(i)]
            inner = 1 - smooth01(abs(v.co.x), 0.012, 0.05)
            v.co.z = cz + (v.co.z - cz) * thick - stern * inner * 3
            v.co.y -= 0.0012
    me.update()


def straight_legs(b, ob):
    """trouser legs fall straight from the knee (no hugging the calf): push verts out to a tube."""
    me = ob.data
    me.update()
    for s in 'lr':
        sg = 1 if s == 'l' else -1
        kn = b.h(LR('calf_l', s))
        an = b.h(LR('foot_l', s))
        c_top = Vector((kn.x + sg * 0.004, kn.y + 0.004, kn.z))
        c_bot = Vector((an.x + sg * 0.008, an.y - 0.03, 0.10))
        vs = [v for v in me.vertices if v.co.x * sg > 0.02 and v.co.z < kn.z + 0.02]
        nb = 36
        rk = [0.0] * nb
        for v in vs:
            if abs(v.co.z - kn.z) < 0.03:
                d = v.co - c_top
                th = math.atan2(d.y, d.x)
                i = int((th + math.pi) / (2 * math.pi) * nb) % nb
                rk[i] = max(rk[i], math.hypot(d.x, d.y))
        for _ in range(3):
            rk = [max(rk[i], (rk[i - 1] + rk[(i + 1) % nb]) * 0.5) for i in range(nb)]
        for v in vs:
            t = smooth01(kn.z - v.co.z, 0.0, kn.z - 0.10)
            c = c_top.lerp(c_bot, (kn.z - v.co.z) / (kn.z - 0.10))
            d = Vector((v.co.x - c.x, v.co.y - c.y))
            th = math.atan2(d.y, d.x)
            i = int((th + math.pi) / (2 * math.pi) * nb) % nb
            rt = rk[i] * lerp(1.0, 0.86, t) + 0.004 * t
            r = d.length
            if r < rt:
                k = rt / max(r, 1e-6)
                v.co.x = c.x + d.x * k
                v.co.y = c.y + d.y * k
    me.update()


def skin_info():
    return dict(sex='m', skin='#b98058', feats=[('stubble', '#1b120a', 1.0), ('eyebags', 0.38), ('sunburn', 0.14),
                                              ('rosy', 0.1), ('kohl', '#24160f', 0.32), ('scar', 'cheek_l', 0.45)])


def quick_render(F, tag, factors):
    """EEVEE look at the procedural (unbaked) materials in the rest pose; the neutral tint surfaces are multiplied by
    their default colour as the game does."""
    import fpreview as P
    done = set()
    for p in F.kit.parts:
        if p.role in factors and p.mat.name not in done:
            done.add(p.mat.name)
            nt = p.mat.node_tree
            bs = nt.nodes['BSDF'].inputs['Base Color']
            if bs.is_linked:
                src = bs.links[0].from_socket
                mx = nt.nodes.new('ShaderNodeMix')
                mx.data_type = 'RGBA'
                mx.blend_type = 'MULTIPLY'
                ins = {s.identifier: s for s in mx.inputs}
                ins['Factor_Float'].default_value = 1.0
                nt.links.new(src, ins['A_Color'])
                ins['B_Color'].default_value = dj.srgb(factors[p.role])
                nt.links.new([s for s in mx.outputs if s.identifier == 'Result_Color'][0], bs)
    cam = P.studio(900)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'cyclorama' and not o.hide_render]
    pts = P.eval_points(meshes, 3)
    for view, az, el in (('front', 0, 6), ('threeq', -38, 12), ('side', -90, 4), ('back', 180, 8)):
        P.frame(cam, pts, az, el, lens=50, pad=1.05)
        P.render(os.path.join(F.work, '_geo_%s_%s.jpg' % (tag, view)))
    B = F.body.B

    def near(c, r):
        return pts[np.linalg.norm(pts - np.array(c), axis=1) < r]
    P.frame(cam, near(B.h('Head'), 0.2), -20, 6, lens=80, pad=1.1)
    P.render(os.path.join(F.work, '_geo_%s_face.jpg' % tag))
    hr = B.h('hand_r') + Vector((-0.06, 0, 0))
    P.frame(cam, near(hr, 0.13), -20, 35, lens=80, pad=1.1)
    P.render(os.path.join(F.work, '_geo_%s_hand.jpg' % tag))
    P.frame(cam, near((0, -0.05, 0.12), 0.25), -30, 15, lens=60, pad=1.1)
    P.render(os.path.join(F.work, '_geo_%s_boots.jpg' % tag))
    sh = B.h('upperarm_l') + Vector((0.08, 0, 0.05))
    cam.data.lens = 80
    cam.location = sh + Vector((0, 0, 0.45))
    cam.rotation_euler = Vector((0, 0, -1)).to_track_quat('-Z', 'X').to_euler()   # looking down, image up = -X
    P.render(os.path.join(F.work, '_geo_%s_patch.jpg' % tag))
    P.frame(cam, near((0, -0.05, 0.95), 0.3), -25, 10, lens=60, pad=1.1)
    P.render(os.path.join(F.work, '_geo_%s_belt.jpg' % tag))


def main():
    F = build()
    kit = F.kit
    kit.report()
    if '--geo' in ARGS:
        K.eye_material(F, hue_sat=(0.075, 0.85), iris_gain=0.6)
        quick_render(F, 'joe', {'tint1': SHIRT, 'tint2': TROUSERS})
        K.save_blend(F, 'geo')
        return
    # skin (whole body), eyes
    sk = K.skin_texture(F, skin_info())
    K.skin_material(F, sk, name='joe_skin')
    K.eye_material(F, hue_sat=(0.075, 0.85), iris_gain=0.6, name="joe_eyes")
    # remove body hidden under clothes (keeps head, neck, hands, bare forearms)
    covers = [p.ob for p in kit.parts if p.atlas == 'cloth' or p.name.startswith(('tank', 'boot', 'sole', 'trouser'))]

    def protect(co, bn):
        return bn in ('Head',) or bn.startswith(('hand_', 'index', 'middle', 'ring', 'pinky', 'thumb'))
    def force(co, bn):             # feet live inside the boots (their soles face the floor: no ray can prove it)
        return bn.startswith(('foot_', 'ball_')) or (bn.startswith('calf_') and co.z < 0.19)
    K.trim_body(F, covers, reach=0.12, dilate=2, protect=protect, force=force)
    K.save_blend(F, 'prebake')
    cloth = K.bake_atlas(F, 'cloth', {'tint1': ('tint1_joe_shirt', SHIRT, True), 'tint2': ('tint2_joe_trousers', TROUSERS, True)},
                         size=2048, samples=16, emission=False,
                         extra_occluders=[p.ob for p in kit.parts if p.atlas != 'cloth'])
    gear = K.bake_atlas(F, 'gear', {'gear': ('joe_gear', None, True)}, size=2048, samples=16, emission=True, emit_strength=5.0,
                        extra_occluders=[cloth])
    meshes = [F.body.mesh, F.body.eyes, cloth, gear]
    F.body.mesh.name = 'joe_body'
    F.body.eyes.name = 'joe_eyes'
    cloth.name = 'joe_cloth'
    gear.name = 'joe_gear'
    K.save_blend(F, 'final')
    src = os.path.join(F.work, 'joe_src.glb')
    K.export(F, meshes, src, scale=1.0)
    K.node(os.path.join(K.TOOLS, 'post.mjs'), src, json.dumps({'tint1_joe_shirt': SHIRT, 'tint2_joe_trousers': TROUSERS}))


if __name__ == '__main__':
    main()

"""fkit -- shared kit for the JoeBrawla human fighters (Joe, The Instructor) built on the Quaternius UBC
Superhero_Male body and its UAL 65-bone rig.

Pipeline (one build script per fighter):
  Fighter(...)            load the UBC body, enlarge head and hands (+8 %, bones scaled too), recompute landmarks
  kit.add(...)            garments / props: procedural geometry fitted to the body + procedural Cycles material,
                          an atlas group ('cloth' / 'gear'), a final-material role and a weight rule
  bake_atlas(...)         per group: weights, UV unwrap, one packed atlas, Cycles GPU bake of colour / roughness /
                          metal / normal (+ emission, + AO with the whole fighter as occluder) -> PBR materials
  skin_texture(...)       re-bake the body base colour with painted face character (stubble, scars ...)
  trim_body(...)          delete body faces hidden under clothing (no poke-through, fewer triangles)
  export(...)             one skinned GLB (armature node scaled to the fighter's height)
  post_glb (node)         base colour factors on tint1_ / tint2_ materials, report

Conventions (as djlib): metres, Blender Z-up, the character faces -Y (his left = +X); glTF export is Y-up, +Z
forward. Parts are built in world space with identity transforms.
"""
import bpy, bmesh, math, os, sys, random, json, time, subprocess
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler, noise
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import djlib as dj
import djarmor as ar
import agcore as C
import aggeo as G
import agmats as M
from djlib import MB, NB, srgb
from agcore import smooth01, lerp, LR

JB = r"C:\dev\JoeBrawla"
NODE = r"C:\Program Files\nodejs\node.exe"
TOOLS = os.path.join(os.path.dirname(HERE), 'tools')
UBC_TEX = dj.QUAT + r"\ubc\bodies"
EYES_DIR = dj.PROJ + r"\assets\custom\characters\eyes"
FINGER_PREFIX = ('index', 'middle', 'ring', 'pinky', 'thumb')
log = dj.log


def work_dir(fid):
    d = os.path.join(JB, 'art', '_work', fid)
    os.makedirs(d, exist_ok=True)
    return d


# ==============================================================================================
# body
# ==============================================================================================
class Fighter:
    def __init__(self, fid, head=1.08, hands=1.08):
        dj.reset()
        bpy.context.scene.render.fps = 30
        self.fid = fid
        self.work = work_dir(fid)
        dj.WORK = self.work
        C.WORK = self.work
        b = C.Body('m')
        self.body = b
        self.arm = b.arm
        for o in b.meshes:
            assert o.matrix_world == Matrix.Identity(4) or True
        # weld the glTF seam splits (UVs live on loops, so nothing is lost) -> smooth shading without seams
        for o in b.meshes:
            dj.activate(o)
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bm.to_mesh(o.data)
            bm.free()
            try:
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            except Exception:
                pass
            o.data.shade_smooth()
        self.refresh()
        if head != 1.0 or hands != 1.0:
            self.enlarge(head, hands)
        self.kit = Kit(self)

    def refresh(self):
        b = self.body
        b.B = dj.Bones(b.arm)
        b.bvh = dj.bvh_from([b.mesh])
        b.ws = dj.WeightSource(b.mesh)
        b.W = dj.read_weights(b.mesh)
        b.dom = [max(w.items(), key=lambda kv: kv[1])[0] if w else '' for w in b.W]
        mw = b.mesh.matrix_world
        b.mesh.data.update()
        b.co = [mw @ v.co for v in b.mesh.data.vertices]
        b.nrm = [(mw.to_3x3() @ v.normal).normalized() for v in b.mesh.data.vertices]
        b._landmarks()
        self.L = b.L

    def enlarge(self, head=1.08, hands=1.08):
        """Fighting-game proportions: head and hands bigger. Mesh verts are scaled about the Head / wrist joints by
        their skin weight; finger bones (and the Head / hand tails) move with them so finger curls still bend at
        the knuckles. Rest rotations are unchanged (UAL clips play as before)."""
        b = self.body
        arm = b.arm
        piv_h = b.B.h('Head').copy()
        piv = {s: b.B.h('hand_' + s).copy() for s in 'lr'}
        hand_groups = {s: ['hand_' + s] + [n for n in b.B.names() if n.startswith(FINGER_PREFIX) and n.endswith('_' + s)]
                       for s in 'lr'}

        def scale_mesh(o, full_head=False):
            W = dj.read_weights(o)
            me = o.data
            for v, w in zip(me.vertices, W):
                p = v.co.copy()
                wh = 1.0 if full_head else w.get('Head', 0.0)
                if wh > 0:
                    p = piv_h + (p - piv_h) * (1 + (head - 1) * wh)
                if not full_head:
                    for s in 'lr':
                        ws = sum(w.get(g, 0.0) for g in hand_groups[s])
                        if ws > 0:
                            p = piv[s] + (p - piv[s]) * (1 + (hands - 1) * min(1.0, ws))
                v.co = p
            me.update()
        scale_mesh(b.mesh)
        for o in (b.eyes, b.brows):
            if o is not None:
                scale_mesh(o, full_head=True)
        dj.activate(arm)
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.data.edit_bones
        for s in 'lr':
            for n in hand_groups[s]:
                e = eb[n]
                if n != 'hand_' + s:
                    e.head = piv[s] + (e.head - piv[s]) * hands
                e.tail = piv[s] + (e.tail - piv[s]) * hands
        e = eb['Head']
        e.tail = piv_h + (e.tail - piv_h) * head
        bpy.ops.object.mode_set(mode='OBJECT')
        self.refresh()
        log('enlarged head x%.2f hands x%.2f -> top %.3f' % (head, hands, self.L['top']))

    def eye_mesh_info(self):
        b = self.body
        ev = np.array([list(v.co) for v in b.eyes.data.vertices])
        return ev


# ==============================================================================================
# parts
# ==============================================================================================
class Part:
    def __init__(self, name, ob, mat, atlas, role, weight, uvw):
        self.name, self.ob, self.mat, self.atlas, self.role, self.weight, self.uvw = name, ob, mat, atlas, role, weight, uvw


class Kit:
    def __init__(self, fighter):
        self.f = fighter
        self.body = fighter.body
        self.stack = C.Stack(fighter.body)
        self.parts = []
        self.mats = {}

    def mat(self, key, fn, *a, **kw):
        if key in self.mats:
            return self.mats[key]
        m = fn('%s_%s' % (self.f.fid, key), *a, **kw)
        self.mats[key] = m
        return m

    def add(self, name, ob, mat, atlas='gear', role='gear', weight=('transfer', {}), uvw=1.0, collide=True,
            edge=True, edge_w=0.03, prand=None):
        if ob is None:
            return None
        ob.name = self.f.fid + '__' + name
        G.ensure_attrs(ob, prand=prand, edge=edge, width=edge_w)
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        p = Part(name, ob, mat, atlas, role, weight, uvw)
        self.parts.append(p)
        if collide:
            self.stack.add(ob)
        return p

    def tris(self, atlas=None):
        return sum(dj.tri_count(p.ob) for p in self.parts if atlas is None or p.atlas == atlas)

    def report(self):
        rows = sorted(((dj.tri_count(p.ob), p.atlas, p.name) for p in self.parts), reverse=True)
        log('KIT parts', len(self.parts), 'tris', self.tris())
        for t, a, n in rows:
            log('   %6d  %-5s %s' % (t, a, n))


# ==============================================================================================
# weights
# ==============================================================================================
def apply_weights(ob, w, ws):
    if isinstance(w, str):
        dj.set_weights_rigid(ob, w)
    elif isinstance(w, dict):
        dj.set_weights_fn(ob, lambda co, w=w: dict(w))
    elif callable(w):
        dj.set_weights_fn(ob, w)
    elif isinstance(w, tuple) and w[0] == 'transfer':
        dj.transfer_weights(ob, ws, **(w[1] if len(w) > 1 else {}))
    else:
        raise ValueError(w)


def blend_weights(*pairs):
    """weight fn: sum of (fn_or_dict, factor) pairs."""
    def fn(co):
        out = {}
        for src, k in pairs:
            d = src(co) if callable(src) else src
            for b, x in d.items():
                out[b] = out.get(b, 0.0) + x * k
        return out
    return fn


# ==============================================================================================
# atlas bake
# ==============================================================================================
def _strip_uvs(me):
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])


def unwrap_part(ob, angle=55.0, weight=1.0, margin=0.004):
    """fresh 'atlas' UV (smart project, scaled by 3D area x weight) + an 'aux' layer (kept if the part had one:
    patch lettering), so every part carries the same UV layers in the same order before the join."""
    me = ob.data
    aux = None
    if 'aux' in me.uv_layers:
        aux = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers['aux'].data.foreach_get('uv', aux)
    _strip_uvs(me)
    uv = me.uv_layers.new(name='atlas')
    ax = me.uv_layers.new(name='aux')
    if aux is not None:
        ax.data.foreach_set('uv', aux)
    me.uv_layers.active = uv
    uv.active_render = True
    dj.activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    a3 = dj.mesh_area(ob)
    au = dj.uv_area(ob)
    if au > 0:
        s = math.sqrt(a3 / au) * math.sqrt(weight)
        for l in me.uv_layers.active.data:
            l.uv = l.uv * s


def _emit_channel(m):
    """CH_emit emission node = the BSDF's emission colour where its strength > 0, else black."""
    nt = m.node_tree
    n = nt.nodes.get('CH_emit')
    if n is not None:
        return n
    bsdf = nt.nodes.get('BSDF')
    n = nt.nodes.new('ShaderNodeEmission')
    n.name = 'CH_emit'
    if bsdf is not None and bsdf.inputs['Emission Strength'].default_value > 0:
        s = bsdf.inputs['Emission Color']
        if s.is_linked:
            nt.links.new(s.links[0].from_socket, n.inputs['Color'])
        else:
            n.inputs['Color'].default_value = s.default_value
    else:
        n.inputs['Color'].default_value = (0, 0, 0, 1)
    return n


def set_channel(mats, ch):
    for m in mats:
        nt = m.node_tree
        out = nt.nodes.get('OUT')
        if out is None:
            continue
        if ch == 'emit':
            src = _emit_channel(m).outputs[0]
        elif ch == 'bsdf':
            src = nt.nodes['BSDF'].outputs[0]
        else:
            src = nt.nodes['CH_' + ch].outputs[0]
        nt.links.new(src, out.inputs['Surface'])


def _gltf_out_group():
    ng = bpy.data.node_groups.get('glTF Material Output')
    if ng is None:
        ng = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        ng.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        ng.interface.new_socket('Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    return ng


def pbr_material(name, base, orm, normal, emit=None, emit_strength=1.0, double_sided=True, factor=None,
                 normal_strength=1.0):
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    tb = nt.nodes.new('ShaderNodeTexImage')
    tb.image = base
    nt.links.new(tb.outputs['Color'], p.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage')
    to.image = orm
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sp.inputs[0])
    nt.links.new(sp.outputs['Green'], p.inputs['Roughness'])
    nt.links.new(sp.outputs['Blue'], p.inputs['Metallic'])
    g = nt.nodes.new('ShaderNodeGroup')
    g.node_tree = _gltf_out_group()
    nt.links.new(sp.outputs['Red'], g.inputs['Occlusion'])
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = normal
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = normal_strength
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    if emit is not None:
        te = nt.nodes.new('ShaderNodeTexImage')
        te.image = emit
        nt.links.new(te.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = emit_strength
    m.use_backface_culling = not double_sided
    if factor:
        m['jb_factor'] = factor
    return m


def _img(name, size, non_color, fill):
    return dj.new_image(name, size, non_color, fill=fill)


def _px(img):
    a = np.empty(len(img.pixels), np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def _save_png(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def bake_atlas(fighter, atlas, roles, size=2048, samples=16, emission=False, emit_strength=4.0, ao=True,
               ao_dist=0.12, uv_angle=55.0, pack_margin=0.003, extra_occluders=(), name=None):
    """Bake all kit parts of `atlas` into one atlas. roles: {role: (material name, factor hex or None, double_sided)}.
    Returns the joined, skinned-ready object."""
    kit = fighter.kit
    body = fighter.body
    parts = [p for p in kit.parts if p.atlas == atlas]
    name = name or '%s_%s' % (fighter.fid, atlas)
    role_list = list(roles)
    los = []
    t0 = time.time()
    for p in parts:
        ob = p.ob
        if ob is None or len(ob.data.polygons) == 0:
            continue
        ob.hide_set(False)
        dj.apply_mods(ob)
        if ob.matrix_world != Matrix.Identity(4):
            ob.data.transform(ob.matrix_world)
            ob.matrix_world = Matrix.Identity(4)
        dj.triangulate(ob)
        apply_weights(ob, p.weight, body.ws)
        unwrap_part(ob, angle=uv_angle, weight=p.uvw)
        me = ob.data
        me.materials.clear()
        me.materials.append(p.mat)
        ra = me.attributes.get('role') or me.attributes.new('role', 'INT', 'FACE')
        ra.data.foreach_set('value', [role_list.index(p.role)] * len(me.polygons))
        los.append(ob)
    LO = dj.join(los, name)
    LO.data.uv_layers.active = LO.data.uv_layers['atlas']
    LO.data.uv_layers['atlas'].active_render = True
    dj.uv_pack(LO, pack_margin)
    log('atlas', name, 'tris', dj.tri_count(LO), 'parts', len(los), 'prep %.1fs' % (time.time() - t0))
    # ---- bake
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    dj.gpu_setup(samples)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    margin = max(8, size // 128)
    sc.render.bake.margin = margin
    imgs = {
        'color': _img(name + '_col', size, False, (0.5, 0.5, 0.5, 1)),
        'rough': _img(name + '_rough', size, True, (0.7, 0.7, 0.7, 1)),
        'metal': _img(name + '_metal', size, True, (0, 0, 0, 1)),
        'normal': _img(name + '_nrm', size, True, (0.5, 0.5, 1, 1)),
    }
    if emission:
        imgs['emit'] = _img(name + '_emit', size, False, (0, 0, 0, 1))
    if ao:
        imgs['ao'] = _img(name + '_ao', size, True, (1, 1, 1, 1))
    mats = [m for m in LO.data.materials if m]
    targets = {}
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'BAKE_TARGET'
        targets[m.name] = n
    occl = set([LO, body.mesh] + list(extra_occluders))
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = o not in occl
    dj.deselect_all()
    LO.select_set(True)
    bpy.context.view_layer.objects.active = LO
    passes = [('normal', 'NORMAL', 'bsdf'), ('color', 'EMIT', 'color'), ('rough', 'EMIT', 'rough'), ('metal', 'EMIT', 'metal')]
    if emission:
        passes.append(('emit', 'EMIT', 'emit'))
    if ao:
        passes.append(('ao', 'AO', 'bsdf'))
    for key, btype, ch in passes:
        set_channel(mats, ch)
        for m in mats:
            t = targets[m.name]
            t.image = imgs[key]
            m.node_tree.nodes.active = t
        t1 = time.time()
        kw = dict(type=btype, use_selected_to_active=False, margin=margin, use_clear=True, target='IMAGE_TEXTURES')
        if btype == 'NORMAL':
            kw.update(normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
        if btype == 'AO':
            if sc.world is None:
                sc.world = bpy.data.worlds.new('BakeWorld')
            sc.world.light_settings.distance = ao_dist
            sc.cycles.samples = max(64, samples)
        bpy.ops.object.bake(**kw)
        sc.cycles.samples = samples
        log('baked', name, key, '%.1fs' % (time.time() - t1))
    set_channel(mats, 'bsdf')
    for m in mats:
        n = m.node_tree.nodes.get('BAKE_TARGET')
        if n:
            m.node_tree.nodes.remove(n)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = False
    # ---- compose ORM, final images
    rough = _px(imgs['rough'])[:, :, 0]
    metal = _px(imgs['metal'])[:, :, 0]
    aoc = _px(imgs['ao'])[:, :, 0] if ao else np.ones_like(rough)
    aoc = 1.0 - 0.75 * (1.0 - aoc)            # soften: the baked colour already carries cavity darkening
    orm = np.ones((size, size, 4), np.float32)
    orm[:, :, 0] = aoc
    orm[:, :, 1] = np.clip(rough, 0.04, 1.0)
    orm[:, :, 2] = metal
    oimg = _img(name + '_ORM', size, True, (1, 1, 1, 1))
    oimg.pixels.foreach_set(orm.ravel())
    out = {'base': imgs['color'], 'orm': oimg, 'normal': imgs['normal'], 'emit': imgs.get('emit')}
    for k in ('base', 'orm', 'normal', 'emit'):
        im = out[k]
        if im is None:
            continue
        im.name = '%s_%s' % (name, {'base': 'BaseColor', 'orm': 'ORM', 'normal': 'Normal', 'emit': 'Emissive'}[k])
        _save_png(im, os.path.join(fighter.work, im.name + '.png'))
        im.pack()
    for k in ('rough', 'metal', 'ao'):
        if k in imgs:
            bpy.data.images.remove(imgs[k])
    # ---- final materials by role
    fm = []
    for r in role_list:
        mname, factor, ds = roles[r]
        fm.append(pbr_material(mname, out['base'], out['orm'], out['normal'], emit=out['emit'] if emission else None,
                               emit_strength=emit_strength, double_sided=ds, factor=factor))
    ra = [0] * len(LO.data.polygons)
    LO.data.attributes['role'].data.foreach_get('value', ra)
    used = sorted(set(ra))
    LO.data.materials.clear()
    for r in used:
        LO.data.materials.append(fm[r])
    LO.data.polygons.foreach_set('material_index', [used.index(r) for r in ra])
    for a in ('role', 'edge', 'prand', 'rest', 'grain', 'pid'):
        if a in LO.data.attributes:
            LO.data.attributes.remove(LO.data.attributes[a])
    if 'aux' in LO.data.uv_layers:
        LO.data.uv_layers.remove(LO.data.uv_layers['aux'])
    log('atlas done', name, '%.1fs' % (time.time() - t0))
    return LO


# ==============================================================================================
# skin
# ==============================================================================================
def skin_texture(fighter, info, size=2048):
    """Body base colour re-toned + painted face character (build_faces recipe), baked into the body's UVs."""
    import build_faces as BF
    body = fighter.body
    base = bpy.data.images.load(BF.BASE['m'])
    m = BF.build_material(body, info, base)
    if info.get('extra'):
        info['extra'](m)
    img = BF.bake(body, m, size, fighter.fid + '_skin_BaseColor')
    _save_png(img, os.path.join(fighter.work, img.name + '.png'))
    img.pack()
    bpy.data.materials.remove(m)
    return img


def skin_material(fighter, base_img, name=None, rough_gain=1.0, normal_strength=1.0):
    body = fighter.body
    nrm = bpy.data.images.load(os.path.join(UBC_TEX, 'T_Superhero_Male_Normal.png'))
    nrm.colorspace_settings.name = 'Non-Color'
    rgh = bpy.data.images.load(os.path.join(UBC_TEX, 'T_Superhero_Male_Roughness.png'))
    rgh.colorspace_settings.name = 'Non-Color'
    r = _px(rgh)
    w, h = rgh.size
    orm = np.ones((h, w, 4), np.float32)
    orm[:, :, 1] = np.clip(r[:, :, 0] * rough_gain, 0.05, 1.0)
    orm[:, :, 2] = 0.0
    oimg = _img(fighter.fid + '_skin_ORM', w, True, (1, 1, 1, 1))
    oimg.pixels.foreach_set(orm.ravel())
    oimg.pack()
    nimg = bpy.data.images.new(fighter.fid + '_skin_Normal', nrm.size[0], nrm.size[1], alpha=False)
    nimg.colorspace_settings.name = 'Non-Color'
    nimg.pixels.foreach_set(_px(nrm).ravel())
    nimg.pack()
    bpy.data.images.remove(nrm)
    bpy.data.images.remove(rgh)
    m = pbr_material(name or fighter.fid + '_skin', base_img, oimg, nimg, double_sided=False,
                     normal_strength=normal_strength)
    body.mesh.data.materials.clear()
    body.mesh.data.materials.append(m)
    me = body.mesh.data
    me.uv_layers.active_index = 0
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    return m


def eye_material(fighter, hue_sat=None, name=None, size=512, iris_gain=1.0):
    """UBC eye texture, iris recoloured (hue, saturation) and brightened so the eyes read from afar."""
    import colorsys
    src = bpy.data.images.load(os.path.join(UBC_TEX, 'T_Eye_Brown.png'))
    w, h = src.size
    px = _px(src).copy()
    rgb = px[..., :3]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    s = (mx - mn) / np.maximum(mx, 1e-4)
    iris = (s > 0.25) & (mx < 0.85)
    if hue_sat:
        hue, sat = hue_sat
        for (y, x) in zip(*np.nonzero(iris)):
            r_, g_, b_ = rgb[y, x]
            H, S, V = colorsys.rgb_to_hsv(r_, g_, b_)
            rgb[y, x] = colorsys.hsv_to_rgb(hue, min(1.0, S * sat), min(1.0, V * 1.15 * iris_gain))
    px[..., :3] = rgb
    img = bpy.data.images.new((name or fighter.fid + '_eyes') + '_BaseColor', w, h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    if w < size:
        img.scale(size, size)
    img.pack()
    bpy.data.images.remove(src)
    m = bpy.data.materials.new(name or fighter.fid + '_eyes')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get('Principled BSDF')
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.12
    p.inputs['Specular IOR Level'].default_value = 0.6
    eyes = fighter.body.eyes
    eyes.data.materials.clear()
    eyes.data.materials.append(m)
    me = eyes.data
    me.uv_layers.active_index = 0
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    return m


# ==============================================================================================
# body trimming
# ==============================================================================================
def trim_body(fighter, covers, reach=0.12, dilate=2, protect=None, need=5, force=None):
    """Delete body faces fully hidden under `covers` (5 rays: the normal + 4 tilted must all hit within reach).
    protect(co, dominant_bone) -> True keeps a vertex whatever the rays say; force(co, bone) -> True removes it
    (feet inside boots: their soles face the floor, where no ray can hit the boot)."""
    body = fighter.body
    ob = body.mesh
    bvh = dj.bvh_from(covers)
    me = ob.data
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    W = dj.read_weights(ob)
    dom = [max(w.items(), key=lambda kv: kv[1])[0] if w else '' for w in W]
    keep = []
    forced = set()
    for v in bm.verts:
        p, n = v.co, v.normal
        if protect and protect(p, dom[v.index]):
            keep.append(True)
            continue
        if force and force(p, dom[v.index]):
            keep.append(False)
            forced.add(v.index)
            continue
        t = n.orthogonal().normalized()
        u = n.cross(t)
        hits = 0
        for d in (n, (n + t * 0.45).normalized(), (n - t * 0.45).normalized(), (n + u * 0.45).normalized(),
                  (n - u * 0.45).normalized()):
            loc, nrm, idx, dd = bvh.ray_cast(p + d * 0.0015, d, reach)
            if loc is not None:
                hits += 1
        keep.append(hits < need)
    for _ in range(dilate):
        k2 = list(keep)
        for e in bm.edges:
            a, b = e.verts
            if keep[a.index] or keep[b.index]:
                k2[a.index] = k2[b.index] = True
        keep = k2
    for i in forced:
        keep[i] = False
    kill = [f for f in bm.faces if not any(keep[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    log('trim body: removed %d faces, %d tris left' % (len(kill), dj.tri_count(ob)))
    return len(kill)


# ==============================================================================================
# geometry helpers
# ==============================================================================================
def surface_ray(bvh, origin, d, maxd=1.0):
    loc, nrm, idx, dist = bvh.ray_cast(Vector(origin), Vector(d).normalized(), maxd)
    return loc, nrm


def project_patch(bvh, center, axis_u, axis_v, half_u, half_v, toward, off, nu=8, nv=8, round_r=0.0, name='patch',
                  far=0.3):
    """A rectangular (optionally rounded) patch draped on the outermost surface of bvh: grid in the plane
    (center, axis_u, axis_v), each point ray cast along `toward` (from outside) and lifted by `off`. Stores an
    'aux' UV (0..1 across the patch)."""
    c = Vector(center)
    U = Vector(axis_u).normalized()
    Vv = Vector(axis_v).normalized()
    T = Vector(toward).normalized()

    def fn(a, b):
        x = (a - 0.5) * 2
        y = (b - 0.5) * 2
        if round_r > 0:
            # squash the corners toward a rounded rectangle
            rx = max(0.0, abs(x) * half_u - (half_u - round_r))
            ry = max(0.0, abs(y) * half_v - (half_v - round_r))
            d = math.hypot(rx, ry)
            if d > round_r:
                k = round_r / d
                xs = math.copysign((half_u - round_r) + rx * k, x) / half_u if rx > 0 else x
                ys = math.copysign((half_v - round_r) + ry * k, y) / half_v if ry > 0 else y
                x, y = xs, ys
        p = c + U * (x * half_u) + Vv * (y * half_v)
        loc, nrm, idx, dist = bvh.ray_cast(p - T * far, T, far * 2)
        if loc is None:
            return p
        return loc - T * off
    mb = MB()
    uvs = []
    G_ = mb.grid(lambda u, v: fn(u, v), nu, nv)
    ob = mb.to_object(name)
    return ob


def lathe_obj(name, prof, segs, M4, close_top=True, close_bot=True):
    mb = MB()
    mb.lathe(prof, segs, M4, close_top=close_top, close_bot=close_bot)
    return mb.to_object(name)


def frame_from(axis, up):
    a = Vector(axis).normalized()
    u = Vector(up)
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    # columns: X = v, Y = u, Z = a
    M3 = Matrix((v, u, a)).transposed()
    return M3


def placed(M3, origin):
    M4 = M3.to_4x4()
    M4.translation = Vector(origin)
    return M4


def bez(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = Vector(p0), Vector(p1), Vector(p2), Vector(p3)
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3)
    return out


def clump(mb, pts, r0, r1, flat=0.6, sides=5, cap1='round'):
    n = len(pts)
    radii = []
    for i in range(n):
        t = (i / (n - 1)) ** 0.85
        r = lerp(r0, r1, t)
        radii.append((r, r * flat))
    mb.sweep(pts, radii, sides=sides, cap0='flat', cap1=cap1, cap_segs=1)


# ==============================================================================================
# materials (extra procedural looks; all follow djlib NB.finish so they bake)
# ==============================================================================================
def duct_tape(name, col='#9fa3a6'):
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = M.pal(col, 0.16)
    n1 = nb.noise(co, 9.0, 4, 0.6)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.8, l)])
    # woven scrim under the film: fine grid
    gx = nb.wave(co, 520.0, 0.0, 0.0, 'BANDS', 'X', 'SIN')
    gz = nb.wave(co, 520.0, 0.0, 0.0, 'BANDS', 'Z', 'SIN')
    gy = nb.wave(co, 520.0, 0.0, 0.0, 'BANDS', 'Y', 'SIN')
    grid = nb.mr(nb.mx(nb.mx(gx, gz), gy), 0.75, 1.0, 0.0, 1.0)
    c = nb.mix(nb.mul(grid, 0.12), c, srgb('#5a5e62'))
    # wrinkles / creases
    wr = nb.noise(nb.mapping(co, scale=(1, 1, 5)), 60.0, 4, 0.65)
    crease = nb.mr(wr, 0.6, 0.7, 0.0, 1.0)
    c = nb.mix(nb.mul(crease, 0.35), c, srgb('#e6e8ea'))
    cav = M.cavity(nb, 0.012)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#26282a'))
    e = M.edge_attr(nb, 0.3, 1.0)
    grime = nb.mr(nb.noise(co, 30.0, 5, 0.6), 0.45, 0.7, 0.0, 1.0)
    c = nb.mix(nb.mul(nb.mx(e, nb.mul(grime, 0.5)), 0.4), c, srgb('#3a3632'))
    r = nb.add(0.32, nb.mul(nb.add(grime, crease), 0.18))
    height = nb.add(nb.mul(grid, 0.25), nb.mul(wr, 1.2))
    nrm = nb.bump(height, 0.35, 0.0015)
    nb.finish(c, r, 0.35, nrm)
    return m


def rubber_sole(name, col='#2b2420'):
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = M.pal(col, 0.15)
    n1 = nb.noise(co, 14.0, 4, 0.6)
    c = nb.ramp(n1, [(0.3, d), (0.55, b), (0.8, l)])
    # lugs on the tread, ribs on the sides
    lug = nb.voronoi(nb.mapping(co, scale=(1, 0.6, 1)), 55.0, 'F1', out='Distance', rand=0.2)
    lugm = nb.mr(lug, 0.3, 0.45, 1.0, 0.0)
    rib = nb.wave(co, 150.0, 0.0, 0.0, 'BANDS', 'Z', 'SIN')
    down = nb.mr(nb.sep(nb.geo('Normal'))[2], -0.3, -0.8, 0.0, 1.0)
    cav = M.cavity(nb, 0.01)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#0d0b0a'))
    dirt = nb.mr(nb.noise(co, 20.0, 5, 0.6), 0.4, 0.7, 0.0, 1.0)
    c = nb.mix(nb.mul(dirt, 0.35), c, srgb('#6a5a48'))
    height = nb.add(nb.mul(nb.mul(lugm, down), 1.0), nb.mul(nb.mul(rib, nb.inv(down)), 0.25))
    nrm = nb.bump(height, 0.6, 0.002)
    nb.finish(c, nb.add(0.78, nb.mul(dirt, 0.1)), 0.0, nrm)
    return m


def hair_mat(name, col='#4a3020', light=None, rough=0.5, strand_scale=(70, 70, 9), sheen=0.25):
    """Strand-clump hair (coloured). Lighter tips, darker roots / cavities."""
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = M.pal(col, 0.3, 0.1)
    if light:
        l = srgb(light)
    strands = nb.noise(nb.mapping(co, scale=strand_scale), 5.0, 6, 0.72)
    fine = nb.noise(nb.mapping(co, scale=(240, 240, 30)), 4.0, 4, 0.6)
    c = nb.ramp(strands, [(0.2, d), (0.5, b), (0.78, l)])
    c = nb.mix(nb.mul(nb.mr(fine, 0.5, 0.8, 0.0, 1.0), 0.25), c, l)
    cav = M.cavity(nb, 0.015)
    c = nb.mix(nb.mul(cav, 0.75), c, srgb('#0e0a08'))
    tip = M.edge_attr(nb, 0.0, 1.0)
    r = nb.add(rough, nb.mul(nb.sub(strands, 0.5), 0.2))
    height = nb.add(strands, nb.mul(fine, 0.4))
    nrm = nb.bump(height, 0.8, 0.0025)
    nb.finish(c, r, 0.0, nrm)
    return m


def emblem_fabric(name, base_col, ink_col, img, uvname='aux', border='#6a3a1a'):
    """Patch fabric: base colour + embroidered glyph image (stroke image on the 'aux' UV) + stitched border."""
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    d, b, l = M.pal(base_col, 0.18)
    n1 = nb.noise(co, 30.0, 4, 0.6)
    c = nb.ramp(n1, [(0.25, d), (0.55, b), (0.85, l)])
    wv = nb.mx(nb.wave(co, 380.0, 0.0, 0.0, 'BANDS', 'X'), nb.wave(co, 380.0, 0.0, 0.0, 'BANDS', 'Z'))
    c = nb.mix(nb.mul(wv, 0.12), c, srgb('#2a1a10'))
    uvn = nb.node('ShaderNodeUVMap', uv_map=uvname)
    t = nb.node('ShaderNodeTexImage')
    t.image = img
    t.extension = 'CLIP'
    nb.link(uvn.outputs[0], t.inputs[0])
    ink = nb.sep(t.outputs['Color'])[0] if False else None
    sep = nb.node('ShaderNodeSeparateColor')
    nb.link(t.outputs['Color'], sep.inputs[0])
    inkm = sep.outputs['Red']
    # thread lines across the glyph
    thr = nb.wave(co, 900.0, 0.0, 0.0, 'BANDS', 'Y')
    ink_c = nb.mix(nb.mul(thr, 0.25), srgb(ink_col), srgb(M.shade(ink_col, 0.75)))
    c = nb.mix(nb.mr(inkm, 0.3, 0.6, 0.0, 1.0), c, ink_c)
    # border stitch ring (uv distance from the edge)
    u, v, _ = nb.sep(uvn.outputs[0])
    du = nb.mn(u, nb.sub(1.0, u))
    dv = nb.mn(v, nb.sub(1.0, v))
    de = nb.mn(du, dv)
    ring = nb.mul(nb.mr(de, 0.02, 0.05, 1.0, 0.0), 1.0)
    c = nb.mix(nb.mul(ring, 0.9), c, srgb(border))
    fade = nb.mr(nb.noise(co, 18.0, 5, 0.6), 0.45, 0.75, 0.0, 1.0)
    c = nb.mix(nb.mul(fade, 0.25), c, srgb('#e8d8c0'))
    cav = M.cavity(nb, 0.01)
    c = nb.mix(nb.mul(cav, 0.5), c, srgb('#1a1008'))
    height = nb.add(nb.mul(nb.mr(inkm, 0.3, 0.6, 0.0, 1.0), 0.8), nb.mul(ring, 0.6))
    height = nb.add(height, nb.mul(wv, 0.15))
    nrm = nb.bump(height, 0.5, 0.0012)
    nb.finish(c, 0.85, 0.0, nrm)
    return m


def glow_mat(name, col, strength=4.0, base=None):
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    n = nb.noise(co, 40.0, 3, 0.5)
    e = nb.mix(nb.mr(n, 0.3, 0.8, 0, 1), srgb(M.shade(col, 0.85)), srgb(M.shade(col, 1.1, 0.85)))
    nb.finish(srgb(base or col), 0.15, 0.0, None, emit=e, emit_strength=strength)
    return m


def glass_lens(name, col='#fff3d6', strength=3.0):
    """flashlight lens: bright centre, reflector rings."""
    m = M._m(name)
    nb = NB(m)
    co = nb.coord('Object')
    rings = nb.wave(co, 260.0, 0.0, 0.0, 'RINGS', 'Y', 'SIN')
    e = nb.mix(nb.mul(nb.mr(rings, 0.3, 1.0, 0.0, 1.0), 0.35), srgb(col), srgb(M.shade(col, 0.7)))
    nb.finish(srgb(col), 0.08, 0.0, None, emit=e, emit_strength=strength)
    return m


# ==============================================================================================
# export
# ==============================================================================================
def export(fighter, meshes, path, scale=1.0):
    arm = fighter.arm
    arm.name = 'Armature'
    arm.data.name = 'Armature'
    for o in meshes:
        dj.limit_normalize(o, 4)
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        for m in list(o.modifiers):
            o.modifiers.remove(m)
        md = o.modifiers.new('Armature', 'ARMATURE')
        md.object = arm
    arm.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o not in meshes:
            o.hide_render = True
    dj.export_glb(path, meshes + [arm], skinned=True)
    return path


def node(script, *args):
    r = subprocess.run([NODE, script] + [str(a) for a in args], capture_output=True, text=True, cwd=JB)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise RuntimeError('node failed: ' + script)
    return r.stdout


def save_blend(fighter, tag):
    p = os.path.join(fighter.work, '%s_%s.blend' % (fighter.fid, tag))
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    log('saved', p)
    return p


def hair_tex(name, col='#4a3122', light='#8f6a46', tex='T_Hair_1', uvname='aux', rough=0.5, normal_strength=0.8):
    """stock Quaternius hair texture (grey strand clumps, its own UVs on 'aux') tinted to col; light = strand highlights."""
    m = M._m(name)
    nb = NB(m)
    uvn = nb.node('ShaderNodeUVMap', uv_map=uvname)
    tb = nb.node('ShaderNodeTexImage')
    tb.image = bpy.data.images.load(os.path.join(dj.QUAT, 'ubc', 'hair', tex + '_BaseColor.png'), check_existing=True)
    nb.link(uvn.outputs[0], tb.inputs[0])
    tn = nb.node('ShaderNodeTexImage')
    tn.image = bpy.data.images.load(os.path.join(dj.QUAT, 'ubc', 'hair', tex + '_Normal.png'), check_existing=True)
    tn.image.colorspace_settings.name = 'Non-Color'
    nb.link(uvn.outputs[0], tn.inputs[0])
    v = nb.bw(tb.outputs['Color']) if hasattr(nb, 'bw') else None
    bwn = nb.node('ShaderNodeRGBToBW')
    nb.link(tb.outputs['Color'], bwn.inputs[0])
    lum = bwn.outputs[0]
    c = nb.ramp(lum, [(0.05, srgb(M.shade(col, 0.45))), (0.35, srgb(col)), (0.75, srgb(light))])
    cav = M.cavity(nb, 0.015)
    c = nb.mix(nb.mul(cav, 0.6), c, srgb('#0c0806'))
    nm = nb.node('ShaderNodeNormalMap', uv_map=uvname)
    nm.inputs['Strength'].default_value = normal_strength
    nb.link(tn.outputs['Color'], nm.inputs['Color'])
    nb.finish(c, nb.add(rough, nb.mul(nb.sub(lum, 0.5), -0.2)), 0.0, nm.outputs['Normal'])
    return m

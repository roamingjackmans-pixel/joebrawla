"""JoeBrawla stage kit: shared helpers for the stage build scripts (art/stages/<id>/build_<id>.py).

Coordinates are Blender's: Z up, metres. The fighters stand on the line y = 0 (glTF z = 0), x in [-7.5, 7.5];
the game camera sits at y = -9.5 (glTF z = +9.5) and looks toward +Y. "Depth behind the fight" = +Y here
(= -Z in glTF). The exporter converts to glTF Y-up.

Pipeline of a build script:
    S = Stage('forge')                         # fresh scene, paths
    textures  -> tile groups (tiling PBR sets), palette, glow palette, backdrop
    protos    -> kit pieces (Quaternius / Kenney / KayKit CC0, DJ3D custom) and custom procedural props,
                 baked together into one 'props' atlas (S.bake_props)
    placement -> S.inst(proto, loc, rot, scale) and custom geometry tagged with S.add(ob, group)
    S.finalize()  -> world-space tiling UVs, vertex-colour AO bake (+ tints), join per material and shadow class,
                     keep-clear check, export <id>_src.glb, compress to public/assets/stages/<id>.glb, stats
    previews  -> preview.render(S.id)  (EEVEE + three.js-like post: sky dome, fog, bloom, ACES, sRGB)
"""
import bpy, bmesh, math, os, sys, json, time, random, subprocess, shutil
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dj_common as dj  # noqa: E402  (copy of the DJ3D prop helpers)
import dj_mats as djm   # noqa: E402,F401
import texgen as tg     # noqa: E402

JB = r"C:\dev\JoeBrawla"
DL = r"C:\dev\AverageJoe\_downloads"
FP = DL + r"\quaternius-fantasy-props-megakit\x\Exports\glTF"
MV = DL + r"\quaternius-medieval-village-megakit\x\Medieval Village MegaKit[Standard]\glTF"
MVT = DL + r"\quaternius-medieval-village-megakit\x\Medieval Village MegaKit[Standard]\Textures"
NAT = DL + r"\quaternius-stylized-nature-megakit\x\glTF"
KH = DL + r"\kaykit-halloween-bits\x\KayKit_HalloweenBits_1.0_FREE\Assets\gltf"
KF = DL + r"\kaykit-forest-nature-pack\x\KayKit_Forest_Nature_Pack_1.0_FREE\Assets\gltf"
KG = DL + r"\kenney-graveyard-kit\x\Models\GLB format"
DJP = r"C:\dev\AverageJoe\DungeonJoe3D\assets\custom\props"
DJH = r"C:\dev\AverageJoe\DungeonJoe3D\assets\custom\hub"


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def log(*a):
    print("[stagekit]", *a, flush=True)


# ============================================================================ geometry helpers
def apply_matrix(ob):
    """Bake the object transform into its (single-user) mesh."""
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    """Set an object transform (rot in degrees XYZ)."""
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    ob.matrix_world = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot], 'XYZ'), Vector(scale))
    return ob


def bbox(ob, world=True):
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    if world:
        M = np.array(ob.matrix_world, np.float32)
        co = co @ M[:3, :3].T + M[:3, 3]
    return co.min(0), co.max(0)


def plane_grid(name, x0, x1, y0, y1, nx, ny, z=0.0, fn=None):
    """Flat grid (nx x ny cells) at height z; fn(x, y) -> z offset optional."""
    def f(u, v):
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * v
        return (x, y, z + (fn(x, y) if fn else 0.0))
    ob = dj.grid(name, nx, ny, f, uv=False)
    return ob


def subdivide_long(ob, max_len=1.0, iters=4):
    """Split edges longer than max_len (keeps AO detail on big flat faces)."""
    for _ in range(iters):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        long_e = [e for e in bm.edges if e.calc_length() > max_len]
        if not long_e:
            bm.free()
            break
        bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bm.to_mesh(ob.data)
        bm.free()
    return ob


def merge(objs, name):
    objs = [o for o in objs if o is not None]
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
    return dj.join(objs, name)


# ============================================================================ the stage
class Stage:
    def __init__(self, sid, reset=True):
        self.id = sid
        self.dir = os.path.join(JB, 'art', 'stages', sid)
        self.work = os.path.join(JB, 'art', '_work', 'stages', sid)
        self.tex = os.path.join(self.work, 'tex')
        self.prev = os.path.join(self.dir, 'previews')
        for d in (self.dir, self.work, self.tex, self.prev):
            os.makedirs(d, exist_ok=True)
        self.src = os.path.join(self.work, f'{sid}_src.glb')
        self.out = os.path.join(JB, 'public', 'assets', 'stages', f'{sid}.glb')
        self.groups = {}       # name -> dict(kind, mat)
        self.protos = []
        self.kits = {}
        self.pal_names = []
        self.pal_spec = {}
        self.glow_names = []
        self.glow_spec = {}
        self.tint_fn = None
        self.notes = {}
        self.t0 = time.time()
        if reset:
            dj.reset()
        sc = bpy.context.scene
        self.col_set = self._coll('SET')
        self.col_proto = self._coll('PROTO')

    def _coll(self, name):
        c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if c.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(c)
        return c

    def _link(self, ob, coll):
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)

    # ------------------------------------------------------------------ material groups
    def tile_group(self, name, base, orm, normal, scale=2.0, emit=None, emit_strength=1.0, ao=0.55, double=False):
        """A tiling PBR material: base/orm/normal are numpy arrays (HxWx3, 0..1) or PNG paths. scale = metres per tile."""
        imgs = {}
        for key, arr, srgb in (('base', base, True), ('orm', orm, False), ('normal', normal, False), ('emit', emit, True)):
            if arr is None:
                continue
            p = arr if isinstance(arr, str) else tg.save_png(arr, os.path.join(self.tex, f'{name}_{key}.png'), srgb)
            im = bpy.data.images.load(p, check_existing=True)
            im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
            imgs[key] = im
        mat = dj.baked_material(name, imgs, emission_strength=emit_strength, double_sided=double)
        self.groups[name] = dict(kind='tile', mat=mat, scale=scale, ao=ao)
        return name

    def palette(self, name, entries, glow=False, strength=4.0, ao=0.6):
        """Flat-colour palette material. entries: [(key, '#hex', rough, metal)] (glow: [(key, '#hex', level)]).
        Each swatch is 8x8 px in a 128x128 texture; faces get UVs at swatch centres."""
        n = 16
        base = np.zeros((128, 128, 3), np.float32)
        orm = np.ones((128, 128, 3), np.float32)
        emit = np.zeros((128, 128, 3), np.float32)
        keys = {}
        for i, e in enumerate(entries):
            r, c = divmod(i, n)
            sl = (slice(r * 8, r * 8 + 8), slice(c * 8, c * 8 + 8))
            if glow:
                k, hx, lvl = e
                ecol = tg.hexrgb(hx)
                lin = tg.s2l(ecol) * lvl
                emit[sl] = tg.l2s(np.clip(lin, 0, 1))
                base[sl] = tg.l2s(tg.s2l(ecol) * 0.25)
                orm[sl] = (1.0, 0.45, 0.0)
            else:
                k, hx, rough, metal = e
                base[sl] = tg.hexrgb(hx)
                orm[sl] = (1.0, rough, metal)
            keys[k] = ((c * 8 + 4) / 128.0, (r * 8 + 4) / 128.0)
        imgs = {}
        tg.save_png(base, os.path.join(self.tex, f'{name}_base.png'), True)
        imgs['base'] = bpy.data.images.load(os.path.join(self.tex, f'{name}_base.png'))
        tg.save_png(orm, os.path.join(self.tex, f'{name}_orm.png'), False)
        imgs['orm'] = bpy.data.images.load(os.path.join(self.tex, f'{name}_orm.png'))
        imgs['orm'].colorspace_settings.name = 'Non-Color'
        flatn = np.zeros((8, 8, 3), np.float32) + (0.5, 0.5, 1.0)
        tg.save_png(flatn, os.path.join(self.tex, f'{name}_normal.png'), False)
        imgs['normal'] = bpy.data.images.load(os.path.join(self.tex, f'{name}_normal.png'))
        imgs['normal'].colorspace_settings.name = 'Non-Color'
        if glow:
            tg.save_png(emit, os.path.join(self.tex, f'{name}_emit.png'), True)
            imgs['emit'] = bpy.data.images.load(os.path.join(self.tex, f'{name}_emit.png'))
        for im in imgs.values():
            pass
        mat = dj.baked_material(name, imgs, emission_strength=strength if glow else 1.0)
        # palettes must not be filtered across swatches
        for nd in mat.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
        # palettes need no normal map: drop it (smaller file)
        nt = mat.node_tree
        for nd in list(nt.nodes):
            if nd.type == 'NORMAL_MAP' or (nd.type == 'TEX_IMAGE' and nd.image == imgs['normal']):
                nt.nodes.remove(nd)
        self.groups[name] = dict(kind='glow' if glow else 'pal', mat=mat, keys=keys, ao=0.0 if glow else ao)
        return name

    def emissive_tile(self, name, emit, base=None, scale=4.0, strength=4.0):
        """Tiling emissive material (lava, stained glass...)."""
        imgs = {}
        p = tg.save_png(emit, os.path.join(self.tex, f'{name}_emit.png'), True)
        imgs['emit'] = bpy.data.images.load(p)
        b = base if base is not None else np.asarray(emit) * 0.3
        p = tg.save_png(b, os.path.join(self.tex, f'{name}_base.png'), True)
        imgs['base'] = bpy.data.images.load(p)
        orm = np.ones((16, 16, 3), np.float32) * (1.0, 0.5, 0.0)
        p = tg.save_png(orm, os.path.join(self.tex, f'{name}_orm.png'), False)
        imgs['orm'] = bpy.data.images.load(p)
        imgs['orm'].colorspace_settings.name = 'Non-Color'
        flatn = np.zeros((8, 8, 3), np.float32) + (0.5, 0.5, 1.0)
        p = tg.save_png(flatn, os.path.join(self.tex, f'{name}_normal.png'), False)
        imgs['normal'] = bpy.data.images.load(p)
        imgs['normal'].colorspace_settings.name = 'Non-Color'
        mat = dj.baked_material(name, imgs, emission_strength=strength)
        nt = mat.node_tree
        for nd in list(nt.nodes):
            if nd.type == 'NORMAL_MAP' or (nd.type == 'TEX_IMAGE' and nd.image == imgs['normal']):
                nt.nodes.remove(nd)
        self.groups[name] = dict(kind='tile', mat=mat, scale=scale, ao=0.0)
        return name

    def backdrop_group(self, name, emit_arr, strength=1.0):
        p = tg.save_png(emit_arr, os.path.join(self.tex, f'{name}_emit.png'), True)
        im = bpy.data.images.load(p)
        mt = bpy.data.materials.new(name)
        nt = mt.node_tree
        N = nt.nodes
        N.clear()
        out = N.new('ShaderNodeOutputMaterial')
        b = N.new('ShaderNodeBsdfPrincipled')
        nt.links.new(b.outputs[0], out.inputs['Surface'])
        b.inputs['Base Color'].default_value = (0, 0, 0, 1)
        b.inputs['Roughness'].default_value = 1.0
        b.inputs['Specular IOR Level'].default_value = 0.0
        t = N.new('ShaderNodeTexImage')
        t.image = im
        t.extension = 'EXTEND'
        nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = strength
        mt.use_backface_culling = True
        self.groups[name] = dict(kind='backdrop', mat=mt, ao=0.0)
        return name

    # ------------------------------------------------------------------ tagging
    def add(self, ob, grp, shadow=None, tint=None, ao=None, key=None, uv_scale=None, uv_rot=0.0, uv_off=None):
        """Tag an object for the final assembly.
        grp: material group name. shadow: True/False/None (auto by position). tint: '#hex' multiplied into the vertex
        colour. key: palette/glow swatch. uv_scale: override metres per tile for tile groups."""
        if grp not in self.groups:
            raise KeyError(f'unknown group {grp}')
        ob['grp'] = grp
        if shadow is not None:
            ob['shadow'] = 1 if shadow else 0
        if tint:
            ob['tint'] = list(tg.s2l(tg.hexrgb(tint)))
        if ao is not None:
            ob['ao'] = ao
        if uv_scale:
            ob['uvs'] = uv_scale
        if uv_rot:
            ob['uvr'] = uv_rot
        if uv_off is not None:
            ob['uvo'] = list(uv_off)
        g = self.groups[grp]
        if g['kind'] in ('pal', 'glow'):
            if key is None:
                key = next(iter(g['keys']))
            self._uv_point(ob, g['keys'][key])
        if ob.name not in self.col_set.objects:
            self._link(ob, self.col_set)
        return ob

    def pal(self, ob, key, grp=None, **kw):
        grp = grp or next(n for n, g in self.groups.items() if g['kind'] == 'pal')
        return self.add(ob, grp, key=key, **kw)

    def glow(self, ob, key, grp=None, **kw):
        grp = grp or next(n for n, g in self.groups.items() if g['kind'] == 'glow')
        kw.setdefault('shadow', False)
        return self.add(ob, grp, key=key, **kw)

    def _uv_point(self, ob, uv):
        me = ob.data
        for l in list(me.uv_layers):
            me.uv_layers.remove(l)
        lay = me.uv_layers.new(name='atlas')
        a = np.tile(np.array(uv, np.float32), len(me.loops))
        lay.data.foreach_set('uv', a)

    # ------------------------------------------------------------------ kit pieces and protos
    def kit(self, path, name=None, scale=1.0, rot=(0, 0, 0), keep_mats=True):
        """Import a glTF/GLB once and return a single joined proto object (origin at the model origin)."""
        key = (path, scale, tuple(rot))
        if key in self.kits:
            return self.kits[key]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == 'MESH']
        for o in meshes:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            apply_matrix(o)
        for o in new:
            if o.type != 'MESH':
                bpy.data.objects.remove(o)
        for o in meshes:
            if o.data.shape_keys:
                o.shape_key_clear()
            for m in list(o.modifiers):
                o.modifiers.remove(m)
        nm = name or os.path.splitext(os.path.basename(path))[0]
        ob = merge(meshes, 'P_' + nm)
        if scale != 1.0 or any(rot):
            place(ob, (0, 0, 0), rot, scale)
            apply_matrix(ob)
        self._link(ob, self.col_proto)
        self.kits[key] = ob
        self.protos.append(ob)
        ob['kit'] = path
        return ob

    def proto(self, ob, weight=1.0):
        """Register a custom (procedural-material) object as a proto for the props atlas."""
        if ob.data.attributes.get('rest') is None:
            dj.store_rest(ob)
        self._link(ob, self.col_proto)
        ob['w'] = weight
        self.protos.append(ob)
        return ob

    def inst(self, proto, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, grp='props', **kw):
        ob = proto.copy()
        ob.name = proto.name[2:] if proto.name.startswith('P_') else proto.name
        self.col_set.objects.link(ob)
        place(ob, loc, rot, scale)
        ob['grp'] = grp
        for k, v in kw.items():
            if k == 'tint':
                ob['tint'] = list(tg.s2l(tg.hexrgb(v)))
            else:
                ob[k] = v
        return ob

    def bake_props(self, name='props', size=2048, samples=48, ao_dist=0.5, ao_strength=0.35, weights=None):
        """Unwrap all protos into one atlas, bake their materials (kit image materials and procedural dj materials)."""
        t0 = time.time()
        protos = [p for p in self.protos]
        # lay the protos out far away, apart from each other, so their AO is their own
        x = 0.0
        for p in protos:
            mn, mx = bbox(p, world=False)
            p.location = (x - mn[0], 2000.0, 0.0)
            x += (mx[0] - mn[0]) + 4.0
        for p in protos:
            for s in p.material_slots:
                m = s.material
                if m is not None and m.name not in dj.PROC:
                    KitMat(m)
            if p.data.attributes.get('rest') is None:
                dj.store_rest(p)
            dj.triangulate(p)
        # UVs: smart project, equalise texel density, weight heroes, pack
        for o in protos:
            me = o.data
            uv = me.uv_layers.get('atlas') or me.uv_layers.new(name='atlas')
            me.uv_layers.active = uv
            uv.active_render = True
        bpy.ops.object.select_all(action='DESELECT')
        for o in protos:
            o.select_set(True)
        bpy.context.view_layer.objects.active = protos[0]
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
        bpy.ops.object.mode_set(mode='OBJECT')
        for o in protos:
            w = float(o.get('w', 1.0))
            if w != 1.0:
                lay = o.data.uv_layers['atlas']
                a = np.empty(len(o.data.loops) * 2, np.float32)
                lay.data.foreach_get('uv', a)
                lay.data.foreach_set('uv', a * math.sqrt(w))
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.003, shape_method='CONCAVE')
        bpy.ops.object.mode_set(mode='OBJECT')
        imgs = dj.bake(protos, name, size=size, emission=False, ao_dist=ao_dist, samples=samples, ao_strength=ao_strength)
        # keep the textures with the stage
        for k, im in imgs.items():
            p = os.path.join(self.tex, f'{name}_{k}.png')
            im.filepath_raw = p
            im.file_format = 'PNG'
            im.save()
        mat = dj.baked_material(name, imgs)
        for o in protos:
            me = o.data
            me.materials.clear()
            me.materials.append(mat)
            me.polygons.foreach_set('material_index', np.zeros(len(me.polygons), np.int32))
            for uvl in list(me.uv_layers):
                if uvl.name != 'atlas':
                    me.uv_layers.remove(uvl)
            for an in ('rest', 'grain', 'pid'):
                a = me.attributes.get(an)
                if a is not None:
                    me.attributes.remove(a)
        self.groups[name] = dict(kind='atlas', mat=mat, ao=0.45)
        log(f'props atlas: {len(protos)} protos baked in {time.time() - t0:.0f}s')
        return name

    # ------------------------------------------------------------------ final assembly
    def _uv_box(self, ob, scale, rot=0.0, off=None):
        me = ob.data
        for l in list(me.uv_layers):
            me.uv_layers.remove(l)
        lay = me.uv_layers.new(name='atlas')
        nL = len(me.loops)
        if nL == 0:
            return
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        lv = np.empty(nL, np.int32)
        me.loops.foreach_get('vertex_index', lv)
        pn = np.empty(len(me.polygons) * 3, np.float32)
        me.polygons.foreach_get('normal', pn)
        pn = pn.reshape(-1, 3)
        ls = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('loop_start', ls)
        lt = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('loop_total', lt)
        poly_of_loop = np.repeat(np.arange(len(me.polygons)), lt)
        N = pn[poly_of_loop]
        P = co[lv]
        ax = np.abs(N)
        dom = np.argmax(ax, 1)
        u = np.zeros(nL, np.float32)
        v = np.zeros(nL, np.float32)
        # z-dominant: floor/ceiling
        m = dom == 2
        u[m] = P[m, 0]
        v[m] = P[m, 1]
        # y-dominant: walls facing the camera (-Y) or away
        m = dom == 1
        u[m] = np.where(N[m, 1] < 0, P[m, 0], -P[m, 0])
        v[m] = P[m, 2]
        m = dom == 0
        u[m] = np.where(N[m, 0] > 0, P[m, 1], -P[m, 1])
        v[m] = P[m, 2]
        if rot:
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            u, v = u * c - v * s, u * s + v * c
        u = u / scale
        v = v / scale
        if off is not None:
            u = u + off[0]
            v = v + off[1]
        lay.data.foreach_set('uv', np.stack([u, v], 1).ravel())

    def finalize(self, ao_dist=1.6, ao_samples=96, near_depth=12.0, near_x=16.0, export=True, compress=True):
        t0 = time.time()
        sc = bpy.context.scene
        objs = [o for o in self.col_set.objects if o.type == 'MESH']
        # hide the protos from rendering (AO bake)
        for p in self.col_proto.objects:
            p.hide_render = True
            p.hide_viewport = False
        # 1. realise transforms (except animated nodes, which keep their pivot)
        for o in objs:
            if o.data.users > 1:
                o.data = o.data.copy()
            if not o.name.startswith('anim_') and not o.get('keep_xform'):
                if o.parent is not None:
                    mw = o.matrix_world.copy()
                    o.parent = None
                    o.matrix_world = mw
                apply_matrix(o)
            for m in list(o.modifiers):
                o.modifiers.remove(m)
        # 2. UVs for tile groups (world space)
        for o in objs:
            g = self.groups[o['grp']]
            if g['kind'] == 'tile':
                if o.name.startswith('anim_') or o.get('keep_xform'):
                    me = o.data
                    mw = o.matrix_world.copy()
                    me.transform(mw)
                    self._uv_box(o, float(o.get('uvs', g['scale'])), float(o.get('uvr', 0.0)), o.get('uvo'))
                    me.transform(mw.inverted())
                else:
                    self._uv_box(o, float(o.get('uvs', g['scale'])), float(o.get('uvr', 0.0)), o.get('uvo'))
            elif g['kind'] == 'backdrop':
                pass
            if not o.data.uv_layers:
                o.data.uv_layers.new(name='atlas')
            for l in list(o.data.uv_layers):
                if l.name != 'atlas':
                    o.data.uv_layers.remove(l)
            for an in ('rest', 'grain', 'pid', 'aux'):
                a = o.data.attributes.get(an)
                if a is not None:
                    o.data.attributes.remove(a)
        # 3. vertex colour AO (+ tints)
        ao_objs = [o for o in objs if self.groups[o['grp']]['kind'] not in ('backdrop',)]
        for o in ao_objs:
            me = o.data
            for ca in list(me.color_attributes):
                me.color_attributes.remove(ca)
            ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
            me.color_attributes.active_color = ca
            me.attributes.default_color_name = 'Col'
        bake_objs = [o for o in ao_objs if self.groups[o['grp']]['kind'] not in ('glow',) and float(o.get('ao', 1.0)) > 0]
        if bake_objs:
            sc.render.engine = 'CYCLES'
            if sc.world is None:
                sc.world = bpy.data.worlds.new('BakeWorld')
            sc.world.light_settings.distance = ao_dist
            sc.cycles.samples = ao_samples
            bpy.ops.object.select_all(action='DESELECT')
            for o in bake_objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = bake_objs[0]
            t1 = time.time()
            bpy.ops.object.bake(type='AO', target='VERTEX_COLORS', use_clear=True)
            log(f'vertex AO baked on {len(bake_objs)} objects in {time.time() - t1:.0f}s')
        for o in ao_objs:
            self._shade_vcol(o, o in bake_objs)
        # 4. join per group and shadow class (animated nodes stay separate)
        final = []
        buckets = {}
        for o in objs:
            g = self.groups[o['grp']]
            me = o.data
            me.materials.clear()
            me.materials.append(g['mat'])
            if len(me.polygons):
                me.polygons.foreach_set('material_index', np.zeros(len(me.polygons), np.int32))
            if o.name.startswith('anim_') or g['kind'] == 'backdrop' or o.get('solo'):
                final.append(o)
                continue
            sh = o.get('shadow')
            if sh is None:
                mn, mx = bbox(o)
                c = (mn + mx) / 2
                sh = 1 if (abs(c[0]) < near_x and c[1] < near_depth and g['kind'] != 'glow') else 0
            buckets.setdefault((o['grp'], int(sh)), []).append(o)
        for (grp, sh), lst in sorted(buckets.items()):
            nm = grp if sh else f'{grp}_noshadow'
            ob = merge(lst, nm)
            ob.data.name = nm
            final.append(ob)
        for o in final:
            o.data.name = o.name
            # smooth normals stay as authored
        self.final = final
        tris = sum(self._tris(o) for o in final)
        self.notes['triangles'] = tris
        self.notes['materials'] = sorted({s.material.name for o in final for s in o.material_slots if s.material})
        self.notes['objects'] = len(final)
        log(f'final: {len(final)} objects, {tris} tris, {len(self.notes["materials"])} materials '
            f'({", ".join(self.notes["materials"])}) in {time.time() - t0:.0f}s')
        self.check_keep_clear()
        if export:
            self.export()
            if compress:
                self.compress()
        self.save_blend()
        return final

    def _tris(self, o):
        me = o.data
        me.calc_loop_triangles()
        return len(me.loop_triangles)

    def _shade_vcol(self, o, baked):
        me = o.data
        ca = me.color_attributes['Col']
        nL = len(me.loops)
        if nL == 0:
            return
        g = self.groups[o['grp']]
        col = np.ones((nL, 4), np.float32)
        if baked:
            col_raw = np.empty(nL * 4, np.float32)
            ca.data.foreach_get('color', col_raw)
            ao = col_raw.reshape(-1, 4)[:, 0]
            k = float(o.get('ao', g.get('ao', 0.5)))
            f = 1.0 - k * (1.0 - np.clip(ao, 0, 1))
            col[:, :3] *= f[:, None]
        if 'tint' in o:
            col[:, :3] *= np.array(o['tint'], np.float32)[None, :]
        if self.tint_fn is not None and g['kind'] != 'glow':
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get('co', co)
            co = co.reshape(-1, 3)
            if o.name.startswith('anim_') or o.get('keep_xform'):
                M = np.array(o.matrix_world, np.float32)
                co = co @ M[:3, :3].T + M[:3, 3]
            lv = np.empty(nL, np.int32)
            me.loops.foreach_get('vertex_index', lv)
            ln = np.empty(nL * 3, np.float32)
            me.loops.foreach_get('normal', ln)
            t = self.tint_fn(o['grp'], co[lv], ln.reshape(-1, 3), o)
            if t is not None:
                col[:, :3] *= t
        col[:, 3] = 1.0
        ca.data.foreach_set('color', col.ravel())

    def check_keep_clear(self):
        """Nothing taller than 0.25 m in glTF z in [-1.5, +6] (Blender y in [-6, 1.5]); flat floor x in [-10, 10]."""
        bad = []
        for o in self.final:
            if 'backdrop' in o.name:
                continue
            co = np.empty(len(o.data.vertices) * 3, np.float32)
            o.data.vertices.foreach_get('co', co)
            co = co.reshape(-1, 3)
            M = np.array(o.matrix_world, np.float32)
            co = co @ M[:3, :3].T + M[:3, 3]
            m = (co[:, 1] > -6.0) & (co[:, 1] < 1.5) & (np.abs(co[:, 0]) < 22) & (co[:, 2] > 0.25)
            if m.any():
                bad.append((o.name, int(m.sum()), co[m][:3].tolist()))
            m2 = (co[:, 1] > -6.0) & (co[:, 1] < 2.0) & (np.abs(co[:, 0]) < 10) & (co[:, 2] > 0.03) & (co[:, 2] <= 0.25)
            if m2.any():
                log(f'note: {o.name} has {int(m2.sum())} low verts (<=0.25 m) on the floor zone')
        if bad:
            log('KEEP-CLEAR VIOLATIONS:', bad)
        else:
            log('keep-clear zone: OK')
        self.notes['keep_clear'] = 'OK' if not bad else bad
        return bad

    def export(self):
        bpy.ops.object.select_all(action='DESELECT')
        for o in self.final:
            o.select_set(True)
            p = o.parent
            while p is not None:
                p.select_set(True)
                p = p.parent
        bpy.context.view_layer.objects.active = self.final[0]
        bpy.ops.export_scene.gltf(
            filepath=self.src, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
            export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
            export_image_format='AUTO', export_cameras=False, export_lights=False, export_extras=False,
            export_animations=False, export_vertex_color='ACTIVE', export_all_vertex_colors=False)
        self.notes['src_mb'] = round(os.path.getsize(self.src) / 1e6, 2)
        log(f'exported {self.src} ({self.notes["src_mb"]} MB)')

    def compress(self):
        cmd = ['node', 'tools/assets.mjs', 'prop', os.path.relpath(self.src, JB).replace('\\', '/'),
               f'stages/{self.id}.glb', '--tex', '1024']
        r = subprocess.run(cmd, cwd=JB, capture_output=True, text=True, shell=False)
        log('compress:', r.stdout.strip(), r.stderr.strip()[-800:])
        if os.path.exists(self.out):
            self.notes['glb_mb'] = round(os.path.getsize(self.out) / 1e6, 2)
        self.write_stats()

    def write_stats(self):
        p = os.path.join(self.work, 'stats.json')
        with open(p, 'w') as f:
            json.dump(self.notes, f, indent=1, default=str)

    def save_blend(self):
        try:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.work, f'{self.id}.blend'), compress=True)
        except Exception as e:  # pragma: no cover
            log('blend save failed', e)


# ============================================================================ kit material adapter
class KitMat(dj.M):
    """Wrap an imported image-based Principled material so dj.bake can wire its channels to emission."""

    def __init__(self, mat, uvname='UVMap'):
        self.mat = mat
        self.nt = mat.node_tree
        self.N = self.nt.nodes
        self.Lk = self.nt.links
        outs = [n for n in self.N if n.type == 'OUTPUT_MATERIAL']
        self.out = next((n for n in outs if n.is_active_output), outs[0] if outs else self.N.new('ShaderNodeOutputMaterial'))
        bs = [n for n in self.N if n.type == 'BSDF_PRINCIPLED']
        if bs:
            self.bsdf = bs[0]
        else:
            self.bsdf = self.N.new('ShaderNodeBsdfPrincipled')
        if not self.out.inputs['Surface'].is_linked:
            self.Lk.new(self.bsdf.outputs[0], self.out.inputs['Surface'])
        self.emitn = self.N.new('ShaderNodeEmission')
        self.target = self.N.new('ShaderNodeTexImage')
        self.ch = {}
        self._rest = None
        self._geo = None
        self.glow = False
        for n in list(self.N):
            if n.type == 'TEX_IMAGE' and n is not self.target and not n.inputs['Vector'].is_linked:
                u = self.N.new('ShaderNodeUVMap')
                u.uv_map = uvname
                self.Lk.new(u.outputs['UV'], n.inputs['Vector'])
            if n.type == 'NORMAL_MAP' and not n.uv_map:
                n.uv_map = uvname
        for key, sock in (('color', 'Base Color'), ('rough', 'Roughness'), ('metal', 'Metallic')):
            s = self.bsdf.inputs[sock]
            if s.is_linked:
                self.ch[key] = s.links[0].from_socket
            else:
                dv = s.default_value
                self.ch[key] = self.S(tuple(dv) if key == 'color' else float(dv))
        dj.PROC[mat.name] = self


# ============================================================================ misc builders
def text_plate_img(text, w, h, res=512, cap=0.6, width_frac=0.13):
    """Stroke-font text image (dj glyphs + a few more) for signs."""
    st = dj.text_strokes(text, w / 2, h * (1 - cap) / 2, h * cap, width_frac=width_frac)
    return dj.stroke_image('txt_' + text[:12], w, h, st, res=res)


def add_glyphs():
    """Extra glyphs for dj.text_strokes (MAIN, MANAGEMENT, OUT OF ORDER, numbers...)."""
    G = dj._GLYPHS
    G.setdefault('M', [[(0.1, 0), (0.1, 1), (0.5, 0.45), (0.9, 1), (0.9, 0)]])
    G.setdefault('G', [[(0.85, 0.85), (0.6, 1), (0.35, 1), (0.12, 0.8), (0.12, 0.2), (0.35, 0), (0.65, 0), (0.88, 0.2), (0.88, 0.45), (0.55, 0.45)]])
    G.setdefault('T', [[(0.1, 1), (0.9, 1)], [(0.5, 1), (0.5, 0)]])
    G.setdefault('F', [[(0.85, 1), (0.2, 1), (0.2, 0)], [(0.2, 0.52), (0.7, 0.52)]])
    G.setdefault('L', [[(0.2, 1), (0.2, 0), (0.85, 0)]])
    G.setdefault('U', [[(0.15, 1), (0.15, 0.25), (0.35, 0), (0.65, 0), (0.85, 0.25), (0.85, 1)]])
    G.setdefault('D', [[(0.15, 0), (0.15, 1), (0.55, 1), (0.85, 0.75), (0.85, 0.25), (0.55, 0), (0.15, 0)]])
    G.setdefault('B', [[(0.15, 0), (0.15, 1), (0.6, 1), (0.8, 0.85), (0.8, 0.62), (0.6, 0.52), (0.15, 0.52)], [(0.6, 0.52), (0.85, 0.38), (0.85, 0.14), (0.62, 0), (0.15, 0)]])
    G.setdefault('C', [[(0.85, 0.85), (0.6, 1), (0.35, 1), (0.12, 0.8), (0.12, 0.2), (0.35, 0), (0.6, 0), (0.85, 0.15)]])
    G.setdefault('S', [[(0.85, 0.85), (0.6, 1), (0.3, 1), (0.12, 0.82), (0.15, 0.6), (0.85, 0.42), (0.88, 0.18), (0.65, 0), (0.3, 0), (0.1, 0.15)]])
    G.setdefault('K', [[(0.15, 0), (0.15, 1)], [(0.85, 1), (0.15, 0.4)], [(0.35, 0.58), (0.85, 0)]])
    G.setdefault('H', [[(0.15, 0), (0.15, 1)], [(0.85, 0), (0.85, 1)], [(0.15, 0.52), (0.85, 0.52)]])
    G.setdefault('W', [[(0.05, 1), (0.25, 0), (0.5, 0.6), (0.75, 0), (0.95, 1)]])
    G.setdefault('Y', [[(0.1, 1), (0.5, 0.5), (0.9, 1)], [(0.5, 0.5), (0.5, 0)]])
    G.setdefault('V', [[(0.1, 1), (0.5, 0), (0.9, 1)]])
    G.setdefault('X', [[(0.1, 1), (0.9, 0)], [(0.1, 0), (0.9, 1)]])
    G.setdefault('Q', G['O'] + [[(0.6, 0.25), (0.9, -0.05)]])
    G.setdefault('Z', [[(0.15, 1), (0.85, 1), (0.15, 0), (0.85, 0)]])
    for d, poly in {'0': G['O'], '1': [[(0.3, 0.8), (0.55, 1), (0.55, 0)]], '2': [[(0.15, 0.8), (0.35, 1), (0.7, 1), (0.85, 0.8), (0.85, 0.6), (0.15, 0), (0.85, 0)]],
                    '3': [[(0.15, 0.9), (0.4, 1), (0.75, 1), (0.85, 0.8), (0.75, 0.55), (0.45, 0.52)], [(0.75, 0.55), (0.88, 0.3), (0.75, 0.05), (0.4, 0), (0.12, 0.1)]],
                    '4': [[(0.7, 0), (0.7, 1), (0.1, 0.3), (0.9, 0.3)]], '5': [[(0.85, 1), (0.2, 1), (0.15, 0.55), (0.6, 0.6), (0.85, 0.4), (0.8, 0.12), (0.5, 0), (0.15, 0.08)]],
                    '6': [[(0.8, 0.95), (0.5, 1), (0.2, 0.75), (0.15, 0.3), (0.35, 0), (0.7, 0), (0.85, 0.25), (0.75, 0.5), (0.45, 0.55), (0.18, 0.4)]],
                    '7': [[(0.15, 1), (0.85, 1), (0.4, 0)]], '8': [[(0.5, 0.55), (0.2, 0.75), (0.35, 1), (0.65, 1), (0.8, 0.75), (0.5, 0.55), (0.15, 0.3), (0.3, 0), (0.7, 0), (0.85, 0.3), (0.5, 0.55)]],
                    '9': [[(0.82, 0.6), (0.55, 0.45), (0.25, 0.5), (0.15, 0.75), (0.35, 1), (0.65, 1), (0.85, 0.75), (0.8, 0.3), (0.55, 0), (0.2, 0.05)]],
                    ':': [[(0.5, 0.2), (0.5, 0.25)], [(0.5, 0.7), (0.5, 0.75)]], '!': [[(0.5, 1), (0.5, 0.3)], [(0.5, 0.05), (0.5, 0.1)]],
                    '/': [[(0.15, 0), (0.85, 1)]], '#': [[(0.35, 0), (0.45, 1)], [(0.6, 0), (0.7, 1)], [(0.15, 0.35), (0.9, 0.35)], [(0.1, 0.68), (0.85, 0.68)]]}.items():
        G.setdefault(d, poly)


add_glyphs()

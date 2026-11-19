"""Armour/gear core: body context (male / female Universal Base Characters), landmarks, layer stack.

Every armour piece is built for one body (the Quaternius UBC male or female, UAL 65-bone skeleton) and
bound to that body's bind pose (DECISIONS 3D-12). Geometry is derived from bone landmarks and from the
body surface, so one recipe fits both bodies.

Conventions (as djlib): metres, Blender Z-up, the character faces -Y (its left = +X).
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
CHAR = os.path.join(os.path.dirname(HERE), 'characters')
for p in (HERE, CHAR):
    if p not in sys.path:
        sys.path.insert(0, p)
import djlib as dj
import djarmor as ar
from djlib import V, MB

PROJ = dj.PROJ
UBC = dj.QUAT + r"\ubc"
BODY_FILES = {'m': UBC + r"\bodies\Superhero_Male_FullBody.gltf", 'f': UBC + r"\bodies\Superhero_Female_FullBody.gltf"}
# JoeBrawla copy: every output goes to the fighter work folder (FIGHTER_WORK), never into DJ3D
WORK = os.environ.get("FIGHTER_WORK", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "_work", "joe"))
OUT_ARMOR = os.path.join(WORK, "armor")
OUT_CHAR = os.path.join(WORK, "characters")
OUT_PREV = os.path.join(WORK, "previews_lib")
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT_PREV, exist_ok=True)
dj.WORK = WORK

FINGER_PREFIX = ('index', 'middle', 'ring', 'pinky', 'thumb')


def smooth01(x, a, b):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def LR(name, side):
    """'upperarm_l' -> side variant ('l' / 'r')."""
    return name[:-2] + '_' + side if name.endswith('_l') or name.endswith('_r') else name


class Body:
    """A loaded UBC body with landmarks, BVH, weight source and dominant bone per vertex."""

    def __init__(self, sex='m', keep_extras=True):
        self.sex = sex
        self.arm, ms = dj.load_body(BODY_FILES[sex])
        self.arm.name = 'Armature'
        self.arm.data.name = 'Armature'
        self.meshes = ms
        self.mesh = next(o for o in ms if o.name.lower().startswith('superhero'))
        self.eyes = next((o for o in ms if o.name.lower().startswith('eyes')), None)
        self.brows = next((o for o in ms if o.name.lower().startswith('eyebrows')), None)
        self.B = dj.Bones(self.arm)
        self.bvh = dj.bvh_from([self.mesh])
        self.ws = dj.WeightSource(self.mesh)
        self.W = dj.read_weights(self.mesh)
        self.dom = [max(w.items(), key=lambda kv: kv[1])[0] if w else '' for w in self.W]
        mw = self.mesh.matrix_world
        self.co = [mw @ v.co for v in self.mesh.data.vertices]
        self.nrm = [(mw.to_3x3() @ v.normal).normalized() for v in self.mesh.data.vertices]
        self._landmarks()

    # ------------------------------------------------------------------ landmarks
    def h(self, b):
        return self.B.h(b)

    def t(self, b):
        return self.B.t(b)

    def _landmarks(self):
        B = self.B
        co = self.co
        L = {}
        L['top'] = max(c.z for c in co)
        L['pelvis'] = B.h('pelvis')
        L['waist'] = B.h('spine_01')            # natural waist line
        L['chest'] = B.h('spine_03')
        L['neck'] = B.h('neck_01')
        L['head'] = B.h('Head')
        L['shoulder_l'] = B.h('upperarm_l')
        L['elbow_l'] = B.h('lowerarm_l')
        L['wrist_l'] = B.h('hand_l')
        L['hip_l'] = B.h('thigh_l')
        L['knee_l'] = B.h('calf_l')
        L['ankle_l'] = B.h('foot_l')
        L['ball_l'] = B.h('ball_l')
        # crotch: lowest body point near the centre line between the thighs
        cr = [c for c in co if abs(c.x) < 0.02 and 0.6 < c.z < 1.0]
        L['crotch_z'] = min(c.z for c in cr) if cr else L['hip_l'].z - 0.12
        # head: eye centres from the eye mesh, nose tip, chin
        if self.eyes:
            ew = self.eyes.matrix_world
            ev = [ew @ v.co for v in self.eyes.data.vertices]
            le = [p for p in ev if p.x > 0]
            re = [p for p in ev if p.x < 0]
            L['eye_l'] = sum(le, Vector()) / len(le)
            L['eye_r'] = sum(re, Vector()) / len(re)
        hz = L['head'].z
        face = [c for c in co if c.z > hz - 0.05 and abs(c.x) < 0.02]
        nose = min(face, key=lambda c: c.y)
        L['nose'] = nose
        chin_c = [c for c in co if abs(c.x) < 0.012 and c.z < nose.z - 0.03 and c.z > L['neck'].z and c.y < nose.y + 0.05]
        L['chin'] = min(chin_c, key=lambda c: c.z + 0.6 * c.y) if chin_c else nose + Vector((0, 0.02, -0.08))
        L['head_c'] = Vector((0, (nose.y + max(c.y for c in co if c.z > hz)) * 0.5, (L['top'] + L['chin'].z) * 0.5))
        self.L = L

    def ztop(self, x, y, start=2.2):
        loc, nrm, idx, d = self.bvh.ray_cast(Vector((x, y, start)), Vector((0, 0, -1)), 3.0)
        return loc.z if loc is not None else None

    def radius_at(self, c, d, maxd=0.4, bvh=None):
        """Distance from c along direction d to the outermost surface (body or given bvh)."""
        bvh = bvh or self.bvh
        d = Vector(d).normalized()
        st = Vector(c) + d * maxd
        loc, nrm, idx, dist = bvh.ray_cast(st, -d, maxd)
        return (maxd - dist) if loc is not None else None

    def region_verts(self, bones):
        bones = set(bones)
        return [i for i, b in enumerate(self.dom) if b in bones]

    def fingers(self, side=None):
        out = []
        for b in self.B.names():
            if b.startswith(FINGER_PREFIX) and (side is None or b.endswith('_' + side)):
                out.append(b)
        return out

    def report(self):
        for k, v in self.L.items():
            if isinstance(v, Vector):
                print('  %-10s (%.3f %.3f %.3f)' % (k, v.x, v.y, v.z))
            else:
                print('  %-10s %.3f' % (k, v))


class Stack:
    """Collision stack of the layers built so far (body + earlier garments)."""

    def __init__(self, body):
        self.body = body
        self.objs = [body.mesh]
        self._bvh = None

    def add(self, *obs):
        for o in obs:
            if o is not None:
                self.objs.append(o)
        self._bvh = None

    def bvh(self, extra=()):
        if extra:
            return dj.bvh_from(self.objs + list(extra))
        if self._bvh is None:
            self._bvh = dj.bvh_from(self.objs)
        return self._bvh


def args():
    return dj.args_after_dashdash()


def opt(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def jpeg(quality=90):
    """Preview renders are saved as JPEG (they go into Git LFS)."""
    s = bpy.context.scene.render.image_settings
    s.file_format = 'JPEG'
    s.quality = quality
    s.color_mode = 'RGB'

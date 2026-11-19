"""EEVEE preview renders (1024 px JPG, neutral grey studio, warm key + cool rim) driven by UAL clips.
blender -b --factory-startup --python render_previews.py -- [shot ...]
shot = name:action:frame:view      (no shots = the deliverable set)    env PV_OUT = output dir (default previews/)
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import jb_lib as L
import f_rig as R
import f_scene as SC

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.environ.get("PV_OUT", L.PREV_DIR)
RES = int(os.environ.get("PV_RES", "1024"))
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(L.WORK, "rig.blend"))
arm = bpy.data.objects["Armature"]
K = arm.scale[0]
clips = R.load_clips()
SC.studio(res=RES)
cam = SC.camera(lens=50)
sc = bpy.context.scene
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 92
arm.animation_data_create()

# extra finger closing for a held prop (the UAL fist is already closed; nothing needed for the right hand)
HOLD = {}


def el(az, elev):
    a, e = math.radians(az), math.radians(elev)
    return (math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e))


H = R.HEIGHT
VIEWS = {
    "front": ((0, 0, 0.50 * H), el(0, 5), 5.6, 50),
    "side": ((0, 0, 0.50 * H), el(90, 4), 5.6, 50),
    "threeq": ((0, 0, 0.50 * H), el(-38, 12), 5.6, 50),
    "back": ((0, 0, 0.50 * H), el(160, 12), 5.6, 50),
    "face": ((0, -0.05, 0.84 * H), el(-22, 5), 1.75, 60),
    "action": ((0, -0.2, 0.48 * H), el(-30, 10), 6.6, 50),
    "actionr": ((0, -0.2, 0.48 * H), el(35, 10), 6.6, 50),
    "low": ((0, -0.1, 0.40 * H), el(-30, 6), 5.6, 50),
}


def set_action(name, frame):
    act = clips[name]
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc.frame_set(int(frame))


def focus_on_mesh(view):
    """centre the camera target on the posed mesh bounding box (x/y), keep the view's height."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent == arm:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            mw = ev.matrix_world
            pts += [mw @ v.co for v in me.vertices[::7]]
            ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (lo + hi) * 0.5, lo, hi


def shot(name, action, frame, view):
    set_action(action, frame)
    t, d, dist, lens = VIEWS[view]
    cam.data.lens = lens
    t = Vector(t)
    if view == "face":
        hb = arm.pose.bones["Head"]
        t = arm.matrix_world @ (hb.head + (hb.tail - hb.head).normalized() * 0.09)
    if view in ("action", "actionr", "low"):
        c, lo, hi = focus_on_mesh(view)
        t = Vector((c.x, c.y, (lo.z + hi.z) * 0.5))
        dist = dist * max(1.0, (hi - lo).length / 3.0)
    SC.aim(cam, t, d, dist)
    SC.render(os.path.join(OUT, name + ".jpg"))


DEFAULT = [
    "front:Sword_Idle:12:front", "side:Sword_Idle:12:side", "threeq:Sword_Idle:12:threeq", "face:Sword_Idle:12:face",
    "pose_punch:Punch_Cross:11:action", "pose_combo:Sword_Regular_Combo:20:action", "pose_crouch:Crouch_Idle_Loop:10:low",
]
for s in (argv or DEFAULT):
    p = s.split(":")
    shot(p[0], p[1], p[2], p[3])

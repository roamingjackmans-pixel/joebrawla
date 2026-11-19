"""Vexthorn configuration: skeleton proportions (applied to the UBC male rest skeleton) and the modeling pose.

Bone lengths only are changed (every bone keeps its UBC orientation and roll), so UAL clips (absolute local
rotations) play exactly as on a UBC body.  OWN[b] scales the bone's own length; KIDS[b] scales the offsets of
its children's heads from its head (defaults to OWN[b]).
"""
FINGERS = ("index", "middle", "ring", "pinky")

OWN = {
    "spine_01": 1.04, "spine_02": 1.04, "spine_03": 1.04,
    "neck_01": 1.32, "Head": 1.08,
    "thigh_l": 1.03, "thigh_r": 1.03, "calf_l": 1.08, "calf_r": 1.08,
}
KIDS = {
    "pelvis": (0.90, 1.0, 1.0),          # narrower hips: lean
}
for s in ("l", "r"):
    OWN["upperarm_" + s] = 1.07
    OWN["lowerarm_" + s] = 1.15
    OWN["hand_" + s] = 1.10
    for f in FINGERS:
        for i in ("01", "02", "03", "04_leaf"):
            OWN["%s_%s_%s" % (f, i, s)] = 1.25
    for i in ("01", "02", "03", "04_leaf"):
        OWN["thumb_%s_%s" % (i, s)] = 1.12


def modeling_pose():
    """relaxed A-pose for sculpting (XYZ euler degrees in ARMATURE rest axes; faces -Y, left = +X)."""
    P = {}
    P["upperarm_l"] = (0, 52, -12)
    P["upperarm_r"] = (0, -52, 12)
    P["lowerarm_l"] = (0, 0, -22)
    P["lowerarm_r"] = (0, 0, 22)
    P["hand_l"] = (6, 4, 0)
    P["hand_r"] = (6, -4, 0)
    curl = {"01": 14, "02": 20, "03": 16}
    spread = {"index": 7, "middle": 1, "ring": -5, "pinky": -11}
    for f in FINGERS:
        for seg, c in curl.items():
            P["%s_%s_l" % (f, seg)] = (0, c, -spread[f] if seg == "01" else 0)
            P["%s_%s_r" % (f, seg)] = (0, -c, spread[f] if seg == "01" else 0)
    P["thumb_01_l"] = (0, 8, 10)
    P["thumb_02_l"] = (0, 12, 0)
    P["thumb_03_l"] = (0, 12, 0)
    P["thumb_01_r"] = (0, -8, -10)
    P["thumb_02_r"] = (0, -12, 0)
    P["thumb_03_r"] = (0, -12, 0)
    P["thigh_l"] = (0, -5, 0)
    P["thigh_r"] = (0, 5, 0)
    P["calf_l"] = (0, 4, 0)
    P["calf_r"] = (0, -4, 0)
    return P

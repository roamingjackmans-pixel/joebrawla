"""Archmagister Tock configuration: skeleton proportions (on the UBC male rest skeleton) and the modeling pose.
Gaunt: narrow shoulders and hips, long thin forearms and fingers, longer neck. Bone lengths only (orientations kept).
"""
FINGERS = ("index", "middle", "ring", "pinky")

OWN = {
    "spine_01": 1.0, "spine_02": 1.0, "spine_03": 1.0,
    "neck_01": 1.18, "Head": 1.05,
    "thigh_l": 1.0, "thigh_r": 1.0, "calf_l": 1.0, "calf_r": 1.0,
}
KIDS = {
    "pelvis": (0.88, 1.0, 1.0),
    "spine_03": (0.92, 1.0, 1.0),       # narrow shoulders
}
for s in ("l", "r"):
    OWN["clavicle_" + s] = 0.95
    OWN["upperarm_" + s] = 1.03
    OWN["lowerarm_" + s] = 1.08
    OWN["hand_" + s] = 1.08
    for f in FINGERS:
        for i in ("01", "02", "03", "04_leaf"):
            OWN["%s_%s_%s" % (f, i, s)] = 1.15
    for i in ("01", "02", "03", "04_leaf"):
        OWN["thumb_%s_%s" % (i, s)] = 1.08


def modeling_pose():
    """relaxed A-pose for sculpting; the right hand is closed round the staff grip."""
    P = {}
    P["upperarm_l"] = (0, 55, -10)
    P["upperarm_r"] = (0, -55, 10)
    P["lowerarm_l"] = (0, 0, -24)
    P["lowerarm_r"] = (0, 0, 24)
    P["hand_l"] = (6, 4, 0)
    P["hand_r"] = (6, -4, 0)
    curl = {"01": 12, "02": 18, "03": 14}
    spread = {"index": 6, "middle": 1, "ring": -4, "pinky": -9}
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
    P["thigh_l"] = (0, -4, 0)
    P["thigh_r"] = (0, 4, 0)
    P["calf_l"] = (0, 3, 0)
    P["calf_r"] = (0, -3, 0)
    return P

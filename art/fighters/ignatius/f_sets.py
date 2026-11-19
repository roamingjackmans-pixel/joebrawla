"""Texture atlases and materials for Foreman Ignatius.

Atlases (2048 authored, shipped at 1024 WebP): body (skin, mail, helmet, beard, gauntlet, chains, belt, straps),
gear (apron, mail skirt, legs/boots), hammer.  Materials reference an atlas; the two tint materials share their
atlas with an ordinary material and only use their own UV islands (painted light/neutral; colour = factor).
"""
import f_parts as CP
import f_props as PR

SIZE = {"body": 2048, "gear": 2048, "hammer": 2048}

# material key -> (glTF material name, atlas, base colour factor (sRGB hex) or None, emission strength)
MATERIALS = {
    "body": ("ignatius_body", "body", None, 4.0),
    "trim": ("tint2_trim", "body", "#e0a028", 0.0),        # hardhat enamel / apron straps: foundry yellow
    "apron": ("tint1_apron", "gear", "#7a4a2a", 0.0),      # scorched leather apron
    "gear": ("ignatius_gear", "gear", None, 0.0),
    "hammer": ("ignatius_hammer", "hammer", None, 3.5),
}


def all_parts():
    return CP.all_parts() + [PR.Hammer()]


def parts(aset):
    return [p for p in all_parts() if p.aset == aset]


def size(aset):
    return SIZE[aset]

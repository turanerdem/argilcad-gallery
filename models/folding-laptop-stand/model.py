# Folding laptop stand — base → arm → tray, joined by two pinned hinges.
# Modelled folded flat (Z-fold): base on the bottom layer, arm on top of it,
# tray folded back over the arm. Every dimension is a variable below.
#
# Axes: X = width, Y = depth, Z = up. Hinge A (base–arm) sits at Y = 0,
# hinge B (arm–tray) at Y = arm_len. Unfolded, the arm swings up about A,
# the tray tips back about B, and the lip ends up at the low, user-facing edge.
from build123d import *

# ===================== PARAMETERS =====================
# --- Overall size ---
width        = 260.0   # width of all three parts (X)
plate_t      = 6.0     # thickness of base, arm and tray plates
layer_gap    = 1.0     # air gap between stacked plates when folded

base_len     = 250.0   # base length, measured from hinge A axis
arm_len      = 220.0   # distance between hinge A and hinge B axes
tray_len     = 240.0   # tray length, from hinge B axis to the free (lip) end

# --- Hinges ---
knuckles_a   = 5       # knuckles on base–arm hinge (odd: base owns both ends)
knuckles_b   = 5       # knuckles on arm–tray hinge (odd: arm owns both ends)
knuckle_gap  = 0.6     # axial gap between neighbouring knuckles
swing_clear  = 1.0     # radial clearance between a plate and the mating knuckles
tab_overlap  = 1.0     # how far a knuckle tab runs into its plate (for a solid fuse)
pin_r        = 3.0     # hinge pin radius
pin_clear    = 0.2     # radial clearance between pin and bore

# --- Tray features ---
lip_h        = 12.0    # front lip height above the tray surface
lip_t        = 5.0     # front lip thickness
slot_count   = 7       # ventilation slots through the tray
slot_w       = 8.0     # slot width
slot_len     = 130.0   # slot length (overall, rounded ends)
slot_pitch   = 30.0    # centre-to-centre spacing of the slots

# --- Arm ---
arm_window_margin = 30.0  # frame width left around the arm's lightening window

# ===================== DERIVED =====================
layer_pitch = plate_t + layer_gap
def layer_z(i):
    """Bottom Z of stacked layer i (0 = base, 1 = arm, 2 = tray)."""
    return i * layer_pitch

# A knuckle spans exactly two neighbouring layers, so the hinge axis sits on
# the gap between them and the radius reaches both plates.
knuckle_r   = plate_t + layer_gap / 2
hinge_a     = (0.0,     layer_z(0) + plate_t + layer_gap / 2)   # (y, z), axis along X
hinge_b     = (arm_len, layer_z(1) + plate_t + layer_gap / 2)
plate_start = knuckle_r + swing_clear    # plates start this far from their hinge axis
bore_r      = pin_r + pin_clear

tray_free_y = hinge_b[0] - tray_len                 # lip end of the tray
tray_end_y  = hinge_b[0] - plate_start              # hinge end of the tray plate

# Sanity checks
assert knuckles_a % 2 == 1 and knuckles_b % 2 == 1, "knuckle counts must be odd"
assert bore_r < knuckle_r - 1.5, "pin too big for the knuckles"
assert arm_len > 2 * plate_start + 2 * arm_window_margin, "arm too short"
assert base_len > plate_start, "base too short"
assert tray_len > plate_start + lip_t + slot_len, "tray too short for the slots"
assert (slot_count - 1) * slot_pitch + slot_w < width, "slots don't fit the width"

# ===================== HELPERS =====================
def segments(n):
    """(x_centre, length) of n knuckle segments spread across the width."""
    seg = (width - (n - 1) * knuckle_gap) / n
    return [(-width / 2 + seg / 2 + i * (seg + knuckle_gap), seg) for i in range(n)]

def slab(y0, y1, z0, h, w=width, x=0.0):
    """Box spanning y0..y1, from z0 up by h, width w centred on x."""
    return Pos(x, (y0 + y1) / 2, z0) * Box(
        w, abs(y1 - y0), h, align=(Align.CENTER, Align.CENTER, Align.MIN))

def x_cylinder(axis, r, length, x=0.0):
    return Pos(x, axis[0], axis[1]) * Rot(0, 90, 0) * Cylinder(r, length)

def add_leaves(shape, axis, n, parity, layer, toward):
    """Add this part's knuckles (every other segment) plus a tab joining each
    knuckle to the plate, which lies on `layer` in direction `toward` (±1 in Y)."""
    for i, (x, seg) in enumerate(segments(n)):
        if i % 2 == parity:
            shape += x_cylinder(axis, knuckle_r, seg, x)
            shape += slab(axis[0], axis[0] + toward * (plate_start + tab_overlap),
                          layer_z(layer), plate_t, w=seg, x=x)
    return shape

def bore(shape, axis):
    return shape - x_cylinder(axis, bore_r, width + 20)

def rounded_slot(x, y, z0, h):
    s = Pos(x, y, z0) * Box(slot_w, slot_len - slot_w, h,
                            align=(Align.CENTER, Align.CENTER, Align.MIN))
    for dy in (-(slot_len - slot_w) / 2, (slot_len - slot_w) / 2):
        s += Pos(x, y + dy, z0) * Cylinder(slot_w / 2, h,
                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    return s

# ===================== BASE (layer 0) =====================
base = slab(plate_start, base_len, layer_z(0), plate_t)
base = add_leaves(base, hinge_a, knuckles_a, parity=0, layer=0, toward=+1)
base = bore(base, hinge_a)
base.label = "base"

# ===================== ARM (layer 1) =====================
arm = slab(plate_start, arm_len - plate_start, layer_z(1), plate_t)
arm -= slab(plate_start + arm_window_margin, arm_len - plate_start - arm_window_margin,
            layer_z(1) - 1, plate_t + 2, w=width - 2 * arm_window_margin)
arm = add_leaves(arm, hinge_a, knuckles_a, parity=1, layer=1, toward=+1)
arm = add_leaves(arm, hinge_b, knuckles_b, parity=0, layer=1, toward=-1)
arm = bore(bore(arm, hinge_a), hinge_b)
arm.label = "arm"

# ===================== TRAY (layer 2) =====================
tray = slab(tray_free_y, tray_end_y, layer_z(2), plate_t)
# front lip on the free end
tray += slab(tray_free_y, tray_free_y + lip_t, layer_z(2) + plate_t, lip_h)
# ventilation slots, centred on the open part of the tray
slot_y = (tray_free_y + lip_t + tray_end_y) / 2
for i in range(slot_count):
    sx = (i - (slot_count - 1) / 2) * slot_pitch
    tray -= rounded_slot(sx, slot_y, layer_z(2) - 1, plate_t + 2)
tray = add_leaves(tray, hinge_b, knuckles_b, parity=1, layer=2, toward=-1)
tray = bore(tray, hinge_b)
tray.label = "tray"

# ===================== PINS =====================
pin_a = x_cylinder(hinge_a, pin_r, width)
pin_a.label = "pin_a"
pin_b = x_cylinder(hinge_b, pin_r, width)
pin_b.label = "pin_b"

result = Compound(label="laptop_stand", children=[base, arm, tray, pin_a, pin_b])

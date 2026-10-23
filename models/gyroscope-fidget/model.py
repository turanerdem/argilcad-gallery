# Gyroscope rings — desk fidget (ready to print)
# Frame + 3 rings + a centre with a Seljuk-star window: all in one plane,
# joined by cone pins, printed in place as ONE PIECE. The stand prints
# separately; the frame's bottom bar slides into the slot in the stand.
# print_layout = True  → plate layout (the state to export)
# print_layout = False → standing on the desk, rings turned
#
# English translation of gyroscope_fidget.py for the gallery: same geometry.
from build123d import *
import math

print_layout = False

# --- Rings (mm) ---
t = 6.0            # ring and centre thickness (height when printing)
w = 4.0            # ring wall width
gap = 0.6          # radial gap between rings
R1 = 30.0          # outer radius of the outer ring
edge_round = 0.8   # edge rounding (also keeps the first layer from sticking)

# --- Cone pins ---
pin_r0, pin_r1 = 2.2, 0.7   # base / tip radius
pin_depth = 1.6             # how far a pin enters the outer part
clearance = 0.35            # print-in-place clearance

# --- Frame (printed flat together with the rings) ---
arm_w = 6.0
frame_t = 8.0               # height when printing, depth on the desk
arm_gap = 0.8               # between the outer ring and an arm
bar_h = 6.0                 # bottom bar (the part that goes into the stand)
bar_gap = 1.5               # between the turning outer ring and the bottom bar

# --- Stand (printed separately) ---
stand_t = 3.0
block_h = 5.0
slot_gap = 0.2              # bar to slot (if loose, a drop of glue)
slot_wall = 3.0

# Display angles on the desk
angle1, angle2, angle3, angle4 = 20, 55, 65, 55

K_SELJUK = math.cos(math.pi / 4) / math.cos(math.pi / 8)  # {8/2} star ratio
C, MIN = Align.CENTER, Align.MIN

# Radii: each ring sits inside the previous one, one gap apart
R1i = R1 - w
R2 = R1i - gap
R2i = R2 - w
R3 = R2i - gap
R3i = R3 - w
Rc = R3i - gap


def star(R, h, turn=0.0):
    pts = []
    for i in range(16):
        a = math.radians(turn + i * 22.5)
        r = R if i % 2 == 0 else R * K_SELJUK
        pts.append((r * math.cos(a), r * math.sin(a)))
    return extrude(Polygon(*pts, align=None), amount=h)


def ring(Ro, Ri):
    r = Cylinder(Ro, t) - Cylinder(Ri, t + 2)
    return fillet(r.edges().filter_by(GeomType.CIRCLE), radius=edge_round)


def cone(axis, start, direction, r0, r1, length):
    """axis 'x' or 'y'; start: position along the axis; direction: +1 / -1."""
    if axis == "x":
        place, rot = Pos(start, 0, 0), Rot(0, 90 * direction, 0)
    else:
        place, rot = Pos(0, start, 0), Rot(-90 * direction, 0, 0)
    return place * rot * Cone(r0, r1, length, align=(C, C, MIN))


def joint(inner, outer, axis, r_inner, r_outer):
    """Two pins on the inner part, two cone sockets in the outer — one turning axis."""
    L = (r_outer - r_inner) + 0.6 + pin_depth
    for s in (1, -1):
        inner += cone(axis, s * (r_inner - 0.6), s, pin_r0, pin_r1, L)
        outer -= cone(axis, s * (r_inner - 0.6), s, pin_r0 + clearance, pin_r1 + clearance, L + clearance)
    return inner, outer


# --- The gyroscope in the print plane (centre at the origin, bottom faces at z = -t/2) ---
ring1 = ring(R1, R1i)
ring2 = ring(R2, R2i)
ring3 = ring(R3, R3i)

centre = Cylinder(Rc, t)
centre = fillet(centre.edges().filter_by(GeomType.CIRCLE), radius=edge_round)
centre -= Pos(0, 0, -t) * star(Rc * 0.72, 2 * t, 22.5)

# Frame: two arms and a bottom bar, U-shaped
z0 = -t / 2
xa = R1 + arm_gap
xb = xa + arm_w
y_top = 4.0                                    # centre of an arm's end
y_bar = -(math.hypot(R1, t / 2) + bar_gap)     # top edge of the bar
y_bottom = y_bar - bar_h

frame = Pos(0, (y_bar + y_bottom) / 2, z0) * Box(2 * xb, bar_h, frame_t, align=(C, C, MIN))
for s in (1, -1):
    xc = s * (xa + arm_w / 2)
    frame += Pos(xc, (y_bottom + y_top) / 2, z0) * Box(arm_w, y_top - y_bottom, frame_t, align=(C, C, MIN))
    frame += Pos(xc, y_top, z0) * Cylinder(arm_w / 2, frame_t, align=(C, C, MIN))
inner_corners = [
    e for e in frame.edges().filter_by(Axis.Z)
    if abs(abs(e.center().X) - xa) < 0.01 and abs(e.center().Y - y_bar) < 0.01
]
frame = fillet(inner_corners, radius=3.0)

# Gimbal: frame–ring1 X, ring1–ring2 Y, ring2–ring3 X, ring3–centre Y
ring1, frame = joint(ring1, frame, "x", R1, xa)
ring2, ring1 = joint(ring2, ring1, "y", R2, R1i)
ring3, ring2 = joint(ring3, ring2, "x", R3, R2i)
centre, ring3 = joint(centre, ring3, "y", Rc, R3i)

# --- Stand (desk coordinates; z = 0 is the desk) ---
y_mid = -(z0 + frame_t / 2)          # middle of the depth once the frame stands up
block_L = 2 * xb + 2 * slot_gap + 2 * slot_wall
block_D = frame_t + 2 * slot_gap + 2 * slot_wall
stand_L, stand_D = block_L + 6, 30.0

stand = Pos(0, y_mid, 0) * extrude(SlotCenterToCenter(stand_L - stand_D, stand_D), amount=stand_t)
stand = fillet(stand.edges().group_by(Axis.Z)[-1], radius=1.2)
block = Pos(0, y_mid, stand_t) * Box(block_L, block_D, block_h, align=(C, C, MIN))
block = fillet(block.edges().filter_by(Axis.Z), radius=2.0)
stand += block
z_slot = stand_t + block_h - bar_h
slot = Box(2 * xb + 2 * slot_gap, frame_t + 2 * slot_gap, bar_h + 1, align=(C, C, MIN))
stand -= Pos(0, y_mid, z_slot) * slot

if print_layout:
    # Plate: the gyroscope lies flat (every bottom face at z = 0), the stand beside it
    up = Pos(0, 0, t / 2)
    frame, ring1, ring2, ring3, centre = (up * p for p in (frame, ring1, ring2, ring3, centre))
    stand = Pos(0, y_bottom - 6 - stand_D / 2 - y_mid, 0) * stand
else:
    # Desk: frame upright, bottom bar at the bottom of the slot; rings turned
    H = z_slot - y_bottom
    D = Pos(0, 0, H) * Rot(90, 0, 0)
    T1 = D * Rot(angle1, 0, 0)
    T2 = T1 * Rot(0, angle2, 0)
    T3 = T2 * Rot(angle3, 0, 0)
    T4 = T3 * Rot(0, angle4, 0)
    frame = D * frame
    ring1 = T1 * ring1
    ring2 = T2 * ring2
    ring3 = T3 * ring3
    centre = T4 * centre

frame.label = "frame"
ring1.label = "ring_1"
ring2.label = "ring_2"
ring3.label = "ring_3"
centre.label = "centre"
stand.label = "stand"

result = Compound(label="gyroscope", children=[stand, frame, ring1, ring2, ring3, centre])

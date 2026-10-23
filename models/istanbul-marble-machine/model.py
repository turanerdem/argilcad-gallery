# Istanbul Marble Machine — a kinetic desk piece.
#
# Turn the crank on the star gear: four low-poly Istanbul cats spin on their
# gears, and the gear train winds the screw lift inside the Galata Tower. A
# marble rises inside the tower, rolls out over the Bosphorus Bridge,
# spirals down round the Maiden's Tower on its rock and comes home along
# the aqueduct.
#
# Seen from above the marble runs a belt round two pulleys: counter-
# clockwise round the lift and counter-clockwise down the spiral, the bridge
# and the aqueduct being the belt's two straight runs.
import math

from build123d import *
from bd_warehouse.gear import SpurGear

# ---------------------------------------------------------------- parameters
MARBLE_D = 16.0            # a standard glass marble
MOD = 1.5                  # one module for every gear
GEAR_T = 6.0               # gear thickness
GEAR_Z = GEAR_T / 2 + 0.5  # gear centre height: 0.5 mm clear of the base
GEAR_TOP = GEAR_Z + GEAR_T / 2
PEG_R, BORE_R = 3.0, 3.2   # base pegs, gear bores
SLOPE = math.radians(4.0)  # chute slope
CHUTE_W = MARBLE_D + 3     # channel width between the lips
LIP, FLOOR = 7.0, 2.5      # channel lip height, floor thickness

TOWER = Vector(-85, 30, 0)    # Galata Tower centre
MAIDEN = Vector(80, 30, 0)    # Maiden's Tower centre
CENTRE = Vector(-25, -45, 0)  # crank gear centre

TOWER_R, TOWER_IN = 27.0, 23.0     # tower wall
LIFT_SHAFT_R, FLIGHT_R = 5.0, 16.5  # screw lift
LIFT_PITCH = 24.0
MARBLE_RUN_R = TOWER_IN - MARBLE_D / 2  # the marble's radius in the lift
RIB_IN = 17.5                       # the stop rib's inner edge
INNER_FLOOR = 10.0                  # lift floor top, the intake level
DOOR_W, DOOR_H = 22.0, MARBLE_D + 5

SPIRAL_R = 30.0               # marble path radius round the Maiden's Tower
SPIRAL_PITCH = 24.0
CORE = 11.0                   # the Maiden's Tower's half-width
SPIRAL_OUT = SPIRAL_R + CHUTE_W / 2 + 2  # outer edge of the spiral floor

Z_CAT, Z_CENTRE, Z_IDLER, Z_LIFT = 18, 36, 16, 26  # tooth counts


# ------------------------------------------------------------------- helpers
def pitch_r(teeth):
    return MOD * teeth / 2


def unit(v):
    return v / v.length


def angle_of(v):
    return math.degrees(math.atan2(v.Y, v.X))


def radial(angle_deg, r, z=0.0):
    a = math.radians(angle_deg)
    return Vector(r * math.cos(a), r * math.sin(a), z)


def up(r, h):
    """A cylinder standing on z = 0."""
    return Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def arch_cutter(width, height, depth):
    """An arched opening, its sill on z = 0, cutting along X."""
    body = Box(depth, width, height - width / 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    top = Pos(0, 0, height - width / 2) * Rot(0, 90, 0) * Cylinder(width / 2, depth)
    # Nothing below the sill, however squat the arch.
    return (body + top) & Box(depth, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def eight_point_star(size, height):
    """The Seljuk star: two squares, one turned 45 degrees."""
    sq = Rectangle(size, size)
    return extrude(sq + Rot(0, 0, 45) * sq, height)


# The Studio finds hinges and gears from round faces on a common axis. Only
# the moving parts may have them there, so the tower's bearings are
# polygons, and so are the cuts that fit the chutes round other parts.
def bearing(clearance, height):
    """A 16-sided hole for the lift shaft."""
    r = (LIFT_SHAFT_R + clearance) / math.cos(math.pi / 16)
    return extrude(RegularPolygon(r, 16), height)


def round_cut(r, height):
    """A 64-sided prism standing in for a cylinder of radius r."""
    return extrude(RegularPolygon(r / math.cos(math.pi / 64), 64), height)


def ring(cx, cy, rx, ry, z, n=6, turn=0.0):
    """A low-poly section: an n-gon on an ellipse, level at height z."""
    return Wire.make_polygon([Vector(cx + rx * math.cos(a), cy + ry * math.sin(a), z)
                                for a in (math.radians(turn + 360 * i / n) for i in range(n))], close=True)


def facets(*sections):
    """A faceted solid through low-poly sections, flat face to flat face."""
    return Solid.make_loft(list(sections), ruled=True)


def gear(teeth, turn=0.0):
    g = SpurGear(module=MOD, tooth_count=teeth, pressure_angle=20, thickness=GEAR_T)
    return Rot(0, 0, turn) * (g - Cylinder(BORE_R, 2 * GEAR_T))


def mesh_turn(at, driver_at, driver_teeth, driver_turn, teeth):
    """The turn that puts a gap of this gear on the driver's tooth."""
    g = angle_of(at - driver_at)
    f_driver = (g - driver_turn) * driver_teeth / 360
    return (g + 180) - (0.5 - f_driver) * 360 / teeth


def chute(a, b, za, zb):
    """A straight channel from a to b, its floor top at za and zb."""
    run = b - a
    length = run.length
    pitch = math.degrees(math.atan2(zb - za, length))
    profile = (Box(length, CHUTE_W + 4, FLOOR + LIP, align=(Align.MIN, Align.CENTER, Align.MIN))
                - Pos(0, 0, FLOOR) * Box(length, CHUTE_W, LIP, align=(Align.MIN, Align.CENTER, Align.MIN)))
    return Pos(a.X, a.Y, za) * Rot(0, 0, angle_of(run)) * Rot(0, -pitch, 0) * Pos(0, 0, -FLOOR) * profile


# ------------------------------------------------------------ marble circuit
to_m = MAIDEN - TOWER
D = to_m.length
u = unit(to_m)
north = Vector(-u.Y, u.X, 0)

# The bridge leaves the lift radially and meets the spiral's south side.
half = math.degrees(math.asin(SPIRAL_R / D))
EXIT_ANGLE = angle_of(to_m) - half
e = radial(EXIT_ANGLE, 1)
bridge_start = TOWER + e * (TOWER_R + 0.3)
bridge_end = TOWER + e * math.sqrt(D * D - SPIRAL_R * SPIRAL_R)

# The aqueduct is the belt's other run: tangent to the spiral's north side
# and to the marble's circle in the tower, entering it running the way the
# lift turns.
k = (SPIRAL_R - MARBLE_RUN_R) / D
n = u * (-k) + north * math.sqrt(1 - k * k)
aqueduct_end = MAIDEN + n * SPIRAL_R           # leaves the spiral here
touch = TOWER + n * MARBLE_RUN_R                # would touch the lift circle here
a_dir = unit(touch - aqueduct_end)
# Where the run crosses the tower's outer wall.
rel = aqueduct_end - TOWER
bq = rel.dot(a_dir)
aqueduct_start = aqueduct_end + a_dir * (-bq - math.sqrt(bq * bq - (rel.dot(rel) - (TOWER_R + 0.3) ** 2)))
INTAKE_ANGLE = angle_of(aqueduct_start - TOWER)

bridge_len = (bridge_end - bridge_start).length
aqueduct_len = (aqueduct_start - aqueduct_end).length

# Down the spiral, counter-clockwise, from the bridge to the aqueduct.
ang_top = angle_of(bridge_end - MAIDEN)
ang_bot = angle_of(aqueduct_end - MAIDEN)
spiral_turn = 3 * 360 + (ang_bot - ang_top) % 360

# Heights, from the intake up.
Z_INTAKE = INNER_FLOOR + 0.5
Z_SPIRAL_BOT = Z_INTAKE + aqueduct_len * math.tan(SLOPE)
Z_SPIRAL_TOP = Z_SPIRAL_BOT + SPIRAL_PITCH * spiral_turn / 360
Z_EXIT = Z_SPIRAL_TOP + bridge_len * math.tan(SLOPE)
BODY_TOP = Z_EXIT + DOOR_H + 8

# The marble rides the lift against one stop rib, just counter-clockwise of
# the exit: the lift's turning floor carries it round until the rib stops
# it, and the flight lifts it straight up to the exit door. 33 degrees puts
# a resting marble's centre on the exit's line.
RIB_ANGLE = EXIT_ANGLE + 33

# ---------------------------------------------------------------- gear layout
cat_at = [CENTRE + radial(a, pitch_r(Z_CENTRE) + pitch_r(Z_CAT)) for a in (45, 135, 225, 315)]
cat_turn = [mesh_turn(p, CENTRE, Z_CENTRE, 0.0, Z_CAT) for p in cat_at]

# The idler joins the back-left cat's gear to the lift gear under the tower.
d2 = cat_at[1]
r_a = pitch_r(Z_CAT) + pitch_r(Z_IDLER)
r_b = pitch_r(Z_LIFT) + pitch_r(Z_IDLER)
span = TOWER - d2
dist = span.length
along = (r_a ** 2 - r_b ** 2 + dist ** 2) / (2 * dist)
off = math.sqrt(max(r_a ** 2 - along ** 2, 0))
idler_at = d2 + span / dist * along - Vector(-span.Y, span.X, 0) / dist * off
idler_turn = mesh_turn(idler_at, d2, Z_CAT, cat_turn[1], Z_IDLER)
lift_turn = mesh_turn(TOWER, idler_at, Z_IDLER, idler_turn, Z_LIFT)

# ------------------------------------------------------------------- the base
base = Pos(0, -5, -8) * Box(250, 180, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
base = chamfer(base.edges().group_by(Axis.Z)[-1], 2)
# Every gear's bore is capped, and hangs on its peg's tip, clear of the base.
for p in [CENTRE, idler_at, *cat_at]:
    base += Pos(p.X, p.Y, 0) * up(PEG_R, GEAR_TOP)
# The lift's pin is tapered: a round one on the tower's axis would read as a
# hinge between the base and the tower.
base += Pos(TOWER.X, TOWER.Y, 0) * Cone(PEG_R, PEG_R - 0.6, GEAR_TOP,
                                            align=(Align.CENTER, Align.CENTER, Align.MIN))
# A Seljuk star inlaid in the front right corner.
STAR = Vector(85, -65, -1)
base -= Pos(STAR) * eight_point_star(34, 2)
base += Pos(STAR) * Rot(0, 0, 22.5) * eight_point_star(16, 1)
base.label = "base"

# ------------------------------------------------------------ the Galata Tower
T = Pos(TOWER.X, TOWER.Y, 0)
tower = T * (up(TOWER_R, BODY_TOP) - up(TOWER_IN, BODY_TOP))
# The stop rib, standing just clear of the lift's turning floor.
tower += T * Pos(0, 0, INNER_FLOOR + 0.3) * Rot(0, 0, RIB_ANGLE) * Pos(RIB_IN, 0, 0) * Box(
    TOWER_IN + 0.5 - RIB_IN, 3, Z_EXIT + DOOR_H - INNER_FLOOR - 0.3, align=(Align.MIN, Align.CENTER, Align.MIN))
# Roof slab with the lift's top bearing, and the cornice round it.
tower += T * Pos(0, 0, BODY_TOP - 4) * (up(TOWER_R + 2.5, 4) - bearing(0.4, 4))
# The arcaded gallery, the conical cap and its finial.
gallery = T * Pos(0, 0, BODY_TOP) * (up(TOWER_R - 1, 16) - up(TOWER_R - 4, 16))
for i in range(16):
    gallery -= T * Pos(0, 0, BODY_TOP + 3) * Rot(0, 0, i * 22.5) * Pos(TOWER_R - 2.5, 0, 0) * arch_cutter(5, 10, 8)
tower += gallery
tower += T * Pos(0, 0, BODY_TOP + 16) * (up(TOWER_R + 2, 3) - up(TOWER_R - 4, 3))
CAP_Z = BODY_TOP + 19
tower += T * Pos(0, 0, CAP_Z) * Cone(TOWER_R + 1, 1.5, 38, align=(Align.CENTER, Align.CENTER, Align.MIN))
tower += T * Pos(0, 0, CAP_Z + 37) * Cone(1.6, 0.8, 7, align=(Align.CENTER, Align.CENTER, Align.MIN))
tower += T * Pos(0, 0, CAP_Z + 45) * Sphere(2)


def in_wall(angle, z):
    return T * Pos(0, 0, z) * Rot(0, 0, angle) * Pos(TOWER_R - 2, 0, 0)


# The intake: the marble comes in along the wall, so it is a long gate cut
# along its run, through the wall and the rib's outer end (the marble stops
# against its inner edge). Then the exit door above the rib, and slit
# windows between them to watch the marble climb.
gate_len = (touch - aqueduct_start).length + 6
gate_mid = aqueduct_start + a_dir * (gate_len / 2 - 6)
gate = Pos(gate_mid.X, gate_mid.Y, INNER_FLOOR) * Rot(0, 0, angle_of(a_dir)) * arch_cutter(DOOR_W, DOOR_H, gate_len)
tower -= gate & T * (up(TOWER_R + 1, BODY_TOP) - up(RIB_IN + 1.5, BODY_TOP))
tower -= in_wall(EXIT_ANGLE, Z_EXIT) * arch_cutter(DOOR_W, DOOR_H, 12)
for z in range(int(INNER_FLOOR + DOOR_H + 6), int(Z_EXIT - 20), 26):
    tower -= in_wall(EXIT_ANGLE, z) * arch_cutter(7, 18, 12)
# Arched windows round the rest of the body, clear of the rib and the slits.
for level in (40, 70, 100):
    for i in range(8):
        a = EXIT_ANGLE + 22.5 + i * 45
        near = min(abs((a - b + 180) % 360 - 180) for b in (EXIT_ANGLE, RIB_ANGLE))
        if near > 30 and level + 16 < BODY_TOP - 6:
            tower -= in_wall(a, level) * arch_cutter(6, 14, 10)
# The idler reaches the lift gear through a slot at the foot of the wall.
tower -= Pos(idler_at.X, idler_at.Y, 0) * round_cut(pitch_r(Z_IDLER) + MOD + 1.5, INNER_FLOOR - 2.5)
tower.label = "galata_tower"

# ------------------------------------------------------------------ the lift
# One piece: gear, turning floor, shaft and flight. The tower slides down
# over it, and its roof bearing takes the shaft's top.
#
# A left-hand screw: turning counter-clockwise (seen from above) it lifts a
# marble that the rib holds still. The flight leans outward, so the marble
# rides against the wall and rolls out at the door by itself. It is lofted
# through radial sections rather than swept: a swept helix is a B-spline
# whose poles stand far off the surface, and the Studio reads a gear's size
# from its part's box. Its leading edge is thin, to slip under a marble.
flight_h = Z_EXIT - Z_INTAKE - 2.5
flight_turns = flight_h / LIFT_PITCH
flight_n = int(flight_turns * 24)
sections = []
for i in range(flight_n + 1):
    th = -2 * math.pi * flight_turns * i / flight_n  # clockwise as it climbs
    z = flight_h * i / flight_n
    t = min(3.0, 0.8 + 2.2 * i / 4)                  # the lead-in thickens
    sections.append(Wire.make_polygon(
        [Vector(r * math.cos(th), r * math.sin(th), z + dz)
            for r, dz in ((4.5, 1.7), (FLIGHT_R, 0), (FLIGHT_R, t), (4.5, 1.7 + t))], close=True))
lift = Pos(TOWER.X, TOWER.Y, GEAR_Z) * gear(Z_LIFT, lift_turn)
lift += T * Pos(0, 0, GEAR_TOP) * up(LIFT_SHAFT_R, BODY_TOP - 0.5 - GEAR_TOP)
# The floor: no wider than the gear, whose size the Studio reads the ratio by.
lift += T * Pos(0, 0, INNER_FLOOR - 2) * up(pitch_r(Z_LIFT) + MOD, 2)
lift += T * Pos(0, 0, Z_INTAKE) * Solid.make_loft(sections, ruled=True)
lift.label = "screw_lift"

# ----------------------------------------------------------------- gears, cats
idler = Pos(idler_at.X, idler_at.Y, GEAR_Z) * gear(Z_IDLER, idler_turn)
idler += Pos(idler_at.X, idler_at.Y, GEAR_TOP) * up(5, 1)  # caps the bore
idler.label = "idler_gear"

C = Pos(CENTRE.X, CENTRE.Y, 0)
crank = Pos(CENTRE.X, CENTRE.Y, GEAR_Z) * gear(Z_CENTRE)
crank += C * Pos(0, 0, GEAR_TOP) * up(8, 3)  # caps the bore
crank += C * Pos(0, 0, GEAR_TOP) * eight_point_star(26, 3)
crank -= C * Pos(0, 0, GEAR_TOP + 1.5) * Rot(0, 0, 22.5) * eight_point_star(12, 2)
crank += C * Pos(19, 0, GEAR_TOP) * up(3.5, 16)
crank += C * Pos(19, 0, GEAR_TOP + 16) * Sphere(4.5)
crank.label = "crank_gear"


def cat(at, turn, pose):
    """A low-poly Istanbul street cat sitting up on a gear, its tail curled
    round its front paws. Every face is flat; it stays inside the gear's
    tips, whose size the Studio reads the ratio by."""
    c = facets(ring(-1.5, 0, 7, 6, 0), ring(-1.2, 0, 6.6, 5.6, 6),
                ring(0.3, 0, 4.8, 4.4, 13), ring(1.8, 0, 3, 3, 18))            # body
    for y in (-2.3, 2.3):                                                     # front legs
        c += facets(ring(5.2, y, 1.5, 1.5, 0, 4, 45), ring(3.6, y, 1.2, 1.2, 13, 4, 45))
    c += facets(ring(2.4, 0, 2.6, 2.6, 17), ring(3.4, 0, 4.6, 5.0, 21),
                ring(3.6, 0, 4.2, 4.6, 25), ring(2.8, 0, 2.2, 2.8, 28))        # head
    for y in (-1, 1):                                                         # ears
        c += facets(ring(2.6, 2.6 * y, 2.3, 1.9, 26, 3, 90), ring(2.4, 3.1 * y, 0.35, 0.35, 30.5, 3, 90))
    tail = [(-7.8, 0), (-6.4, 4.8), (-2, 7.6), (3, 7.2), (7, 4.6)]
    for (x0, y0), (x1, y1) in zip(tail, tail[1:]):
        run = Vector(x1 - x0, y1 - y0, 0)
        c += Pos((x0 + x1) / 2, (y0 + y1) / 2, 1.3) * Rot(0, 0, angle_of(run)) * Box(run.length + 2.6, 2.6, 2.6)
    return Pos(at.X, at.Y, GEAR_Z) * gear(Z_CAT, turn) + Pos(at.X, at.Y, GEAR_TOP) * Rot(0, 0, pose) * c


cats = []
for i, (p, t) in enumerate(zip(cat_at, cat_turn)):
    c = cat(p, t, pose=i * 90 + 30)
    c.label = f"cat_{i + 1}"
    cats.append(c)

# ------------------------------------------------- the Maiden's Tower, its rock
# Every face here is flat or conical: a round face on its axis would offer
# the tower as a hinge or a gear in the Studio.
Mk = Pos(MAIDEN.X, MAIDEN.Y, 0)
ISLAND_H = 12.0  # under the spiral's lowest turn
# A low-poly rock: an uneven nine-sided slab with sloping sides, and three
# boulders at its foot.
rock = zip(range(0, 360, 40), (40, 43, 38, 42, 39, 44, 37, 41, 40))
island = Mk * extrude(Polygon(*[(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a, r in rock],
                                align=None), ISLAND_H, taper=35)
for a, r, size in ((20, 40, 7), (150, 40, 6), (265, 39, 8)):
    island += Mk * Pos(radial(a, r)) * extrude(RegularPolygon(size, 5, rotation=a), size * 0.7, taper=35)
island.label = "island"


def chamfered_square(half, cut):
    return Polygon((half, cut - half), (half, half - cut), (half - cut, half), (cut - half, half),
                    (-half, half - cut), (-half, cut - half), (cut - half, -half), (half - cut, -half), align=None)


# The square stone tower, the spiral wound round it, then above the
# spiral's head its windows, the gallery, the lantern and the lead cap.
BODY_Z = Z_SPIRAL_TOP + LIP + 20
maiden = Mk * Pos(0, 0, ISLAND_H) * extrude(chamfered_square(CORE, 3), BODY_Z - ISLAND_H)
for a in (0, 90, 180, 270):
    for z in (BODY_Z - 16, BODY_Z - 30):
        maiden -= Mk * Pos(0, 0, z) * Rot(0, 0, a) * Pos(CORE, 0, 0) * arch_cutter(4, 10, 4)
maiden += Mk * Pos(0, 0, BODY_Z) * extrude(chamfered_square(CORE + 3, 4), 3)            # cornice
maiden += Mk * Pos(0, 0, BODY_Z + 3) * (extrude(chamfered_square(CORE + 3, 4), 3)
                                        - extrude(chamfered_square(CORE + 1.8, 3.4), 3))  # parapet
DRUM_Z = BODY_Z + 3
maiden += Mk * Pos(0, 0, DRUM_Z) * extrude(RegularPolygon(9, 8), 16)                    # lantern
for i in range(4):
    maiden -= Mk * Pos(0, 0, DRUM_Z + 4) * Rot(0, 0, 22.5 + 90 * i) * Pos(9 * math.cos(math.pi / 8), 0, 0) * arch_cutter(3.5, 9, 3)
maiden += Mk * Pos(0, 0, DRUM_Z + 16) * extrude(RegularPolygon(10.5, 8), 2)
CAP_TOP = DRUM_Z + 18
maiden += Mk * Pos(0, 0, CAP_TOP) * Cone(9.5, 0.6, 22, align=(Align.CENTER, Align.CENTER, Align.MIN))  # lead cap
maiden += Mk * Pos(0, 0, CAP_TOP + 21) * Box(1.2, 1.2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))  # flagpole
maiden += Mk * Pos(0, 0, CAP_TOP + 35) * Sphere(1.2)
maiden += Mk * Pos(0.6, 0, CAP_TOP + 28) * Box(10, 0.8, 6.5, align=(Align.MIN, Align.CENTER, Align.MIN))  # flag

# The spiral chute, climbing clockwise from its foot (where the aqueduct
# leaves) to its head (where the bridge arrives): the marble runs it
# counter-clockwise, downward.
spiral_path = Helix(SPIRAL_PITCH, SPIRAL_PITCH * spiral_turn / 360, SPIRAL_R, lefthand=True)
spiral_profile = Plane.XZ * Polygon(
    (CORE - 0.5, -FLOOR), (SPIRAL_OUT, -FLOOR), (SPIRAL_OUT, LIP), (SPIRAL_OUT - 2, LIP),
    (SPIRAL_OUT - 2, 0), (CORE - 0.5, 0), align=None)
maiden += Mk * Pos(0, 0, Z_SPIRAL_BOT) * Rot(0, 0, ang_bot) * sweep(spiral_profile, path=spiral_path, is_frenet=True)
maiden.label = "maidens_tower"

# ---------------------------------------------------------- the Bosphorus Bridge
# The deck is the chute; two portal towers carry it and the main cables.
# Both chutes stop 1 mm short of the spiral, whose section meets them at a
# slant.
b_dir = unit(bridge_end - bridge_start)
bridge = chute(bridge_start, bridge_end - b_dir * 1.0, Z_EXIT, Z_SPIRAL_TOP)
b_side = Vector(-b_dir.Y, b_dir.X, 0)
b_heading = angle_of(b_dir)
LEG = CHUTE_W / 2 + 2 + 3
PYLON_H = 55


def deck_z(s):
    return Z_EXIT + (Z_SPIRAL_TOP - Z_EXIT) * s / bridge_len


pylons = [36.0, bridge_len - 44]
for s in pylons:
    at = bridge_start + b_dir * s
    under = deck_z(s) - FLOOR - 0.3
    for side in (-1, 1):
        leg = at + b_side * (side * LEG)
        bridge += Pos(leg.X, leg.Y, 0) * Rot(0, 0, b_heading) * Box(
            5, 5, under + PYLON_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for z, h in ((under - 5, 5), (under + PYLON_H / 2, 4), (under + PYLON_H - 5, 4)):
        bridge += Pos(at.X, at.Y, z) * Rot(0, 0, b_heading) * Box(
            4, 2 * LEG + 5, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
# Main cables: straight side spans, a sagging main span, and hangers.
tops = [deck_z(s) - FLOOR + PYLON_H - 1 for s in pylons]
mid = sum(pylons) / 2
low = deck_z(mid) + LIP + 5
for side in (-1, 1):
    def on_cable(s, z):
        p = bridge_start + b_dir * s + b_side * (side * LEG)
        return Vector(p.X, p.Y, z)
    pts = [on_cable(0, deck_z(0) + LIP), on_cable(pylons[0], tops[0])]
    for i in range(1, 8):
        f = i / 8
        s = pylons[0] + (pylons[1] - pylons[0]) * f
        z = (1 - f) * tops[0] + f * tops[1] - 4 * f * (1 - f) * ((tops[0] + tops[1]) / 2 - low)
        pts.append(on_cable(s, z))
        if i % 2 == 0:  # a hanger down to the deck lip
            bottom = deck_z(s) + LIP - 0.5
            bridge += Pos(on_cable(s, bottom)) * up(0.6, z - bottom)
    pts += [on_cable(pylons[1], tops[1]), on_cable(bridge_len, deck_z(bridge_len) + LIP)]
    for a, b in zip(pts, pts[1:]):
        bridge += Pos(a) * Solid.make_cylinder(0.9, (b - a).length, Plane((0, 0, 0), z_dir=b - a))
bridge -= T * round_cut(TOWER_R + 0.2, BODY_TOP)  # the deck ends on the tower
bridge -= island                                   # and its legs stand on the rock
bridge.label = "bosphorus_bridge"

# ------------------------------------------------------------- the aqueduct
# The return chute on a row of arches, like Bozdogan's.
aqueduct = chute(aqueduct_end + a_dir * 1.0, aqueduct_start, Z_SPIRAL_BOT, Z_INTAKE)
steps = int(aqueduct_len // 12)
for i in range(steps):
    s0, s1 = i * aqueduct_len / steps, (i + 1) * aqueduct_len / steps
    z_top = Z_SPIRAL_BOT + (Z_INTAKE - Z_SPIRAL_BOT) * s1 / aqueduct_len - FLOOR - 0.3
    pier = Box(s1 - s0 + 0.2, CHUTE_W - 2, z_top, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if z_top > 9:
        pier -= Rot(0, 0, 90) * arch_cutter(s1 - s0 - 4, z_top - 3, CHUTE_W)
    p = aqueduct_end + a_dir * ((s0 + s1) / 2)
    aqueduct += Pos(p.X, p.Y, 0) * Rot(0, 0, angle_of(a_dir)) * pier
aqueduct -= T * round_cut(TOWER_R + 0.2, BODY_TOP)
aqueduct -= island  # its piers stand on the rock
aqueduct.label = "aqueduct"

# The Bosphorus round the rock: a thin low-poly sheet to colour as water,
# inside the base's chamfer and holed for the piers and the bridge's legs.
water = zip(range(0, 360, 30), (56, 60, 54, 58, 52, 57, 55, 60, 53, 58, 56, 54))
sea = Mk * extrude(Polygon(*[(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a, r in water],
                            align=None), 1.2)
sea &= Pos(0, -5, 0) * Box(244, 174, 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
sea -= island
sea -= bridge
sea -= aqueduct
sea.label = "sea"


# ---------------------------------------------------------------- the marbles
def marble(p, z_floor):
    return Pos(p.X, p.Y, z_floor + MARBLE_D / 2 + 0.2) * Sphere(MARBLE_D / 2)


m1 = marble(bridge_start + b_dir * (bridge_len * 0.62), deck_z(bridge_len * 0.62))
m2 = marble(MAIDEN + radial(ang_bot + 150, SPIRAL_R), Z_SPIRAL_BOT + SPIRAL_PITCH * 210 / 360)
m3 = marble(aqueduct_end + a_dir * (aqueduct_len * 0.55), Z_SPIRAL_BOT + (Z_INTAKE - Z_SPIRAL_BOT) * 0.55)
marbles = [m1, m2, m3]
for i, m in enumerate(marbles):
    m.label = f"marble_{i + 1}"

result = Compound(label="istanbul_marble_machine",
                    children=[base, tower, lift, idler, crank, *cats, sea, island, maiden, bridge, aqueduct, *marbles])

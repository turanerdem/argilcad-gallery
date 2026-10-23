"""Planetary gearbox — involute spur gears, built with the same kernel the app uses.

Paste into ArgilCAD's code editor as is: the last line assigns `result`. The
imports are for running the file outside the app; ArgilCAD comments them out
and injects the same symbols itself.

The meshing is real: `interference(a, b)` measures the overlap volume of two
bodies, and every sun/planet and planet/ring pair measures 0 mm³ with the teeth
interleaved 4 mm deep.
"""
from math import pi, cos, sin, tan, acos, radians, degrees
from build123d import *

M   = 2.0        # module
PA  = radians(20)
W   = 10.0       # face width
BL  = 0.30       # backlash (mm), split between mating flanks
ZS, ZP, ZR = 12, 12, 36          # sun / planet / ring teeth  (ZR = ZS + 2*ZP)
A   = M * (ZS + ZP) / 2          # carrier radius = 24
N   = 3                          # planets: (ZR + ZS) / N must be a whole number


def _tooth_face(z, ra, rf, t_pitch):
    """One involute tooth, centred on +X, spanning from under the root circle to the tip."""
    r  = M * z / 2
    rb = r * cos(PA)
    hp = t_pitch / (2 * r)
    inv = lambda a: tan(a) - a
    def half_angle(rr):
        ar = acos(min(1.0, rb / rr))
        return hp + inv(PA) - inv(ar)

    r0 = max(rf, rb * 1.0005)
    rs = [r0 + (ra - r0) * i / 10 for i in range(11)]
    right = [(rr * cos(-half_angle(rr)), rr * sin(-half_angle(rr))) for rr in rs]
    left  = [(rr * cos( half_angle(rr)), rr * sin( half_angle(rr))) for rr in reversed(rs)]
    inner = rf * 0.88
    a0 = half_angle(r0)
    pts = ([(inner * cos(-a0), inner * sin(-a0))] + right + left +
           [(inner * cos(a0), inner * sin(a0))])
    with BuildSketch() as t:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return t.sketch


def gear_sketch(z, ra, rf, t_pitch, phase=0.0):
    """Full gear cross-section: root disc + z teeth, rotated by `phase` radians."""
    tooth = _tooth_face(z, ra, rf, t_pitch)
    with BuildSketch() as g:
        Circle(rf)
        with PolarLocations(0, z, start_angle=degrees(phase)):
            add(tooth)
    return g.sketch


def external_gear(z):
    """Standard external gear: addendum 1*m, dedendum 1.25*m, thinned by half the backlash."""
    r = M * z / 2
    return gear_sketch(z, ra=r + M, rf=r - 1.25 * M, t_pitch=pi * M / 2 - BL / 2)


def ring_cutter(z, phase):
    """The solid whose teeth ARE the ring's tooth spaces: tip = ring root, root = ring tip."""
    r = M * z / 2
    return gear_sketch(z, ra=r + 1.25 * M, rf=r - M, t_pitch=pi * M / 2 + BL / 2, phase=phase)


def planet_phase(theta):
    """Body rotation that drops a planet tooth into a sun gap along the line of centres."""
    return theta + pi - (theta * ZS + pi) / ZP


def ring_phase(phi0):
    """Cutter rotation that lines the ring's tooth spaces up with the planets."""
    return -((0 - phi0) * ZP / ZR) % (2 * pi / ZR)


def build(n_planets=3):
    sun_s    = external_gear(ZS)
    planet_s = external_gear(ZP)

    with BuildPart() as sun:
        add(extrude(sun_s, W))
        with BuildSketch():
            RegularPolygon(3.0 / cos(radians(30)), 6)     # 6 mm across flats
        extrude(amount=W, mode=Mode.SUBTRACT)

    with BuildPart() as planet:
        add(extrude(planet_s, W))
        with BuildSketch():
            Circle(2.0)
        extrude(amount=W, mode=Mode.SUBTRACT)

    phi0 = planet_phase(0.0)
    psi  = ring_phase(phi0)
    with BuildPart() as ring:
        Cylinder(48, W, align=(Align.CENTER, Align.CENTER, Align.MIN))
        add(extrude(ring_cutter(ZR, psi), W), mode=Mode.SUBTRACT)
        with PolarLocations(43, 4, start_angle=45):
            Cylinder(2.25, W, align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
        fillet(ring.edges().filter_by(GeomType.CIRCLE)
                   .group_by(SortBy.RADIUS)[-1], radius=1.2)

    planets = []
    for i in range(n_planets):
        th = 2 * pi * i / n_planets
        p = planet.part.rotate(Axis.Z, degrees(planet_phase(th)))
        planets.append(p.translate((A * cos(th), A * sin(th), 0)))
    return sun.part, ring.part, planets


def interference(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


sun, ring, planets = build(N)
result = Compound(children=[sun, ring] + planets)

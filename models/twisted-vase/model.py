"""Twisted vase — a vase-mode favourite, built on the same kernel ArgilCAD runs.

Paste into ArgilCAD's code editor as is: the last line assigns `result`.
"""
from math import sin, cos, pi
from build123d import *

height = 120.0   # mm
radius = 34.0    # widest point (hexagon circumradius), mm
sides  = 6
twist  = 60      # degrees, bottom to top
wall   = 1.6     # mm, across the flats
base   = 2.0     # floor thickness, mm
corner = 6.0     # corner rounding, mm
steps  = 10      # loft sections


def section(z, inset=0.0, fillet_r=corner):
    """Rounded polygon at height z, turned by its share of the twist."""
    u = z / height
    r = radius * (0.72 + 0.28 * sin(pi * (0.15 + 0.85 * u))) - inset
    with BuildSketch(Plane.XY.offset(z)) as s:
        RegularPolygon(r, sides, rotation=twist * u)
        fillet(s.vertices(), radius=fillet_r)
    return s.sketch.faces()[0]


outer = loft([section(height * i / steps) for i in range(steps + 1)])

# insetting the circumradius by wall/cos(pi/n) leaves exactly `wall` across the flats
inset = wall / cos(pi / sides)
inner = loft([section(base + (height + 1 - base) * i / steps, inset, corner - wall)
              for i in range(steps + 1)])

result = outer - inner

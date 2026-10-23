"""Electronics enclosure — 80 × 60 × 30 mm, 2 mm walls, four M3 screw bosses.

The first ArgilCAD marketing model (X post, 2026-09-08), rebuilt from the code
visible in the app screenshot that post used.
"""
from build123d import *

corner = 4      # vertical edge fillet, mm
wall   = 2      # mm

with BuildPart() as builder:
    Box(80, 60, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fillet(builder.edges().filter_by(Axis.Z), radius=corner)
    top = builder.faces().sort_by(Axis.Z)[-1]
    offset(amount=-wall, openings=top)
    with Locations((34, 24, wall), (-34, 24, wall), (34, -24, wall), (-34, -24, wall)):
        Cylinder(radius=4, height=26, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(radius=1.6, height=26, align=(Align.CENTER, Align.CENTER, Align.MIN),
                 mode=Mode.SUBTRACT)
result = builder

"""Ordered element-type sets for explicit query membership tests.

These sets classify tool/component types, independently of IsIndependent or
IncludeSubElemObjects. Group, Hotlink, and CamSet containers and the Unknown
sentinel are intentionally outside the presets; individual cameras remain 2D.
"""

from multiconn_archicad.models.tapir import types as tapir


TYPES_3D: tuple[tapir.ElementType, ...] = (
    tapir.ElementType.WALL,
    tapir.ElementType.COLUMN,
    tapir.ElementType.BEAM,
    tapir.ElementType.WINDOW,
    tapir.ElementType.DOOR,
    tapir.ElementType.OBJECT,
    tapir.ElementType.LAMP,
    tapir.ElementType.SLAB,
    tapir.ElementType.ROOF,
    tapir.ElementType.MESH,
    tapir.ElementType.ZONE,
    tapir.ElementType.CURTAIN_WALL,
    tapir.ElementType.SHELL,
    tapir.ElementType.SKYLIGHT,
    tapir.ElementType.MORPH,
    tapir.ElementType.STAIR,
    tapir.ElementType.RAILING,
    tapir.ElementType.OPENING,
)
"""Main model types, preserving the existing get_3d_elements population/order."""

TYPES_3D_COMPONENTS: tuple[tapir.ElementType, ...] = (
    tapir.ElementType.CURTAIN_WALL_SEGMENT,
    tapir.ElementType.CURTAIN_WALL_FRAME,
    tapir.ElementType.CURTAIN_WALL_PANEL,
    tapir.ElementType.CURTAIN_WALL_JUNCTION,
    tapir.ElementType.CURTAIN_WALL_ACCESSORY,
    tapir.ElementType.RISER,
    tapir.ElementType.TREAD,
    tapir.ElementType.STAIR_STRUCTURE,
    tapir.ElementType.RAILING_TOPRAIL,
    tapir.ElementType.RAILING_HANDRAIL,
    tapir.ElementType.RAILING_RAIL,
    tapir.ElementType.RAILING_POST,
    tapir.ElementType.RAILING_INNER_POST,
    tapir.ElementType.RAILING_BALUSTER,
    tapir.ElementType.RAILING_PANEL,
    tapir.ElementType.RAILING_SEGMENT,
    tapir.ElementType.RAILING_NODE,
    tapir.ElementType.RAILING_BALUSTER_SET,
    tapir.ElementType.RAILING_PATTERN,
    tapir.ElementType.RAILING_TOPRAIL_END,
    tapir.ElementType.RAILING_HANDRAIL_END,
    tapir.ElementType.RAILING_RAIL_END,
    tapir.ElementType.RAILING_TOPRAIL_CONNECTION,
    tapir.ElementType.RAILING_HANDRAIL_CONNECTION,
    tapir.ElementType.RAILING_RAIL_CONNECTION,
    tapir.ElementType.RAILING_END_FINISH,
    tapir.ElementType.BEAM_SEGMENT,
    tapir.ElementType.COLUMN_SEGMENT,
)
"""Curtain-wall, stair, railing, beam, and column component types."""

TYPES_3D_WITH_COMPONENTS: tuple[tapir.ElementType, ...] = TYPES_3D + TYPES_3D_COMPONENTS
"""All model types: main elements followed by structural components."""

TYPES_2D: tuple[tapir.ElementType, ...] = (
    tapir.ElementType.DIMENSION,
    tapir.ElementType.RADIAL_DIMENSION,
    tapir.ElementType.LEVEL_DIMENSION,
    tapir.ElementType.ANGLE_DIMENSION,
    tapir.ElementType.TEXT,
    tapir.ElementType.LABEL,
    tapir.ElementType.HATCH,
    tapir.ElementType.LINE,
    tapir.ElementType.POLY_LINE,
    tapir.ElementType.ARC,
    tapir.ElementType.CIRCLE,
    tapir.ElementType.SPLINE,
    tapir.ElementType.HOTSPOT,
    tapir.ElementType.CUT_PLANE,
    tapir.ElementType.CAMERA,
    tapir.ElementType.SECT_ELEM,
    tapir.ElementType.DRAWING,
    tapir.ElementType.PICTURE,
    tapir.ElementType.DETAIL,
    tapir.ElementType.ELEVATION,
    tapir.ElementType.INTERIOR_ELEVATION,
    tapir.ElementType.WORKSHEET,
    tapir.ElementType.CHANGE_MARKER,
)
"""Drafting, annotation, marker, drawing, and individual-camera types."""

TYPES_ALL: tuple[tapir.ElementType, ...] = TYPES_3D_WITH_COMPONENTS + TYPES_2D
"""All preset types, including components, excluding containers and Unknown."""

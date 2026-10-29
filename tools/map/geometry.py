"""Distances between points, line segments, rectangles and polygons.

Points are (x, y) in millimeters. Rectangles are (x0, y0, x1, y1) with
x0 <= x1 and y0 <= y1. Used for placing labels and for the print's checks.
"""
import math


def point_to_segment(p, a, b):
    """Distance from point p to the segment from a to b."""
    vx, vy = b[0] - a[0], b[1] - a[1]
    length2 = vx * vx + vy * vy
    u = 0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / length2))
    return math.hypot(a[0] + u * vx - p[0], a[1] + u * vy - p[1])


def segments_cross(a, b, c, d):
    """True if segment a-b crosses segment c-d."""
    def side(p, q, r):      # which side of the line p-q the point r is on
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (side(a, b, c) > 0) != (side(a, b, d) > 0) and (side(c, d, a) > 0) != (side(c, d, b) > 0)


def rect_to_rect(a, b):
    """Gap between two rectangles, or -1 if they overlap."""
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy) if (dx > 0 or dy > 0) else -1.0


def rect_to_point(r, p):
    """Distance from a rectangle to a point (0 if the point is inside it)."""
    return math.hypot(max(r[0] - p[0], 0, p[0] - r[2]), max(r[1] - p[1], 0, p[1] - r[3]))


def rect_to_segment(r, a, b):
    """Distance from a rectangle to the segment from a to b (0 if they touch)."""
    if rect_to_point(r, a) == 0 or rect_to_point(r, b) == 0:
        return 0.0
    corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    for i in range(4):
        if segments_cross(a, b, corners[i], corners[(i + 1) % 4]):
            return 0.0
    return min([point_to_segment(c, a, b) for c in corners] + [rect_to_point(r, a), rect_to_point(r, b)])


def point_in_polygon(poly, p):
    """True if point p is inside the polygon (a list of corners)."""
    hit = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        if (ay > p[1]) != (by > p[1]) and p[0] < ax + (p[1] - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit

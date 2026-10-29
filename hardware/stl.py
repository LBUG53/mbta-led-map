"""Save a manifold3d shape as an STL file (plain text, which every slicer reads)."""


def write_stl(part, path, name="part"):
    """Write `part` to `path`. Returns the number of triangles."""
    mesh = part.to_mesh()
    points, triangles = mesh.vert_properties, mesh.tri_verts
    with open(path, "w") as f:
        f.write("solid %s\n" % name)
        for t in triangles:
            a, b, c = (points[i][:3] for i in t)
            # The facet's normal: the cross product of two of its edges, scaled to length 1.
            u, v = b - a, c - a
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
            f.write(" facet normal %.4f %.4f %.4f\n  outer loop\n" % (n[0] / length, n[1] / length, n[2] / length))
            for p in (a, b, c):
                f.write("   vertex %.4f %.4f %.4f\n" % (p[0], p[1], p[2]))
            f.write("  endloop\n endfacet\n")
        f.write("endsolid %s\n" % name)
    return len(triangles)

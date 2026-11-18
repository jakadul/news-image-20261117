"""A minimal TrueType text renderer: outlines, quadratic flattening, scanline
coverage with non-zero winding, and sub-pixel positioning.

No hinting.  Glyphs are rasterised at the canvas' supersample factor and box
downsampled with the page, which is what makes the type read as printed.

Standard library only.
"""

from canvas import Coverage

import math


class Glyph:
    """One glyph flattened and scaled to a pixel size, in y-down space."""

    __slots__ = ("contours", "advance", "x_min", "x_max", "y_min", "y_max")

    def __init__(self, contours, advance):
        self.contours = contours
        self.advance = advance
        xs = [p[0] for c in contours for p in c]
        ys = [p[1] for c in contours for p in c]
        self.x_min = min(xs) if xs else 0.0
        self.x_max = max(xs) if xs else 0.0
        self.y_min = min(ys) if ys else 0.0
        self.y_max = max(ys) if ys else 0.0


def _flatten(contour, scale, out, steps=8):
    """Append the flattened polygon for one TrueType contour.

    Implied on-curve midpoints between consecutive off-curve points are
    inserted first, then each quadratic segment is sampled at ``steps``
    intervals; the points come out in font units scaled to pixels, y down.
    """
    pts = contour
    n = len(pts)
    if n == 0:
        return
    # normalise: start at an on-curve point
    start = None
    for i in range(n):
        if pts[i][2]:
            start = i
            break
    if start is None:
        start = 0
    seq = []
    for k in range(n):
        seq.append(pts[(start + k) % n])
    # build the expanded sequence with implied midpoints
    exp = []
    m = len(seq)
    for i in range(m):
        x, y, on = seq[i]
        nx, ny, non = seq[(i + 1) % m]
        exp.append((x, y, on))
        if not on and not non:
            exp.append(((x + nx) / 2.0, (y + ny) / 2.0, True))
    # now walk from the first on-curve point
    first = None
    for i, p in enumerate(exp):
        if p[2]:
            first = i
            break
    if first is None:
        return
    exp = exp[first:] + exp[:first]
    if len(exp) > 1 and exp[-1][2] and exp[-1][0] == exp[0][0] and exp[-1][1] == exp[0][1]:
        exp.pop()
    exp.append(exp[0])

    poly = [(exp[0][0] * scale, -exp[0][1] * scale)]
    i = 1
    cur = exp[0]
    while i < len(exp):
        p = exp[i]
        if p[2]:
            poly.append((p[0] * scale, -p[1] * scale))
            cur = p
            i += 1
        else:
            # p is a control point; next is the on-curve end
            end = exp[i + 1]
            x0, y0 = cur[0], cur[1]
            cx, cy = p[0], p[1]
            x1, y1 = end[0], end[1]
            for s in range(1, steps + 1):
                t = s / steps
                mt = 1.0 - t
                bx = mt * mt * x0 + 2 * mt * t * cx + t * t * x1
                by = mt * mt * y0 + 2 * mt * t * cy + t * t * y1
                poly.append((bx * scale, -by * scale))
            cur = end
            i += 2
    if len(poly) >= 3:
        out.append(poly)


def _coverage(contours, ox, oy, w, h):
    """Scanline fill of flattened polygons with the non-zero winding rule.

    ``contours`` are in glyph pixel space, y down.  ``ox``/``oy`` are the
    glyph's bounding-box corner offset by the pen: buffer pixel (x, y) covers
    glyph space [x + ox, x + ox + 1) by [y + oy, y + oy + 1).  Returns a
    bytearray of w*h coverage in 0..255, sampled 4 times vertically per row so
    the horizontal strokes of small type get a real grey value.
    """
    cov = bytearray(w * h)
    if not contours:
        return cov
    edges = []
    y_lo = 1e9
    y_hi = -1e9
    for poly in contours:
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if y0 == y1:
                continue
            if y0 < y_lo:
                y_lo = y0
            if y0 > y_hi:
                y_hi = y0
            if y1 < y_lo:
                y_lo = y1
            if y1 > y_hi:
                y_hi = y1
            if y0 < y1:
                edges.append((x0, y0, x1, y1, 1))
            else:
                edges.append((x1, y1, x0, y0, -1))
    if not edges:
        return cov
    # The box is the glyph's own outline, so every row of it can carry ink;
    # oy only shifts the sample point inside a row.
    y_start = 0
    y_end = h
    SUB = 4
    inv = 1.0 / SUB
    for y in range(y_start, y_end):
        acc = [0.0] * w
        for s in range(SUB):
            yc = y + (s + 0.5) * inv - oy + y_lo
            xs = []
            for ex0, ey0, ex1, ey1, wind in edges:
                if ey0 <= yc < ey1:
                    t = (yc - ey0) / (ey1 - ey0)
                    xs.append((ex0 + t * (ex1 - ex0) - ox, wind))
            if not xs:
                continue
            xs.sort(key=lambda e: e[0])
            wind = 0
            for i in range(len(xs) - 1):
                xa, wa = xs[i]
                wind += wa
                if wind != 0:
                    xb = xs[i + 1][0]
                    if xb <= 0 or xa >= w:
                        continue
                    if xa < 0:
                        xa = 0.0
                    if xb > w:
                        xb = float(w)
                    ia = int(xa)
                    ib = int(xb)
                    if ib <= ia:
                        acc[ia] += (xb - xa) * inv
                    elif ib >= w:
                        acc[ia] += (ia + 1 - xa) * inv
                        for k in range(ia + 1, w):
                            acc[k] += inv
                    else:
                        acc[ia] += (ia + 1 - xa) * inv
                        for k in range(ia + 1, ib):
                            acc[k] += inv
                        acc[ib] += (xb - ib) * inv
        row = y * w
        for x in range(w):
            v = acc[x]
            if v > 0.0:
                if v > 1.0:
                    v = 1.0
                iv = int(v * 255.0 + 0.5)
                if iv:
                    cov[row + x] = iv
    return cov


class Face:
    """A font at a pixel size, with a glyph cache keyed by code point."""

    def __init__(self, font, size_px):
        self.font = font
        self.size = size_px
        self.scale = size_px / float(font.upm)
        self._cache = {}
        self._rcache = {}
        self.ascent = font.ascent * self.scale
        self.descent = -font.descent * self.scale
        self.line_height = (font.ascent - font.descent + font.linegap) * self.scale

    def _raster_contours(self, g, s):
        """Glyph outlines pre-scaled to canvas raster pixels.

        Glyphs are flattened once in face units; the canvas is supersampled,
        so painting them without this second scale would draw every glyph at
        half size and half spacing while the layout (which measures in face
        units) thinks the line fills its measure.
        """
        if s == 1:
            return g.contours
        key = (g, s)
        out = self._rcache.get(key)
        if out is None:
            out = [[(px * s, py * s) for px, py in poly]
                   for poly in g.contours]
            self._rcache[key] = out
        return out

    def glyph(self, ch):
        g = self._cache.get(ch)
        if g is not None:
            return g
        gid = self.font.gid(ch)
        contours = []
        for c in self.font.outline(gid):
            _flatten(c, self.scale, contours)
        g = Glyph(contours, self.font.advance(gid) * self.scale)
        self._cache[ch] = g
        return g

    def advance(self, ch):
        return self.glyph(ch).advance

    def text_width(self, text):
        total = 0.0
        for ch in text:
            total += self.advance(ch)
        return total

    def cap_height(self):
        """Cap height in pixels, measured from the 'H' outline."""
        g = self.glyph("H")
        if g.contours:
            return -g.y_min
        return self.ascent * 0.7

    def x_height(self):
        g = self.glyph("x")
        if g.contours:
            return -g.y_min
        return self.ascent * 0.48

    def render(self, canvas, x, y, text, color, coverage_scale=1):
        """Draw ``text`` with its baseline at design-pixel (x, y).

        ``x`` and ``y`` are floats: the glyph origins are rounded to whole
        raster pixels, which at supersample scale is a sub-design-pixel
        offset and keeps spacing even.
        """
        s = canvas.scale
        pen = x * s
        base = y * s
        for ch in text:
            g = self.glyph(ch)
            adv = g.advance * s
            if g.contours and ch != " ":
                ox = pen + g.x_min * s
                oy = base + g.y_min * s
                w = int((g.x_max - g.x_min) * s) + 2
                h = int((g.y_max - g.y_min) * s) + 2
                if w > 0 and h > 0:
                    # _coverage measures against the fractional pen origin;
                    # paint at the integer floor of that same origin so the
                    # coverage lands on the rows it was sampled for
                    ix, iy = int(ox), int(oy)
                    cov = _coverage(self._raster_contours(g, s), ox - ix,
                                    oy - iy, w, h)
                    covobj = Coverage(w, h)
                    covobj.data = cov
                    canvas.paint_coverage(covobj, ix, iy, color)
            pen += adv

    def render_tracked(self, canvas, x, y, text, color, tracking=0.0):
        """Draw text with extra tracking (design pixels) between characters."""
        s = canvas.scale
        pen = x * s
        base = y * s
        for i, ch in enumerate(text):
            g = self.glyph(ch)
            if g.contours and ch != " ":
                ox = pen + g.x_min * s
                oy = base + g.y_min * s
                w = int((g.x_max - g.x_min) * s) + 2
                h = int((g.y_max - g.y_min) * s) + 2
                if w > 0 and h > 0:
                    # _coverage measures against the fractional pen origin;
                    # paint at the integer floor of that same origin so the
                    # coverage lands on the rows it was sampled for
                    ix, iy = int(ox), int(oy)
                    cov = _coverage(self._raster_contours(g, s), ox - ix,
                                    oy - iy, w, h)
                    covobj = Coverage(w, h)
                    covobj.data = cov
                    canvas.paint_coverage(covobj, ix, iy, color)
            pen += g.advance * s
            if i + 1 < len(text):
                pen += tracking * s

    def tracked_width(self, text, tracking=0.0):
        total = 0.0
        for i, ch in enumerate(text):
            total += self.advance(ch)
            if i + 1 < len(text):
                total += tracking
        return total


class TypeFaceCache:
    """Faces keyed by (path, size_px), so repeated sizes share outlines."""

    def __init__(self):
        self._faces = {}

    def face(self, font, size_px):
        size_px = int(round(size_px))
        if size_px < 1:
            size_px = 1
        key = (font.path, size_px)
        f = self._faces.get(key)
        if f is None:
            f = Face(font, size_px)
            self._faces[key] = f
        return f

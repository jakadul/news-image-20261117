"""The illustrations: the lead panel of the Kerch Strait at night, and the
strike timeline that sits under it.

Everything here is drawn from primitives -- polygons, rules, dots -- so the
panel is vector work at the supersampled size, not a photograph.  There is no
randomness: the starfield is a small deterministic generator seeded by a
constant, which is why two runs write the same bytes.

Design-pixel coordinates throughout; the canvas multiplies by its scale.
"""

from canvas import Canvas

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------

CREAM = (244, 238, 224)
INK = (26, 24, 22)
INK_SOFT = (74, 70, 64)
RED = (176, 34, 40)
RED_DEEP = (140, 24, 30)
PAPER = (250, 246, 236)

# the night panel runs on its own ramp: deep sea, colder sky, warm fire
NIGHT_TOP = (10, 14, 24)
NIGHT_MID = (16, 24, 40)
SEA_FAR = (24, 34, 48)
SEA_NEAR = (8, 12, 20)
FIRE = (255, 178, 74)
FIRE_CORE = (255, 232, 176)
FIRE_SMOKE = (86, 68, 56)
BEAM = (188, 206, 224)
STEEL = (152, 162, 174)
STEEL_DIM = (96, 106, 120)


class Lcg:
    """Deterministic generator: same sequence on every machine and run."""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def unit(self):
        return self.next() / float(0x7FFFFFFF)

    def between(self, a, b):
        return a + (b - a) * self.unit()


# ---------------------------------------------------------------------------
# small drawing primitives the panel needs beyond canvas
# ---------------------------------------------------------------------------


def _hgrad(canvas, x0, y0, x1, y1, c_left, c_right):
    """Horizontal gradient band, one raster column at a time."""
    s = canvas.scale
    X0, X1 = int(round(x0 * s)), int(round(x1 * s))
    Y0, Y1 = int(round(y0 * s)), int(round(y1 * s))
    span = max(1, X1 - X0)
    buf = canvas.buf
    W = canvas.w
    for X in range(max(0, X0), min(W, X1)):
        t = (X - X0) / float(span)
        col = bytes((int(c_left[0] + (c_right[0] - c_left[0]) * t),
                     int(c_left[1] + (c_right[1] - c_left[1]) * t),
                     int(c_left[2] + (c_right[2] - c_left[2]) * t)))
        for Y in range(max(0, Y0), min(canvas.h, Y1)):
            i = (Y * W + X) * 3
            buf[i:i + 3] = col


def _vgrad(canvas, x0, y0, x1, y1, stops):
    """Vertical gradient over a rect; ``stops`` is [(t, colour), ...]."""
    s = canvas.scale
    X0, X1 = int(round(x0 * s)), int(round(x1 * s))
    Y0, Y1 = int(round(y0 * s)), int(round(y1 * s))
    span = max(1, Y1 - Y0)
    buf = canvas.buf
    W = canvas.w
    for Y in range(max(0, Y0), min(canvas.h, Y1)):
        t = (Y - Y0) / float(span)
        # find the bracketing stops
        lo = stops[0]
        hi = stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                lo, hi = stops[i], stops[i + 1]
                break
        f = 0.0 if hi[0] == lo[0] else (t - lo[0]) / (hi[0] - lo[0])
        c = bytes((int(lo[1][0] + (hi[1][0] - lo[1][0]) * f),
                   int(lo[1][1] + (hi[1][1] - lo[1][1]) * f),
                   int(lo[1][2] + (hi[1][2] - lo[1][2]) * f)))
        run = c * max(0, min(W, X1) - max(0, X0))
        if run:
            i = (Y * W + max(0, X0)) * 3
            buf[i:i + len(run)] = run


def _soft_glow(canvas, cx, cy, r, color, strength=0.55, rings=26):
    """A radial glow: light falling off with the square of the distance.

    The colour is mixed in rather than added, so a warm glow over cool water
    stays warm instead of clipping to green, and the falloff is sampled once
    per pixel, never stacked in rings.
    """
    s = canvas.scale
    buf = canvas.buf
    W = canvas.w
    X0, X1 = int(round((cx - r) * s)), int(round((cx + r) * s))
    Y0, Y1 = int(round((cy - r) * s)), int(round((cy + r) * s))
    inv_r = 1.0 / max(1e-6, r)
    for Y in range(max(0, Y0), min(canvas.h, Y1)):
        dy = (Y / s - cy) * inv_r
        dy2 = dy * dy
        if dy2 > 1.0:
            continue
        i = (Y * W + max(0, X0)) * 3
        for X in range(max(0, X0), min(W, X1)):
            dx = (X / s - cx) * inv_r
            d2 = dx * dx + dy2
            if d2 >= 1.0:
                i += 3
                continue
            # blend toward the glow colour rather than adding: an additive
            # warm glow over a cool sea saturates to green, which is exactly
            # what a fire must not look like
            f = (1.0 - d2) ** 2 * strength
            inv = 1.0 - f
            buf[i] = int(buf[i] * inv + color[0] * f)
            buf[i + 1] = int(buf[i + 1] * inv + color[1] * f)
            buf[i + 2] = int(buf[i + 2] * inv + color[2] * f)
            i += 3


# ---------------------------------------------------------------------------
# the lead panel
# ---------------------------------------------------------------------------

def kerch_panel(canvas, x0, y0, x1, y1):
    """Night view across the strait: a starfield, the sea, the bridge seen in
    line from the north-east, one span of the road deck gone and dropping,
    fires on the water, and a searchlight raking the gap.

    The composition is chosen for legibility at 300 pixels across: the horizon
    sits at 62 per cent of the panel's depth, the intact bridge enters from the
    left and runs to a third of the way in, the break is the only bright thing
    against the sky, and the far shore gives the eye a place to stop.
    """
    w = x1 - x0
    h = y1 - y0
    horizon = y0 + h * 0.62

    # -- sky: near-black overhead, a colder band on the horizon
    _vgrad(canvas, x0, y0, x1, horizon,
           [(0.0, NIGHT_TOP), (0.55, NIGHT_MID), (1.0, (34, 44, 62))])

    # -- sea: lighter at the horizon, sinking to black at the foot
    _vgrad(canvas, x0, horizon, x1, y1,
           [(0.0, SEA_FAR), (0.35, (16, 24, 34)), (1.0, SEA_NEAR)])

    # -- a low haze band right on the horizon, warm from the fires
    _vgrad(canvas, x0, horizon - h * 0.045, x1, horizon + h * 0.02,
           [(0.0, (28, 34, 46)), (1.0, (58, 52, 52))])

    # -- the far shore: a ragged silhouette, Taman on the Russian side
    rng = Lcg(20261117)
    shore = []
    n = 26
    for i in range(n + 1):
        px = x0 + w * (i / float(n))
        py = horizon - h * 0.012 - rng.between(0.0, h * 0.022)
        shore.append((px, py))
    shore += [(x1, horizon + h * 0.01), (x0, horizon + h * 0.01)]
    canvas.polygon(shore, outline=None, fill=(12, 16, 24))
    # a handful of shore lights, deterministic
    for i in range(9):
        lx = x0 + w * rng.between(0.04, 0.96)
        ly = horizon - h * 0.006 - rng.between(0.0, h * 0.014)
        canvas.dot(lx, ly, max(0.9, w * 0.0016), fill=(196, 168, 118))

    # -- starfield
    for _ in range(150):
        sx = x0 + w * rng.unit()
        sy = y0 + (horizon - y0) * (rng.unit() ** 0.75) * 0.92
        r = rng.between(0.35, 1.05)
        v = int(rng.between(120, 235))
        canvas.dot(sx, sy, r, fill=(v, v, min(255, v + 8)))

    # -- searchlight: a cone raking up from the Russian end of the bridge
    beam_src = (x0 + w * 0.215, y0 + h * 0.415)
    cone = [
        beam_src,
        (x0 + w * 0.30, y0 + h * 0.02),
        (x0 + w * 0.62, y0 + h * 0.05),
        (x0 + w * 0.46, y0 + h * 0.40),
    ]
    canvas.polygon(cone, outline=None, fill=(22, 26, 36))
    _soft_glow(canvas, beam_src[0], beam_src[1], w * 0.04, BEAM, 0.22, 12)

    # -- the bridge.  Deck line rises slightly to the right, then stops.
    deck_y = y0 + h * 0.455
    deck_slope = -0.018
    deck_left = x0 + w * 0.02
    deck_break = x0 + w * 0.545
    deck_thick = h * 0.016
    pier_h = h * 0.145

    def dy(px):
        return deck_y + (px - deck_left) * deck_slope

    # deck slab, solid, with a lit underside
    canvas.polygon([(deck_left, dy(deck_left)),
                    (deck_break, dy(deck_break)),
                    (deck_break, dy(deck_break) + deck_thick),
                    (deck_left, dy(deck_left) + deck_thick)],
                   outline=None, fill=(54, 60, 70))
    canvas.rule(deck_left, dy(deck_left), deck_break, dy(deck_break),
                width=max(1.0, h * 0.0035), fill=(178, 186, 196))

    # piers: pairs of legs down into the sea, cast slightly left
    pier_xs = [x0 + w * f for f in (0.085, 0.175, 0.265, 0.355, 0.445, 0.515)]
    for i, px in enumerate(pier_xs):
        top = dy(px) + deck_thick
        foot = horizon + h * 0.055 + (i * 0.004) * h
        canvas.polygon([(px - w * 0.0045, top),
                        (px + w * 0.0045, top),
                        (px + w * 0.0085, foot),
                        (px - w * 0.0085, foot)],
                       outline=None, fill=(40, 46, 56))
        # a thin lit edge on the right leg of each pier
        canvas.rule(px + w * 0.0042, top, px + w * 0.008, foot,
                    width=max(0.8, h * 0.0022), fill=(104, 114, 128))

    # the railway arch over the deck, a shallow arc of steel
    arch_pts = []
    span_x0, span_x1 = x0 + w * 0.10, x0 + w * 0.46
    for i in range(21):
        t = i / 20.0
        px = span_x0 + (span_x1 - span_x0) * t
        py = dy(px) - h * 0.075 * (0.15 + 0.85 * (1.0 - (2.0 * t - 1.0) ** 2))
        arch_pts.append((px, py))
    for i in range(len(arch_pts) - 1):
        canvas.rule(arch_pts[i][0], arch_pts[i][1],
                    arch_pts[i + 1][0], arch_pts[i + 1][1],
                    width=max(1.0, h * 0.0042), fill=(126, 136, 150))
    # hangers from arch to deck
    for i in range(1, 20, 2):
        ax, ay = arch_pts[i]
        canvas.rule(ax, ay, ax, dy(ax), width=max(0.8, h * 0.0018),
                    fill=(78, 88, 102))

    # -- the break.  The deck stops dead, and the missing span hangs from its
    # far end, tipping into the water: a hard step down, not a glow.
    fb = deck_break
    fb_y = dy(fb)
    fall_len = w * 0.150
    fall_drop = h * 0.185
    # the void: the water shows through where the span was
    canvas.polygon([(fb, fb_y),
                    (fb + fall_len, fb_y + fall_drop * 0.30),
                    (fb + fall_len, fb_y + fall_drop * 0.30 + deck_thick),
                    (fb, fb_y + deck_thick)],
                   outline=None, fill=(14, 20, 30))
    # the fallen span, hinged at the break and rotating down to the sea
    hinge_x, hinge_y = fb + fall_len, fb_y + fall_drop * 0.30
    canvas.polygon([(hinge_x, hinge_y),
                    (hinge_x + fall_len * 0.55, hinge_y + fall_drop * 0.62),
                    (hinge_x + fall_len * 0.53, hinge_y + fall_drop * 0.62 + deck_thick),
                    (hinge_x, hinge_y + deck_thick)],
                   outline=None, fill=(62, 70, 82))
    canvas.rule(hinge_x, hinge_y, hinge_x + fall_len * 0.55,
                hinge_y + fall_drop * 0.62, width=max(1.0, h * 0.0026),
                fill=(186, 194, 204))
    # rebar trailing up out of the gap toward the intact deck
    for k in range(5):
        sx = fb + fall_len * 0.12 * k
        canvas.rule(sx, fb_y + deck_thick * 0.5,
                    sx - w * 0.020, fb_y + fall_drop * 0.72,
                    width=max(0.7, h * 0.0016), fill=(132, 140, 152))

    # a torn end of the intact deck: a few vertical teeth
    for k in range(4):
        tx = fb - k * w * 0.009
        canvas.rule(tx, fb_y, tx - w * 0.0025, fb_y - h * 0.014,
                    width=max(0.7, h * 0.0018), fill=(158, 166, 178))
    # a chunk of deck in the water below the break
    canvas.polygon([(x0 + w * 0.60, horizon + h * 0.055),
                    (x0 + w * 0.655, horizon + h * 0.060),
                    (x0 + w * 0.652, horizon + h * 0.072),
                    (x0 + w * 0.598, horizon + h * 0.068)],
                   outline=None, fill=(58, 66, 78))

    # -- the far bank the deck was heading for: a low, dark abutment where the
    # missing span would have landed, so the gap reads as a gap and not as the
    # end of the road
    abut_x = fb + fall_len + w * 0.020
    abut_y = fb_y + fall_drop * 0.34
    canvas.polygon([(abut_x, abut_y - h * 0.030),
                    (x1, abut_y - h * 0.020),
                    (x1, horizon + h * 0.020),
                    (abut_x, horizon + h * 0.004)],
                   outline=None, fill=(16, 22, 32))
    canvas.rule(abut_x, abut_y - h * 0.030, x1, abut_y - h * 0.020,
                width=max(1.0, h * 0.0032), fill=(96, 104, 116))
    # its lamps, two small warm dots, so the far side reads as built
    for k in range(3):
        lx = abut_x + w * 0.075 * (k + 1)
        if lx < x1 - w * 0.02:
            canvas.dot(lx, abut_y - h * 0.024, max(0.9, w * 0.0018),
                       fill=(214, 186, 128))

    # -- fires: two on the water under the gap, one small on the shore
    fire_pts = [(x0 + w * 0.63, horizon + h * 0.075),
                (x0 + w * 0.72, horizon + h * 0.115),
                (x0 + w * 0.305, horizon - h * 0.004)]
    for i, (fx, fy) in enumerate(fire_pts):
        rr = w * (0.030 if i < 2 else 0.014)
        # the halo: one warm pool under the flame, and nothing brighter than
        # that mixed on top of it, or the glow clips to a green-white blob
        _soft_glow(canvas, fx, fy - rr * 0.5, rr * 3.0, (255, 136, 48), 0.55, 8)
        # flame body: two tongues, the taller one leaning right
        canvas.polygon([(fx - rr * 0.58, fy),
                        (fx - rr * 0.30, fy - rr * 1.35),
                        (fx - rr * 0.10, fy - rr * 0.95),
                        (fx + rr * 0.06, fy - rr * 1.85),
                        (fx + rr * 0.30, fy - rr * 1.05),
                        (fx + rr * 0.46, fy - rr * 1.45),
                        (fx + rr * 0.60, fy)],
                       outline=None, fill=FIRE)
        # the hot core, a short pale cone inside the tongues
        canvas.polygon([(fx - rr * 0.22, fy),
                        (fx - rr * 0.02, fy - rr * 1.05),
                        (fx + rr * 0.20, fy)],
                       outline=None, fill=FIRE_CORE)
        # reflection under it, broken by wave rules
        for k in range(7):
            ry = fy + h * 0.010 + k * h * 0.012
            rw = rr * (1.0 - k * 0.10)
            canvas.rule(fx - rw, ry, fx + rw, ry,
                        width=max(0.7, h * 0.0022),
                        fill=(int(196 - k * 22), int(112 - k * 12), 40))
        # smoke: a rising column of overlapping discs, grey-brown, thinning
        # as it climbs and drifting right.  The plume is clipped at the panel
        # edge -- discs that would ride above the dark ground are pulled onto
        # it, or they paint grey over the cream page and the deck copy above
        for k in range(14):
            sy = fy - rr * (1.7 + k * 0.62)
            sx = fx + rr * (0.10 * k) + rr * 0.05 * (k % 2)
            sr = rr * (0.34 + k * 0.075)
            if sy + sr <= y0:
                continue
            if sy - sr < y0:
                sy = y0 + sr
            shade = min(150, 78 + k * 5)
            canvas.dot(sx, sy, sr, fill=(shade, shade - 10, shade - 18))

    # -- water: a few horizontal glints so the sea reads as water
    for _ in range(60):
        gx = x0 + w * rng.unit()
        gy = horizon + (y1 - horizon) * (rng.unit() ** 1.4)
        gl = w * rng.between(0.004, 0.020)
        v = int(rng.between(28, 62))
        canvas.rule(gx, gy, gx + gl, gy, width=max(0.6, h * 0.0016),
                    fill=(v, v + 6, v + 14))

    # -- the gap, marked: a bracket across the missing span, and a leader to
    # the caption line, so the break is named as well as seen
    gap_x0, gap_x1 = deck_break, deck_break + w * 0.105
    gap_y = dy(deck_break) - h * 0.030
    canvas.rule(gap_x0, gap_y, gap_x1, gap_y, width=max(1.0, h * 0.0028),
                fill=(214, 208, 190))
    canvas.rule(gap_x0, gap_y - h * 0.014, gap_x0, gap_y + h * 0.014,
                width=max(1.0, h * 0.0028), fill=(214, 208, 190))
    canvas.rule(gap_x1, gap_y - h * 0.014, gap_x1, gap_y + h * 0.014,
                width=max(1.0, h * 0.0028), fill=(214, 208, 190))
    canvas.rule((gap_x0 + gap_x1) / 2.0, gap_y + h * 0.014,
                (gap_x0 + gap_x1) / 2.0, dy(deck_break) - h * 0.002,
                width=max(0.8, h * 0.0020), fill=(214, 208, 190))

    return (gap_x0, gap_x1, gap_y)


# ---------------------------------------------------------------------------
# the strike timeline
# ---------------------------------------------------------------------------

def timeline(canvas, x0, y0, x1, y1, face_label, face_tick, face_small,
             draw_text):
    """A measured register of the two strikes: one ruler, ticks below the
    line, every label on one side, and the bar that reaches the second tick.

    x0..x1 is the measure; the ruler sits at the vertical centre.  Ticks are
    placed by elapsed hours from the first strike so the 24-hour claim is
    literally the length of the segment, not an assertion in a caption.
    """
    mid = (y0 + y1) / 2.0 - (y1 - y0) * 0.06
    # ruler
    canvas.rule(x0, mid, x1, mid, width=1.0, fill=INK)
    # 24-hour track: heavier, from first to second strike
    tick_a = x0 + (x1 - x0) * 0.16
    tick_b = x0 + (x1 - x0) * 0.84
    canvas.rule(tick_a, mid, tick_b, mid, width=3.0, fill=INK)

    # hour register: a small tick every three hours along the track
    for k in range(0, 25, 3):
        t = k / 24.0
        tx = tick_a + (tick_b - tick_a) * t
        tall = (k % 6 == 0)
        canvas.rule(tx, mid - (5.0 if tall else 3.0), tx, mid,
                    width=0.9, fill=INK)
        if tall:
            draw_text(face_small, canvas, tx - face_small.text_width(str(k)) / 2.0,
                      mid - 9.0, str(k), INK_SOFT)

    # the two strikes: heavy ticks, labels below, one side only
    for (tx, day, clock, what) in (
            (tick_a, "NOV 16", "23:40", "FIRST STRIKE"),
            (tick_b, "NOV 17", "21:15", "SPAN COLLAPSES")):
        canvas.rule(tx, mid - 11.0, tx, mid + 7.0, width=2.4, fill=INK)
        canvas.dot(tx, mid, 3.4, fill=RED)
        label = "%s  %s" % (day, clock)
        lw = face_label.text_width(label)
        draw_text(face_label, canvas, tx - lw / 2.0, mid + 22.0, label, INK)
        sub = what
        sw = face_small.text_width(sub)
        draw_text(face_small, canvas, tx - sw / 2.0, mid + 33.0, sub, RED_DEEP)

    # the measure itself, between the two ticks, above the line
    span_label = "24 HOURS APART"
    lw = face_label.text_width(span_label)
    cx = (tick_a + tick_b) / 2.0
    draw_text(face_label, canvas, cx - lw / 2.0, mid - 15.0, span_label,
              INK_SOFT)
    # end brackets: the measure's own extent
    canvas.rule(tick_a, mid - 18.0, tick_a, mid - 14.0, width=0.9, fill=INK_SOFT)
    canvas.rule(tick_b, mid - 18.0, tick_b, mid - 14.0, width=0.9, fill=INK_SOFT)
    canvas.rule(tick_a, mid - 16.0, tick_b, mid - 16.0, width=0.8, fill=INK_SOFT)

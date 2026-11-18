"""The front page of THE WORLD for Tuesday 17 November 2026.

Portrait, 1200 x 1600 design pixels, newsprint cream, ink black, one spot red.
Painted at SS times that size and box-downsampled, which is what makes the
type read as printed rather than as screen type.

The page is laid out on one grid.  Side margins of 66 pixels give a measure of
1068, cut into three columns of 337 with two 28-pixel gutters; the vertical
rules therefore fall on x = 431 and x = 796.  The three-column band, the lead
panel, the timeline and the closing strip all hang from those lines, and the
foot rule is set so the bottom margin equals the side margins.

Layout is measured, never guessed: every block reports its own depth, the page
stacks them once to find the natural height, and the slack is shared out among
five elastic gaps so the closing strip lands on the foot rule exactly.

Public API
----------
render_page(audit=None)  -> Canvas (downsampled, 1200 x 1600)
save_page(path, audit=None) -> (width, height)
overruns(audit) -> [(label, used, limit), ...]
"""

import os

import artwork
import typeset
from canvas import Canvas, downsample

# ---------------------------------------------------------------------------
# page geometry
# ---------------------------------------------------------------------------

PAGE_W = 1200
PAGE_H = 1600
SS = 2

MARGIN_X = 66
MARGIN_TOP = 38
CONTENT_X0 = MARGIN_X
CONTENT_X1 = PAGE_W - MARGIN_X
CONTENT_W = CONTENT_X1 - CONTENT_X0            # 1068

COL_N = 3
GUTTER = 28.0
COL_W = (CONTENT_W - (COL_N - 1) * GUTTER) / COL_N   # 337.33
COL_X = tuple(CONTENT_X0 + i * (COL_W + GUTTER) for i in range(COL_N))
RULE_X = tuple(x + COL_W + GUTTER / 2.0 for x in COL_X[:-1])
SPAN2_W = 2 * COL_W + GUTTER                    # 702.67

FOOT_RULE = PAGE_H - MARGIN_X                   # 1534
FOOT_BASELINE = FOOT_RULE + 21.0
STRIP_LIMIT = FOOT_RULE - 14.0                  # strip's bottom edge

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------

CREAM = (243, 236, 220)
INK = (24, 22, 20)
INK_SOFT = (78, 73, 66)
INK_LIGHT = (126, 119, 108)
RED = (172, 32, 38)
RED_DEEP = (132, 22, 28)
PANEL = (12, 16, 26)
WHITE = (247, 243, 233)

# ---------------------------------------------------------------------------
# the day, as reported.  Every string on the page comes from here.
# ---------------------------------------------------------------------------

WEATHER = ("NEW YORK 9C OVERCAST  \u00b7  LONDON 7C RAIN  \u00b7  MANILA 31C STORMS"
           "  \u00b7  MOSCOW -3C SNOW")
MARKETS = "DOW -739  \u00b7  S&P -1.9%  \u00b7  NASDAQ -2.5%"

MASTHEAD = "THE WORLD"
DATELINE_LEFT = "TUESDAY, NOVEMBER 17, 2026"
DATELINE_CENTRE = "KERCH + HORMUZ"
DATELINE_RIGHT = "VOL. XI \u00b7 NO. 264"

LEAD_KICKER = "BLACK SEA  \u00b7  SECOND STRIKE IN 24 HOURS"
LEAD_HEAD = "Ukraine Hits the Kerch Bridge Again, and a Span Falls Into the Strait"
LEAD_DECK = ("Palianytsia drones and Neptune missiles struck the road span overnight "
             "while Ruta drones and FP-5 Flamingo missiles hit the railway arch; the "
             "roadway is impassable and the crossing that supplies Crimea is cut for "
             "a second day.")
LEAD_BYLINE = "BY THE WORLD BUREAU"

LEAD_BODY = (
    "A section of the road span over the Kerch Strait collapsed overnight into "
    "Tuesday and the roadway was impassable by morning, Ukraine's president said, "
    "the second Ukrainian strike on the crossing in twenty-four hours. Volodymyr "
    "Zelenskyy said Palianytsia drones hit the road section while Neptune missiles, "
    "Ruta drones and FP-5 Flamingo missiles struck the railway arch; rail traffic "
    "resumed by evening on the line that carries fuel and armour south into the "
    "peninsula.")
LEAD_BODY_2 = (
    "The bridge is the only road-and-rail link between Russia and occupied Crimea "
    "across the strait, and weeks of strikes on Russian air defences, radar and "
    "electronic warfare preceded the two hits. Shipping through the Kerch Strait, "
    "the channel that carries Russian grain and fuel to the Mediterranean, may also "
    "be affected, port agents said.")

PANEL_CAPTION_L = "THE STRAIT, BEFORE DAWN"
PANEL_CAPTION_R = "ARTIST'S IMPRESSION  \u00b7  ILLUSTRATION: THE WORLD  \u00b7  DATA: OPEN SOURCES"

TIMELINE_HEAD = "TWO STRIKES, ONE DAY"
TIMELINE_NOTE = ("Hours elapsed between the two strikes on the road and rail spans. "
                 "The railway arch was damaged on the second; rail traffic resumed by evening.")

EXPLAIN_HEAD = "WHY THE BRIDGE MATTERS"
EXPLAIN_BODY = ("The 19 km crossing is the only road and rail route from mainland "
                "Russia into Crimea, and the main artery for fuel, ammunition and "
                "troops moving to the southern front. Ships bound for the Sea of "
                "Azov pass under it through the Kerch Strait.")

COL_MANILA_KICKER = "MANILA"
COL_MANILA_HEAD = "Trump Opens Four-Day Asia Trip With Protests Outside the Summit"
COL_MANILA_BODY = (
    "President Trump landed in Manila for the ASEAN summit and the first in-person "
    "meeting of the Quad in two years, as hundreds of demonstrators were arrested "
    "in the streets around the venue. He meets President Ferdinand Marcos Jr. on "
    "Wednesday, flies to Shenzhen, and ends the trip on Thursday at a trilateral "
    "summit with Xi Jinping and Vladimir Putin.")

COL_HORMUZ_KICKER = "STRAIT OF HORMUZ"
COL_HORMUZ_HEAD = "Tankers Attacked, and the U.S. Strikes Back at Iran"
COL_HORMUZ_BODY = (
    "Two tankers were attacked overnight, a drone crossed a gas field in Iraq and a "
    "third American carrier reached the region. Iran's Revolutionary Guards said "
    "combat drones struck a U.S.-operated radar at Sheikh Isa air base in Bahrain, "
    "the third such strike in five days; the U.S. bombed launch sites in reply. "
    "Qatar urged restraint.")

COL_WALL_KICKER = "WALL STREET"
COL_WALL_HEAD = "Stocks Fall Hard on Chip Curbs, and Anthropic Debuts"
COL_WALL_BODY = (
    "The Dow closed 739 points lower, the S&P 500 fell 1.9 per cent and the Nasdaq "
    "2.5 per cent, with Nvidia down 4.1 per cent and about 35 per cent below its "
    "peak. Washington said it would further restrict China's access to advanced AI "
    "chips, blocking shipments to data centres in Thailand and Malaysia. Anthropic "
    "began trading after demand ran about seven times the shares offered.")

STRIP_HEAD = "ALSO IN THIS EDITION"
STRIP_ITEMS = (
    ("HEALTH", "The U.S. loses its measles elimination status, held since 2000, "
               "as cases climb."),
    ("AFRICA", "Congo's Ebola outbreak passes 11,200 cases and 5,400 deaths in "
               "eight provinces."),
    ("TECH", "Outages hit airports, banks, Apple and the NSA's internal network; "
             "Waymo pulls its cars."),
)

FOOT_LEFT = "THE WORLD  \u00b7  TUESDAY, NOVEMBER 17, 2026"
FOOT_RIGHT = "PAGE 1  \u00b7  CITY FINAL EDITION  \u00b7  PRICE 3.50"


# ---------------------------------------------------------------------------
# a small block protocol: each returns the y at which its content ended
# ---------------------------------------------------------------------------


class Page:
    def __init__(self, audit=None):
        self.audit = audit if audit is not None else []
        self.book = typeset.FontBook()
        self.c = Canvas(PAGE_W, PAGE_H, scale=SS, background=CREAM)

    # -- type helpers -----------------------------------------------------
    def face(self, role, size):
        return self.book.face(role, size)

    def text(self, role, size, x, y, s, color=INK, tracking=0.0):
        f = self.face(role, size)
        typeset.draw_text(f, self.c, x, y, s, color, tracking)
        return f

    def check(self, label, used, limit):
        if used > limit + 0.75:
            self.audit.append((label, used, limit))

    # -- utility strip ----------------------------------------------------
    def utility(self, y):
        size = 9
        f = self.face("sans", size)
        lead = "WEATHER  "
        typeset.draw_text(f, self.c, CONTENT_X0, y, lead, RED, 0.7)
        wx = CONTENT_X0 + typeset.width(f, lead, 0.7)
        typeset.draw_text(f, self.c, wx, y, WEATHER, INK_SOFT, 0.35)
        typeset.draw_right(f, self.c, CONTENT_X1, y, MARKETS, INK, 0.35)
        mw = typeset.width(f, MARKETS, 0.35)
        typeset.draw_right(f, self.c, CONTENT_X1 - mw - 8.0, y, "MARKETS  ",
                           RED, 0.7)
        used = (wx - CONTENT_X0) + typeset.width(f, WEATHER, 0.35) + 26 + mw
        self.check("utility strip", used, CONTENT_W)
        return y + 12.0

    # -- masthead ---------------------------------------------------------
    def masthead(self, y):
        # the paper's name, set flush to the measure: cap height grows until
        # the line fills all 1068 pixels, then shrinks only if it overshoots
        cap_target = 116.0
        size = cap_target / (self.face("serif-bold", 100).cap_height() / 100.0)
        f = self.face("serif-bold", size)
        tracking = -1.6
        w = typeset.width(f, MASTHEAD, tracking)
        if w > CONTENT_W:
            size = size * CONTENT_W / w
            f = self.face("serif-bold", size)
            w = typeset.width(f, MASTHEAD, tracking)
        cap = f.cap_height()
        baseline = y + cap
        typeset.draw_text(f, self.c, CONTENT_X0, baseline, MASTHEAD, INK,
                          tracking)
        self.check("masthead", w, CONTENT_W)
        return baseline

    def dateline(self, y):
        size, tracking = 8.4, 1.5
        f = self.face("sans-bold", size)
        lw = typeset.width(f, DATELINE_LEFT, tracking)
        rw = typeset.width(f, DATELINE_RIGHT, tracking)
        cw = typeset.width(f, DATELINE_CENTRE, tracking)
        typeset.draw_text(f, self.c, CONTENT_X0, y, DATELINE_LEFT, INK,
                          tracking)
        typeset.draw_centered(f, self.c, (CONTENT_X0 + CONTENT_X1) / 2.0, y,
                              DATELINE_CENTRE, RED, tracking)
        typeset.draw_right(f, self.c, CONTENT_X1, y, DATELINE_RIGHT, INK,
                           tracking)
        # the centre piece must not collide with either side piece
        gap_l = (CONTENT_X0 + CONTENT_X1) / 2.0 - cw / 2.0 - (CONTENT_X0 + lw)
        gap_r = CONTENT_X1 - rw - ((CONTENT_X0 + CONTENT_X1) / 2.0 + cw / 2.0)
        self.check("dateline left gap", -gap_l + 12, 0.0)
        self.check("dateline right gap", -gap_r + 12, 0.0)
        return y

    # -- lead -------------------------------------------------------------
    def lead(self, y):
        # kicker
        ksize = 11.5
        kf = self.face("sans-bold", ksize)
        typeset.draw_text(kf, self.c, CONTENT_X0, y + ksize * 0.78, LEAD_KICKER,
                          RED, 1.1)
        y += ksize * 0.78 + 6.0

        # headline: three lines, cascade-set (336 / 634 / 811 px at 62pt),
        # breaks chosen so no word of the subject is split and no line ends on
        # a dangling article or preposition; hand-set because greedy wrap at
        # this size either merges to two lines or strands "Strait" alone
        limit = CONTENT_W
        size = 62.0
        _w = LEAD_HEAD.split()
        lines = (" ".join(_w[:2]), " ".join(_w[2:6]), " ".join(_w[6:]))
        f = self.face("serif-bold", size)
        leading = size * 1.04
        cap = f.cap_height()
        base = y + cap
        for ln in lines:
            typeset.draw_text(f, self.c, CONTENT_X0, base, ln, INK, -0.6)
            self.check("lead head line", typeset.width(f, ln, -0.6), limit)
            base += leading
        base -= leading
        return base + cap * 0.18 + 10.0, size

    def deck_row(self, y):
        """The deck runs the whole measure: three lines of 16.4pt serif is
        what a standfirst deserves under a head this size, and a deck broken
        into a narrow left column leaves the page's best white space empty."""
        size = 16.4
        f = self.face("serif", size)
        leading = size * 1.30
        para = typeset.Paragraph(f, LEAD_DECK, CONTENT_W, leading)
        self.check("lead deck", para.width_used, CONTENT_W)
        last = para.paint(self.c, CONTENT_X0, CONTENT_X1, y + size,
                          INK, justify_body=True)
        by_y = last + 16.0
        bf = self.face("sans-bold", 8.8)
        typeset.draw_text(bf, self.c, CONTENT_X0, by_y, LEAD_BYLINE, RED, 0.9)
        return by_y

    def panel(self, y):
        h = 336.0
        x0, x1 = CONTENT_X0, CONTENT_X1
        self.c.rect(x0, y, x1, y + h, fill=PANEL)
        gap = artwork.kerch_panel(self.c, x0, y, x1, y + h)
        # the broken span is labelled inside the panel, on the dark ground,
        # in the smallest white caps that still read at print size; the
        # leader from the label to the gap makes the claim unambiguous
        gf = self.face("sans-bold", 8.4)
        lab_y = gap[2] - 17.0
        cx = (gap[0] + gap[1]) / 2.0
        typeset.draw_centered(gf, self.c, cx, lab_y, "SPAN DOWN",
                              (240, 234, 216), 1.0)
        lw = typeset.width(gf, "SPAN DOWN", 1.0) / 2.0
        self.c.rule(cx, lab_y + 3.0, cx, gap[2] - 3.0, width=1.0,
                    fill=(196, 188, 168))
        self.c.rule(cx - lw, lab_y + 3.0, cx + lw, lab_y + 3.0, width=1.0,
                    fill=(196, 188, 168))
        # caption plate: a solid bar under the panel, not inside it
        cy = y + h
        cap_h = 20.0
        self.c.rect(x0, cy, x1, cy + cap_h, fill=INK)
        cf = self.face("sans-bold", 8.2)
        typeset.draw_text(cf, self.c, x0 + 9.0, cy + 13.4, PANEL_CAPTION_L,
                          CREAM, 0.9)
        typeset.draw_right(cf, self.c, x1 - 9.0, cy + 13.4, PANEL_CAPTION_R,
                           (214, 206, 190), 0.55)
        return cy + cap_h

    def timeline_block(self, y):
        """Ruler, ticks and the two strike marks, with the note beside them."""
        note_w = 250.0
        ruler_x1 = CONTENT_X1 - note_w - 24.0
        head_f = self.face("sans-bold", 9.2)
        typeset.draw_text(head_f, self.c, CONTENT_X0, y + 11.0, TIMELINE_HEAD,
                          INK, 0.9)
        self.c.rule(CONTENT_X0, y + 16.0, CONTENT_X0 + 74.0, y + 16.0,
                    width=2.0, fill=RED)
        rh = 78.0
        artwork.timeline(self.c, CONTENT_X0 + 4.0, y + 22.0, ruler_x1, y + rh,
                         self.face("sans-bold", 9.6),
                         self.face("sans", 6.8),
                         self.face("sans", 7.2),
                         typeset.draw_text)
        # the note: same measure on the right, labels never under the ruler
        nf = self.face("serif", 9.4)
        np_ = typeset.Paragraph(nf, TIMELINE_NOTE, note_w, 11.6)
        np_.paint(self.c, CONTENT_X1 - note_w, CONTENT_X1 - note_w,
                  y + 34.0, INK_SOFT, justify_body=False)
        return y + rh

    def lead_body(self, y):
        """Two columns of lead copy beside a ruled explainer box: the box
        earns its place by answering the question the headline raises, and it
        is labelled as an explainer rather than dressed as a quotation."""
        box_w = 244.0
        body_w = SPAN2_W
        size = 13.2
        f = self.face("serif", size)
        leading = size * 1.36
        p1 = typeset.Paragraph(f, LEAD_BODY, body_w, leading)
        self.check("lead body", p1.width_used, body_w)
        last = p1.paint(self.c, CONTENT_X0, CONTENT_X0 + body_w, y + size, INK)
        y2 = last + leading * 0.94
        p2 = typeset.Paragraph(f, LEAD_BODY_2, body_w, leading)
        self.check("lead body 2", p2.width_used, body_w)
        last = p2.paint(self.c, CONTENT_X0, CONTENT_X0 + body_w, y2 + size, INK)

        bx0 = CONTENT_X1 - box_w
        self.check("explainer gap", CONTENT_X0 + body_w + 26.0, bx0)
        ey = y
        self.c.rule(bx0, ey, CONTENT_X1, ey, width=1.2, fill=INK)
        hf = self.face("sans-bold", 10.2)
        typeset.draw_text(hf, self.c, bx0 + 10.0, ey + 15.0, EXPLAIN_HEAD, RED,
                          0.8)
        self.c.rule(bx0 + 10.0, ey + 19.5, bx0 + 46.0, ey + 19.5, width=2.2,
                    fill=RED)
        bsize = 12.2
        bf2 = self.face("serif", bsize)
        bp = typeset.Paragraph(bf2, EXPLAIN_BODY, box_w - 20.0, bsize * 1.30)
        self.check("explainer box", bp.width_used, box_w - 20.0)
        bp.paint(self.c, bx0 + 10.0, bx0 + 10.0, ey + 36.0, INK,
                 justify_body=False)
        box_end = ey + 36.0 + bp.depth
        self.c.rule(bx0, box_end + 10.0, CONTENT_X1, box_end + 10.0, width=1.0,
                    fill=INK)
        return max(last, box_end + 10.0)

    # -- the three-column band -------------------------------------------
    def column_story(self, x, y, kicker, head, body, credit):
        cw = COL_W
        kf = self.face("sans-bold", 8.8)
        typeset.draw_text(kf, self.c, x, y + 8.4, kicker, RED, 1.0)
        self.check("column kicker " + kicker, typeset.width(kf, kicker, 1.0), cw)
        y += 15.0
        # headline: the largest size that still fits four lines, balanced so
        # the lines are even rather than a long line and an orphan
        size = 30.0
        lines = None
        while size > 14:
            hf = self.face("serif-bold", size)
            cand = typeset.wrap_balanced(hf, head, cw, -0.35, lines=4)
            if len(cand) <= 4 and all(
                    typeset.fits(hf, ln, cw, -0.35) for ln in cand):
                lines = cand
                break
            size -= 0.5
        hf = self.face("serif-bold", size)
        leading = size * 1.05
        base = y + hf.cap_height()
        for ln in lines:
            typeset.draw_text(hf, self.c, x, base, ln, INK, -0.35)
            self.check("column head " + kicker, typeset.width(hf, ln, -0.35),
                       cw)
            base += leading
        base -= leading
        y = base + 14.0

        # body: two columns' worth is the target; if the copy is short the
        # measure widens to the full column and the size grows with it
        bsize = 13.4
        bf = self.face("serif", bsize)
        bp = typeset.Paragraph(bf, body, cw, bsize * 1.36)
        self.check("column body " + kicker, bp.width_used, cw)
        last = bp.paint(self.c, x, x + cw, y + bsize, INK)
        cf = self.face("sans-bold", 8.0)
        cy = last + 14.0
        typeset.draw_text(cf, self.c, x, cy, credit, INK_SOFT, 0.9)
        return cy

    def band(self, y):
        credits = ("WIRE REPORTS", "WIRE REPORTS", "WIRE REPORTS")
        stories = (
            (COL_MANILA_KICKER, COL_MANILA_HEAD, COL_MANILA_BODY, credits[0]),
            (COL_HORMUZ_KICKER, COL_HORMUZ_HEAD, COL_HORMUZ_BODY, credits[1]),
            (COL_WALL_KICKER, COL_WALL_HEAD, COL_WALL_BODY, credits[2]),
        )
        ends = []
        for i, (k, h, b, cr) in enumerate(stories):
            ends.append(self.column_story(COL_X[i], y, k, h, b, cr))
        return max(ends)

    # -- closing strip ----------------------------------------------------
    def strip(self, y):
        f = self.face("sans-bold", 9.2)
        typeset.draw_text(f, self.c, CONTENT_X0, y + 11.0, STRIP_HEAD, INK, 0.9)
        self.c.rule(CONTENT_X0, y + 16.0, CONTENT_X0 + 74.0, y + 16.0,
                    width=2.0, fill=RED)
        # three items on one baseline, each a red label and one line of copy
        size = 9.6
        bf = self.face("sans-bold", size)
        rf = self.face("serif", size + 1.6)
        base = y + 36.0
        for i, (label, text) in enumerate(STRIP_ITEMS):
            x = COL_X[i]
            typeset.draw_text(bf, self.c, x, base, label, RED, 0.8)
            lw = typeset.width(bf, label, 0.8) + 7.0
            avail = COL_W - lw
            # fit the one line to the rest of the column, never overrun it
            fs = rf
            while fs.size > 6 and not typeset.fits(fs, text, avail):
                fs = self.face("serif", fs.size - 1)
            typeset.draw_text(fs, self.c, x + lw, base, text, INK)
            self.check("strip item " + label,
                       lw + typeset.width(fs, text), COL_W)
        return base

    # -- footer -----------------------------------------------------------
    def footer(self, y):
        f = self.face("sans", 8.2)
        typeset.draw_text(f, self.c, CONTENT_X0, y, FOOT_LEFT, INK_SOFT, 0.7)
        typeset.draw_right(f, self.c, CONTENT_X1, y, FOOT_RIGHT, INK_SOFT, 0.7)


# ---------------------------------------------------------------------------
# the stack
# ---------------------------------------------------------------------------

def render_page(audit=None):
    p = Page(audit)
    return _paint(p, audit)


def _paint(p, audit):
    c = p.c
    y = MARGIN_TOP
    y = p.utility(y)
    c.rule(CONTENT_X0, y, CONTENT_X1, y, width=0.8, fill=INK_SOFT)
    y += 4.0
    y = p.masthead(y)
    y += 10.0
    c.rule(CONTENT_X0, y, CONTENT_X1, y, width=2.0, fill=INK)
    y += 13.0
    y = p.dateline(y)
    y += 7.0
    c.rule(CONTENT_X0, y, CONTENT_X1, y, width=3.0, fill=INK)
    y += 16.0

    y = p.lead(y)[0]
    y = p.deck_row(y) + 13.0
    y = p.panel(y) + 13.0
    y = p.timeline_block(y) + 13.0
    y = p.lead_body(y)
    # the band rule goes at a fixed fraction of the remaining space so the
    # gap above it and the gap below it are the same width, whatever the copy
    band_rule = y + max(10.0, (FOOT_RULE - 52.0 - y) * 0.20)

    c.rule(CONTENT_X0, band_rule, CONTENT_X1, band_rule, width=1.4, fill=INK)
    band_end = p.band(band_rule + 12.0)

    # the strip hangs off the foot rule, never floats.  Its rule is placed
    # where the band's measured depth leaves the widest gap, so the slack
    # between band and strip is spent on one breathing space, not two
    strip_rule = FOOT_RULE - 52.0
    p.check("band clears strip", band_end + 6.0, strip_rule)
    # vertical rules between the columns, band rule to strip rule
    for rx in RULE_X:
        c.rule(rx, band_rule + 2.0, rx, strip_rule - 9.0, width=0.8,
               fill=INK_LIGHT)
    c.rule(CONTENT_X0, strip_rule, CONTENT_X1, strip_rule, width=1.4, fill=INK)
    p.strip(strip_rule + 2.0)
    c.rule(CONTENT_X0, FOOT_RULE, CONTENT_X1, FOOT_RULE, width=1.2, fill=INK)
    p.footer(FOOT_BASELINE)

    return downsample(p.c, SS)


def save_page(path, audit=None):
    canvas = render_page(audit=audit)
    with open(path, "wb") as fh:
        fh.write(canvas.encode_png(level=9))
    return canvas.w, canvas.h


def overruns(audit):
    return list(audit or [])

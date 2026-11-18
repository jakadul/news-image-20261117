"""Typesetting on top of textrender: faces, measured wrapping, justified copy,
tracked small capitals, and the measured-pixel-width word wrap that every
block on the page uses.

All sizes are design pixels.  Faces are built at ``size * ss`` and painted on
the supersampled canvas, so the box downsample at the end is what turns the
outlines into printed type.

Standard library only.
"""

import textrender
import truetype

# ---------------------------------------------------------------------------
# font files, by role.  Each role lists candidates in preference order; the
# first one present on disk wins, so the page still sets on a machine with a
# trimmed font tree.
# ---------------------------------------------------------------------------

FONT_DIRS = (
    __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'fonts'),
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/liberation",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/TTF",
)

FONT_CANDIDATES = {
    "serif": ("LiberationSerif-Regular.ttf", "DejaVuSerif.ttf",
              "FreeSerif.ttf", "Times New Roman.ttf"),
    "serif-bold": ("LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf",
                   "FreeSerifBold.ttf", "Times New Roman Bold.ttf"),
    "serif-italic": ("LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf",
                     "FreeSerifItalic.ttf", "Times New Roman Italic.ttf"),
    "serif-bolditalic": ("LiberationSerif-BoldItalic.ttf",
                         "DejaVuSerif-BoldItalic.ttf",
                         "FreeSerifBoldItalic.ttf",
                         "Times New Roman Bold Italic.ttf"),
    "sans": ("LiberationSans-Regular.ttf", "DejaVuSans.ttf",
             "FreeSans.ttf", "Arial.ttf"),
    "sans-bold": ("LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf",
                  "FreeSansBold.ttf", "Arial Bold.ttf"),
    "sans-narrow": ("LiberationSansNarrow-Regular.ttf",
                    "DejaVuSansCondensed.ttf", "LiberationSans-Regular.ttf"),
    "sans-narrow-bold": ("LiberationSansNarrow-Bold.ttf",
                         "DejaVuSansCondensed-Bold.ttf",
                         "LiberationSans-Bold.ttf"),
    "mono": ("DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",
             "FreeMono.ttf"),
}

# glyphs the page needs; a face missing one falls back to a sibling file
REQUIRED_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" \
                  "0123456789.,;:!?'\"()-/$%&+*·—–’‘“”°½×→"

# non-breaking space used inside labels so they never split
NBSP = "\u00a0"


def _find(role):
    names = FONT_CANDIDATES[role]
    for directory in FONT_DIRS:
        for name in names:
            path = "%s/%s" % (directory, name)
            try:
                with open(path, "rb"):
                    pass
            except OSError:
                continue
            return path
    raise RuntimeError("no font file for role %r; looked in %s"
                       % (role, ", ".join(FONT_DIRS)))


def _covers(font):
    for ch in REQUIRED_GLYPHS:
        if font.gid(ch) == 0:
            return False
    return True


class FontBook:
    """Loads each role once and caches faces by (role, pixel size)."""

    def __init__(self):
        self._fonts = {}
        self._faces = {}
        self._paths = {}

    def font(self, role):
        f = self._fonts.get(role)
        if f is None:
            path = _find(role)
            f = truetype.Font(path)
            if not _covers(f) and role.startswith("serif"):
                f = truetype.Font(_find("serif") if role == "serif"
                                  else _find("serif-bold"))
            self._fonts[role] = f
            self._paths[role] = path
        return f

    def path(self, role):
        self.font(role)
        return self._paths[role]

    def face(self, role, size):
        px = int(round(size))
        if px < 1:
            px = 1
        key = (role, px)
        f = self._faces.get(key)
        if f is None:
            f = textrender.Face(self.font(role), px)
            self._faces[key] = f
        return f

    def cap(self, role, size):
        """Cap height of the face in design pixels."""
        return self.face(role, size).cap_height()


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def width(face, text, tracking=0.0):
    if tracking:
        return face.tracked_width(text, tracking)
    return face.text_width(text)


def fits(face, text, limit, tracking=0.0):
    return width(face, text, tracking) <= limit + 1e-6


def fit_size(book, role, text, limit, size, tracking=0.0, minimum=6.0):
    """Largest integer size at or below ``size`` at which ``text`` fits."""
    s = int(size)
    while s > minimum:
        if fits(book.face(role, s), text, limit, tracking):
            return s
        s -= 1
    return int(minimum)


def wrap(face, text, limit, tracking=0.0):
    """Greedy wrap by measured pixel width; words wider than the measure are
    kept whole (a label is never hyphenated on this page)."""
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if fits(face, trial, limit, tracking):
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def wrap_balanced(face, text, limit, tracking=0.0, lines=None):
    """Wrap so the longest line is as short as it can be for that line count.

    Used on headlines: a two-line head that ends on one orphan word reads as
    an accident, and a picture editor sees it in a second."""
    greedy = wrap(face, text, limit, tracking)
    target = lines if lines is not None else len(greedy)
    if target <= 1:
        return greedy
    lo = max(width(face, w, tracking) for w in text.split())
    hi = limit
    best = greedy
    for _ in range(24):
        mid = (lo + hi) / 2.0
        trial = wrap(face, text, mid, tracking)
        if len(trial) <= target:
            best = trial
            hi = mid
        else:
            lo = mid
    if len(best) != target:
        return greedy
    return best


def tracked_fit(book, role, text, limit, size, tracking, minimum=5.0):
    """Size and tracking for a small-caps line that must sit exactly on the
    measure (the dateline row).  Returns (size, tracking)."""
    t = tracking
    s = int(size)
    while s >= minimum:
        face = book.face(role, s)
        for tk in (t, t * 0.8, t * 0.6, t * 0.4, t * 0.2, 0.0):
            if fits(face, text, limit, tk):
                return s, tk
        s -= 1
    return int(minimum), 0.0


# ---------------------------------------------------------------------------
# painting
# ---------------------------------------------------------------------------


def draw_text(face, canvas, x, y, text, color, tracking=0.0):
    """Paint one line with its baseline at (x, y)."""
    if not text:
        return
    if tracking:
        face.render_tracked(canvas, x, y, text, color, tracking)
    else:
        face.render(canvas, x, y, text, color)


def draw_centered(face, canvas, cx, y, text, color, tracking=0.0):
    w = width(face, text, tracking)
    draw_text(face, canvas, cx - w / 2.0, y, text, color, tracking)


def draw_right(face, canvas, right, y, text, color, tracking=0.0):
    w = width(face, text, tracking)
    draw_text(face, canvas, right - w, y, text, color, tracking)


def justify(face, canvas, x0, x1, y, words, color, last_line_left=True):
    """Draw one justified line; the caller has already chosen the words."""
    if not words:
        return
    text = " ".join(words)
    if last_line_left or len(words) == 1:
        draw_text(face, canvas, x0, y, text, color)
        return
    word_w = sum(width(face, w) for w in words)
    gap = (x1 - x0 - word_w) / float(len(words) - 1)
    natural = width(face, " ")
    pen = x0
    for i, w in enumerate(words):
        draw_text(face, canvas, pen, y, w, color)
        pen += width(face, w)
        if i + 1 < len(words):
            pen += gap
    return gap - natural


class Paragraph:
    """A measured block of copy: wrap once, then paint line by line."""

    __slots__ = ("lines", "words", "face", "leading", "width_used")

    def __init__(self, face, text, limit, leading, tracking=0.0):
        self.face = face
        self.leading = leading
        self.lines = wrap(face, text, limit, tracking)
        self.words = [ln.split(" ") for ln in self.lines]
        self.width_used = max([width(face, ln, tracking) for ln in self.lines]
                              or [0.0])

    @property
    def depth(self):
        if not self.lines:
            return 0.0
        return self.leading * (len(self.lines) - 1)

    def paint(self, canvas, x0, x1, baseline, color, justify_body=True,
              tracking=0.0):
        """Paint from the first baseline; returns the last baseline."""
        y = baseline
        n = len(self.lines)
        for i, words in enumerate(self.words):
            last = (i == n - 1)
            if justify_body and not last:
                justify(self.face, canvas, x0, x1, y, words, color)
            else:
                draw_text(self.face, canvas, x0, y, self.lines[i], color,
                          tracking)
            y += self.leading
        return y - self.leading


def vertical_stack(lines, leading, first_baseline, cap):
    """Baselines for a stack of caps-height lines starting at a top edge."""
    out = []
    y = first_baseline
    for _ in lines:
        out.append(y)
        y += leading
    return out

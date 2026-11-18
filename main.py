#!/usr/bin/env python3
"""Entry point for the make.fun bounty news-image-20261117.

Reads nothing, fetches nothing, writes one file: <output_dir>/entry.png, the
front page of THE WORLD for Tuesday 17 November 2026.

    python3 main.py                 # writes /output/entry.png
    python3 main.py out             # writes out/entry.png
    MAKEFUN_OUTPUT_DIR=out python3 main.py

Standard library only.  Two runs write the same bytes.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import frontpage


def main(argv):
    out_dir = None
    if len(argv) > 1:
        out_dir = argv[1]
    if not out_dir:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")

    audit = []
    width, height = frontpage.save_page(path, audit=audit)

    print("wrote %s (%dx%d, %d bytes)"
          % (path, width, height, os.path.getsize(path)))

    bad = frontpage.overruns(audit)
    if bad:
        for label, used, limit in bad:
            print("OVERRUN %s: %.1f > %.1f px" % (label, used, limit),
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

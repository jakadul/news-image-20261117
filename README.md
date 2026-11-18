# THE WORLD — front page, Tuesday 17 November 2026

[![Make.fun competition](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/badge/news-image-20261117)
[![Rank](https://make.fun/badge/news-image-20261117/jakadul/news-image-20261117/rank.svg)](https://make.fun/badge/news-image-20261117/jakadul/news-image-20261117/rank)
[![Reward](https://make.fun/badge/news-image-20261117/jakadul/news-image-20261117/reward.svg)](https://make.fun/badge/news-image-20261117/jakadul/news-image-20261117/reward)

A program that writes one image: the front page of a newspaper called
**THE WORLD** for Tuesday 17 November 2026 — the day Ukraine struck the Kerch
Bridge for the second time in 24 hours, tankers were attacked in the Strait of
Hormuz, Trump landed in Manila for the ASEAN summit, and Wall Street fell hard
on chip export curbs while Anthropic went public.

The page is a real front page, not a poster: utility strip and masthead, a
red-kickered lead story with a night illustration of the strait and a measured
two-strike timeline, a three-column band (Manila / Hormuz / Wall Street), a
closing strip (measles elimination status lost, Congo Ebola past 11,200 cases,
tech outages), and newspaper footer furniture.

## Run it

```sh
python3 -P -s main.py              # writes /output/entry.png
python3 -P -s main.py out          # writes out/entry.png
MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

Output: portrait PNG, 1200 × 1600 pixels, newsprint cream and ink black with
one spot red. Deterministic — two runs produce byte-identical files.

## How it is built

Standard library only; nothing is installed before it runs.

| Module | Role |
| --- | --- |
| `main.py` | entrypoint: resolves the output dir, renders, writes `entry.png`, audits overruns |
| `frontpage.py` | the page layout: masthead, lead, panel, timeline, columns, strip, footer |
| `artwork.py` | the illustrations: Kerch Strait night panel and the strike timeline diagram |
| `typeset.py` | faces, measured pixel-width wrapping, justified copy, tracking |
| `textrender.py` | TrueType outline rasterizer: quadratic flattening, scanline coverage |
| `truetype.py` | TrueType parser (`head`, `hmtx`, `cmap`, `glyf` tables) via `struct` |
| `canvas.py` | RGB raster with supersampling, box downsample, PNG encoder via `zlib` |

The page is painted at 2× and box-downsampled, so the type reads as printed
rather than as screen type. Every block measures its own depth, the page stacks
them once to find the natural height, and the slack is shared among elastic
gaps so the closing strip lands on the foot rule exactly. No randomness
anywhere: the starfield is an LCG seeded by a constant.

## License

MIT — see [LICENSE](LICENSE). SPDX-License-Identifier: MIT.
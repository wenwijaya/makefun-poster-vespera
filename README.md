# VESPERA — The Poster for a Place That Isn't There

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wenwijaya/makefun-poster-vespera/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wenwijaya/makefun-poster-vespera/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![license: MIT](https://img.shields.io/badge/license-MIT-yellow)](./LICENSE)

A travel poster for a place that does not exist, drawn entirely in code for
[make.fun's the-poster-for-a-place-that-i-2-20261121-0539 bounty](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
($50 in USDC).

## The entry

**VESPERA — where the evening never ends.** One landmark, one promise: the
Glass Lighthouse, a cream tower on a dark rock islet, sweeping a beam of gold
across a violet dusk sea toward a low sun, while a single sailboat crosses
the sun's path on the water. The place name is set large across the sky in a
hand-written 5x7 bitmap font, with the tagline beneath it and the lighthouse
named in the footer.

The program is a single self-contained `main.py` — Python 3.13 standard
library only, no network, no file reads, no clocks, no unseeded randomness.
It paints the poster pixel by pixel (gradient sky and sea, sun with halo,
layered headlands, the lighthouse and its beam, birds, stars, and the
poster type) and writes a 1024x1024 PNG with a hand-rolled encoder. Two
runs produce byte-identical output.

## Run it

```sh
python3 main.py
# writes /output/entry.png (1024x1024, under 1 MiB)
```

---

<sub>Entered on [make.fun](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539) · AI agent entry, built by the entrant's own coding agent.</sub>

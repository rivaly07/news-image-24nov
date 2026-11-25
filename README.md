News image — Tuesday 24 November 2026

A deterministic, offline newspaper-style 1024×1024 image built from 32 supplied stories. The page combines a dated masthead and fact strip, a lead story illustration, a three-column story grid, a geographic dateline map, and short additional story listings. Headlines, figures, dates and source labels are rendered from news.json; that supplied dataset is not independently verified reporting.

Render with Python 3 and Pillow:

    MAKEFUN_OUTPUT_DIR=out python3 render.py

This writes out/entry.png. The checked-in entry.png is copied by the Node 22 standard-library script:

    MAKEFUN_OUTPUT_DIR=/tmp/mfout node main.ts

main.ts copies ./entry.png into the selected directory (default: /output); it does not render or access the network. Rendering uses Pillow and the URW Base35 fonts at /usr/share/fonts/opentype/urw-base35/.

Source outlets listed in news.json: Al Jazeera, AP, Reuters, RBC-Ukraine, ABC News, Rio Times, AFP, Radio Tamazuj, Bloomberg, UNICEF, Miami Herald, SBS, PINA, and Investopedia.

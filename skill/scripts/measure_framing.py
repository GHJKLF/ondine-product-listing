#!/usr/bin/env python3
"""Subject bounding box as fractions of the frame, for slot layout QA.
usage: measure_framing.py <preview.jpg> [...]
ponytail: pixels differing >110 from the pixel directly above the frame top count as subject; ignores the soft vignette. Not valid for slot 05 (non-flat background) or slot 04 (area metric)."""
import sys
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f).convert('RGB'); w, h = im.size; px = im.load()
    def diff(x, y):
        bg = px[x, 3]; return sum(abs(a - b) for a, b in zip(px[x, y], bg)) > 110
    rows = [y for y in range(h) if sum(diff(x, y) for x in range(0, w, 3)) > 3]
    cols = [x for x in range(w) if sum(diff(x, y) for y in range(0, h, 3)) > 3]
    print(f, 'height', round((rows[-1] - rows[0]) / h, 3), 'top', round(rows[0] / h, 3), 'bottom', round(1 - rows[-1] / h, 3),
          'left', round(cols[0] / w, 3), 'right', round(1 - cols[-1] / w, 3), 'cx', round((cols[0] + cols[-1]) / 2 / w, 3), 'cy', round((rows[0] + rows[-1]) / 2 / h, 3))

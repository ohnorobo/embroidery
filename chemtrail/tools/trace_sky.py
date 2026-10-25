"""Trace the sky-and-plane shape from the patch photo into tools/white_trace.svg.

Steps: threshold the photo, fit the outer and inner circles, straighten the fuselage, keep the black
pixels inside the inner circle (plane + contrail column), mirror-average for symmetry, subtract from the
inner circle, and trace the resulting white shape with potrace. Needs numpy, scipy, Pillow and potrace.
Run: python3 tools/trace_sky.py
"""
import os, subprocess, numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); PROJECT = os.path.dirname(HERE)
SRC = os.path.join(PROJECT, "33202.jpg")
N = 2000                 # working resolution (px)
BAND = 0.82              # below this fraction of the inner radius everything inside the circle is black
                         # (lobe bottoms end around 0.7), extended 40 px past the circle so the column overlaps the disc

g = np.asarray(Image.open(SRC).convert("L").resize((N, N), Image.LANCZOS)).astype(float)
black = ndi.gaussian_filter(g, 2) < 0.35*255
yy, xx = np.mgrid[:N, :N]

def fit_circle(ex, ey):
    A = np.c_[2*ex, 2*ey, np.ones_like(ex)]; b = ex**2 + ey**2
    (a, bb, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    return a, bb, np.sqrt(c + a*a + bb*bb)

# outer disc
patch = ndi.binary_fill_holes(black)
lab, n = ndi.label(patch); patch = lab == (np.argmax(ndi.sum(patch, lab, range(1, n+1))) + 1)
edge = patch & ~ndi.binary_erosion(patch); ey, ex = np.nonzero(edge)
cx, cy, R_OUT = fit_circle(ex, ey)
# inner circle: rim of the largest white region, upper part only (away from the plane and lobes)
white = patch & ~black
lab, n = ndi.label(white); field = lab == (np.argmax(ndi.sum(white, lab, range(1, n+1))) + 1)
fe = field & ~ndi.binary_erosion(field); ey, ex = np.nonzero(fe)
d = np.hypot(ex-cx, ey-cy); sel = (d > 0.65*R_OUT) & (d < 0.82*R_OUT) & (ey < cy + 0.17*R_OUT)
icx, icy, R_IN = fit_circle(ex[sel], ey[sel])
# fuselage tilt from the centre line of the black run around x=cx
pts = []
for y in range(int(cy-0.58*R_OUT), int(cy), 4):
    row = black[y]; x0 = int(round(cx))
    if not row[x0]: continue
    l = x0
    while row[l-1]: l -= 1
    r = x0
    while row[r+1]: r += 1
    if r - l < 140: pts.append((y, (l+r)/2))
pts = np.array(pts); m, _ = np.polyfit(pts[:, 0], pts[:, 1], 1); tilt = np.degrees(np.arctan(m))
print(f"outer R {R_OUT:.1f}px  inner R {R_IN:.1f}px ({R_IN/R_OUT:.3f} of outer)  tilt {tilt:.2f} deg")

# straighten and recentre on the inner circle
rot = ndi.rotate(black.astype(float), -tilt, reshape=False, order=1) > 0.5
rot = ndi.shift(rot.astype(float), (N/2-icy, N/2-icx), order=1) > 0.5
r = np.hypot(xx-N/2, yy-N/2)
mask = (rot & (r < R_IN)) | ((r < R_IN+40) & (yy > N/2 + R_IN*BAND))
mir = mask[:, ::-1]
sym = (ndi.gaussian_filter(mask.astype(float), 2) + ndi.gaussian_filter(mir.astype(float), 2))/2 > 0.5
sym = ndi.binary_opening(sym, iterations=2); sym = ndi.binary_closing(sym, iterations=2)   # despeckle only
sym |= sym[:, ::-1]
white_shape = (r < R_IN) & ~sym
pbm = os.path.join(HERE, "white_trace.pbm")
Image.fromarray((~white_shape).astype(np.uint8)*255).save(pbm)
subprocess.run(["potrace", pbm, "-s", "-o", os.path.join(HERE, "white_trace.svg"),
                "--turdsize", "300", "--alphamax", "1.2", "--opttolerance", "0.6", "--unit", "10"], check=True)
os.remove(pbm)
ys = np.nonzero(white_shape.any(axis=1))[0]
print(f"white shape spans y {ys.min()}..{ys.max()} (lobe bottoms at {(ys.max()-N/2)/R_IN:.2f} of inner R); inner R in doc units: {R_IN*490/R_OUT:.1f}")

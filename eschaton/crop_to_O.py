"""Bake the crop-to-O into eschaton-only-O.svg.

Reads the SVG, then:
  * sets viewBox / width / height to the O's actual bounding box (~84 x 96)
  * updates both group transforms so the O lands at (0,0)
  * rewrites path1's `d` to "background rect + O hole" with fill-rule=evenodd
  * removes path2-path5 from the background group
  * removes every path from the inverse group except path36 (the O)

Run with: python3 crop_to_O.py
"""

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_PATH = Path(__file__).parent / "eschaton-only-O.svg"
BACKUP_PATH = SVG_PATH.with_suffix(".svg.bak")

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
INKSTITCH_NS = "http://inkstitch.org/namespace"

# Preserve the original namespace prefixes on output.
ET.register_namespace("", SVG_NS)
ET.register_namespace("inkscape", INKSCAPE_NS)
ET.register_namespace("sodipodi", SODIPODI_NS)
ET.register_namespace("inkstitch", INKSTITCH_NS)

# --- tunables ---------------------------------------------------------------

BUFFER = 8  # pt of padding on each side of the O

# O bounds in the *original* SVG coordinate space (from path36).
O_X, O_Y = 765.4, 133.2
O_W, O_H = 83.6, 95.3

# --- derived ----------------------------------------------------------------

CANVAS_W = O_W + 2 * BUFFER
CANVAS_H = O_H + 2 * BUFFER

NEW_VIEWBOX = f"0 0 {CANVAS_W:g} {CANVAS_H:g}"
NEW_WIDTH = f"{CANVAS_W:g}pt"
NEW_HEIGHT = f"{CANVAS_H:g}pt"

# Group transform: matrix(0.1,0,0,-0.1,e,f) where
#   SVG_x = 0.1 * path_x + e
#   SVG_y = -0.1 * path_y + f
# We want the O's top-left (originally SVG (O_X, O_Y)) to land at (BUFFER, BUFFER):
#   e = BUFFER - O_X
#   f = BUFFER + O_Y  (y axis is flipped, so f is *added*: -0.1*(O_Y/0.1) + f = BUFFER)
E = BUFFER - O_X
F = BUFFER + O_Y
NEW_TRANSFORM = f"matrix(0.1,0,0,-0.1,{E:g},{F:g})"

# Background rect in path-coords covering the new viewBox.
# SVG (0,0) -> path ((-E)/0.1, F/0.1)
# SVG (W,H) -> path ((W-E)/0.1, (F-H)/0.1)
RECT_X0 = round(-E / 0.1)
RECT_X1 = round((CANVAS_W - E) / 0.1)
RECT_Y_TOP = round(F / 0.1)        # corresponds to SVG y=0
RECT_Y_BOT = round((F - CANVAS_H) / 0.1)  # corresponds to SVG y=CANVAS_H

NEW_PATH1_D = (
    f"M {RECT_X0},{RECT_Y_TOP} H {RECT_X1} V {RECT_Y_BOT} H {RECT_X0} Z "
    "M 8138,1324 "
    "c 216,-107 352,-558 237,-783 "
    "-30,-59 -57,-84 -130,-118 "
    "-58,-27 -66,-28 -215,-28 "
    "h -155 l -62,34 "
    "c -78,42 -109,85 -129,182 "
    "-30,142 7,367 86,516 "
    "43,84 75,123 133,167 "
    "79,60 155,70 235,30 z"
)


def q(tag: str) -> str:
    """Qualify an SVG-namespaced tag."""
    return f"{{{SVG_NS}}}{tag}"


def ensure_evenodd(path_el: ET.Element) -> None:
    """Add fill-rule:evenodd to the path's style (preserving other props)."""
    style = path_el.get("style", "") or ""
    parts = [p.strip() for p in style.split(";") if p.strip()]
    parts = [p for p in parts if not p.startswith("fill-rule")]
    parts.append("fill-rule:evenodd")
    path_el.set("style", ";".join(parts))


def main() -> None:
    if not SVG_PATH.exists():
        raise SystemExit(f"missing: {SVG_PATH}")

    shutil.copy2(SVG_PATH, BACKUP_PATH)
    print(f"backup -> {BACKUP_PATH.name}")

    tree = ET.parse(SVG_PATH)
    root = tree.getroot()

    # 1. resize the canvas
    root.set("viewBox", NEW_VIEWBOX)
    root.set("width", NEW_WIDTH)
    root.set("height", NEW_HEIGHT)

    # 2. retransform the two groups
    bg = root.find(q("g") + "[@id='background']")
    inv = root.find(q("g") + "[@id='g12']")
    if bg is None or inv is None:
        raise SystemExit("could not locate expected groups")
    bg.set("transform", NEW_TRANSFORM)
    inv.set("transform", NEW_TRANSFORM)

    # 3. rewrite path1: background rect + O hole only, evenodd fill
    path1 = bg.find(q("path") + "[@id='path1']")
    if path1 is None:
        raise SystemExit("missing path1")
    path1.set("d", NEW_PATH1_D)
    ensure_evenodd(path1)

    # 4. drop the other background fills (counters for non-O letters)
    removed_bg = 0
    for pid in ("path2", "path3", "path4", "path5"):
        p = bg.find(q("path") + f"[@id='{pid}']")
        if p is not None:
            bg.remove(p)
            removed_bg += 1

    # 5. drop every inverse-group path except path36
    removed_inv = 0
    for p in list(inv.findall(q("path"))):
        if p.get("id") != "path36":
            inv.remove(p)
            removed_inv += 1

    tree.write(SVG_PATH, xml_declaration=True, encoding="UTF-8")
    print(f"removed {removed_bg} background paths, {removed_inv} inverse paths")
    print(f"wrote -> {SVG_PATH.name}")


if __name__ == "__main__":
    main()

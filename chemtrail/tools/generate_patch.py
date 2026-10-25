"""Generate the Chemtrail Operations patch SVGs.

Outputs (in the project folder):
  chemtrail_patch.svg           clean artwork, no Ink/Stitch markup
  chemtrail_patch_livetext.svg  same, with editable SVG text
  chemtrail_patch_stitch.svg    Ink/Stitch-ready: hidden fabric/debug layers, satin lettering, cut line, merrow satin
Needs: fonttools svgpathtools numpy (python3 -m pip install --user --break-system-packages ...)
Run:   python3 tools/generate_patch.py
"""
import re, sys, os, math, numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__)); PROJECT = os.path.dirname(HERE)
FONT = "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf"   # preview lettering only; stitched letters use the Ink/Stitch Small Font
FAMILY = "Arial Narrow"
OUT = os.path.join(PROJECT, "chemtrail_patch.svg")
k = 490/887.3
PATCH_D_MM = 60.0
FILL_DEBUG_COLOR = "#1e90ff"   # sky-and-plane thread color in the stitch file while debugging (real color: #ffffff)
TEXT_DEBUG_COLOR = "#00b400"   # lettering thread color in the stitch file while debugging (real color: #ffffff)
STITCH_MERROW = True          # include the cut line + satin ring in the stitch file
TRIM_LETTERS = False          # trim after every letter (filehelper.com choked on these)
C = 500; R_OUT = 490; DOC_MM = PATCH_D_MM*1000/(2*R_OUT); R_IN = round(665.26*k, 1)
CAP_MM = 4.0                                # lettering cap height; Glacial Tiny is wide, so taller letters sweep further around the ring
SKY_SCALE = 0.96                            # shrink the sky-and-plane about the centre to widen the lettering band
CAP = CAP_MM*1000/DOC_MM
BORDER_W = 35; BORDER_COLOR = "#808080"
R_SKY = round(665.26*k*SKY_SCALE,1)
GAP = (R_OUT-BORDER_W - R_SKY - CAP)/2   # equal clearance above and below the text
TOP_TXT, TOP_RB, TOP_CAP, TOP_SPAN = "CHEMTRAIL OPERATIONS", R_SKY+GAP, CAP, 152.0
BOT_TXT, BOT_CAP, BOT_RB, BOT_SPAN = "FLIGHT  CREW", CAP, R_OUT-BORDER_W-GAP, 80.0

# ---- bake potrace transform into a path: absolute first M, relative rest
def bake(fn):
    src=open(fn).read()
    ks=k*SKY_SCALE; sx=0.1*ks; sy=-0.1*ks; tx=C-1000*ks; ty=C+1000*ks
    out=[]
    for d in re.findall(r'<path d="([^"]+)"', src):
        toks=re.findall(r'[MmLlCcZz]|-?\d+\.?\d*', d)
        i=0; first=True
        while i<len(toks):
            t=toks[i]
            if t.isalpha(): out.append(t); i+=1; continue
            x=float(toks[i]); y=float(toks[i+1]); i+=2
            if first: out.append(f"{x*sx+tx:.2f} {y*sy+ty:.2f}"); first=False
            else: out.append(f"{x*sx:.2f} {y*sy:.2f}")
    return " ".join(out)
white_d=bake(os.path.join(HERE, "white_trace.svg"))

# ---- font
f = TTFont(FONT); gs = f.getGlyphSet(); cmap = f.getBestCmap(); hmtx = f["hmtx"]
bp = BoundsPen(gs); gs[cmap[ord("H")]].draw(bp); cap_units = bp.bounds[3]
def glyph_path(ch, M):
    """M: 3x3 affine mapping font units (y up) -> svg coords."""
    pen = SVGPathPen(gs)
    tp = TransformPen(pen, (M[0,0], M[1,0], M[0,1], M[1,1], M[0,2], M[1,2]))
    gs[cmap[ord(ch)]].draw(tp)
    return pen.getCommands()
def adv(ch): return hmtx[cmap[ord(ch)]][0]
def T(dx,dy): return np.array([[1,0,dx],[0,1,dy],[0,0,1]],float)
def S(sx,sy): return np.array([[sx,0,0],[0,sy,0],[0,0,1]],float)
def Rz(a): c,s=math.cos(a),math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]],float)
flip = T(C,C) @ S(1,-1)   # math coords (y up, origin center) -> svg

# top text on arc: fit letters into TOP_SPAN degrees at baseline radius
s = TOP_CAP/cap_units
widths=[adv(ch)*s for ch in TOP_TXT]
nat_arc = math.degrees(sum(widths)/TOP_RB)
print("top nat_arc",nat_arc,"extra deg/letter",(TOP_SPAN-nat_arc)/(len(TOP_TXT)-1),"text outer r",TOP_RB+TOP_CAP)
extra = (TOP_SPAN-nat_arc)/(len(TOP_TXT)-1)  # letter-spacing in degrees
paths_top=[]; ang = 90 + TOP_SPAN/2  # start at left (larger angle), move clockwise
for ch,w in zip(TOP_TXT,widths):
    half = math.degrees(w/TOP_RB)/2
    phi = math.radians(ang-half)
    M = flip @ T(TOP_RB*math.cos(phi), TOP_RB*math.sin(phi)) @ Rz(phi-math.pi/2) @ S(s,s) @ T(-adv(ch)/2,0)
    if ch!=" ": paths_top.append(glyph_path(ch,M))
    ang -= 2*half+extra
# bottom text on an arc concentric with the top text, tops of letters toward center
s2 = BOT_CAP/cap_units
widths=[adv(ch)*s2 for ch in BOT_TXT]
nat2 = math.degrees(sum(widths)/BOT_RB)
extra2=(BOT_SPAN-nat2)/(len(BOT_TXT)-1)
paths_bot=[]; ang=-90-BOT_SPAN/2   # start at lower-left, move counterclockwise (toward right)
for ch,w in zip(BOT_TXT,widths):
    half=math.degrees(w/BOT_RB)/2
    phi=math.radians(ang+half)
    M = flip @ T(BOT_RB*math.cos(phi), BOT_RB*math.sin(phi)) @ Rz(phi+math.pi/2) @ S(s2,s2) @ T(-adv(ch)/2,0)
    if ch!=" ": paths_bot.append(glyph_path(ch,M))
    ang += 2*half+extra2

svg=f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{DOC_MM:.3f}mm" height="{DOC_MM:.3f}mm" viewBox="0 0 1000 1000">
  <title>Chemtrail Operations Flight Crew patch</title>
  <rect id="debug-background" x="0" y="0" width="1000" height="1000" fill="#cfe3ff"/>
  <circle id="fabric" cx="{C}" cy="{C}" r="{R_OUT}" fill="#000000"/>
  <path id="sky-and-plane" d="{white_d}" fill="#ffffff" fill-rule="evenodd"/>
  <g id="lettering" fill="#ffffff">
    <g id="text-top">
{chr(10).join(f'      <path d="{p}"/>' for p in paths_top)}
    </g>
    <g id="text-bottom">
{chr(10).join(f'      <path d="{p}"/>' for p in paths_bot)}
    </g>
  </g>
  <g id="merrow-border">
    <path id="border-ring" fill="{BORDER_COLOR}" fill-rule="evenodd" d="M {C+R_OUT} {C} A {R_OUT} {R_OUT} 0 1 0 {C-R_OUT} {C} A {R_OUT} {R_OUT} 0 1 0 {C+R_OUT} {C} Z M {C+R_OUT-BORDER_W} {C} A {R_OUT-BORDER_W} {R_OUT-BORDER_W} 0 1 0 {C-R_OUT+BORDER_W} {C} A {R_OUT-BORDER_W} {R_OUT-BORDER_W} 0 1 0 {C+R_OUT-BORDER_W} {C} Z"/>
  </g>
</svg>
'''
open(OUT,"w").write(svg)

# stitch-ready variant: hide non-stitched layers, add Ink/Stitch params
FILL = 'inkstitch:fill_underlay="True" inkstitch:angle="0" inkstitch:row_spacing_mm="0.25" inkstitch:max_stitch_length_mm="3"'
TEXT = 'inkstitch:fill_underlay="False" inkstitch:angle="45" inkstitch:row_spacing_mm="0.2" inkstitch:max_stitch_length_mm="2"'
st = svg.replace('xmlns="http://www.w3.org/2000/svg"', 'xmlns="http://www.w3.org/2000/svg" xmlns:inkstitch="http://inkstitch.org/namespace"')
st = st.replace('  <title>Chemtrail Operations Flight Crew patch</title>', '  <title>Chemtrail Operations Flight Crew patch</title>\n  <metadata><inkstitch:inkstitch_svg_version>3</inkstitch:inkstitch_svg_version></metadata>')
st = st.replace('<rect id="debug-background"', '<rect id="debug-background" style="display:none"')
st = st.replace('<circle id="fabric"', '<circle id="fabric" style="display:none"')
CUT_R = R_OUT - 10   # cut line ~0.9 mm inside the satin's outer edge
def circ(rad):      # closed circle for the running-stitch cut line
    return f"M {C+rad} {C} A {rad} {rad} 0 0 1 {C-rad} {C} A {rad} {rad} 0 0 1 {C+rad} {C} Z"
def rail(rad):      # open 360-degree arc, four quarter arcs, starting at 6 o'clock, clockwise on screen
    pts=[(C, C+rad),(C-rad, C),(C, C-rad),(C+rad, C),(C, C+rad)]
    return f"M {pts[0][0]} {pts[0][1]} " + " ".join(f"A {rad} {rad} 0 0 1 {x} {y}" for x,y in pts[1:])
def rungs(r_in, r_out, angles_deg):   # radial segments crossing both rails
    out=[]
    for a in angles_deg:
        a=math.radians(a); r0=r_in-6; r1=r_out+6
        out.append(f"M {C+r0*math.cos(a):.2f} {C+r0*math.sin(a):.2f} L {C+r1*math.cos(a):.2f} {C+r1*math.sin(a):.2f}")
    return " ".join(out)
SATIN_D = f"{rail(R_OUT)} {rail(R_OUT-BORDER_W)} {rungs(R_OUT-BORDER_W, R_OUT, (45,135,225,315))}"
hide = "" if STITCH_MERROW else ' style="display:none"'
cut_line = f'''  <g id="cut-line-group"{hide}>
    <path id="cut-line" d="{circ(CUT_R)}" fill="none" stroke="#ff0000" stroke-width="1"
      inkstitch:stroke_method="running_stitch" inkstitch:running_stitch_length_mm="2.5"/>
  </g>
'''
merrow = f'''<g id="merrow-border"{hide}>
    <path id="merrow-satin" d="{SATIN_D}" fill="none" stroke="{BORDER_COLOR}" stroke-width="1"
      inkstitch:satin_column="True" inkstitch:zigzag_spacing_mm="0.4" inkstitch:pull_compensation_mm="0.3"
      inkstitch:contour_underlay="True" inkstitch:center_walk_underlay="True" inkstitch:zigzag_underlay="True"/>
  </g>'''
st = re.sub(r'<g id="merrow-border">.*?</g>', merrow, st, flags=re.S)
st = st.replace('  <path id="sky-and-plane"', cut_line + '  <path id="sky-and-plane"', 1)   # cut line stitches first
st = st.replace('<path id="sky-and-plane"', f'<path id="sky-and-plane" {FILL}').replace('id="sky-and-plane" ' + FILL + ' d=', 'id="sky-and-plane" ' + FILL + ' d=')
st = re.sub(r'(<path id="sky-and-plane"[^>]*fill=")#ffffff"', r'\1'+FILL_DEBUG_COLOR+'"', st)
import xml.etree.ElementTree as ET
from svgpathtools import parse_path
STITCH_FONT = "glacial_tiny"   # Ink/Stitch satin font for the stitched lettering (needs 60wt thread); "small_font" also works
FONT_DIR = os.path.expanduser("~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/inkstitch/inkstitch.app/Contents/Resources/fonts/" + STITCH_FONT)
NS = {'svg':'http://www.w3.org/2000/svg','inkscape':'http://www.inkscape.org/namespaces/inkscape','sodipodi':'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'}
froot = ET.parse(os.path.join(FONT_DIR, "→.svg")).getroot()
import json
FONT_H = float(froot.get('viewBox').split()[3])
_guides = {g.get('{%s}label' % NS['inkscape']): float(g.get('position').split(',')[1]) for g in froot.iter('{%s}guide' % NS['sodipodi'])}
FONT_BASELINE, FONT_CAPS = FONT_H - _guides['baseline'], FONT_H - _guides['caps']     # guides are stored bottom-up
_fj = json.load(open(os.path.join(FONT_DIR, "font.json")))
ADV = _fj.get("horiz_adv_x") or {}; ADV_DEFAULT = _fj.get("horiz_adv_x_default"); ADV_SPACE = _fj.get("horiz_adv_x_space", 10)
KERN = _fj.get("kerning_pairs") or {}
glyphs = {}
for g in froot.findall('svg:g', NS):
    lab = g.get('{%s}label' % NS['inkscape']) or ''
    if lab.startswith('GlyphLayer-'):
        paths = list(g.iter('{%s}path' % NS['svg']))
        xs=[]; ys=[]
        for p in paths:
            x0,x1,y0,y1 = parse_path(p.get('d')).bbox(); xs += [x0,x1]; ys += [y0,y1]
        glyphs[lab[len('GlyphLayer-'):]] = (paths, min(xs), max(xs))
def advance(ch):   # font units; falls back to the glyph ink width when the font gives none
    a = ADV.get(ch) or ADV_DEFAULT
    if a is None: _,x0,x1 = glyphs[ch]; a = x1 - x0
    return a
fs = CAP/(FONT_BASELINE-FONT_CAPS)              # doc units per font unit
LETTER_GAP = 0.10*1000/DOC_MM                   # extra space between letters, on top of the font advance
WORD_GAP = ADV_SPACE*fs                          # the font space advance
STROKE = f"fill:none;stroke:{TEXT_DEBUG_COLOR};stroke-width:0.3"
def glyph_group(ch, M, idx):
    a,b,c,d,e,f = M[0,0],M[1,0],M[0,1],M[1,1],M[0,2],M[1,2]
    paths, x0, x1 = glyphs[ch]
    out=[f'      <g id="glyph-{idx}-{ch}" transform="matrix({a:.5f} {b:.5f} {c:.5f} {d:.5f} {e:.3f} {f:.3f})">']
    for j,p in enumerate(paths):
        attrs = {k:v for k,v in p.attrib.items() if k.startswith('{http://inkstitch.org/namespace}')}
        inkst = " ".join(f'inkstitch:{k.split("}")[1]}="{v}"' for k,v in attrs.items())
        trim = ' inkstitch:trim_after="True"' if (TRIM_LETTERS and j==len(paths)-1) else ''
        style = re.sub(r'stroke:#[0-9a-fA-F]+', 'stroke:'+TEXT_DEBUG_COLOR, p.get('style') or '')
        if 'stroke:' not in style: style += ';stroke:'+TEXT_DEBUG_COLOR
        style = re.sub(r'fill:[^;]+', 'fill:none', style) if 'fill:' in style else style+';fill:none'
        out.append(f'        <path id="glyph-{idx}-{ch}-{j}" style="{style.strip(";")}" {inkst}{trim} d="{p.get("d")}"/>')
    out.append('      </g>')
    return "\n".join(out)
def arc_text(text, rb, span, top, start_idx):
    # width of each character cell along the baseline (doc units), including kerning with the previous char
    cells=[]
    for i,ch in enumerate(text):
        if ch==" ": cells.append(WORD_GAP); continue
        w = advance(ch)*fs + LETTER_GAP
        if i>0 and text[i-1]!=" ": w -= KERN.get(f"{text[i-1]} {ch}", 0)*fs
        cells.append(w)
    nat = math.degrees(sum(cells)/rb); span=max(span,nat); extra=(span-nat)/(len(text)-1)
    print(f"satin {'top' if top else 'bottom'}: natural span {nat:.1f} deg, target {span:.1f}, extra {extra:.2f} deg/letter")
    ang = 90+span/2 if top else -90-span/2
    out=[]; i=start_idx
    for ch,w in zip(text,cells):
        half=math.degrees(w/rb)/2
        phi=math.radians(ang-half if top else ang+half)
        if ch!=" ":
            local = S(1,-1) @ T(-advance(ch)/2, -FONT_BASELINE)     # center the advance box on the anchor, baseline at y=0, y up
            M = flip @ T(rb*math.cos(phi), rb*math.sin(phi)) @ Rz(phi-math.pi/2 if top else phi+math.pi/2) @ S(fs,fs) @ local
            out.append(glyph_group(ch, M, i)); i+=1
        ang += (-(2*half+extra)) if top else (2*half+extra)
    return "\n".join(out)
satin_text = ('  <g id="lettering-satin">\n    <g id="text-top">\n' + arc_text(TOP_TXT, TOP_RB, TOP_SPAN, True, 0)
            + '\n    </g>\n    <g id="text-bottom">\n' + arc_text(BOT_TXT, BOT_RB, BOT_SPAN, False, 100) + '\n    </g>\n  </g>')
st = re.sub(r'  <g id="lettering" fill="#ffffff">.*?\n  </g>\n', satin_text + "\n", st, flags=re.S)
open(OUT.replace(".svg","_stitch.svg"),"w").write(st)

# live-text variant
top_path_r = TOP_RB
a0=math.radians(90+TOP_SPAN/2); a1=math.radians(90-TOP_SPAN/2)
x0,y0 = C+top_path_r*math.cos(a0), C-top_path_r*math.sin(a0)
x1,y1 = C+top_path_r*math.cos(a1), C-top_path_r*math.sin(a1)
b0=math.radians(90+BOT_SPAN/2); b1=math.radians(90-BOT_SPAN/2)
bx0,by0 = C+BOT_RB*math.cos(b0), C+BOT_RB*math.sin(b0)
bx1,by1 = C+BOT_RB*math.cos(b1), C+BOT_RB*math.sin(b1)
fs = TOP_CAP/cap_units*f["head"].unitsPerEm; fs2 = BOT_CAP/cap_units*f["head"].unitsPerEm
svg_t = svg.split('<g id="lettering"')[0] + f'''<defs>
    <path id="top-arc" d="M {x0:.2f} {y0:.2f} A {top_path_r:.2f} {top_path_r:.2f} 0 0 1 {x1:.2f} {y1:.2f}"/>
    <path id="bottom-arc" d="M {bx0:.2f} {by0:.2f} A {BOT_RB:.2f} {BOT_RB:.2f} 0 0 0 {bx1:.2f} {by1:.2f}"/>
  </defs>
  <g id="lettering" fill="#ffffff" font-family="{FAMILY}" font-weight="bold">
    <text font-size="{fs:.1f}" textLength="{math.radians(TOP_SPAN)*top_path_r:.1f}" lengthAdjust="spacing"><textPath href="#top-arc">{TOP_TXT}</textPath></text>
    <text font-size="{fs2:.1f}" textLength="{math.radians(BOT_SPAN)*BOT_RB:.1f}" lengthAdjust="spacing" xml:space="preserve"><textPath href="#bottom-arc">{BOT_TXT}</textPath></text>
  </g>
  <g id="merrow-border">
    <path id="border-ring" fill="{BORDER_COLOR}" fill-rule="evenodd" d="M {C+R_OUT} {C} A {R_OUT} {R_OUT} 0 1 0 {C-R_OUT} {C} A {R_OUT} {R_OUT} 0 1 0 {C+R_OUT} {C} Z M {C+R_OUT-BORDER_W} {C} A {R_OUT-BORDER_W} {R_OUT-BORDER_W} 0 1 0 {C-R_OUT+BORDER_W} {C} A {R_OUT-BORDER_W} {R_OUT-BORDER_W} 0 1 0 {C+R_OUT-BORDER_W} {C} Z"/>
  </g>
</svg>
'''
open(OUT.replace(".svg","_livetext.svg"),"w").write(svg_t)
print("sky R mm",round(R_SKY*DOC_MM/1000,2),"band gap mm",round(GAP*DOC_MM/1000,2),"doc mm",round(DOC_MM,3),"top cap mm",round(TOP_CAP*DOC_MM/1000,2),"bottom cap mm",round(BOT_CAP*DOC_MM/1000,2),"ring mm",round(BORDER_W*DOC_MM/1000,2));print("cap units",cap_units,"R_IN",R_IN,"paths",len(paths_top),len(paths_bot))

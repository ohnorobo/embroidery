#!/bin/bash
# Repeatable pipeline: source painting -> rotated/cropped eye rectangle -> multi-colour SVG.
# Usage: ./make_eyes.sh <config-file>
# Requires: ImageMagick (magick), potrace, rsvg-convert. No Python needed.
set -euo pipefail
cd "$(dirname "$0")"
CONF=${1:?usage: make_eyes.sh <config-file>}
# shellcheck source=/dev/null
source "$CONF"
: "${SRC:?}" "${NAME:?}" "${EYE1_X:?}" "${EYE1_Y:?}" "${EYE2_X:?}" "${EYE2_Y:?}" "${CROP_W:?}" "${CROP_H:?}"
UPSCALE=${UPSCALE:-4}            # enlarge factor before tracing for smoother curves
TURD=${TURD:-10}                 # potrace: drop specks smaller than this many (upscaled) pixels
ALPHAMAX=${ALPHAMAX:-1.0}        # potrace: corner smoothing (0 = sharp corners, 1.33 = very smooth)
SHIFT_X=${SHIFT_X:-0}; SHIFT_Y=${SHIFT_Y:-0}   # nudge the crop (in rotated image pixels)
# LAYERS: array of "name|svg-fill|sample-colour|fuzz|blur[|grow]", traced in order (later = on top).
#   grow = px to fatten the traced shape so it tucks under the layer drawn on top of it (no gap at the line edge).
#   sample-colour = a pixel colour from the crop; fuzz = how far from it still counts (%).
# SKIN="sample-colour|fuzz|blur" region that gets dots; SKIN_EXCLUDE=("colour|fuzz|blur" ...) keeps solid areas (whites) clear.
# SKIN also gets DOT_COLOR dots, DOT_SPACING apart, DOT_RADIUS big.
DOT_COLOR=${DOT_COLOR:-#c0392b}; DOT_SPACING=${DOT_SPACING:-4}; DOT_RADIUS=${DOT_RADIUS:-1.1}
DOT_ANGLE_SRC=${DOT_ANGLE_SRC:-0}   # angle of the halftone grid rows in the SOURCE image (deg); rotation is added automatically
DOT_STAGGER=${DOT_STAGGER:-0}       # 1 = offset alternate rows by half a spacing (brick/hex pattern), 0 = square grid
DOT_ROW_SPACING=${DOT_ROW_SPACING:-$DOT_SPACING}  # distance between rows (defaults to DOT_SPACING)
DOTS_UNDER=${DOTS_UNDER:-lines}     # layers the dot grid continues underneath (space-separated); other layers knock dots out
EXCLUDE_GROW=${EXCLUDE_GROW:-1}     # px to fatten each SKIN_EXCLUDE area so dots on its edge go too
ENCLOSED_BY=${ENCLOSED_BY:-lines}   # layer whose strokes enclose tears / eye whites
ENCLOSED_MAX_AREA=${ENCLOSED_MAX_AREA:-0}  # >0: any pocket enclosed by that layer, up to this many px, gets no dots
# LAYER_PRUNE=("layer|inside-layer|max-area" ...): drop pieces of <layer> that lie entirely inside <inside-layer>
#   (grown by 1 source px) and are at most max-area source px² (e.g. dark flecks inside the hair traced as black).
ENCLOSED_NOT_NEAR=${ENCLOSED_NOT_NEAR:-}  # "excess|radius": a source pixel is a red dot when R exceeds both G and B by more than <excess> (0..1);
                                          #   pocket pixels within <radius> px of one are NOT cleared, so a pocket running into dotted skin stays dotted
ENCLOSED_GAP=${ENCLOSED_GAP:-0}     # px to fatten the strokes before flood-filling, so small breaks in an outline still enclose
# MANUAL_DOTS=file: hand edits, one per line, "keep SX SY" or "remove SX SY" in SOURCE image pixels.
#   The nearest grid dot to each point is forced in or out. output/<NAME>/dots.txt lists every drawn dot as
#   "crop_x crop_y source_x source_y" to copy coordinates from.
MANUAL_DOTS=${MANUAL_DOTS:-}
# SKIN="all" means: every pixel not claimed by a layer or SKIN_EXCLUDE gets dots (most robust when the crop is all face)

OUT=output/$NAME; mkdir -p "$OUT/layers"
S=$((UPSCALE*100))%

# --- 1. Rotate so the eye line is horizontal, crop ------------------------------------------
read -r ANGLE ROT CX CY <<<"$(awk -v x1="$EYE1_X" -v y1="$EYE1_Y" -v x2="$EYE2_X" -v y2="$EYE2_Y" \
  'BEGIN{pi=atan2(0,-1); a=atan2(y2-y1,x2-x1)*180/pi; printf "%.3f %.3f %.1f %.1f\n", a, -a, (x1+x2)/2, (y1+y2)/2}')"
echo "$NAME: eye line angle ${ANGLE}°, midpoint ($CX,$CY); rotating by ${ROT}°"
X0=$(awk -v c="$CX" -v w="$CROP_W" -v s="$SHIFT_X" 'BEGIN{printf "%d", c-w/2+s}')
Y0=$(awk -v c="$CY" -v h="$CROP_H" -v s="$SHIFT_Y" 'BEGIN{printf "%d", c-h/2+s}')
magick "$SRC" -virtual-pixel white -distort SRT "$CX,$CY 1 $ROT $CX,$CY" \
  -crop "${CROP_W}x${CROP_H}+${X0}+${Y0}" +repage "$OUT/crop_color.png"

# mask <out> <colour> <fuzz> <blur> <scale%> : black where the crop is near <colour>, else white
mask() { magick "$OUT/crop_color.png" -resize "$5" -blur "0x$4" -fuzz "$3" \
           -transparent "$2" -alpha extract -threshold 50% -alpha off "$1"; }

# --- 2. Trace each colour layer -------------------------------------------------------------
GROUPS_SVG=""
for spec in "${LAYERS[@]}"; do
  IFS='|' read -r lname fill sample fuzz blur grow <<<"$spec"
  mask "$OUT/layers/$lname.png" "$sample" "$fuzz" "$blur" "$S"
  for rule in "${LAYER_PRUNE[@]-}"; do
    [[ -z "$rule" ]] && continue
    IFS='|' read -r target inside maxarea <<<"$rule"; [[ "$target" == "$lname" ]] || continue
    # inside-region grown 1 source px; a white 1px frame means pieces touching the crop edge count as "outside" and are kept
    magick "$OUT/layers/$inside.raw.png" -morphology Erode "Disk:$UPSCALE" -shave 1x1 -bordercolor white -border 1 "$OUT/layers/prune_region.png"
    magick "$OUT/layers/$lname.png" -negate -define connected-components:mean-color=false -connected-components 8 -depth 16 "$OUT/layers/prune_labels.png" 2>/dev/null
    touching=$(magick "$OUT/layers/prune_labels.png" \( "$OUT/layers/prune_region.png" -depth 16 \) -compose Multiply -composite -depth 16 -format %c histogram:info:- \
      | awk '{v=$2; gsub(/[()]/,"",v); split(v,a,","); if(a[1]+0>0) print a[1]+0}' | sort -un | paste -sd, -)
    remove=$(magick "$OUT/layers/$lname.png" -negate -define connected-components:verbose=true -connected-components 8 null: 2>/dev/null \
      | awk -v ids=",$touching," -v max=$((maxarea*UPSCALE*UPSCALE)) '$1 ~ /^[0-9]+:$/ && $NF ~ /white|srgb\(255,255,255\)|gray\(255\)/ \
          {id=$1; sub(":","",id); if(index(ids, ","id",")==0 && $(NF-1)+0<=max) print id}' | paste -sd, -)
    if [[ -n "$remove" ]]; then
      magick "$OUT/layers/$lname.png" -negate -define connected-components:remove-ids="$remove" -define connected-components:mean-color=true \
        -connected-components 8 -negate -threshold 50% "$OUT/layers/$lname.png" 2>/dev/null
      echo "pruned $(echo "$remove" | tr ',' '\n' | wc -l | tr -d ' ') piece(s) of '$lname' lying inside '$inside'"
    fi
  done
  cp "$OUT/layers/$lname.png" "$OUT/layers/$lname.raw.png"      # ungrown copy, used for dot knockout
  if [[ -n "${grow:-}" && "$grow" != 0 ]]; then
    # black=shape (IM treats white as foreground): Close drops black specks thinner than ~2 source px, Erode then grows the shape
    magick "$OUT/layers/$lname.png" -morphology Close "Disk:$UPSCALE" -morphology Erode "Disk:$((grow*UPSCALE))" "$OUT/layers/$lname.png"
  fi
  magick "$OUT/layers/$lname.png" "$OUT/layers/$lname.pbm"
  potrace "$OUT/layers/$lname.pbm" --svg --turdsize "$TURD" --alphamax "$ALPHAMAX" \
    --width "${CROP_W}pt" --height "${CROP_H}pt" -o "$OUT/layers/$lname.svg"
  rm "$OUT/layers/$lname.pbm"
  g=$(sed -n '/<g /,/<\/g>/p' "$OUT/layers/$lname.svg" | sed "s/fill=\"#000000\"/id=\"$lname\" fill=\"$fill\"/")
  GROUPS_SVG+="$g"$'\n'
done

# --- 3. Skin dots: regular grid, only where the skin mask is set and no layer covers it ------
DOTS_SVG=""
if [[ -n "${SKIN:-}" ]]; then
  IFS='|' read -r sample fuzz blur <<<"$SKIN"
  if [[ "$SKIN" == all ]]; then
    magick -size "${CROP_W}x${CROP_H}" xc:black "$OUT/layers/skin_raw.png"
  else
    mask "$OUT/layers/skin_raw.png" "$sample" "$fuzz" "$blur" 100%
  fi
  cp "$OUT/layers/skin_raw.png" "$OUT/layers/skin.png"
  i=0
  for spec in "${SKIN_EXCLUDE[@]-}"; do     # solid areas of this colour (eye whites, tears) get no dots
    [[ -z "$spec" ]] && continue; i=$((i+1))
    IFS='|' read -r sample fuzz blur <<<"$spec"
    mask "$OUT/layers/skin_exclude$i.png" "$sample" "$fuzz" "$blur" 100%
    # black = excluded area (IM treats white as foreground): Close drops black specks, Erode grows the black area
    magick "$OUT/layers/skin.png" \( "$OUT/layers/skin_exclude$i.png" -morphology Close Disk:1 -morphology Erode "Disk:$EXCLUDE_GROW" -negate \) \
      -compose Lighten -composite "$OUT/layers/skin.png"
  done
  if (( ENCLOSED_MAX_AREA > 0 )); then     # pockets fully enclosed by ENCLOSED_BY strokes (tears, eye whites) get no dots
    # work at tracing resolution (the traced mask) so thin outlines stay closed, downscale the pockets at the end
    cp "$OUT/layers/$ENCLOSED_BY.raw.png" "$OUT/layers/enclosed_strokes.png"
    (( ENCLOSED_GAP > 0 )) && magick "$OUT/layers/enclosed_strokes.png" -morphology Erode "Disk:$((ENCLOSED_GAP*UPSCALE))" "$OUT/layers/enclosed_strokes.png"
    # flood from the border through non-stroke pixels; whatever stays white is enclosed
    magick "$OUT/layers/enclosed_strokes.png" -bordercolor white -border 1 -fill black -draw "color 0,0 floodfill" -shave 1x1 \
      -negate -alpha off -threshold 50% "$OUT/layers/enclosed_all.png"
    # drop pockets bigger than ENCLOSED_MAX_AREA (e.g. a face region that happens to be ringed by lines)
    big=$(magick "$OUT/layers/enclosed_all.png" -define connected-components:verbose=true -connected-components 4 null: 2>/dev/null \
      | awk -v max="$((ENCLOSED_MAX_AREA*UPSCALE*UPSCALE))" '$1 ~ /^[0-9]+:$/ && $NF ~ /^(srgb\(0,0,0\)|black|gray\(0\))$/ && $(NF-1)+0 > max {split($3,c,","); printf "-fill white -draw \"color %d,%d floodfill\" ", c[1], c[2]}')
    eval magick "$OUT/layers/enclosed_all.png" $big -resize "${CROP_W}x${CROP_H}!" -threshold 50% "$OUT/layers/enclosed.png"
    if [[ -n "$ENCLOSED_NOT_NEAR" ]]; then
      IFS='|' read -r excess radius <<<"$ENCLOSED_NOT_NEAR"
      magick "$OUT/crop_color.png" -fx "(r-g>$excess && r-b>$excess)?0:1" -threshold 50% "$OUT/layers/enclosed_dots.png"   # black = a red dot pixel
      magick "$OUT/layers/enclosed_dots.png" -morphology Erode "Disk:$radius" -negate "$OUT/layers/enclosed_dotted.png"   # white = near a dot
      magick "$OUT/layers/enclosed.png" "$OUT/layers/enclosed_dotted.png" -compose Lighten -composite "$OUT/layers/enclosed.png"
    fi
    # Erode grows the black pockets by EXCLUDE_GROW (plus the gap the strokes were fattened by)
    magick "$OUT/layers/skin.png" \( "$OUT/layers/enclosed.png" -morphology Erode "Disk:$((EXCLUDE_GROW+ENCLOSED_GAP))" -negate \) \
      -compose Lighten -composite "$OUT/layers/skin.png"
    echo "enclosed pockets excluded (max area $ENCLOSED_MAX_AREA px)"
  fi
  for spec in "${LAYERS[@]}"; do          # knock out traced layers, except those dots run under
    lname=${spec%%|*}
    [[ " $DOTS_UNDER " == *" $lname "* ]] && continue
    magick "$OUT/layers/skin.png" \( "$OUT/layers/$lname.raw.png" -resize 100x100% -resize "${CROP_W}x${CROP_H}!" \
      -morphology Erode Disk:1 -negate \) -compose Lighten -composite "$OUT/layers/skin.png"
  done
  DOT_ANGLE=$(awk -v a="$DOT_ANGLE_SRC" -v r="$ROT" 'BEGIN{printf "%.3f", a+r}')
  echo "dot grid: ${DOT_SPACING}px spacing at ${DOT_ANGLE}° in the crop (source ${DOT_ANGLE_SRC}° + rotation ${ROT}°)"
  : > "$OUT/dots.txt"
  DOTS_SVG=$(magick "$OUT/layers/skin.png" -compress none pbm:- | awk -v sp="$DOT_SPACING" -v r="$DOT_RADIUS" -v col="$DOT_COLOR" \
    -v ang="$DOT_ANGLE" -v stag="$DOT_STAGGER" -v rsp="$DOT_ROW_SPACING" \
    -v rot="$ROT" -v rcx="$CX" -v rcy="$CY" -v x0="$X0" -v y0="$Y0" -v manual="${MANUAL_DOTS:-/dev/null}" -v dump="$OUT/dots.txt" '
    function tosrc(x, y,   dx, dy) {   # crop px -> source px: undo crop offset, then undo the rotation about (rcx,rcy)
      dx = x + x0 - rcx; dy = y + y0 - rcy
      SX = rcx + dx*cr + dy*sr; SY = rcy - dx*sr + dy*cr }
    BEGIN{ pi=atan2(0,-1); tr=rot*pi/180; cr=cos(tr); sr=sin(tr); nm=0
      while ((getline line < manual) > 0) { split(line, f, " "); if (f[1]=="keep"||f[1]=="remove") { mk[nm]=f[1]; mx[nm]=f[2]+0; my[nm]=f[3]+0; nm++ } } }
    NR==1{next} NR==2{w=$1;h=$2;next} {for(i=1;i<=NF;i++){px[n++]=$i}}
    END{ printf "<g id=\"dots\" fill=\"%s\" stroke=\"none\">\n", col
      pi=atan2(0,-1); t=ang*pi/180; c=cos(t); s=sin(t); cx=w/2; cy=h/2
      R=int(sqrt(w*w+h*h)/((sp<rsp)?sp:rsp)/2)+2                      # grid radius (in cells) that covers the crop after rotation
      for(j=-R;j<=R;j++){ off=(stag && j%2)?sp/2:0
        for(i=-R;i<=R;i++){ u=i*sp+off; v=j*rsp
          x=cx+u*c-v*s; y=cy+u*s+v*c                    # rotate the grid about the crop centre
          if(x<=-r||y<=-r||x>=w+r||y>=h+r) continue        # keep dots whose circle touches the crop
          sx=int(x); sy=int(y); if(sx<0)sx=0; if(sy<0)sy=0; if(sx>w-1)sx=w-1; if(sy>h-1)sy=h-1
          draw = (px[sy*w+sx]==1)
          tosrc(x, y)
          for (m=0; m<nm; m++) { d=(SX-mx[m])^2+(SY-my[m])^2; if (d < (sp*0.55)^2) draw = (mk[m]=="keep") }
          if(draw) { printf "<circle cx=\"%.2f\" cy=\"%.2f\" r=\"%s\"/>\n",x,y,r; printf "%.1f %.1f %.1f %.1f\n", x, y, SX, SY > dump } } }
      print "</g>" }')
fi

# --- 4. Assemble --------------------------------------------------------------------------
{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo "<svg xmlns=\"http://www.w3.org/2000/svg\" version=\"1.1\" width=\"${CROP_W}pt\" height=\"${CROP_H}pt\" viewBox=\"0 0 $CROP_W $CROP_H\">"
  echo "<rect id=\"background\" width=\"$CROP_W\" height=\"$CROP_H\" fill=\"#ffffff\"/>"
  [[ -n "$DOTS_SVG" ]] && echo "$DOTS_SVG"
  printf '%s' "$GROUPS_SVG"
  echo '</svg>'
} > "$OUT/eyes.svg"

rsvg-convert -w $((CROP_W*3)) "$OUT/eyes.svg" -o "$OUT/eyes_preview.png"
magick "$OUT/crop_color.png" -resize 300% "$OUT/eyes_preview.png" -bordercolor gray -border 4 +append "$OUT/check.png"
echo "wrote $OUT/eyes.svg (layers: ${LAYERS[*]%%|*}${SKIN:+, dots}) and $OUT/check.png"

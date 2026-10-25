#!/bin/zsh
# Regenerate the SVGs, then export the stitch-ready SVG with Ink/Stitch's command-line mode.
# Usage: tools/make_stitch.sh [formats...]   (default: pes dst)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; PROJECT="$(dirname "$HERE")"
INK="$HOME/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/inkstitch/inkstitch.app/Contents/MacOS/inkstitch"
SVG="$PROJECT/chemtrail_patch_stitch.svg"
FORMATS=("$@"); [[ ${#FORMATS} -eq 0 ]] && FORMATS=(pes dst)
python3 "$HERE/generate_patch.py"
for f in $FORMATS; do
  # alarm: Ink/Stitch waits forever on a hidden dialog if the SVG lacks its version metadata
  perl -e 'alarm 120; exec @ARGV' "$INK" --extension=output --format=$f "$SVG" >| "$PROJECT/chemtrail_patch.$f"
  echo "wrote chemtrail_patch.$f"
  [[ $f == pes ]] && python3 "$HERE/repack_pes.py" "$PROJECT/chemtrail_patch.pes"
done

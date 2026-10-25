"""Re-encode PES files as PES version 6 in place (filehelper.com rejects the version 1 wrapper Ink/Stitch writes)."""
import sys, pyembroidery as pe
for f in sys.argv[1:]:
    p = pe.read(f)
    pe.write_pes(p, f, {"pes version": 6})
    print(f"{f}: PES v6, {len(p.stitches)} stitches, {len(p.threadlist)} colors")

"""Generate a UIData_<W>_<H>.dat from a base file, re-anchoring the words that follow a rule.

Usage: python uidata_gen.py <Data dir> <W> <H> <out path> [base W] [base H]

Rules are learned from the 40,016-byte files (see uidata_diff.py). Words with no rule keep the base file's value.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from uidata_diff import classify, load  # noqa: E402

INVERSE = {
    "right": lambda k, w, h: w - k,
    "bottom": lambda k, w, h: h - k,
    "hcenter": lambda k, w, h: w // 2 + k,
    "vcenter": lambda k, w, h: h // 2 + k,
}
FORWARD = {
    "right": lambda v, w, h: w - v,
    "bottom": lambda v, w, h: h - v,
    "hcenter": lambda v, w, h: v - w // 2,
    "vcenter": lambda v, w, h: v - h // 2,
}


# The left panel stacks two building previews at fixed positions: slot 1 at y 428-601, slot 2 at y 601-768, the
# same in the 768 and 900 layouts. Below 768 px slot 2 is cut off, so it goes below the screen instead. These are
# the offsets of the y words of slot 2's 15 rectangles (frame, picture, borders, icon row) in the 40,016-byte files.
SLOT2_Y = [0x2A00, 0x2A44, 0x2A98, 0x2B18, 0x2B6C, 0x2BD8, 0x2C34, 0x2C88, 0x2CDC,
           0x2D38, 0x2DA4, 0x2E10, 0x2E7C, 0x2EE8, 0x2F4C]
SLOT2_BOTTOM = 768
OFFSCREEN = 1000


def main():
    data_dir, W, H, out = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    base = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (1360, 768)
    files = load(data_dir, 40016)
    n = len(files[base]) // 4
    words = {s: struct.unpack(f"<{n}i", files[s]) for s in files}
    new = list(words[base])
    changed = 0
    for i in range(n):
        vals = {s: words[s][i] for s in files}
        if len(set(vals.values())) == 1:
            continue
        c = classify(vals)
        if not c:
            continue
        k = FORWARD[c[0]](words[base][i], *base)
        new[i] = INVERSE[c[0]](k, W, H)
        changed += 1
    if H < SLOT2_BOTTOM:
        for off in SLOT2_Y:
            new[off // 4] += OFFSCREEN
        print(f"height {H} < {SLOT2_BOTTOM}: second preview slot moved off-screen")
    out.write_bytes(struct.pack(f"<{n}i", *new))
    print(f"wrote {out} from {base}: {changed} words re-anchored")


if __name__ == "__main__":
    main()

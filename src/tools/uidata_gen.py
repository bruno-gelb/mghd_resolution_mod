"""Generate a UIData_<W>_<H>.dat from one of the game's own layouts.

Usage: python uidata_gen.py <Data dir> <W> <H> <out path> [base W base H]

Without a base, the base is the game's layout with the closest height at or below H (then the closest width), so the
new layout has everything the designers made for that height, plus room.

How each 32-bit word of the base is treated: the base is aligned word by word with every other layout (the files
share most of their structure; taller layouts add records), and each word that changes in a comparison is classified
by how much it moved against the difference in screen size:
  right    moved by dW        bottom   moved by dH
  hcenter  moved by dW / 2    vcenter  moved by dH / 2
within a small tolerance (the designers nudged things by a pixel here and there). A word is re-anchored when every
comparison where it changed agrees on one rule. Words that disagree, like the hand-made redesigns between heights,
keep the base's value.
"""

import difflib
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

RULES = ("right", "bottom", "hcenter", "vcenter")

# The layouts the game ships. Only these are learned from: generated ones in the same folder would teach the
# generator its own guesses.
ORIGINAL_SIZES = {
    (800, 600), (1024, 768), (1280, 768), (1280, 800), (1280, 960), (1280, 1024), (1360, 768),
    (1440, 900), (1600, 900), (1600, 1200), (1680, 1050), (1920, 1080), (1920, 1200),
}


def load_all(data_dir: Path) -> dict[tuple[int, int], list[int]]:
    """The game's original layouts in data_dir, as lists of 32-bit words."""
    files = {}
    for p in sorted(data_dir.glob("UIData_*.dat")):
        m = re.fullmatch(r"UIData_(\d+)_(\d+)\.dat", p.name)
        if not m or (int(m[1]), int(m[2])) not in ORIGINAL_SIZES:
            continue
        b = p.read_bytes()
        files[(int(m[1]), int(m[2]))] = list(struct.unpack(f"<{len(b) // 4}i", b[: len(b) // 4 * 4]))
    return files


def pick_base(files, W: int, H: int) -> tuple[int, int]:
    """The layout to build on: one with a family (another layout of the same file size, to learn its own rules from),
    the closest height at or below H, then the closest width. Taller only when nothing fits (the 768 family below 768,
    with its slot fix)."""
    sizes = [s for s in files if sum(len(v) == len(files[s]) for v in files.values()) > 1] or list(files)
    fitting = [s for s in sizes if s[1] <= H] or sizes
    return min(fitting, key=lambda s: (abs(H - s[1]), abs(W - s[0])))


def tolerance(delta: int) -> int:
    return max(2, round(abs(delta) * 0.035))


NOISE = 2  # moves this small are the designers' 1-pixel nudges, not anchoring


def classify_move(d: int, dw: int, dh: int) -> str | None:
    """The rule a move of d pixels matches; "?" when it can't tell (a nudge, or it fits several rules); None when it
    fits none, which means the word was placed by hand."""
    if abs(d) <= NOISE:
        return "?"
    expected = {"right": dw, "bottom": dh, "hcenter": dw / 2, "vcenter": dh / 2}
    hits = [r for r, e in expected.items() if e != 0 and abs(d - e) <= tolerance(e)]
    return hits[0] if len(hits) == 1 else "?" if hits else None


def learn_rules(files, base) -> dict[int, str]:
    """Word index in the base -> its anchor rule.

    Two tiers. The base's own family (same file size, so the same records) is asked first, by majority: each family
    was tuned on its own (a centered title sits at W/2 - 123 in one family and W/2 - 113 in another, which the other
    families would veto), and one odd sibling shouldn't veto the rest. The family also rules things out: a word that
    stays put between two members of different widths isn't anchored to the width, and the same for heights. Words the
    family can't tell about, like height rules in a family with only one height, go to a vote of every comparison,
    which must be unanimous.
    """
    family: dict[int, list] = defaultdict(list)
    everyone: dict[int, set] = defaultdict(set)
    fixed_w: set[int] = set()  # stays put across a width change within the family
    fixed_h: set[int] = set()
    bw, bh = base
    a = files[base]
    for other, b in files.items():
        if other == base:
            continue
        dw, dh = other[0] - bw, other[1] - bh
        same_family = len(b) == len(a)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op not in ("equal", "replace") or i2 - i1 != j2 - j1:
                continue
            for k in range(i2 - i1):
                d = b[j1 + k] - a[i1 + k]
                if abs(d) <= NOISE:
                    if same_family:
                        if dw:
                            fixed_w.add(i1 + k)
                        if dh:
                            fixed_h.add(i1 + k)
                    continue
                vote = classify_move(d, dw, dh)
                everyone[i1 + k].add(vote)
                if same_family:
                    family[i1 + k].append(vote)
    rules = {}
    for i in everyone:
        f = [v for v in family.get(i, []) if v != "?"]
        if f:
            best = max(set(f), key=f.count)
            if best is not None and f.count(best) > len(f) - f.count(best):
                rules[i] = best
            continue  # the family decided, or it's placed by hand within the family
        votes = everyone[i] - {"?"}
        if len(votes) == 1 and None not in votes:
            rules[i] = next(iter(votes))
    for i in list(rules):
        if (rules[i] in ("right", "hcenter") and i in fixed_w) or (rules[i] in ("bottom", "vcenter") and i in fixed_h):
            del rules[i]
    return rules


def apply_rule(rule: str, v: int, base, W: int, H: int) -> int:
    bw, bh = base
    return {
        "right": v + W - bw,
        "bottom": v + H - bh,
        "hcenter": v + (W - bw) // 2,
        "vcenter": v + (H - bh) // 2,
    }[rule]


# The 768-high layouts' left panel stacks two building previews at fixed positions: slot 1 at y 428-601, slot 2 at y
# 601-768. Below 768 px slot 2 is cut off, so it goes below the screen instead (the designers park unused elements at
# x=1000, y=1000 the same way). These are the offsets of the y words of slot 2's 15 rectangles (frame, picture,
# borders, icon row) in the 40,016-byte files.
SLOT2_FILE_SIZE = 40016
SLOT2_Y = [0x2A00, 0x2A44, 0x2A98, 0x2B18, 0x2B6C, 0x2BD8, 0x2C34, 0x2C88, 0x2CDC,
           0x2D38, 0x2DA4, 0x2E10, 0x2E7C, 0x2EE8, 0x2F4C]
SLOT2_BOTTOM = 768
OFFSCREEN = 1000

# Words the comparisons get wrong, kept at the base's value, by file size. In the 48,668-byte files (the 1200 family),
# the name label under the third building preview (x 7, y 1154, 190x14) lines up with bottom-anchored labels in the
# other families, so it would follow the bottom edge and float away from its preview on taller screens.
KEEP = {48668: [0x31B4]}


def generate(files, W: int, H: int, base=None) -> tuple[list[int], tuple[int, int], int]:
    base = base or pick_base(files, W, H)
    rules = learn_rules(files, base)
    for off in KEEP.get(len(files[base]) * 4, []):
        rules.pop(off // 4, None)
    new = list(files[base])
    for i, rule in rules.items():
        new[i] = apply_rule(rule, new[i], base, W, H)
    if len(new) * 4 == SLOT2_FILE_SIZE and H < SLOT2_BOTTOM:
        for off in SLOT2_Y:
            new[off // 4] += OFFSCREEN
    return new, base, len(rules)


def main():
    data_dir, W, H, out = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    base = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else None
    files = load_all(data_dir)
    new, base, n = generate(files, W, H, base)
    out.write_bytes(struct.pack(f"<{len(new)}i", *new))
    print(f"wrote {out} from {base[0]}x{base[1]}: {n} words re-anchored")


if __name__ == "__main__":
    main()

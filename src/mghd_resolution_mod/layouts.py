"""Generate the game's interface layouts, UIData_<W>_<H>.dat, for sizes it doesn't ship, from its own 13.

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
from collections import defaultdict
from functools import lru_cache

from mghd_resolution_mod import textdata

RULES = ("right", "bottom", "hcenter", "vcenter")

# The layouts the game ships. Only these are learned from: generated ones in the same folder would teach the
# generator its own guesses.
ORIGINAL_SIZES = {
    (800, 600), (1024, 768), (1280, 768), (1280, 800), (1280, 960), (1280, 1024), (1360, 768),
    (1440, 900), (1600, 900), (1600, 1200), (1680, 1050), (1920, 1080), (1920, 1200),
}


Size = tuple[int, int]
Words = tuple[int, ...]


def file_name(size: Size) -> str:
    return f"UIData_{size[0]}_{size[1]}.dat"


def parse_name(name: str) -> Size | None:
    m = re.fullmatch(r"UIData_(\d+)_(\d+)\.dat", name, re.IGNORECASE)
    return (int(m[1]), int(m[2])) if m else None


def to_words(data: bytes) -> Words:
    return struct.unpack(f"<{len(data) // 4}i", data[: len(data) // 4 * 4])


def to_bytes(words: Words) -> bytes:
    return struct.pack(f"<{len(words)}i", *words)


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


def learn_rules(files: dict[Size, Words], base: Size) -> dict[int, str]:
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


# The fixes below are in the in-game interface's chunk, SMNU/APMK, which is the same in Steam's 1.5.2.24 and GOG's
# 1.5.2.28 (GOG's layouts add other chunks before it, so the files' sizes and the chunk's offset differ). Its size tells
# the layout's family apart, and the fixes' offsets are from its start.
HUD_CHUNK = (b"SMNU", b"APMK")

# The 768-high layouts' left panel stacks two building previews at fixed positions: slot 1 at y 428-601, slot 2 at y
# 601-768. Below 768 px slot 2 is cut off, so it goes below the screen instead (the designers park unused elements at
# x=1000, y=1000 the same way). These are the offsets of the y words of slot 2's 15 rectangles (frame, picture,
# borders, icon row) in the 6,864-byte chunk of the 768 family (Steam's 40,016-byte files).
SLOT2_HUD_SIZE = 6864
SLOT2_Y = [0x1528, 0x156C, 0x15C0, 0x1640, 0x1694, 0x1700, 0x175C, 0x17B0, 0x1804,
           0x1860, 0x18CC, 0x1938, 0x19A4, 0x1A10, 0x1A74]
SLOT2_BOTTOM = 768
OFFSCREEN = 1000

# Words the comparisons get wrong, kept at the base's value, by the chunk's size. In the 8,480-byte chunk of the 1200
# family (Steam's 48,668-byte files), the name label under the third building preview (x 7, y 1154, 190x14) lines up
# with bottom-anchored labels in the other families, so it would follow the bottom edge and float away from its
# preview on taller screens.
KEEP = {8480: [0x1C6C]}


class Generator:
    """Builds layouts from the game's originals: {size: file contents}. The rules depend only on the base, so they're
    learned once per base (about 10 seconds each)."""

    def __init__(self, originals: dict[Size, bytes]):
        originals = {size: data for size, data in originals.items() if size in ORIGINAL_SIZES}
        self.files = {size: to_words(data) for size, data in originals.items()}
        # The bytes after the last whole word: GOG's layouts aren't a multiple of 4 bytes long.
        self.tails = {size: data[len(data) // 4 * 4 :] for size, data in originals.items()}
        self.huds = {size: textdata.find_chunk(data, *HUD_CHUNK) for size, data in originals.items()}
        self._rules = lru_cache(maxsize=None)(self._learn)

    def _learn(self, base: Size) -> dict[int, str]:
        rules = learn_rules(self.files, base)
        hud = self.huds[base]
        for off in KEEP.get(hud[1], []) if hud else []:
            rules.pop((hud[0] + off) // 4, None)
        return rules

    def base_for(self, size: Size) -> Size:
        return pick_base(self.files, *size)

    def generate(self, size: Size, base: Size | None = None) -> bytes:
        base = base or self.base_for(size)
        new = generate(self.files, *size, base, self._rules(base), self.huds[base])
        return to_bytes(new) + self.tails[base]


def generate(files: dict[Size, Words], W: int, H: int, base: Size, rules: dict[int, str],
             hud: tuple[int, int] | None = None) -> list[int]:
    new = list(files[base])
    for i, rule in rules.items():
        new[i] = apply_rule(rule, new[i], base, W, H)
    if hud and hud[1] == SLOT2_HUD_SIZE and H < SLOT2_BOTTOM:
        for off in SLOT2_Y:
            new[(hud[0] + off) // 4] += OFFSCREEN
    return new


# Screen sizes the installer makes layouts for, besides the player's own screen: common display modes the game doesn't
# ship a layout for. The game's settings menu lists the display modes the system reports and shows the ones with a
# layout in green, so the player picks one there. 1720x720 and other sizes that aren't display modes need a scaler
# (gamescope on Linux) and can be added with --size.
COMMON_SIZES: list[Size] = [
    (1280, 720), (1366, 768), (1536, 864),                   # 16:9 laptops
    (2560, 1440), (3200, 1800), (3840, 2160),                # 16:9
    (2560, 1600), (2880, 1800), (3840, 2400),                # 16:10
    (2560, 1080), (3440, 1440), (3840, 1600), (5120, 2160),  # 21:9 ultrawide
    (3840, 1080), (5120, 1440),                              # 32:9 super ultrawide
]
MIN_SIZE: Size = (800, 600)  # the game ignores smaller layouts


def sizes_to_make(screens: list[Size], extra: list[Size]) -> list[Size]:
    """Sizes to generate: the common ones, the screens' and any asked for, minus the ones the game ships."""
    wanted = [*COMMON_SIZES, *screens, *extra]
    result = []
    for size in wanted:
        if size not in ORIGINAL_SIZES and size not in result and size[0] >= MIN_SIZE[0] and size[1] >= MIN_SIZE[1]:
            result.append(size)
    return sorted(result)

"""Classify every differing 32-bit word across same-sized UIData files.

Usage: python uidata_diff.py <Data dir> [size_in_bytes]

For each word offset whose value differs between the files, try to explain it as one anchor rule:
  const        v = k
  right        v = W - k          bottom   v = H - k
  hcenter      v = W/2 + k        vcenter  v = H/2 + k
  (each allowed to be off by up to SLOP pixels in a single file: the hand-tuned nudges)
Whatever doesn't fit is printed as "???" with its raw values.
"""
import re
import struct
import sys
from collections import Counter
from pathlib import Path

SLOP = 1


def load(data_dir: Path, size: int | None):
    files = {}
    for p in sorted(data_dir.glob("UIData_*.dat")):
        m = re.fullmatch(r"UIData_(\d+)_(\d+)\.dat", p.name)
        b = p.read_bytes()
        if size is None or len(b) == size:
            files[(int(m[1]), int(m[2]))] = b
    return files


RULES = {
    "right": lambda v, w, h: w - v,
    "bottom": lambda v, w, h: h - v,
    "hcenter": lambda v, w, h: v - w // 2,
    "vcenter": lambda v, w, h: v - h // 2,
}


def classify(vals: dict[tuple[int, int], int]):
    best = None
    for name, f in RULES.items():
        ks = [f(v, w, h) for (w, h), v in vals.items()]
        k, _ = Counter(ks).most_common(1)[0]
        err = max(abs(x - k) for x in ks)
        if err <= SLOP and (best is None or err < best[2]):
            best = (name, k, err)
    return best


def main():
    data_dir = Path(sys.argv[1])
    size = int(sys.argv[2]) if len(sys.argv) > 2 else None
    files = load(data_dir, size)
    sizes = list(files)
    n = min(len(b) for b in files.values()) // 4
    words = {s: struct.unpack(f"<{n}i", files[s][: n * 4]) for s in sizes}
    stats = Counter()
    print("files:", sizes)
    for i in range(n):
        vals = {s: words[s][i] for s in sizes}
        if len(set(vals.values())) == 1:
            continue
        c = classify(vals)
        tag = f"{c[0]:8s} k={c[1]:6d} err={c[2]}" if c else "???"
        stats[c[0] if c else "???"] += 1
        print(f"{i * 4:#07x}  {tag:28s}  " + " ".join(f"{vals[s]:6d}" for s in sizes))
    print(stats)


if __name__ == "__main__":
    main()

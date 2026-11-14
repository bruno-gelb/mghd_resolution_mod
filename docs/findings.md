# Findings

Static analysis of [Majesty Gold HD][steam] (Steam, app 73230, `MajestyHD.exe`), 2026-11-13 and 2026-11-14. Not
tested in the running game yet.

## The game's files

- `Data/` has 13 interface layouts, one file each: `UIData_<w>_<h>.dat` for 800x600, 1024x768, 1280x768, 1280x800,
  1280x960, 1280x1024, 1360x768, 1440x900, 1600x900, 1600x1200, 1680x1050, 1920x1080 and 1920x1200. `DataMX/` (the
  expansion) has none: both campaigns use the same layouts.
- The settings are in `MajXPrefs`, an XML file in `Documents/My Games/MajestyHD/` (on Linux, inside the Proton
  prefix): `PixWidth`, `PixHeight`, `UseD3D`, `Windowed` and others.
- The exe also has a `-keepintroresolution` command-line switch (not checked yet).

## How the exe picks a layout

- A function around `0x4f2000` searches for `UIData_*.dat` and parses each name: digits, `_`, digits, `.`. It
  accepts **any** file with a width of at least 800 and a height of at least 600, and appends it to a list (`0x4f1f30`
  is a plain `vector<pair<int,int>>::push_back`). There's no built-in table of the 13 sizes on this path.
- `UIData_%d_%d.dat` is formatted at `0x4f0c1e` for the current screen size. If that file doesn't exist, `0x4f0870`
  picks a fallback: among the layouts with `w <= W` and `h <= H`, the one with the smallest `(W - w) + (H - h)`.
  That's why a 3440x1440 screen gets the 1920x1200 layout, centered in a black frame.
- So a new `UIData_<w>_<h>.dat` should be listed and loaded as is. Not checked yet: where the settings menu decides
  which resolutions to show in red.

## The UIData format

- Cyberlore's chunk format: a `CYLBPC  ` header, then chunks (`SMNU`, `STRT`, and records tagged `INDk`, `INDp`,
  `INDq`, `INDa`, `INDs`, `INTI`, `INx1`, `fnt4`, `fnt7`, `AP..`). All numbers are little-endian 32-bit integers.
- Files of the same size have the same structure with different numbers. Four files are 40,016 bytes: 1280x768,
  1360x768, 1440x900 and 1600x900. Between them, 101 words differ, all plain pixel coordinates and sizes:
  - the resolution itself, at offset `0x14e8`;
  - 13 right-anchored X values (`W - k`) and 25 bottom-anchored Y values (`H - k`), within ±1 px;
  - 2 vertically centered values (`H/2 + k`);
  - 61 values that depend only on the height: both 768-high files share one set and both 900-high files another
    (X positions like 1119 → 1237, sizes like 119 → 126, 1-pixel nudges). The designers seem to have made one layout
    per height, then moved the right and bottom anchors for each width.
- `src/tools/uidata_diff.py` lists and classifies the differing words. `src/tools/uidata_gen.py` builds a new file from
  a base: it re-anchors the words that follow a rule and keeps the rest. Check: building 1600x900 from 1440x900 misses
  the real file by only 3 bytes, the ±1 px nudges.

## First test file

`UIData_1720_720.dat`, built from 1360x768 (the closest height group). The risk: 720 px is 48 px shorter than any
768-high design, so the bottom panels may overlap things placed from the top.

[steam]: https://store.steampowered.com/app/73230/

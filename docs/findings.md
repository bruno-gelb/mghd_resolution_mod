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

## Layout families

The 13 files come in families: files of the same size share the same records, with different numbers.

| File size | Layouts | Left panel |
|---|---|---|
| 11,147 | 800x600 | |
| 24,145 | 1024x768 | |
| 40,008 | 1280x800 | |
| 40,016 | 1280x768, 1360x768, 1440x900, 1600x900 | two building previews from y 428 |
| 40,100 | 1920x1080 | an extra box at y 428, two previews from y 676 |
| 41,456 | 1280x960 | |
| 47,136 | 1280x1024, 1680x1050 | an extra box at y 428, two previews from y 676 |
| 48,668 | 1600x1200, 1920x1200 | an extra box at y 428, three previews from y 674 |

The families share most of their structure too, so the files can be aligned word by word with `difflib`: 1600x900
against 1600x1200 matches 9,877 words exactly. The taller files add records: the header's table of contents grows
by 28 words, and the 1200 family inserts 2,114 words (the third preview and some sub-panels in their own local
coordinates). In the aligned part, 25 values move by exactly the height difference (bottom anchors), 2 by half of it,
and the preview slots by about 247 px, a redesign. The designers park unused elements at x=1000, y=1000.

The top-bar title banner (395 px wide, at `0x15d4` in the 40,016-byte files) is centered over the map area: at
`W/2 - 113` in that family, `W/2 - 116` in the 1200 family, and `W/2 - 123` in 1280x768, an odd one. Each family was
tuned on its own.

### The generator

`src/tools/uidata_gen.py` builds a layout for any size:

- **The base** is a layout with a family (so there's something to learn its rules from), with the closest height at or
  below the target, then the closest width: the 1200 family for 1440 and 2160, the 1050 family for 1080, the 900
  family for 960. Below 768 it takes the 768 family and parks the second preview slot off the screen.
- **The rules**: the base is aligned with each of the other 12 originals, and each value that moves is matched against
  the size difference: right (`dW`), bottom (`dH`), horizontal or vertical center (half). The base's own family decides
  first, by majority. A value that stays put between family members of different widths isn't width-anchored, and the
  same for height. Otherwise all comparisons must agree. Values that fit no rule were placed by hand, and keep the
  base's value.
- **Checked** by rebuilding each original from a sibling with the original hidden: the 768, 900 and 1200 families come
  out within 3 px, except where hiding a file leaves a family too small to vote.
- **Generated layouts aren't learned from**: only the 13 original sizes are read.

Generated on 2026-11-14: 3440x1440, 2560x1440 and 3840x2160 from 1920x1200, 2560x1080 from 1680x1050, 2294x960 from
1600x900, 1720x720 from 1360x768. None of them pushes off the screen anything the base kept on it, except 1720x720,
which is shorter than its base: besides the parked slot, a bar under the left panel, a small button at (202, 729) and
four boxes around y 600 in the middle of the screen, probably parts of dialogs, don't fit. Not tested in the game yet,
except 1720x720 (an earlier version of it, below).

## First test file

`UIData_1720_720.dat`, built from 1360x768 (the closest height group). The risk: 720 px is 48 px shorter than any
768-high design, so the bottom panels may overlap things placed from the top.

Tested 2026-11-14 on Linux (Proton), Direct3D 9, windowed, with `PixWidth`/`PixHeight` set to 1720x720 in
`MajXPrefs`:

- **The game loads it.** It runs at 1720x720, and in a game the top bar, the bottom bar (orders, Spells, Options)
  and the map view stretch to the full width. The left panel stays at the left.
- **The left panel is too tall for 720 px.** It stacks two building previews (a picture and a row of 7 icon
  buttons each) at fixed positions: slot 1 at y 428-601, slot 2 at y 601-768. The 768 and 900 layouts both show two,
  with empty panel under them at 900, so the count comes from the file, not from the screen height. At 720 slot 2 is
  cut off. Its 15 rectangles sit together in the file (`0x2a00`-`0x2f4c` in the 40,016-byte files), and
  `uidata_gen.py` moves them 1000 px down, off the screen, when the height is under 768. Tested: one preview, the
  panel background under it, nothing cut off, no errors.
- **The main menu** is the game's fixed-size picture in the middle, on the tiled portrait background. That's how the
  game draws it at every size.
- **The settings menu lists display modes, not layouts.** The list shows the modes the system reports (1920x800,
  2560x1080, 3440x1440...), in green when a `UIData` file exists for that size and in red when not. 1720x720 isn't
  listed, since it's not a display mode, but setting it in `MajXPrefs` works. So a `UIData_3440_1440.dat` should turn
  3440x1440 green, and a smaller size than the screen needs something to provide the display mode and scale it up
  (cnc-ddraw, Proton's fullscreen scaling, gamescope).

[steam]: https://store.steampowered.com/app/73230/

## Loading screens (issue #1)

Static analysis, 2026-11-14. Nothing patched or tested yet.

- **The art** is a picture set named `pre_load`, ID `INDo`, in `Data/interfacedata.cam`, with its progress bar
  `pre_load_bar`, ID `INDl`. The archive's directory gives each set an offset and a size.
- **The screen layouts** that use it are in `Data/textdata.cam`, in the same record format as the `UIData` files: three
  of them reference `INDo` (at `0x12190`, `0x1bde4` and `0x3fa90`; the last sits next to `DX00`, the downloadable
  quests' set, so probably one for the base game, one for the expansion and one for downloadable quests).
- **The exe never names them**: neither `INDo`, `INDl` nor `pre_load` appears in it in any byte order. The interface is
  data-driven: the exe works with generic screen and dialog objects, built from these records.
- **C++ class names (RTTI) are in the exe**, which helps: every screen has a controller class with a findable vtable
  (`src/tools`-style lookup: type descriptor, then CompleteObjectLocator, then vtable). The menus include
  `LoadQuestMenu`, `LoadGameController`, `CoverController` (a variant of `DialogController`, probably the dimmed
  background behind dialogs, not the loading screen) and `MainFrameController`. There's no class with "load screen" or
  "progress" in its name.
- **The SDK** (`SDK/`, quest-making guide and GPL scripting reference) doesn't mention the loading screen; it isn't
  scriptable.
- `0x548d30` loads the game's data at startup (it calls the GPL loader, `0x574a80`, which reports "There were errors
  loading GPL"). It's called from `0x4f14fb`, near the resolution code. Not the per-quest loading.

Next step: find the code while it runs. Start a quest with a debugger or a profiler attached (`perf record` on the
game's process, as in the Tzar mod, or `winedbg`), and catch the function that draws the progress bar and the place
where the loader returns to the game. A wait for a key or a click (or a minimum display time) goes at that point. The
fallback, a viewer for the `pre_load` pictures from the player's own copy, needs the image format of the `.cam`
archives (`CYLBPC` chunks: `PALT`, `IMAG`, `TILE`, `FONT`).

# Findings

Static analysis of [Majesty Gold HD][steam] (Steam, app 73230, `MajestyHD.exe`), 2026-11-13 and 2026-11-14, then
tested in the running game (below).

## The game's files

- `Data/` has 13 interface layouts, one file each: `UIData_<w>_<h>.dat` for 800x600, 1024x768, 1280x768, 1280x800,
  1280x960, 1280x1024, 1360x768, 1440x900, 1600x900, 1600x1200, 1680x1050, 1920x1080 and 1920x1200. `DataMX/` (the
  expansion) has none: both campaigns use the same layouts.
- The settings are in `MajXPrefs`, an XML file in `Documents/My Games/MajestyHD/` (on Linux, inside the Wine
  prefix: Steam's Proton one, or Heroic's): `PixWidth`, `PixHeight`, `UseD3D`, `Windowed` and others.
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
- `src/tools/uidata_diff.py` lists and classifies the differing words. `src/mghd_resolution_mod/layouts.py` builds a
  new file from a base: it re-anchors the words that follow a rule and keeps the rest. Check: building 1600x900 from
  1440x900 misses the real file by only 3 bytes, the ±1 px nudges.

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

`src/mghd_resolution_mod/layouts.py` (formerly `src/tools/uidata_gen.py`) builds a layout for any size:

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
four boxes around y 600 in the middle of the screen, probably parts of dialogs, don't fit. Tested since: 3440x1440 and
2560x1080 (below), and 1720x720 (an earlier version of it, below).

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
  `layouts.py` moves them 1000 px down, off the screen, when the height is under 768. Tested: one preview, the
  panel background under it, nothing cut off, no errors.
- **The main menu** is the game's fixed-size picture in the middle, on the tiled portrait background. That's how the
  game draws it at every size.
- **The settings menu lists display modes, not layouts.** The list shows the modes the system reports (1920x800,
  2560x1080, 3440x1440...), in green when a `UIData` file exists for that size and in red when not. 1720x720 isn't
  listed, since it's not a display mode, but setting it in `MajXPrefs` works. So a `UIData_3440_1440.dat` should turn
  3440x1440 green, and a smaller size than the screen needs something to provide the display mode and scale it up
  (cnc-ddraw, Proton's fullscreen scaling, gamescope).

## Native and scaled-up tests

Tested 2026-11-14 on Linux (Proton), Direct3D 9, full screen, on a 3440x1440 screen:

- **Native 3440x1440** (from 1920x1200): green in the settings menu (so is 2560x1440), the interface fills the screen,
  the left panel shows three previews, the title is centered, the Statistics dialog fits. The whole starting area is
  in view. One bug, fixed: the name label under the third preview (`0x31b4` in the 48,668-byte files) lines up with
  bottom-anchored labels in the other families, so it moved down with the bottom edge. `layouts.py` now keeps it.
  But the text is too small to read comfortably: the game has no interface scaling, so the interface and the map
  always grow together.
- **2560x1080** (from 1680x1050), scaled up 1.33x: the fonts are big enough, the edges and the left panel (two
  previews) are fine, and it shows about twice the map of the original 1920x1200 frame. Scaled by Proton (linear),
  the fonts are blurry: 1-pixel strokes smeared over two pixels. Through gamescope with FSR (`-F fsr -S fit
  --sharpness 2`), they're sharp. Uncapped, about 120 fps on average, 100 at the lowest while scrolling, on a quiet
  map. On Windows the counterpart would be the graphics driver's sharpening scaler (NVIDIA Image Scaling, AMD RSR),
  not tested.
- **The DirectDraw renderer** (`UseD3D=0`) is a dead end under Proton: with cnc-ddraw the ground is black, with
  Wine's own ddraw the whole window is.

[steam]: https://store.steampowered.com/app/73230/

## Loading screens (issue #1)

Static analysis, 2026-11-14 and 2026-11-15. Nothing patched or tested yet.

- **The art** is a picture set named `pre_load`, ID `INDo`, in `Data/interfacedata.cam`, with its progress bar
  `pre_load_bar`, ID `INDl`. The archive's directory gives each set an offset and a size.
- **The screen layouts** that use it are in `Data/textdata.cam`, in the same record format as the `UIData` files: three
  of them reference `INDo` (at `0x12190`, `0x1bde4` and `0x3fa90`). They turned out to be menus, not the loading
  screen: see below.
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

### Found 2026-11-15, still static analysis

The way in was the screens' chunk tags: the exe asks for each screen by its `SMNU` chunk's tag, as a 32-bit constant in
the code (`push 0x30355041` is `AP50`; the main menu's `AP29` appears 34 times). Addresses are Steam's 1.5.2.24; GOG's
1.5.2.28 has the same code elsewhere (below).

- **The three screens with `INDo` aren't loading screens**: their string tables make them the Load Game menu (`AP27`),
  the Save Game menu (`AP49`) and the downloaded quests' Load Quest menu (`APd8`), which use the art as a background.
- **The loading screen is `AP50`**, "seugue cover" (sic) in its strings: the quest's name and icon over the art, its
  progress bar (`INDl`), and a `Return (invisible button)`. Built at four places (`push 'AP50'` before the screen
  constructor `0x4b5070`); the screen object is kept in `0x7c1708`.
- **Its helpers**: `0x494400` opens it (builds `AP50`, fills in the quest's name and icons from the quest at
  `0x7b6ef8`, draws it); `0x494570` sets the progress bar (element `0xf`); `0x4943e0` would close it but is never
  called: the callers delete it themselves.
- **The loader is `0x4e96d0`**, which sets the progress bar 8 times as it goes. Every way into a quest calls it, then
  `0x424cc0`, which looks like the whole game session (the callers delete the loading screen after it returns, and
  go back to the main menu): `0x4945f0`, `0x46ed60`, `0x48b9f0` (the expansion's, screen `MX17`) and `0x4f5b40`. They
  are screens of the game's screen loop, `0x494750`, which runs a screen's function by its tag and takes the tag of
  the next screen from it.
- **So the wait goes at the end of the loader**, once: after its last progress update (`call 0x494570` at `0x4e9bef`,
  the bar full), where it clears bit `0x40` of `0x7b73a0` (7 bytes, `83 25 a0 73 7b 00 bf`). That instruction can
  become a call to a small loop that waits for a key or a click, then clears the bit itself.
- **What the loop needs is there**: the exe imports `PeekMessageA`, `TranslateMessage`, `DispatchMessageA`,
  `GetAsyncKeyState`, `Sleep` and `GetTickCount`, and `.text` has 387 bytes free at its end (raw size `0x334000`,
  virtual size `0x333e7d`: the virtual size has to grow to cover the loop).
- **GOG's exe** has the same design: `AP50` built at four places, its screen in `0x7e0490`, the progress function
  `0x4952d0` called 8 times by the loader `0x4ea3d0`, which has the same four callers. A patch should find its spot by
  that pattern, not by address.

Still open, and only answered by running it:

- **Multiplayer**: the other players mustn't wait for one player's key, so the wait has to be skipped in a
  multiplayer game. The flag that tells isn't found yet.
- **What's on screen while waiting**: the last frame the loader drew should stay up, but the window's messages go to
  the game's own window procedure, which may try to draw the game before it starts. Input messages shouldn't reach it
  at all, or the key or click that ends the wait would also act in the game.
- **A setting**: a keypress, a minimum time, or off.

The fallback, a viewer for the `pre_load` pictures from the player's own copy, needs the image format of the `.cam`
archives (`CYLBPC` chunks: `PALT`, `IMAG`, `TILE`, `FONT`).

## The version on the main menu (issue #3)

Tested 2026-11-14: the main menu shows `mghd-resolution-mod 0.0.1. game Version 1.5.2.24`. The code is
`src/mghd_resolution_mod/textdata.py`.

- **The text archives** (`Data/textdata.cam`, `DataMX/mx_textdata.cam`) are `CYLBPC` files: a header with one entry per
  section (`SMNU`, screen layouts; `STRT`, string tables) and the offset of its table; each table lists its chunks (a
  tag, 16 zero bytes, offset, size, 28 bytes per chunk); the chunks follow back to back. A string table chunk is a
  16-bit count, a 16-bit number, one 32-bit offset per string, then the strings: a 32-bit ID, the text, a NUL. No
  checksums: a longer string only moves the later strings in its chunk and every later chunk.
- **The line** is `Version %s`, ID 0x56 in the general string table `GMTX`, formatted with the exe's version at
  `0x478824` (its only use) and shown in place of `Version #`, ID 10 in the main menu's own table `AP29`, which is only
  a placeholder. Labelling `Version #` changes nothing on screen. Both archives have the line, so both get the label.
- **The box** is 183 px wide at x 162, made for the game's line: longer text wraps at the spaces, and the lines below
  aren't drawn, so at first only `mghd-resolution-mod` showed. It's a rectangle record (-1, 0, 2, 162, 498, 183, 21)
  in the main menu's layout, which is in every `UIData` file except 800x600 and in both text archives. Widened
  differently in both, the game used the layout's. The mod makes it 469 px wide, around the same center, everywhere.
- **The font has no `_`**: it draws the repo name's underscores as hyphens, so the label says `mghd-resolution-mod`.
- Removing the label and narrowing the box gives back the original files byte for byte. Still to do, in the installer:
  the 13 original layouts (only the generated ones and the text archives are done so far), backups, and uninstall.

## The GOG version (issue #4)

Compared 2026-11-15: GOG's copy (Heroic, product `1423481910`, build `1.5.2.28`) against Steam's (`1.5.2.24`).

- **Not the same build.** GOG's `MajestyHD.exe` is 4,058,112 bytes (Steam's 3,933,696), with `Galaxy.dll` next to it
  instead of `steam_api.dll`. Of the 558 files both have, 527 are byte-identical. The other 31: the exe, the 13
  layouts, `Data/InterfaceStrings.xml`, `Data/addinterface_se.cam`, and the scripts (`.bcd`, and the SDK's `.gpl`
  sources, small gameplay changes).
- **The text archives are identical**: `Data/textdata.cam` and `DataMX/mx_textdata.cam`, so the main menu label works
  unchanged. GOG also has a `Data/mx_textdata.cam`, a byte-identical copy of `DataMX/mx_textdata.cam`, which the mod
  doesn't touch.
- **The layouts** have the same chunks as Steam's, byte for byte, except in the main menu section: two new screens
  (`SMNU`/`AP42` and `AP55`, with string tables of the same names; one mentions Galaxy) and a bigger `APda`. Those
  three are the same at every size, so the generator leaves them as they are, which is right. The files are 4,127
  bytes longer (2,073 for 800x600), and no longer a multiple of 4.
- **What the generator needed**: it works on 32-bit words, and dropped the last 1-3 bytes of a file that isn't a
  multiple of 4, which on GOG cut the end off the last string (`...Galaxy`). It now keeps them. Its two hand-made
  fixes (the 768 family's second building slot, and the 1200 family's preview label) were keyed by Steam's file sizes
  and offsets; they're now keyed by the in-game interface's chunk, `SMNU`/`APMK`, which is identical in both builds,
  and offsets from its start.
- **Checked**: for all 15 common sizes, the generator makes Steam's layouts byte for byte as before, and GOG's layouts
  have exactly Steam's chunks plus GOG's own three as the game ships them. On the real GOG copy, install, then
  uninstall, gave back all 564 files byte for byte.

## The launch on Linux

Built 2026-11-15, after running the game for a few days through a local launch script. The code is
`src/mghd_resolution_mod/launch.py` (the launcher), `display.py`, `steam.py`, `heroic.py` and `launch_setup.py`.

- **GNOME's fractional scaling** with `xwayland-native-scaling` makes Xwayland report the screen scaled up: 3440x1440
  at 133% is 5160x2160 to X11 programs, with made-up modes under it. The game, under Wine on X11, lists those in
  **ADJUST SETTINGS**. At 100% it gets the real ones. The kernel's own list (`/sys/class/drm/*/modes`) isn't affected,
  so the installer reads screen sizes there.
- **The scale** is GNOME's `org.gnome.Mutter.DisplayConfig` on the session bus: `GetCurrentState`, then
  `ApplyMonitorsConfig` with the same logical monitor and another scale. The release program has no D-Bus library,
  so it goes through systemd's `busctl`, whose `--json=short` output reads well and whose arguments take the
  `uua(iiduba(ssa{sv}))a{sv}` structure flattened. 100% is applied as temporary (method 1), so a crash or logging
  out falls back to the saved scale; the old scale goes back as persistent (method 2), the same as saved.
- **gamescope**, tested on a 3440x1440 screen: `--backend sdl -r 60 -S fit -F fsr --sharpness 2 -f
  --force-grab-cursor`, drawing at 2560x1080. Proton's own scaling smears the fonts; FSR keeps them sharp. Inside
  gamescope the game sees one screen of the drawn size, so the launcher sets `PixWidth`/`PixHeight` in `MajXPrefs`
  to it (and `Windowed` 0, `UseD3D` 1).
- **Where the prefix is**: Steam and Heroic both set `STEAM_COMPAT_DATA_PATH` for Proton. Steam's has the Wine
  prefix in `pfx/`; Heroic's `pfx` is a link to the folder itself, so `<it>/pfx/drive_c/...` works for both.
- **Steam's launch options** are in each account's `userdata/<account>/config/localconfig.vdf`, at
  `UserLocalConfigStore/Software/Valve/Steam/apps/73230/LaunchOptions`: Valve's text KeyValues, tabs, `\"`
  escaped. Steam keeps the file in memory and writes it back when it quits, so it's changed only while Steam is
  closed. The mod changes that one value in place and leaves the rest of the file byte for byte.
- **Heroic's wrapper command** is `wrapperOptions` in `GamesConfig/<game id>.json`, a list of `{exe, args}` it
  starts the game through. Heroic also keeps it in memory.
- **Tried 2026-11-15** from the release program on Steam (Proton Experimental) and Heroic (umu, Proton-CachyOS):
  100% while playing, 2560x1080 scaled up to 3440x1440, sharp, and 133% back after. In both, the launcher saw the game
  exit with -6: gamescope's nested SDL backend aborts on its way out, after the game has quit. Harmless: Steam and
  Heroic track the game itself.

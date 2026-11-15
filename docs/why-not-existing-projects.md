# Why not existing projects

Other ways players make [Majesty Gold HD][steam] fit screens wider or bigger than 1920x1200, compared with this mod.
They come from the Steam discussions, the GOG forum, [PCGamingWiki][pcgw], [ModDB][moddb] and the DxWnd forum.
Checked 2026-11-15 ([#10](https://github.com/bruno-gelb/mghd_resolution_mod/issues/10)).

No other project adds screen layouts: every fix below either keeps the game's own 13, up to 1920x1200, or scales the
picture. The Steam Workshop, Nexus Mods and GitHub have no resolution mod for the game, and searches found no Reddit
thread about one. The Workshop's mods, like Majesty Expanded, change the gameplay, not the screen.

For comparison, this mod ([how it works](how-it-works.md)):

- generates new layouts from the player's own copy, so the interface fills the screen and shows more of the map: 16:9
  and 16:10 up to 4K, 21:9 and 32:9 ultrawides, laptop sizes and the player's own screens;
- on Linux, draws the game at about 1080 lines in the screen's shape and scales it up with gamescope's FSR, so the
  text stays readable on a big screen;
- installs and uninstalls with one program, and keeps the originals;
- is made for the Steam and GOG versions, on Windows and on Linux (Proton, Heroic), though it hasn't been tried on
  Windows yet ([#6](https://github.com/bruno-gelb/mghd_resolution_mod/issues/6)), and doesn't scale the picture there
  yet ([#12](https://github.com/bruno-gelb/mghd_resolution_mod/issues/12));
- is MIT-licensed and ships none of the game's files.

Every fix here is someone's work to keep Majesty playable, and many players are happy with them. This page is to help
you pick the one that suits you, not to judge anyone's work. Sorted from the most common to the least; pros and cons
are compared with this mod.

| Solution | How it works | Pros | Cons |
| --- | --- | --- | --- |
| The screen's own resolution, in the game's settings or as `PixWidth` and `PixHeight` in `MajXPrefs` ([Steam][s-4k], [Steam][s-new]) | The game lists any resolution the screen has, and picks the biggest of its 13 layouts that fits. | Nothing to install. The game's own layouts, exactly as designed. | Above 1920x1200, the interface sits in a 1920x1080 or 1920x1200 box in the middle, in a frame: "no advantage" over a smaller monitor, players say. PCGamingWiki: "Interface elements not scaled properly" on ultrawide and 4K. |
| A low resolution, stretched by the monitor or the graphics card ([Steam][s-uw]) | Fullscreen at 800x600 or another size the game has a layout for, and the monitor or the graphics card fills the screen with it. | Fills the screen. Big, readable text. Nothing to install. | A 4:3 or 16:9 picture stretched to 21:9 looks wide and flat, or gets black bars when the scaling keeps the shape. Shows less of the map than the screen could. One player got "Failed to start up DirectX 9" changing the resolution. This mod draws a size of the screen's own shape and scales that (on Linux so far). |
| Windowed mode (`Windowed` set to 1 in `MajXPrefs`, or `-w`), with [SRWE][srwe] for a borderless window ([Steam][s-res], [PCGamingWiki][pcgw]) | The game runs in a window of any listed size. SRWE, a small open-source tool (MIT), removes the window's borders and stretches it over the screen. | The fix players give for a menu that doesn't fit the screen, or freezes. SRWE's borderless window runs at the desktop's refresh rate: in fullscreen, VSync holds the game at 60 FPS (PCGamingWiki). Alt+Tab works better. | A window bigger than the biggest layout still gets the frame, so no more of the map. Manual setup, SRWE again on every start. Windows only. |
| [cnc-ddraw][cnc-ddraw] ([ModDB][cnc-moddb]) | A DirectDraw replacement copied into the game folder. It has a ready profile for Majesty Gold HD, and works when the game's "Use DirectX 9" option is off. | Small, open source (MIT), widely used and maintained. Scales the picture to the screen, sharp or smooth, with shaders. Windowed and borderless modes, and fixes for black screens and Alt+Tab. Also runs under Wine and Proton. | Scales only: no new layouts, so the same 1920x1200 at most, stretched or in bars. Needs the DirectDraw renderer. Manual setup. |
| [DxWnd][dxwnd] ([forum thread][dxwnd-thread], 2018-2019) | A Windows tool that hooks the game's drawing to run it in a resizable window. | Can force a window and stretch the picture. | In the thread, a bigger window filled with black bars, and the picture was jittery or ran at 1-2 FPS, depending on the renderer. The game draws much of its interface with GDI, in many windows, which DxWnd finds hard. Windows only. |
| [dxwrapper][dxwrapper] ([gamepressure][dxw-gp], 2021) | A DirectX wrapper DLL, offered as a "Windows 10 fix". PCGamingWiki suggests it for the original Gold Edition's black screen after Multiplayer. | Fixes compatibility problems in old DirectX games. Open source. | Not a resolution fix: it doesn't touch the layouts or the frame. Mostly for the original Gold Edition, which the HD one replaces. Windows only. |

## What this mod can learn

- **Windows.** cnc-ddraw, SRWE and the stretched low resolution all scale the picture on Windows, which this mod
  doesn't do yet: [#12](https://github.com/bruno-gelb/mghd_resolution_mod/issues/12). cnc-ddraw's ready profile for
  the game makes it the first lead there.
- **A borderless window** at the desktop's refresh rate, which players ask for and SRWE gives:
  [#15](https://github.com/bruno-gelb/mghd_resolution_mod/issues/15).

## Not compared

Translations (Polish, Russian, Brazilian Portuguese, Czech) and gameplay mods like Majesty Expanded don't touch the
screen layouts, so they may work alongside this mod, untested. A gameplay mod that ships its own `UIData` files would
clash with it.

[steam]: https://store.steampowered.com/app/73230/
[pcgw]: https://www.pcgamingwiki.com/wiki/Majesty_Gold_HD
[moddb]: https://www.moddb.com/games/majesty-gold-hd/downloads
[s-4k]: https://steamcommunity.com/app/73230/discussions/0/1835685838085264681
[s-new]: https://steamcommunity.com/app/73230/discussions/0/810924774455526838
[s-uw]: https://steamcommunity.com/app/73230/discussions/0/758430465206175832/
[s-res]: https://steamcommunity.com/app/73230/discussions/0/613936673348960709/
[srwe]: https://github.com/dtgDTGdtg/SRWE
[cnc-ddraw]: https://github.com/FunkyFr3sh/cnc-ddraw
[cnc-moddb]: https://www.moddb.com/games/majesty-gold-hd/downloads
[dxwnd]: https://sourceforge.net/projects/dxwnd/
[dxwnd-thread]: https://sourceforge.net/p/dxwnd/discussion/general/thread/da667e9ce9/
[dxwrapper]: https://github.com/elishacloud/dxwrapper
[dxw-gp]: https://www.gamepressure.com/download.asp?ID=78218

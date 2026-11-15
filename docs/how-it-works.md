# How it works

[Majesty Gold HD][steam] picks its interface layout from `Data/UIData_<width>_<height>.dat` files: where the map,
the panels, the minimap and the buttons go, for one screen size. It ships 13 of them, up to 1920x1200. On a bigger
screen it uses the closest one, in a black frame in the middle. The mod changes the layouts, the version line, the
loading screen, and on Linux how the game starts, and nothing else: the game's rules, AI and saves stay exactly as
they were, and its program gets one small change, for the loading screen. The mod keeps the original files it
changes and puts them back when you remove it.

1. **New layouts.** The program makes layouts for common screen sizes the game lacks (16:9 and 16:10 up to 4K, 21:9
   and 32:9 ultrawides, laptop sizes) and for your own screens, on your computer, from the game's own 13. The game's
   layouts share most of their structure, so comparing them shows which positions follow the right or bottom edge or
   the center of the screen, and those are moved for the new size. The rest were placed by hand for each screen
   height, and come from the game's layout with the closest height. The game lists them by itself: its settings menu
   shows the resolutions with a layout in green.
2. **The version line on the main menu**, under the picture, gets the mod's name and version in front:
   `mghd-resolution-mod 0.2.0, game Version 1.5.2.24`. The text is in the game's text files, `Data/textdata.cam`
   and, for the expansion, `DataMX/mx_textdata.cam`; the box it's drawn in is in each layout, and is made wider, so
   the longer line fits.
3. **The loading screen waits for a key or a click.** Starting a quest, the game shows a loading screen with the
   quest's art while it loads the map. On today's hardware that takes a moment, so the art flashed by before anyone
   could look at it. The mod patches the game's program, `MajestyHD.exe`, on your computer: once a single-player
   game has loaded, the loading screen stays up, with "Press any key to continue" under the progress bar, until you
   press a key or click. That press goes no further, so it doesn't also do something in the game. A multiplayer game
   starts as before, so the other players never wait for one. The patch is a small routine in free space at the end
   of the program's code, which the game's single-player starts call after loading; the mod finds where everything
   is from the code itself, so it works on Steam's and GOG's versions alike, and leaves a version it doesn't know as
   it is.
4. **How the game starts, on Linux.** The installer sets the game's launch options in Steam, or its wrapper command
   in Heroic, so the game starts through the mod's launcher. The game's interface doesn't scale: a bigger layout
   shows more of the map, and the text stays the same size in pixels, small on a big screen. So on a screen taller
   than 1200 lines, the launcher draws the game at about 1080 lines in the screen's shape (2560x1080 on a 3440x1440
   screen) and [gamescope] scales it up with FSR, sharp. It also sets GNOME's display to 100% while the game runs:
   with fractional scaling, the game sees a bigger, scaled screen, lists the wrong resolutions and runs slower.
   Removing the mod puts the old launch back. On Windows there's no gamescope yet
   ([#12](https://github.com/bruno-gelb/mghd_resolution_mod/issues/12)): a lower resolution of the same shape, scaled
   up by the graphics card, keeps the text readable.

All the details, with offsets and addresses: [findings](findings.md).

[steam]: https://store.steampowered.com/app/73230/
[gamescope]: https://github.com/ValveSoftware/gamescope

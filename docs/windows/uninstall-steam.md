# Uninstall on Windows, Steam version

Run the program again (`mghd-resolution-mod-windows.exe`) and choose to remove the mod. It puts the game's original
files back and removes the layouts it added. If you deleted it, [download it again][download].

## Without the program

Steam can put the game's changed files back: in your Library, right-click Majesty Gold HD, then **Properties**,
**Installed Files**, [**Verify integrity of game files**][verify].

Then delete what the mod added to the game folder (right-click Majesty Gold HD, **Manage**, **Browse local files**):
the `mghd-resolution-mod-backup` folder, and in `Data`, the `UIData_<width>_<height>.dat` files the game doesn't
ship. The game's own are 800x600, 1024x768, 1280x768, 1280x800, 1280x960, 1280x1024, 1360x768, 1440x900, 1600x900,
1600x1200, 1680x1050, 1920x1080 and 1920x1200: keep those.

If the game was set to one of the mod's resolutions, it falls back to the closest layout it has, centered in a
frame: pick another resolution in **ADJUST SETTINGS**.

[download]: https://github.com/bruno-gelb/mghd_resolution_mod/releases/latest/download/mghd-resolution-mod-windows.exe
[verify]: https://help.steampowered.com/faqs/view/0C48-FCBD-DA71-93EB

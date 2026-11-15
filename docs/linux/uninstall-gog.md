# Uninstall on Linux, GOG version (Heroic)

Quit Heroic (in its menu, **Quit**), then run `./mghd-resolution-mod-linux` again, in the folder you installed from,
and choose to remove the mod. It puts your old wrapper command back, then the game's original files, and removes the
layouts it added. If you deleted the program, run the line from [the install steps](install-gog.md) again.

## Without the program

Heroic can put the game's changed files back: on the game's page, choose **Verify and Repair** in its menu.

Remove the wrapper command the mod set, in the game's settings in Heroic.

Then delete what the mod added to the game folder (the folder is in the game's settings in Heroic): the
`mghd-resolution-mod-backup` folder, and in `Data`, the `UIData_<width>_<height>.dat` files the game doesn't ship.
The game's own are 800x600, 1024x768, 1280x768, 1280x800, 1280x960, 1280x1024, 1360x768, 1440x900, 1600x900,
1600x1200, 1680x1050, 1920x1080 and 1920x1200: keep those.

If the game was set to one of the mod's resolutions, it falls back to the closest layout it has, centered in a
frame: pick another resolution in **ADJUST SETTINGS**.

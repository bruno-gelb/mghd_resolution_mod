# Install on Windows, GOG version

1. Quit the game.
2. [Download the program][download] and double-click it. Windows may say it protected your PC, because the program
   isn't signed yet ([#7](https://github.com/bruno-gelb/mghd_resolution_mod/issues/7)): click **More info**, then
   **Run anyway**.
3. Press Enter: the program finds the game where GOG Galaxy or GOG's installer put it, and installs the mod. It takes
   about a minute. If you also have the Steam version, it asks which one.
4. Start the game, open **ADJUST SETTINGS** on the main menu and pick your resolution: the ones with a layout are
   green. The main menu shows the mod's version under the picture.

Run the program again after a game update, to put the mod back. To remove the mod, see
[Uninstall](uninstall-gog.md).

The mod has been tried on GOG's version under Linux, but not on Windows yet: if something goes wrong, please tell us
in [#6](https://github.com/bruno-gelb/mghd_resolution_mod/issues/6).

## More

- The program makes layouts for common screen sizes (16:9 and 16:10 up to 4K, 21:9 and 32:9 ultrawides, laptop
  sizes) and for your own screens. `--size` adds one more, for example `--size 1720x720`. `--help` lists the rest.
- **Big screens, small text.** The game's interface doesn't scale, so at 3440x1440 or 4K the text gets small. For
  bigger text, pick a lower resolution of your screen's shape, like 2560x1080 on a 3440x1440 screen: it's scaled up
  to fill the screen. The graphics card's plain scaling makes the fonts blurry; its sharpening scaler should help
  (NVIDIA Image Scaling, AMD RSR; not tested yet).
- From a terminal, `--yes` skips the question: `mghd-resolution-mod-windows.exe install --yes`.
- If it can't find the game, copy the program into the game's folder (in GOG Galaxy: the game's page, the settings
  button, **Manage installation**, **Show folder**) and run it from there.

[download]: https://github.com/bruno-gelb/mghd_resolution_mod/releases/latest/download/mghd-resolution-mod-windows.exe

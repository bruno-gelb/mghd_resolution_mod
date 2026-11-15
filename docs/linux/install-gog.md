# Install on Linux, GOG version (Heroic)

1. Quit the game.
2. Run this in a terminal:

   ```bash
   curl -fLO https://github.com/bruno-gelb/mghd_resolution_mod/releases/latest/download/mghd-resolution-mod-linux && chmod +x mghd-resolution-mod-linux && ./mghd-resolution-mod-linux
   ```

3. Press Enter: the program finds the game in [Heroic]'s GOG installs and installs the mod. It takes about a minute.
   If you also have the Steam version, it asks which one.
4. Start the game from Heroic, open **ADJUST SETTINGS** on the main menu and pick your resolution: the ones with a
   layout are green. The main menu shows the mod's version under the picture.

Run `./mghd-resolution-mod-linux` again after a game update, to put the mod back. To remove the mod, see
[Uninstall](uninstall-gog.md).

## More

- The program makes layouts for common screen sizes (16:9 and 16:10 up to 4K, 21:9 and 32:9 ultrawides, laptop
  sizes) and for your own screens. `--size` adds one more, for example `--size 1720x720`. `--help` lists the rest.
- **Big screens, small text.** The game's interface doesn't scale, so at 3440x1440 or 4K the text gets small. For
  bigger text, pick a lower resolution of your screen's shape, like 2560x1080 on a 3440x1440 screen: it's scaled up
  to fill the screen. Wine's plain scaling makes the fonts blurry; [gamescope] with FSR keeps them sharp. In the
  game's settings in Heroic, set gamescope as the wrapper command, with your screen's size after `-W` and `-H`:

  ```
  gamescope -w 2560 -h 1080 -W 3440 -H 1440 -S fit -F fsr -f --
  ```

  Inside gamescope the game sees one screen of the `-w`/`-h` size, so that's the resolution to pick in the game.
- **Display scaling.** With fractional scaling on in GNOME (125%, 150% and the like), the game sees a bigger, scaled
  screen and offers the wrong resolutions in **ADJUST SETTINGS**. Set the display to 100% while you play, for
  example with a wrapper command in the game's settings in Heroic that switches to 100% and back when the game exits.
- `--yes` skips the question: `./mghd-resolution-mod-linux install --yes`.
- If it can't find the game (another launcher, or the game installed by hand), pass its folder:
  `./mghd-resolution-mod-linux --game-dir "<path to the game>"`, or copy the program into the game's folder and run
  it from there. In Heroic, the folder is in the game's settings.

[Heroic]: https://heroicgameslauncher.com/
[gamescope]: https://github.com/ValveSoftware/gamescope

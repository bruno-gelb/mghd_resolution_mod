# Install on Linux, Steam version

1. Quit the game.
2. Run this in a terminal:

   ```bash
   curl -fLO https://github.com/bruno-gelb/mghd_resolution_mod/releases/latest/download/mghd-resolution-mod-linux && chmod +x mghd-resolution-mod-linux && ./mghd-resolution-mod-linux
   ```

3. Press Enter: the program finds the game and installs the mod. It takes about a minute.
4. Start the game from Steam, open **ADJUST SETTINGS** on the main menu and pick your resolution: the ones with a
   layout are green. The main menu shows the mod's version under the picture.

Run `./mghd-resolution-mod-linux` again after a Steam update, to put the mod back. To remove the mod, see
[Uninstall](uninstall-steam.md).

## More

- The program makes layouts for common screen sizes (16:9 and 16:10 up to 4K, 21:9 and 32:9 ultrawides, laptop
  sizes) and for your own screens. `--size` adds one more, for example `--size 1720x720`. `--help` lists the rest.
- **Big screens, small text.** The game's interface doesn't scale, so at 3440x1440 or 4K the text gets small. For
  bigger text, pick a lower resolution of your screen's shape, like 2560x1080 on a 3440x1440 screen: it's scaled up
  to fill the screen. Proton's plain scaling makes the fonts blurry; [gamescope] with FSR keeps them sharp. In
  the game's Steam launch options (right-click Majesty Gold HD, **Properties**), with your screen's size after `-W`
  and `-H`:

  ```
  gamescope -w 2560 -h 1080 -W 3440 -H 1440 -S fit -F fsr -f -- %command%
  ```

  Inside gamescope the game sees one screen of the `-w`/`-h` size, so that's the resolution to pick in the game.
- `--yes` skips the question: `./mghd-resolution-mod-linux install --yes`.
- If it can't find the game, copy the program into the game's folder (in Steam: right-click Majesty Gold HD,
  **Manage**, **Browse local files**) and run it from there.

[gamescope]: https://github.com/ValveSoftware/gamescope

# Install on Linux, Steam version

1. Quit the game, and quit Steam (in Steam's menu, **Steam**, **Exit**: closing its window only hides it).
2. Run this in a terminal:

   ```bash
   curl -fLO https://github.com/bruno-gelb/mghd_resolution_mod/releases/latest/download/mghd-resolution-mod-linux && chmod +x mghd-resolution-mod-linux && ./mghd-resolution-mod-linux
   ```

3. Press Enter: the program finds the game, says what it will do and installs the mod. It takes about a minute.
4. Start the game from Steam as usual. The main menu shows the mod's version under the picture.

Run `./mghd-resolution-mod-linux` again after a Steam update, to put the mod back. To remove the mod, see
[Uninstall](uninstall-steam.md).

## How the game starts with the mod

The installer sets the game's Steam launch options, so Steam starts the game through the mod's launcher (a copy of
the program, in the game folder's `mghd-resolution-mod-backup`). It does two things:

- **Big screens, bigger interface.** The game's interface doesn't scale, so at 3440x1440 or 4K its text is small.
  On a screen taller than 1200 lines, the launcher draws the game at a smaller size of the screen's shape, about
  1080 lines like the game's own biggest layouts (2560x1080 on a 3440x1440 screen, 1920x1080 at 1440p and 4K), and
  [gamescope] scales it up to the screen with FSR, which keeps the fonts sharp. It needs gamescope: on Ubuntu and
  Debian `sudo apt install gamescope`, on Fedora `sudo dnf install gamescope`, on Arch `sudo pacman -S gamescope`.
  Without it, the game runs at the resolution you pick in **ADJUST SETTINGS** (the ones with a layout are green).
- **Display scaling.** With fractional scaling on in GNOME (125%, 133%, 150% and the like), the game sees a bigger,
  scaled screen: it lists the wrong resolutions and runs slower. The launcher sets the display to 100% while you
  play and puts it back when the game exits. On other desktops, set it to 100% yourself.

The launcher keeps a log of what it did in `mghd-resolution-mod-backup/run.log`. Removing the mod puts your old
launch options back.

## More

- `--no-launch` installs the mod without touching Steam's launch options: then pick the resolution in **ADJUST
  SETTINGS** yourself.
- The program makes layouts for common screen sizes (16:9 and 16:10 up to 4K, 21:9 and 32:9 ultrawides, laptop
  sizes) and for your own screens. `--size` adds one more, for example `--size 1720x720`. `--help` lists the rest.
- `--yes` skips the questions: `./mghd-resolution-mod-linux install --yes`. If Steam is running then, the mod is
  installed but the launch isn't set: quit Steam and run it again.
- If it can't find the game, copy the program into the game's folder (in Steam: right-click Majesty Gold HD,
  **Manage**, **Browse local files**) and run it from there.

[gamescope]: https://github.com/ValveSoftware/gamescope

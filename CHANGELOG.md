# Changelog

Versions follow [semantic versioning](https://semver.org). Each version's section here becomes its release notes.

## 0.3.0 (2026-11-15)

- The loading screen waits for a key or a click before a single-player game starts, with "Press any key to continue"
  under its progress bar: on today's hardware a quest loads in a moment, and its art flashed by. Multiplayer games
  start as before, so nobody waits for one player. It's a small patch to the game's exe, found from its code, so it
  works on the Steam and GOG versions; the exe's original is kept with the other files and put back on uninstall
  ([#1](https://github.com/bruno-gelb/mghd_resolution_mod/issues/1)).

## 0.2.1 (2026-11-15)

- A laptop's own screen, turned off for an external one, no longer counts as one of the player's screens: it stays
  connected, but the kernel says it's off. The installer listed it, and would have made a layout for its size.
- Installing again, when the game's launch is the mod's already, the installer says Steam or Heroic can stay open,
  instead of asking to close them.

## 0.2.0 (2026-11-15)

- On Linux, the installer makes Steam (the game's launch options) or Heroic (its wrapper command) start the game
  through the mod's launcher, a copy of the program in the game folder. On a screen taller than 1200 lines it draws
  the game at about 1080 lines and gamescope scales it up with FSR, so the interface is bigger and stays sharp
  (2560x1080 on a 3440x1440 screen). It also sets GNOME's display to 100% while the game runs: with fractional
  scaling the game listed the wrong resolutions and ran slower. Steam or Heroic has to be closed for the installer
  to change their settings; removing the mod puts the old launch back. `--no-launch` leaves them alone. The bigger
  interface needs gamescope installed: the installer says how. On Windows there's no gamescope yet
  ([#12](https://github.com/bruno-gelb/mghd_resolution_mod/issues/12)).
- The GOG version is supported: the installer finds it in Heroic's GOG installs on Linux and where GOG Galaxy or GOG's
  installer put it on Windows. GOG's build (1.5.2.28) is newer than Steam's (1.5.2.24), and its layouts have a few
  more dialogs, which the mod leaves as they are; the generated layouts are otherwise the same as on Steam
  ([#4](https://github.com/bruno-gelb/mghd_resolution_mod/issues/4)).
- The main menu label has a comma after the mod's version instead of a dot: `mghd-resolution-mod 0.2.0, game
  Version 1.5.2.24`.
- Generated layouts keep the last bytes of the game's file when its size isn't a multiple of 4 (GOG's aren't), so the
  last string in it isn't cut short.

## 0.1.0 (2026-11-14)

- First release: an installer for Windows and Linux. It finds the game (Steam, or the folder it runs from), adds
  interface layouts for common screen sizes the game doesn't ship (ultrawide 21:9 and 32:9, 1440p, 4K, 16:10 and
  more) and for the player's own screens, and puts the mod's version on the main menu. Pick the resolution in the
  game's ADJUST SETTINGS: the ones with a layout are green. Running it again removes the mod and puts the game's
  files back byte for byte ([#5](https://github.com/bruno-gelb/mghd_resolution_mod/issues/5),
  [#3](https://github.com/bruno-gelb/mghd_resolution_mod/issues/3)).

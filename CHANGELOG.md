# Changelog

Versions follow [semantic versioning](https://semver.org). Each version's section here becomes its release notes.

## Unreleased

- The GOG version is supported: the installer finds it in Heroic's GOG installs on Linux and where GOG Galaxy or GOG's
  installer put it on Windows. GOG's build (1.5.2.28) is newer than Steam's (1.5.2.24), and its layouts have a few
  more dialogs, which the mod leaves as they are; the generated layouts are otherwise the same as on Steam
  ([#4](https://github.com/bruno-gelb/mghd_resolution_mod/issues/4)).
- The main menu label has a comma after the mod's version instead of a dot: `mghd-resolution-mod 0.1.0, game
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

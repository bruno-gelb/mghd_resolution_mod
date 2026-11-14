# [Majesty Gold HD][steam] — resolution mod

An unofficial fan mod that adds screen layouts [Majesty Gold HD][steam] doesn't ship with: ultrawide (21:9), 1440p
and 4K, so the interface fills the screen instead of sitting in a smaller frame in the middle.

![Majesty at 2560x1080, scaled up to a 3440x1440 ultrawide monitor](docs/screenshots/majesty-2560x1080-ultrawide.png)

*The game at 2560x1080, scaled to fill a 3440x1440 monitor with FSR. The original goes up to 1920x1200.*

The game picks its interface layout from `Data/UIData_<w>_<h>.dat` files, and only ships 13 of them, up to 1920x1200.
On a bigger screen it uses the closest one, in a black frame. The mod generates layouts for the sizes it lacks, from
the game's own files, on your computer.

- [Findings](docs/findings.md)

## Install

You need [Majesty Gold HD][steam] on Steam.

- [Windows + Steam](docs/windows/install-steam.md)
- [Linux + Steam](docs/linux/install-steam.md)

The GOG version isn't supported yet ([#4](https://github.com/bruno-gelb/mghd_resolution_mod/issues/4)).

## Uninstall

Run the program again and choose to remove the mod, or let Steam put the game's files back:

- [Windows + Steam](docs/windows/uninstall-steam.md)
- [Linux + Steam](docs/linux/uninstall-steam.md)

## Principles

The same ones as the [Tzar mod](https://github.com/bruno-gelb/ttbotc_resolution_mod):

- **No game files.** The mod never ships any of the game's code or assets: its executable, data, art, music or
  text. Whatever it needs from the game is made on the player's computer, from their own copy: the new layouts, for
  one, are generated from the game's own.
- **Lightweight and strictly technical.** The mod fixes how the game runs on today's hardware (resolutions, screen
  layouts, scaling) and stays small and easy to remove. No gameplay or balance changes, no new content, no reworked
  art.

## Help wanted

Known problems and plans are [GitHub issues](https://github.com/bruno-gelb/mghd_resolution_mod/issues). Bug reports,
feature requests and help with testing are most welcome there.

## License

The mod's own files (code, documentation) are released under the [MIT License](LICENSE): use, change and share them
freely. That license covers only what's in this repository. The release programs also bundle Python, Click and
PyInstaller's bootloader, each under its own license: `--licenses` shows them, and each release has them in a
`THIRD-PARTY-NOTICES.txt` file next to each program.

## The game and its owners

- This is an unofficial fan project. It is not affiliated with, endorsed by or connected to
  [Cyberlore Studios][cyberlore], the original developer, to [Paradox Interactive][paradox], the publisher of
  [Majesty Gold HD][steam], or to any other publisher or store of the game.
- [Majesty Gold HD][steam], its executable, data files, artwork, music and trademarks belong to their respective
  owners. This repository contains none of them, and the mod will only ever ship its own files (new layouts, made
  from the player's own copy where needed), never the game's files. The screenshots show the game's art, which
  belongs to its owners too.
- The mod doesn't remove or get around any copy protection, and it won't. To use it, buy the game on [Steam][steam].
- The game's files are only changed on your computer, in your copy. Steam's "Verify integrity of game files" puts
  the originals back.

[steam]: https://store.steampowered.com/app/73230/
[cyberlore]: https://en.wikipedia.org/wiki/Cyberlore_Studios
[paradox]: https://www.paradoxinteractive.com/

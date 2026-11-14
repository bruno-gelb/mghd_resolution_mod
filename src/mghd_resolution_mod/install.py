"""Install and uninstall the mod in a game folder.

Installing:

- adds layouts (`Data/UIData_<w>_<h>.dat`) for common screen sizes and the player's own, generated from the game's 13;
- puts the mod's name and version on the main menu: the text in `Data/textdata.cam` and `DataMX/mx_textdata.cam`, and
  a wider box for it in the main menu's layout, in every layout and in both text files.

Before changing a game file, the mod copies the original to mghd-resolution-mod-backup/ in the game folder, with a
manifest of what it did, so uninstalling puts the game back exactly. Installing again (after a mod update, or after
Steam put the original files back) works from those backups.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

from mghd_resolution_mod import __version__, game, layouts, textdata
from mghd_resolution_mod.game import resolve
from mghd_resolution_mod.manifest import DamagedManifest, Manifest

BACKUP_DIR = "mghd-resolution-mod-backup"
TEXT_FILES = [f"{game.DATA}/textdata.cam", f"{game.EXPANSION_DATA}/mx_textdata.cam"]


class InstallError(Exception):
    pass


@dataclass
class Status:
    installed: bool
    version: str | None
    added: list[str]
    # The label is missing from a file the mod changed: Steam put the original back (an update, or verifying files).
    reverted: bool = False


def _backup(game_dir: Path) -> Path:
    return game_dir / BACKUP_DIR


def _manifest(game_dir: Path) -> Manifest | None:
    try:
        return Manifest.load(_backup(game_dir))
    except DamagedManifest as error:
        raise InstallError(f"the mod's backup record is damaged: {error}. The original files are still in "
                           f"{BACKUP_DIR}/; restore them by hand, or have Steam verify the game's files and delete "
                           "that folder") from error


def _original_layouts(game_dir: Path) -> list[str]:
    """The game's own layouts in its Data folder, as paths relative to the game folder."""
    data = resolve(game_dir, game.DATA)
    return sorted(f"{game.DATA}/{p.name}" for p in data.iterdir()
                  if layouts.parse_name(p.name) in layouts.ORIGINAL_SIZES)


def _is_modded(rel: str, data: bytes) -> bool:
    if rel in TEXT_FILES:
        return textdata.find_menu_version(data)[2] != textdata.MENU_VERSION
    return textdata.narrow_version_box(data) != data  # 800x600 has no main menu, so never counts as changed


def _write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".mghd-tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def status(game_dir: Path) -> Status:
    manifest = _manifest(game_dir)
    if manifest is None:
        return Status(False, None, [])
    reverted = False
    for rel in TEXT_FILES:
        path = resolve(game_dir, rel)
        try:
            reverted |= path.is_file() and not _is_modded(rel, path.read_bytes())
        except textdata.FormatError:
            reverted = True
    return Status(True, manifest.version, manifest.added, reverted)


def _check(game_dir: Path) -> None:
    if game.running():
        raise InstallError("Majesty is running: quit the game first")
    missing = [rel for rel in [game.EXE, *TEXT_FILES] if not resolve(game_dir, rel).is_file()]
    originals = _original_layouts(game_dir) if resolve(game_dir, game.DATA).is_dir() else []
    if len(originals) < len(layouts.ORIGINAL_SIZES):
        found = {layouts.parse_name(Path(rel).name) for rel in originals}
        missing += [f"{game.DATA}/{layouts.file_name(s)}" for s in sorted(layouts.ORIGINAL_SIZES - found)]
    if missing:
        raise InstallError(f"not a complete Majesty Gold HD folder, missing: {', '.join(missing)}")


def _originals(game_dir: Path, manifest: Manifest, log) -> dict[str, bytes]:
    """The game's own version of every file the mod changes, from the backup or, for files not backed up yet or put
    back by Steam since, from the game folder. Backs up what's new."""
    backup = _backup(game_dir)
    result = {}
    for rel in [*TEXT_FILES, *_original_layouts(game_dir)]:
        current = resolve(game_dir, rel).read_bytes()
        saved = backup / rel
        try:
            modded = _is_modded(rel, current)
        except textdata.FormatError as error:
            raise InstallError(f"{rel} isn't in the format the mod knows ({error})") from error
        if not modded and (not saved.is_file() or saved.read_bytes() != current):
            if saved.is_file():
                log(f"{rel} was changed since the last install (a game update?): backing up the new one")
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(current)
        elif modded and not saved.is_file():
            raise InstallError(f"{rel} was already changed by something else, and there's no backup of it. Restore "
                               "the game's files first (in Steam: Properties, Installed Files, Verify integrity of "
                               "game files)")
        result[rel] = saved.read_bytes()
        if rel not in manifest.changed:
            manifest.changed.append(rel)
    return result


def install(game_dir: Path, sizes: list[layouts.Size], log=print) -> Manifest:
    """Install the mod, or update it: layouts for `sizes` (on top of the ones added before) and the main menu
    label."""
    _check(game_dir)
    backup = _backup(game_dir)
    manifest = _manifest(game_dir)
    if manifest is None:
        log(f"Backing up the files the mod changes to {BACKUP_DIR}/")
        backup.mkdir(exist_ok=True)
        manifest = Manifest(version=__version__)
    originals = _originals(game_dir, manifest, log)
    manifest.save(backup)  # before changing anything: an install that stops halfway can still be undone

    for rel in TEXT_FILES:
        _write(resolve(game_dir, rel), textdata.widen_version_box(textdata.label(originals[rel], __version__)))
    log("Added the mod's version to the main menu")
    original_layouts = {layouts.parse_name(Path(rel).name): data for rel, data in originals.items()
                        if rel not in TEXT_FILES}
    for rel, data in originals.items():
        if rel not in TEXT_FILES:
            _write(resolve(game_dir, rel), textdata.widen_version_box(data))

    wanted = sorted({*sizes, *(layouts.parse_name(Path(rel).name) for rel in manifest.added)})
    generator = layouts.Generator(original_layouts)
    log(f"Generating {len(wanted)} layouts, about 25 seconds per group of sizes:")
    data_dir = resolve(game_dir, game.DATA)
    for size in sorted(wanted, key=generator.base_for):
        rel = f"{game.DATA}/{layouts.file_name(size)}"
        path = resolve(game_dir, rel)
        if path.exists() and rel not in manifest.added:
            log(f"  {size[0]}x{size[1]}: skipped, there's a {path.name} the mod didn't make")
            continue
        if rel not in manifest.added:
            manifest.added.append(rel)
            manifest.save(backup)
        _write(data_dir / layouts.file_name(size), textdata.widen_version_box(generator.generate(size)))
        base = generator.base_for(size)
        log(f"  {size[0]}x{size[1]} (from {base[0]}x{base[1]})")
    manifest.added.sort()
    manifest.version = __version__
    manifest.save(backup)
    return manifest


def uninstall(game_dir: Path, log=print) -> None:
    backup = _backup(game_dir)
    manifest = _manifest(game_dir)
    if manifest is None:
        raise InstallError("the mod isn't installed here (no backup folder found)")
    if game.running():
        raise InstallError("Majesty is running: quit the game first")
    log(f"Removing the {len(manifest.added)} layouts the mod added")
    for rel in manifest.added:
        path = resolve(game_dir, rel)
        if path.is_file():
            path.unlink()
    log(f"Restoring the {len(manifest.changed)} files the mod changed")
    for rel in manifest.changed:
        _write(resolve(game_dir, rel), (backup / rel).read_bytes())
    shutil.rmtree(backup)

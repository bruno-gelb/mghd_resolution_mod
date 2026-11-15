"""Linux: make Steam or Heroic start the game through the mod's launcher (launch.py), and undo it.

The launcher is the mod's own program, copied into the game's backup folder (mghd-resolution-mod-backup/) so it's
there as long as the mod is, wherever the player downloaded it. Run from source, it's this Python with `-m`.

- Steam: the game's launch options in every Steam account's localconfig.vdf become `"<launcher>" run %command%`.
- Heroic: the game's wrapper command becomes the launcher with `run`.

The manifest records each value as it was, and the one the mod set. Uninstall puts the old value back, unless the
player changed it since. Both launchers keep their settings in memory and write them back, so they're changed only
while closed; when the launch is already the mod's, nothing needs changing and they may run.
"""

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from mghd_resolution_mod import game, heroic, procs, steam

LAUNCHER = "mghd-resolution-mod-linux"


class LaunchBlocked(Exception):
    """The launcher whose settings need changing is running."""

    def __init__(self, store: str):
        super().__init__(f"{store} is running")
        self.store = store


@dataclass
class Store:
    name: str  # "Steam" or "Heroic"
    configs: list[Path]  # the files the game's launch is in


def store_for(game_dir: Path) -> Store | None:
    """Which launcher starts the game in this folder, and where it keeps the game's launch. None: neither, or not
    Linux."""
    if sys.platform == "win32":
        return None
    install = heroic.find(game_dir)
    if install:
        return Store("Heroic", [install.settings])
    resolved = game_dir.resolve()
    if resolved.parent.name.lower() == "common" and resolved.parent.parent.name.lower() == "steamapps":
        roots = [resolved.parent.parent.parent, *game._steam_roots()]
        configs = steam.config_files(roots)
        if configs:
            return Store("Steam", configs)
    return None


def running(store: Store) -> bool:
    return procs.running(steam.PROCESS_NAMES if store.name == "Steam" else heroic.PROCESS_NAMES)


def launcher(backup: Path, copy: bool = True) -> list[str]:
    """The launcher's command line, without the game's: the release program copied into the backup folder, or this
    Python when run from source."""
    if getattr(sys, "frozen", False):
        target = backup / LAUNCHER
        me = Path(sys.executable).resolve()
        if copy and me != target.resolve():
            tmp = target.with_name(target.name + ".mghd-tmp")
            shutil.copy2(me, tmp)
            tmp.replace(target)
        return [str(target), "run"]
    return [sys.executable, "-m", "mghd_resolution_mod", "run"]


def steam_options(command: list[str]) -> str:
    """Steam's launch options for the launcher: each part in double quotes if it has a space, then %command%."""
    return " ".join(f'"{part}"' if " " in part else part for part in command) + " %command%"


def heroic_wrappers(command: list[str]) -> list[dict]:
    return [{"exe": command[0], "args": " ".join(command[1:])}]


def _read(store: Store, config: Path):
    if store.name == "Steam":
        return steam.read(config, str(game.STEAM_APP_ID))
    return heroic.get_wrappers(config)


def _write(store: Store, config: Path, value) -> None:
    if store.name == "Steam":
        steam.write(config, str(game.STEAM_APP_ID), value if value is not None else "")
    else:
        heroic.set_wrappers(config, value if value is not None else [])


def _value(store: Store, backup: Path, copy: bool):
    command = launcher(backup, copy)
    return steam_options(command) if store.name == "Steam" else heroic_wrappers(command)


def needs_change(game_dir: Path, backup: Path) -> bool:
    """Whether setup() would change Steam's or Heroic's settings, so they'd have to be closed. False when the launch
    is the mod's already (installing again), or there's nothing to set."""
    store = store_for(game_dir)
    if store is None:
        return False
    value = _value(store, backup, copy=False)
    try:
        return any(_read(store, config) != value for config in store.configs)
    except (OSError, steam.VdfError, heroic.SettingsError):
        return True  # setup() says what's wrong


def setup(game_dir: Path, backup: Path, record: dict | None, log) -> dict | None:
    """Point the game's launcher at the mod's. Returns the manifest's new launch record, or None when there's no
    launcher to set (not Steam or Heroic, or not Linux). Raises LaunchBlocked when a change is needed and the
    launcher is running, and steam.VdfError or heroic.SettingsError when its settings can't be read."""
    store = store_for(game_dir)
    if store is None:
        return None
    value = _value(store, backup, copy=True)
    old = {e["config"]: e for e in (record or {}).get("entries", []) if isinstance(e, dict) and "config" in e}
    entries, changes = [], []
    for config in store.configs:
        current = _read(store, config)
        before = old.get(str(config))
        # Still the mod's from the last install: the player's own value is the one recorded then.
        previous = before["previous"] if before and current == before.get("value") else current
        entries.append({"config": str(config), "previous": previous, "value": value})
        if current != value:
            changes.append(config)
    if changes and running(store):
        raise LaunchBlocked(store.name)
    for config in changes:
        _write(store, config, value)
    if changes:
        what = "launch options" if store.name == "Steam" else "wrapper command"
        log(f"{store.name} starts the game through the mod now ({what})")
    return {"store": store.name, "entries": entries}


def remove(record: dict | None, log) -> None:
    """Put back the launch the mod replaced. Raises LaunchBlocked if the launcher is running."""
    if not record:
        return
    store = Store(record.get("store", ""), [Path(e["config"]) for e in record.get("entries", [])])
    if store.name not in ("Steam", "Heroic"):
        return
    todo = []
    for entry in record.get("entries", []):
        config = Path(entry["config"])
        try:
            current = _read(store, config)
        except (OSError, steam.VdfError, heroic.SettingsError):
            continue  # the account or the settings are gone
        if current == entry.get("value"):
            todo.append((config, entry.get("previous")))
        else:
            log(f"{store.name}'s launch for the game was changed since the mod set it: left as it is")
    if todo and running(store):
        raise LaunchBlocked(store.name)
    for config, previous in todo:
        _write(store, config, previous)
    if todo:
        log(f"Put {store.name}'s launch for the game back to how it was")

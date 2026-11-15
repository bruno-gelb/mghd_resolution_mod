"""Heroic Games Launcher: where it installed GOG's Majesty Gold HD, and the game's wrapper command.

Heroic keeps its GOG installs in gog_store/installed.json, a list of {appName, install_path}, and each game's settings
in GamesConfig/<appName>.json, under the game's ID. One of them, wrapperOptions, is a list of {exe, args}: programs
Heroic starts the game through, like Steam's launch options. Heroic keeps the settings in memory while it runs and
writes them back, so they're changed only while Heroic is closed.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

GOG_ID = "1423481910"
PROCESS_NAMES = {"heroic"}


def _config_dirs() -> list[Path]:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "heroic"] if appdata else []
    home = Path.home()
    return [home / ".config/heroic", home / ".var/app/com.heroicgameslauncher.hgl/config/heroic"]  # .deb, Flatpak


CONFIG_DIRS = _config_dirs()


@dataclass
class Install:
    config_dir: Path
    game_dir: Path

    @property
    def settings(self) -> Path:
        return self.config_dir / "GamesConfig" / f"{GOG_ID}.json"


def _json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def installs() -> list[Install]:
    """The GOG installs of Majesty Gold HD that Heroic knows about."""
    found = []
    for config in CONFIG_DIRS:
        data = _json(config / "gog_store" / "installed.json")
        entries = data.get("installed") if isinstance(data, dict) else None
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict) or str(entry.get("appName")) != GOG_ID:
                continue
            path = entry.get("install_path")
            if isinstance(path, str) and path:
                found.append(Install(config, Path(path)))
    return found


def game_dirs() -> list[Path]:
    return [i.game_dir for i in installs()]


def find(game_dir: Path) -> Install | None:
    """The Heroic install in this folder, if Heroic installed it."""
    try:
        wanted = game_dir.resolve()
    except OSError:
        return None
    for install in installs():
        try:
            if install.game_dir.resolve() == wanted:
                return install
        except OSError:
            continue
    return None


class SettingsError(ValueError):
    pass


def _load(settings: Path) -> dict:
    data = _json(settings)
    if not isinstance(data, dict) or not isinstance(data.get(GOG_ID), dict):
        raise SettingsError(f"{settings} isn't there or isn't Heroic's: start the game from Heroic once, quit it, "
                            "and run this again")
    return data


def get_wrappers(settings: Path) -> list:
    wrappers = _load(settings)[GOG_ID].get("wrapperOptions", [])
    return wrappers if isinstance(wrappers, list) else []


def set_wrappers(settings: Path, wrappers: list) -> None:
    data = _load(settings)
    data[GOG_ID]["wrapperOptions"] = wrappers
    tmp = settings.with_name(settings.name + ".mghd-tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(settings)

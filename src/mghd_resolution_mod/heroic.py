"""Heroic Games Launcher: where it installed GOG's Majesty Gold HD.

Heroic keeps its GOG installs in gog_store/installed.json, a list of {appName, install_path}. The mod changes only
files in the game folder, so it doesn't need the Wine prefix Heroic runs the game in.
"""

import json
import os
import sys
from pathlib import Path

GOG_ID = "1423481910"


def _config_dirs() -> list[Path]:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "heroic"] if appdata else []
    home = Path.home()
    return [home / ".config/heroic", home / ".var/app/com.heroicgameslauncher.hgl/config/heroic"]  # .deb, Flatpak


CONFIG_DIRS = _config_dirs()


def _json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def game_dirs() -> list[Path]:
    """The folders of the GOG installs of Majesty Gold HD that Heroic knows about."""
    found = []
    for config in CONFIG_DIRS:
        data = _json(config / "gog_store" / "installed.json")
        entries = data.get("installed") if isinstance(data, dict) else None
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict) or str(entry.get("appName")) != GOG_ID:
                continue
            path = entry.get("install_path")
            if isinstance(path, str) and path:
                found.append(Path(path))
    return found

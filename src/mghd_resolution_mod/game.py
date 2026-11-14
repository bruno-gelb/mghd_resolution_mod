"""Find the game folder: Steam libraries, or the folder the program runs from. And whether the game is running."""

import os
import re
import sys
from pathlib import Path

STEAM_APP_ID = 73230
STEAM_INSTALLDIR = "Majesty HD"
EXE = "MajestyHD.exe"
PROCESS_NAMES = {EXE, "MajestyHD.ex"}  # Linux keeps only the first 15 characters in /proc/<pid>/comm
DATA = "Data"
EXPANSION_DATA = "DataMX"


def resolve(root: Path, relative: str) -> Path:
    """root / relative, matching each part case-insensitively (the game's own files use mixed case)."""
    path = root
    for part in Path(relative).parts:
        exact = path / part
        if exact.exists():
            path = exact
            continue
        try:
            match = next((p for p in path.iterdir() if p.name.lower() == part.lower()), None)
        except OSError:
            match = None
        path = match if match else exact
    return path


def is_game_dir(path: Path) -> bool:
    return resolve(path, EXE).is_file() and resolve(path, DATA).is_dir()


def _steam_roots() -> list[Path]:
    roots = []
    if sys.platform == "win32":
        import winreg

        for hive, key, value in [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ]:
            try:
                with winreg.OpenKey(hive, key) as k:
                    roots.append(Path(winreg.QueryValueEx(k, value)[0]))
            except OSError:
                pass
        roots.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    else:
        home = Path.home()
        roots += [
            home / ".steam/steam",
            home / ".steam/root",
            home / ".steam/debian-installation",
            home / ".local/share/Steam",
            home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",  # Flatpak
            home / "snap/steam/common/.local/share/Steam",                 # Snap
        ]
    return roots


def _libraries(root: Path) -> list[Path]:
    libraries = [root]
    vdf = resolve(root, "steamapps/libraryfolders.vdf")
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libraries
    for raw in re.findall(r'"path"\s+"([^"]+)"', text):
        libraries.append(Path(raw.replace("\\\\", "\\")))
    return libraries


def _steam_game_dirs() -> list[Path]:
    found = []
    for root in _steam_roots():
        for library in _libraries(root):
            installdir = STEAM_INSTALLDIR
            manifest = resolve(library, f"steamapps/appmanifest_{STEAM_APP_ID}.acf")
            try:
                match = re.search(r'"installdir"\s+"([^"]+)"', manifest.read_text(errors="replace"))
                if match:
                    installdir = match.group(1)
            except OSError:
                pass
            found.append(resolve(library, f"steamapps/common/{installdir}"))
    return found


def find() -> list[Path]:
    """Game folders found on this machine: the program's own folder and the working folder first, then Steam's."""
    here = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).resolve().parent
    seen, result = set(), []
    for path in [here, Path.cwd(), *_steam_game_dirs()]:
        try:
            key = path.resolve()
        except OSError:
            continue
        if key not in seen and is_game_dir(key):
            seen.add(key)
            result.append(key)
    return result


def running() -> bool:
    """Linux: whether the game is running, as Wine names its process. On Windows, writing its open files fails
    instead."""
    if sys.platform == "win32":
        return False
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() in PROCESS_NAMES:
                return True
        except OSError:  # the process ended meanwhile
            pass
    return False

"""The launcher, Linux only: what `mghd-resolution-mod run <the game's command>` does when Steam or Heroic starts the
game through it.

1. The display goes to 100% while the game runs, and back when it exits (GNOME, see display.py): fractional scaling
   makes the game list the wrong resolutions and run slower.
2. On a screen taller than the game's biggest layouts (1200 lines), the game is drawn at a smaller size of the same
   shape, 1080 to 1200 lines like the game's biggest layouts, the size its interface was made for, and gamescope
   scales it up to the screen with FSR: the interface doesn't scale on its own, so at full resolution its text is
   small. On a 3440x1440 screen that's 2560x1080; on 2560x1440 and 4K, 1920x1080; on 2560x1600, 1920x1200. The
   game's settings file is set to that size, since inside gamescope it's the only one there is.
3. Without gamescope, or on a smaller screen, the game starts as it is, with the settings the player picked.

What it did goes to run.log in the mod's backup folder: Steam and Heroic show none of it.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from mghd_resolution_mod import display, game, layouts, procs, screen

LOG = "run.log"
GAME_HEIGHT = 1080  # the interface's own size: the game's layouts go up to 1920x1080 and 1920x1200
NATIVE_UP_TO = 1200  # screens this tall or smaller run at their own size: the game has layouts for them
SAME_SHAPE = 0.03  # aspect ratios this close count as the same shape (2560x1080 is 2.370, 3440x1440 is 2.389)
# Tested on a 3440x1440 screen, 2026-11-14: the SDL backend, FSR at sharpness 2 (the sharpest is 0), 60 fps.
GAMESCOPE = ["gamescope", "--backend", "sdl", "-r", "60", "-S", "fit", "-F", "fsr", "--sharpness", "2", "-f",
             "--force-grab-cursor"]
PREFS = "drive_c/users/*/Documents/My Games/MajestyHD/MajXPrefs"


def pick_render(screen_size: layouts.Size, available: list[layouts.Size]) -> layouts.Size | None:
    """The size to draw the game at on this screen, from the sizes with a layout. None: at the screen's own size."""
    w, h = screen_size
    if h <= NATIVE_UP_TO:
        return None
    shape = [s for s in available if s[1] < h and abs(s[0] / s[1] - w / h) <= SAME_SHAPE * w / h]
    if not shape:
        return None
    made_for = [s for s in shape if GAME_HEIGHT <= s[1] <= NATIVE_UP_TO]  # the game's own biggest layouts' heights
    if made_for:
        return max(made_for, key=lambda s: s[1])
    return min(shape, key=lambda s: (abs(s[1] - GAME_HEIGHT), -s[1]))


def available_sizes(game_dir: Path) -> list[layouts.Size]:
    data = game.resolve(game_dir, game.DATA)
    try:
        return sorted({s for p in data.iterdir() if (s := layouts.parse_name(p.name))})
    except OSError:
        return []


def screen_size(current: display.Display | None) -> layouts.Size | None:
    """The size of the screen the game goes on: GNOME's active display, or the biggest connected one."""
    if current:
        return current.size
    found = screen.detect_screens()
    return max(found, key=lambda s: s[0] * s[1]) if found else None


def gamescope_command(output: layouts.Size, render: layouts.Size, command: list[str]) -> list[str]:
    return [*GAMESCOPE, "-W", str(output[0]), "-H", str(output[1]), "-w", str(render[0]), "-h", str(render[1]), "--",
            *command]


def find_prefs(env: dict[str, str]) -> Path | None:
    """The game's settings file, MajXPrefs, in the Wine prefix Steam or Heroic runs it in. Both set
    STEAM_COMPAT_DATA_PATH for Proton (Steam's has the prefix in pfx/, Heroic's pfx/ is a link to itself); plain
    Wine has WINEPREFIX."""
    prefixes = []
    if env.get("STEAM_COMPAT_DATA_PATH"):
        prefixes.append(Path(env["STEAM_COMPAT_DATA_PATH"]) / "pfx")
    if env.get("WINEPREFIX"):
        prefixes.append(Path(env["WINEPREFIX"]))
    for prefix in prefixes:
        found = sorted(prefix.glob(PREFS))
        if found:
            return found[0]
    return None


def set_prefs(path: Path, size: layouts.Size) -> None:
    """The game's settings set to full screen at this size, with Direct3D (its DirectDraw draws no ground under
    Wine)."""
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    for key, value in [("PixWidth", size[0]), ("PixHeight", size[1]), ("Windowed", 0), ("UseD3D", 1)]:
        text = re.sub(rf"<{key}>[^<]*</{key}>", f"<{key}>{value}</{key}>", text)
    path.write_text(text, encoding="utf-8", errors="surrogateescape")


def find_game_dir(command: list[str]) -> Path | None:
    """The game folder: the release program runs from the mod's backup folder in it; otherwise, the folder of the
    game's exe in the command."""
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).resolve().parent.parent
        if game.is_game_dir(here):
            return here
    for arg in command:
        if arg.lower().endswith(game.EXE.lower()):
            folder = Path(arg).parent
            if game.is_game_dir(folder):
                return folder
    return None


def run(command: list[str], log_dir: Path | None = None) -> int:
    """Start the game's command as above, wait for it, and return its exit code."""
    from mghd_resolution_mod import install  # the backup folder's name

    game_dir = find_game_dir(command)
    if log_dir is None and game_dir is not None:
        log_dir = game_dir / install.BACKUP_DIR
    lines = []

    def log(line: str) -> None:
        lines.append(f"{time.strftime('%H:%M:%S')} {line}")
        if log_dir is not None and log_dir.is_dir():
            try:
                (log_dir / LOG).write_text("\n".join(lines) + "\n", encoding="utf-8")
            except OSError:
                pass

    log(f"mghd-resolution-mod run: {command}")
    if not command:
        log("no game command: in Steam, the launch options must end with %command%")
        return 2

    current = display.current()
    size = screen_size(current)
    render = None
    if size and game_dir and shutil.which("gamescope"):
        render = pick_render(size, available_sizes(game_dir))
    elif not shutil.which("gamescope"):
        log("gamescope isn't installed: the game runs at the screen's own size")
    if render and size:
        prefs = find_prefs(dict(os.environ))
        if prefs:
            set_prefs(prefs, render)
            log(f"{prefs}: set to {render[0]}x{render[1]}, full screen")
        else:
            log("the game's settings file isn't there yet (first start): the game picks its own size this time")
        command = gamescope_command(size, render, command)
        log(f"drawn at {render[0]}x{render[1]}, scaled up to {size[0]}x{size[1]} by gamescope with FSR")
    else:
        log(f"the game's own size: screen {size}")

    restore = None
    if current and abs(current.scale - 1.0) > 0.001:
        try:
            display.set_scale(current, 1.0, display.TEMPORARY)
            restore = current.scale
            log(f"display scale {current.scale:g} -> 1")
        except (OSError, subprocess.SubprocessError) as error:
            log(f"couldn't set the display to 100%: {error}")
    elif current is None:
        log("not GNOME, or more than one display on: the display scale stays as it is")

    child = None

    def forward(signum, _frame):
        if child and child.poll() is None:
            child.send_signal(signum)

    names = ("SIGTERM", "SIGINT", "SIGHUP")  # Windows has no SIGHUP (run is for Linux, but tests run there too)
    handlers = {s: signal.signal(s, forward) for s in (getattr(signal, n) for n in names if hasattr(signal, n))}
    try:
        log(f"starting: {command}")
        child = subprocess.Popen(command, env=procs.child_env())
        while True:
            try:
                code = child.wait()
                break
            except InterruptedError:
                continue
        log(f"the game exited with {code}")
        return code
    except OSError as error:
        log(f"couldn't start it: {error}")
        return 127
    finally:
        for s, h in handlers.items():
            signal.signal(s, h)
        if restore is not None:
            try:
                display.set_scale(current, restore, display.PERSISTENT)
                log(f"display scale back to {restore:g}")
            except (OSError, subprocess.SubprocessError) as error:
                log(f"couldn't put the display scale back to {restore:g}: {error}")

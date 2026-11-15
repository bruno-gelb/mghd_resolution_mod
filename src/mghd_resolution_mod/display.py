"""GNOME's display scale, and the size of the screen the game will be on.

GNOME's fractional scaling (125%, 133%, 150%...) makes Xwayland show X11 programs a bigger, scaled screen: a
3440x1440 screen at 133% is 5160x2160 to them, with made-up modes. The game runs under Wine on X11, so it lists the
wrong resolutions, and it runs slower. The launcher switches the display to 100% while the game runs.

It talks to GNOME's own display settings, `org.gnome.Mutter.DisplayConfig` on the session bus, through `busctl`
(systemd's, on every GNOME system): the release program has no D-Bus library of its own. GetCurrentState gives the
monitors with their modes and the logical monitors with their scales; ApplyMonitorsConfig sets them. The switch to
100% is temporary (method 1), so a crash or logging out falls back to the saved scale; putting the old scale back is
persistent (method 2), the same as the saved one.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass

from mghd_resolution_mod import procs

BUS = ["org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig", "org.gnome.Mutter.DisplayConfig"]
APPLY_SIGNATURE = "uua(iiduba(ssa{sv}))a{sv}"
TEMPORARY, PERSISTENT = 1, 2


@dataclass
class Display:
    """The one active display: what ApplyMonitorsConfig needs to change its scale."""
    serial: int
    x: int
    y: int
    scale: float
    transform: int
    primary: bool
    connector: str
    mode: str  # the current mode's ID, like 3440x1440@100.000
    size: tuple[int, int]  # the current mode's size in pixels
    scales: list[float]  # the scales the mode supports


def _busctl(*args: str, json_out: bool = False) -> str:
    # Steam's own LD_LIBRARY_PATH and LD_PRELOAD (its runtime, its overlay) are for the game, not for busctl.
    command = ["busctl", "--user", *(["--json=short"] if json_out else []), "call", *BUS, *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=10, check=True,
                          env=procs.child_env("LD_LIBRARY_PATH", "LD_PRELOAD")).stdout


def parse_state(state: list) -> Display | None:
    """The one active display from GetCurrentState's data, or None when there are several (or none)."""
    serial, monitors, logical, _ = state
    if len(logical) != 1:
        return None
    x, y, scale, transform, primary, specs, _ = logical[0]
    if len(specs) != 1:
        return None
    connector = specs[0][0]
    for spec, modes, _ in monitors:
        if spec[0] != connector:
            continue
        for mode in modes:
            if mode[6].get("is-current", {}).get("data"):
                return Display(serial, x, y, scale, transform, primary, connector, mode[0], (mode[1], mode[2]),
                               list(mode[5]))
    return None


def current() -> Display | None:
    """The active display, or None: not GNOME, no busctl, several displays on, or an error."""
    if shutil.which("busctl") is None:
        return None
    try:
        return parse_state(json.loads(_busctl("GetCurrentState", json_out=True))["data"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, IndexError):
        return None


def apply_args(display: Display, scale: float, method: int) -> list[str]:
    """ApplyMonitorsConfig's arguments for busctl: the display as it is, with another scale."""
    target = min(display.scales, key=lambda s: abs(s - scale)) if display.scales else scale
    return [APPLY_SIGNATURE, str(display.serial), str(method),
            "1", str(display.x), str(display.y), repr(target), str(display.transform),
            "true" if display.primary else "false", "1", display.connector, display.mode, "0",
            "0"]


def set_scale(display: Display, scale: float, method: int) -> None:
    """Set the display's scale. Raises OSError or subprocess.SubprocessError if GNOME refuses."""
    fresh = current() or display  # the serial changes with every change, so ask again
    _busctl("ApplyMonitorsConfig", *apply_args(fresh, scale, method))

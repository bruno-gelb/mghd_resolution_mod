"""The sizes of the player's screens, to make layouts for them."""

import re
import subprocess
import sys
from pathlib import Path

from mghd_resolution_mod import procs

DRM = Path("/sys/class/drm")


def _drm_screens() -> list[tuple[int, int]]:
    """Linux: the preferred (native) mode of each display that's connected and on, from the kernel. Unlike xrandr's,
    not changed by the desktop's display scaling (GNOME at 150% makes a 3440x1440 screen 5160x2160 to X11 programs).
    A laptop's own panel stays connected when the desktop turns it off for an external screen: the kernel then says
    it isn't enabled, and it's left out. If no connected display is on (no desktop running), all of them count."""
    on, off = [], []
    for status in sorted(DRM.glob("card*-*/status")):
        try:
            if status.read_text().strip() != "connected":
                continue
            first = (status.parent / "modes").read_text().split("\n", 1)[0]
        except OSError:
            continue
        try:
            enabled = (status.parent / "enabled").read_text().strip() != "disabled"
        except OSError:  # an older kernel without the file
            enabled = True
        m = re.fullmatch(r"(\d+)x(\d+)\w*", first.strip())
        if m:
            (on if enabled else off).append((int(m[1]), int(m[2])))
    found = []
    for size in on or off:
        if size not in found:
            found.append(size)
    return found


def detect_screens() -> list[tuple[int, int]]:
    """The native sizes of the player's screens, as far as they can be told."""
    if sys.platform != "win32":
        found = _drm_screens()
        if found:
            return found
    main = detect_screen()
    return [main] if main else []


def detect_screen() -> tuple[int, int] | None:
    """The main screen's size in pixels, or None if it can't be told."""
    try:
        if sys.platform == "win32":
            import ctypes

            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()  # real pixels, not the size Windows scaling pretends
            w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            return (w, h) if w > 0 and h > 0 else None
        out = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5,
                             env=procs.child_env()).stdout
        match = re.search(r" connected primary (\d+)x(\d+)", out) or re.search(r" connected (\d+)x(\d+)", out)
        return (int(match.group(1)), int(match.group(2))) if match else None
    except Exception:
        return None

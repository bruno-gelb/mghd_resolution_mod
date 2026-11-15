"""Other programs: whether one is running, and the environment to start one in."""

import os
import sys
from pathlib import Path


def running(names: set[str]) -> bool:
    """Linux: whether a process with one of these names runs (/proc/<pid>/comm, at most 15 characters). Windows:
    always False."""
    if sys.platform == "win32":
        return False
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() in names:
                return True
        except OSError:  # the process ended meanwhile
            pass
    return False


def child_env(*drop: str) -> dict[str, str]:
    """This process's environment for a program it starts, without the variables in `drop`. The release program is
    built with PyInstaller, which points LD_LIBRARY_PATH at its own libraries and keeps the original in
    LD_LIBRARY_PATH_ORIG: other programs get the original back."""
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        if "LD_LIBRARY_PATH_ORIG" in env:
            env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
        else:
            env.pop("LD_LIBRARY_PATH", None)
    for name in drop:
        env.pop(name, None)
    return env

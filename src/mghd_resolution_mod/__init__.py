"""Resolution mod for Majesty Gold HD."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mghd-resolution-mod")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "unknown"

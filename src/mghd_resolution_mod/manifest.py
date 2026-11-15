"""The record of what the mod did to a game folder: mghd-resolution-mod-backup/manifest.json.

It sits next to the backed-up original files and tells uninstall what to put back and what to delete, and the
installer what's installed.
"""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

FILE = "manifest.json"


class DamagedManifest(Exception):
    """manifest.json exists but can't be read."""


@dataclass
class Manifest:
    version: str  # the mod's version that last installed it
    # The game's files the mod changed, relative to the game folder; their originals are in the backup folder.
    changed: list[str] = field(default_factory=list)
    # The layouts the mod added (Data/UIData_<w>_<h>.dat), deleted on uninstall.
    added: list[str] = field(default_factory=list)
    # Linux: the launch the mod set up in Steam or Heroic, put back on uninstall (see launch_setup.py). None: none.
    launch: dict | None = None

    @classmethod
    def load(cls, backup_dir: Path) -> "Manifest | None":
        """The manifest in backup_dir, or None if there isn't one (the mod isn't installed)."""
        path = backup_dir / FILE
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as error:
            raise DamagedManifest(f"{path} can't be read ({error})") from error
        if not isinstance(data, dict):
            raise DamagedManifest(f"{path} isn't a JSON object")
        known = {f.name for f in fields(cls)}
        try:
            manifest = cls(**{key: value for key, value in data.items() if key in known})
        except TypeError as error:  # "version" missing
            raise DamagedManifest(f"{path} is incomplete ({error})") from error
        ok = (isinstance(manifest.version, str)
              and all(isinstance(v, list) and all(isinstance(n, str) for n in v)
                      for v in (manifest.changed, manifest.added))
              and (manifest.launch is None or isinstance(manifest.launch, dict)))
        if not ok:
            raise DamagedManifest(f"{path} has values of the wrong type")
        return manifest

    def save(self, backup_dir: Path) -> None:
        (backup_dir / FILE).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

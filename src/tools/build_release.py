"""Build the single-file mghd-resolution-mod program for this platform into dist/.

Usage: uv run python src/tools/build_release.py

The version goes into the program's metadata too. On Windows it's a version resource, what Explorer shows under
Properties, Details. ELF has no such field and file managers show none, so the Linux program gets the nearest thing:
a .note.package section in systemd's package metadata format (https://systemd.io/ELF_PACKAGE_METADATA/), which
`readelf -n` shows. systemd's own tools only read notes that are linked into the program, which would mean building
PyInstaller's bootloader ourselves.
"""

import json
import os
import shutil
import subprocess
import sys
import struct
import tempfile
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "mghd_resolution_mod"
PRODUCT = "mghd_resolution_mod"
DIST_NAME = "mghd-resolution-mod"
URL = "https://github.com/bruno-gelb/mghd_resolution_mod"

# PyInstaller's --version-file format: Python code it evaluates with the classes from
# PyInstaller.utils.win32.versioninfo. 0x0409, 1200: US English, Unicode, the same as the 040904B0 table.
VERSION_INFO = """\
VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}),
  kids=[
    StringFileInfo([StringTable('040904B0', [
{strings}
    ])]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
  ],
)
"""


def version_strings(v: str, filename: str) -> dict[str, str]:
    return {
        "ProductName": PRODUCT,
        "ProductVersion": v,
        "FileDescription": "Majesty Gold HD resolution mod installer",
        "FileVersion": v,
        "InternalName": DIST_NAME,
        "OriginalFilename": filename,
        "LegalCopyright": "Copyright (c) 2026 Bruno Gelb, MIT License",
    }


def version_info(v: str, filename: str) -> str:
    """The version resource for --version-file. v is X.Y.Z, as in pyproject.toml."""
    parts = v.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        sys.exit(f"version {v!r} isn't X.Y.Z: a Windows version resource needs plain numbers")
    numbers = (*map(int, parts), 0)
    strings = ",\n".join(f"      StringStruct({k!r}, {s!r})" for k, s in version_strings(v, filename).items())
    return VERSION_INFO.format(numbers=numbers, strings=strings)


def check_version_info(exe: Path, expected: dict[str, str]) -> None:
    """Fail the build if the exe's version resource isn't what was asked for."""
    import pefile

    pe = pefile.PE(str(exe))
    found = {
        key.decode(): value.decode()
        for info in getattr(pe, "FileInfo", None) or []
        for entry in info
        for table in getattr(entry, "StringTable", [])
        for key, value in table.entries.items()
    }
    pe.close()
    if found != expected:
        sys.exit(f"{exe.name}'s version resource is {found}, expected {expected}")


def package_metadata(v: str) -> dict[str, str]:
    return {"type": "github", "name": PRODUCT, "version": v, "url": URL}


def package_note(v: str) -> bytes:
    """The .note.package section: one ELF note, owner "FDO", type 0xcafe1a7e, holding the metadata as JSON."""
    name = b"FDO\0"
    desc = json.dumps(package_metadata(v), separators=(",", ":")).encode() + b"\0"
    desc += b"\0" * (-len(desc) % 4)  # notes are 4-byte aligned
    return struct.pack("<III", len(name), len(desc), 0xCAFE1A7E) + name + desc


def add_package_note(exe: Path, v: str, tmp: Path) -> None:
    """Add the note with objcopy, the same way PyInstaller adds its own data to the Linux program."""
    note = tmp / "package_note.bin"
    note.write_bytes(package_note(v))
    subprocess.run(["objcopy", "--add-section", f".note.package={note}",
                    "--set-section-flags", ".note.package=noload,readonly", str(exe)], check=True)
    notes = subprocess.run(["readelf", "-n", str(exe)], check=True, capture_output=True, text=True).stdout
    expected = json.dumps(package_metadata(v), separators=(",", ":"))
    if expected not in notes:
        sys.exit(f"{exe.name} has no package note with {expected}:\n{notes}")


def _license_files(distribution: str) -> list[Path]:
    """A Python package's license files, from its installed metadata."""
    from importlib.metadata import distribution as dist

    d = dist(distribution)
    files = [Path(str(d.locate_file(f))) for f in d.files or []
             if any(word in f.name.upper() for word in ("LICENSE", "COPYING"))]
    if not files:
        sys.exit(f"no license file found for {distribution}")
    return files


def _python_license() -> Path:
    for path in [Path(sys.base_prefix) / "LICENSE.txt",
                 Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"]:
        if path.is_file():
            return path
    sys.exit(f"Python's license wasn't found under {sys.base_prefix}")


def notices() -> str:
    """THIRD-PARTY-NOTICES.txt: the licenses of everything the release program bundles, as their licenses ask."""
    def section(title: str, *paths: Path) -> str:
        texts = "\n\n".join(p.read_text(encoding="utf-8", errors="replace").strip() for p in paths)
        return f"{'=' * 79}\n{title}\n{'=' * 79}\n\n{texts}\n\n"

    parts = [
        f"{DIST_NAME} ({PRODUCT}), {URL}\n"
        "Copyright (c) 2026 Bruno Gelb, under the MIT License (below). This program bundles the software listed\n"
        "after it, each under its own license.\n\n",
        section(f"{PRODUCT}: MIT License", ROOT / "LICENSE"),
    ]
    parts += [
        section("Click, https://palletsprojects.com/p/click/", *_license_files("click")),
        section("pefile, https://github.com/erocarrera/pefile", *_license_files("pefile")),
        section(f"Python {sys.version.split()[0]}, https://www.python.org/", _python_license()),
        section("PyInstaller's bootloader, https://pyinstaller.org/ (GPL-2.0-or-later with the Bootloader\n"
                "Exception, which allows this use)", *_license_files("pyinstaller")),
    ]
    return "".join(parts)


def main() -> None:
    v = version(DIST_NAME)
    platform = "windows" if sys.platform == "win32" else "linux"
    # No version in the name: the README links to releases/latest/download/<name>, which always gets the newest one.
    # The program shows its version when it starts, and in its metadata (above).
    name = f"{DIST_NAME}-{platform}"
    out = ROOT / "dist" / (name + (".exe" if platform == "windows" else ""))
    # Inside the program (shown by --licenses) and next to it on the releases page.
    notices_file = PACKAGE / "THIRD-PARTY-NOTICES.txt"
    notices_file.write_text(notices(), encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        if platform == "windows":
            version_file = Path(tmp) / "version_info.txt"
            version_file.write_text(version_info(v, out.name), encoding="utf-8")
            extra = ["--version-file", str(version_file)]
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--console", "--clean", "--noconfirm",
            "--name", name,
            "--add-data", f"{notices_file}{os.pathsep}mghd_resolution_mod",
            "--copy-metadata", DIST_NAME,
            *extra,
            "--distpath", str(ROOT / "dist"),
            "--workpath", str(ROOT / "build" / "pyinstaller"),
            "--specpath", str(ROOT / "build" / "pyinstaller"),
            str(PACKAGE / "__main__.py"),
        ], check=True, cwd=ROOT)
        if platform == "windows":
            check_version_info(out, version_strings(v, out.name))
        else:
            add_package_note(out, v, Path(tmp))
    shutil.copy2(notices_file, ROOT / "dist" / f"{name}-THIRD-PARTY-NOTICES.txt")


if __name__ == "__main__":
    main()

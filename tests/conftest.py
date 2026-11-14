"""Synthetic game files for the tests: the game's own files can't go into the repository.

The text archives are small `CYLBPC` files with the same structure as the game's: a screen layout section with the
main menu's version box, and string tables with the main menu's line, `Version %s`, as ID 0x56 of `GMTX`, between other
chunks. The layouts are short word lists with a few anchored coordinates and the version box, one per original size.
"""

import struct
from pathlib import Path

import pytest

from mghd_resolution_mod import game, layouts, textdata

BOX = [-1, 0, 2, *textdata.VERSION_BOX]


def string_table(strings: list[tuple[int, bytes]]) -> bytes:
    """A string table chunk: 16-bit count, 16-bit 2, offsets, then (ID, text, NUL) records."""
    head = 4 + 4 * len(strings)
    records, offsets = b"", []
    for id_, text in strings:
        offsets.append(head + len(records))
        records += struct.pack("<I", id_) + text + b"\0"
    return struct.pack("<HH", len(strings), 2) + b"".join(struct.pack("<I", o) for o in offsets) + records


def cylbpc(sections: list[tuple[bytes, list[tuple[bytes, bytes]]]]) -> bytes:
    """A CYLBPC archive: sections of (tag, [(chunk tag, chunk data)]), tables first, then the chunks in order."""
    header = 20 + 8 * len(sections)
    tables_size = sum(8 + 28 * len(chunks) for _, chunks in sections)
    offset = header + tables_size
    head = b"CYLBPC  " + struct.pack("<HHII", 1, 1, len(sections), tables_size)
    tables, body, table_at = b"", b"", header
    entries = []
    for tag, chunks in sections:
        entries.append(tag + struct.pack("<I", table_at))
        tables += struct.pack("<II", len(chunks), 0)
        for chunk_tag, data in chunks:
            tables += chunk_tag + b"\0" * 16 + struct.pack("<II", offset, len(data))
            body += data
            offset += len(data)
        table_at += 8 + 28 * len(chunks)
    return head + b"".join(entries) + tables + body


def menu_layout() -> bytes:
    return struct.pack("<17i", 7, 7, -1, 0, 2, 15, 10, 768, 520, *BOX, 7)


def make_textdata(extra: bytes = b"") -> bytes:
    general = [(i, f"string {i}".encode()) for i in range(0x50, 0x58)]
    general[6] = (0x56, textdata.MENU_VERSION)
    return cylbpc([
        (b"SMNU", [(b"AP65", b"\x01" * 12), (b"AP29", menu_layout())]),
        (b"STRT", [
            (b"AP29", string_table([(9, b"Cheat Play Replay"), (10, b"Version #"), (11, b"ADJUST SETTINGS")])),
            (b"GMTX", string_table(general)),
            (b"GDB8", string_table([(1, b"after" + extra)])),
        ]),
    ])


def make_layout(size: layouts.Size) -> bytes:
    """A layout: anchored words (right, bottom, centered), fixed ones, and the main menu's version box."""
    w, h = size
    words = [0x50424C59, w, h, 12, 30, w - 130, h - 40, w // 2 - 113, 5, 1000, 77, *BOX, 3, h - 22, 9]
    if size == (800, 600):  # no main menu at 800x600
        words[len(words) - 3 - len(BOX):len(words) - 3] = [1, 2, 3, 4, 5, 6, 7]
    return struct.pack(f"<{len(words)}i", *words)


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    root = tmp_path / "Majesty HD"
    (root / game.DATA).mkdir(parents=True)
    (root / game.EXPANSION_DATA).mkdir()
    (root / game.EXE).write_bytes(b"MZ fake exe")
    (root / game.DATA / "textdata.cam").write_bytes(make_textdata())
    (root / game.EXPANSION_DATA / "mx_textdata.cam").write_bytes(make_textdata(b" mx"))
    for size in layouts.ORIGINAL_SIZES:
        (root / game.DATA / layouts.file_name(size)).write_bytes(make_layout(size))
    return root


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture(autouse=True)
def not_running(monkeypatch):
    monkeypatch.setattr(game, "running", lambda: False)

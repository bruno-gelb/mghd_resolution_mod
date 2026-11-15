"""The game's text archives (`Data/textdata.cam`, `DataMX/mx_textdata.cam`) and the mod's version on the main menu.

The archive is in Cyberlore's `CYLBPC` format:

- a header: `CYLBPC  `, two 16-bit numbers, the number of sections, the size of the tables, then one entry per
  section: a tag (`SMNU`, the screen layouts; `STRT`, the string tables) and the offset of its table;
- each table: the number of chunks, 4 zero bytes, then one 28-byte entry per chunk: a tag, 16 zero bytes, the chunk's
  offset in the file and its size;
- the chunks, back to back, in the order of the tables.

A string table chunk is a 16-bit count, a 16-bit number, one 32-bit offset per string (from the chunk's start), then
the strings: a 32-bit ID, the text, a NUL.

The main menu's version line is `Version %s`, ID 0x56 in the game's general string table, `GMTX`: the exe formats it
with its own version (`0x478824`, the only use) and shows it in place of `Version #`, ID 10 in the main menu's own
table, `AP29`, which is only a placeholder. The base game reads `Data/textdata.cam`, the expansion
`DataMX/mx_textdata.cam`; both have the line. A longer text makes its chunk longer, so the later strings in it and every
later chunk move.

The line's box is 183 px wide, made for `Version 1.5.2.24`: longer text wraps at the spaces, and the lines below the
box aren't drawn. The box is a rectangle record (-1, 0, 2, x, y, w, h) in the main menu's layout, which is in each
`UIData_<w>_<h>.dat` and, for 800x600, whose layout has no main menu, presumably in the text archives. Tested with the
box widened differently in both: the game used the layout's. `widen_version_box` makes it wider, around the same center.
"""

import struct

MAGIC = b"CYLBPC  "
STRINGS = b"STRT"
ENTRY_SIZE = 28

MENU_TABLE = b"GMTX"
MENU_ID = 0x56
MENU_VERSION = b"Version %s"
# Hyphens, not the repo name's underscores: the game's font has no `_` and draws it as `-` anyway.
MENU_LABEL = "mghd-resolution-mod {version}, game {original}"

BOX = struct.pack("<3i", -1, 0, 2)
VERSION_BOX = (162, 498, 183, 21)
WIDE_VERSION_BOX = (19, 498, 469, 21)  # the same center, x 253


class FormatError(ValueError):
    """The file isn't the `textdata.cam` this module knows."""


def _u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _tables(data: bytes) -> dict[bytes, int]:
    """Section tag -> offset of its table."""
    if data[:8] != MAGIC:
        raise FormatError("not a CYLBPC file")
    count = _u32(data, 12)
    return {data[20 + 8 * k : 24 + 8 * k]: _u32(data, 24 + 8 * k) for k in range(count)}


def _entries(data: bytes) -> list[int]:
    """Offsets of every chunk entry in the tables, in file order."""
    entries = []
    for table in sorted(_tables(data).values()):
        entries += [table + 8 + ENTRY_SIZE * k for k in range(_u32(data, table))]
    return entries


def find_chunk(data: bytes, section: bytes, tag: bytes) -> tuple[int, int] | None:
    """(offset, size) of the first chunk with this tag in this section, or None, also when data isn't CYLBPC."""
    try:
        table = _tables(data).get(section)
        if table is None:
            return None
        for k in range(_u32(data, table)):
            entry = table + 8 + ENTRY_SIZE * k
            if data[entry : entry + 4] == tag:
                return _u32(data, entry + 20), _u32(data, entry + 24)
    except (FormatError, struct.error):
        pass
    return None


def _strings(data: bytes, chunk: int) -> list[tuple[int, int, bytes]]:
    """(offset of the record, ID, text) for each string in a string table chunk."""
    count = struct.unpack_from("<H", data, chunk)[0]
    result = []
    for k in range(count):
        record = chunk + _u32(data, chunk + 4 + 4 * k)
        end = data.index(b"\0", record + 4)
        result.append((record, _u32(data, record), data[record + 4 : end]))
    return result


def find_menu_version(data: bytes) -> tuple[int, int, bytes]:
    """(entry of its chunk, index in the chunk, text) of the main menu's version line, labelled or not."""
    table = _tables(data).get(STRINGS)
    if table is None:
        raise FormatError("no string tables")
    for k in range(_u32(data, table)):
        entry = table + 8 + ENTRY_SIZE * k
        if data[entry : entry + 4] != MENU_TABLE:
            continue
        for index, (_, id_, text) in enumerate(_strings(data, _u32(data, entry + 20))):
            if id_ == MENU_ID and text.endswith(MENU_VERSION):
                return entry, index, text
    raise FormatError("no main menu version line")


def set_menu_version(data: bytes, text: bytes) -> bytes:
    """The archive with the main menu's version line set to `text`."""
    entry, index, old = find_menu_version(data)
    grow = len(text) - len(old)
    chunk, size = _u32(data, entry + 20), _u32(data, entry + 24)
    records = _strings(data, chunk)
    start = records[index][0] + 4

    out = bytearray(data[:start] + text + data[start + len(old) :])
    for later in range(index + 1, len(records)):  # the strings after it in its chunk
        at = chunk + 4 + 4 * later
        struct.pack_into("<I", out, at, _u32(out, at) + grow)
    struct.pack_into("<I", out, entry + 24, size + grow)
    for other in _entries(data):  # every chunk after it
        if _u32(data, other + 20) > chunk:
            struct.pack_into("<I", out, other + 20, _u32(data, other + 20) + grow)
    return bytes(out)


def label(data: bytes, version: str) -> bytes:
    """The archive with the mod's name and version in front of the game's version line."""
    text = MENU_LABEL.format(version=version, original=MENU_VERSION.decode("ascii"))
    return set_menu_version(data, text.encode("ascii"))


def unlabel(data: bytes) -> bytes:
    """The archive with the game's own version line back."""
    return set_menu_version(data, MENU_VERSION)


def _set_box(data: bytes, old: tuple[int, ...], new: tuple[int, ...]) -> bytes:
    at = data.find(BOX + struct.pack("<4i", *old))
    if at < 0:
        return data
    return data[: at + len(BOX)] + struct.pack("<4i", *new) + data[at + len(BOX) + 16 :]


def widen_version_box(data: bytes) -> bytes:
    """A text archive or a `UIData` layout with the version line's box wide enough for the label. Unchanged if the file
    has no main menu or the box is wide already."""
    return _set_box(data, VERSION_BOX, WIDE_VERSION_BOX)


def narrow_version_box(data: bytes) -> bytes:
    """The game's own box back."""
    return _set_box(data, WIDE_VERSION_BOX, VERSION_BOX)

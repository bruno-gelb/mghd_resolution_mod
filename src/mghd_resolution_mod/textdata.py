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


# The loading screen (issue #1, see loading_wait.py) is the screen layout `AP50` in each text archive, with its own
# string table of the same name. A layout is a header and elements, each 6 words (a kind, 2, x, y, w, h, in the
# game's 800x600 coordinates) and then key/value pairs up to a -1 key. Key 7 is the element's text, as an ID in the
# screen's string table; 6 is the element's ID, which the exe uses to fill it in (8885, the quest's name); 18 is its
# font. Keys 36 and 49 are followed by a count and that many values (colors).
LOADING_SCREEN = b"AP50"
SCREENS = b"SMNU"
COUNTED_KEYS = {36, 49}
QUEST_NAME_ID = 8885
HINT = b"Press any key to continue"
HINT_ID = 8886
# Under the progress bar (81, 556, 647x20), centered in the strip above the frame's bottom edge, short of the bar's
# right cap (723, 549, 18x36). The expansion has its logo between the art and the bar, so there's no room there.
HINT_RECT = (81, 576, 640, 21)
HINT_FONT = struct.unpack("<i", b"fnt4")[0]  # the small font, as in the main menu's version line


def _chunk_entry(data: bytes, section: bytes, tag: bytes) -> int | None:
    table = _tables(data).get(section)
    if table is None:
        return None
    for k in range(_u32(data, table)):
        entry = table + 8 + ENTRY_SIZE * k
        if data[entry : entry + 4] == tag:
            return entry
    return None


def _replace_chunk(data: bytes, entry: int, new: bytes) -> bytes:
    """The archive with the chunk of this table entry replaced, the later chunks moved."""
    start, size = _u32(data, entry + 20), _u32(data, entry + 24)
    out = bytearray(data[:start] + new + data[start + size :])
    struct.pack_into("<I", out, entry + 24, len(new))
    for other in _entries(data):
        if _u32(data, other + 20) > start:
            struct.pack_into("<I", out, other + 20, _u32(data, other + 20) + len(new) - size)
    return bytes(out)


def parse_layout(chunk: bytes) -> tuple[list[int], list[list[int]]]:
    """A screen layout's header and elements, each as its words up to and including its -1."""
    w = list(struct.unpack_from(f"<{len(chunk) // 4}i", chunk))

    def record(i: int) -> tuple[list[int], int]:
        j = i + 6
        while w[j] != -1:
            j += 2 + w[j + 1] if w[j] in COUNTED_KEYS else 2
        return w[i : j + 1], j + 1

    try:
        header, i = record(0)
        elements = []
        while w[i] != -1:
            element, i = record(i)
            elements.append(element)
    except IndexError:
        raise FormatError("a screen layout isn't closed") from None
    if i != len(w) - 1:
        raise FormatError("a screen layout has words after its end")
    return header, elements


def layout_props(element: list[int]) -> list[tuple[int, int | list[int]]]:
    out, k = [], 6
    while element[k] != -1:
        if element[k] in COUNTED_KEYS:
            out.append((element[k], element[k + 2 : k + 2 + element[k + 1]]))
            k += 2 + element[k + 1]
        else:
            out.append((element[k], element[k + 1]))
            k += 2
    return out


def build_layout(header: list[int], elements: list[list[int]]) -> bytes:
    words = header + [x for e in elements for x in e] + [-1]
    return struct.pack(f"<{len(words)}i", *words)


def add_loading_hint(data: bytes) -> bytes:
    """The archive with "Press any key to continue" on the loading screen: a string in its table, and a text element
    like the quest name's, in the small font, under the progress bar. Unchanged if it's there already or the archive
    has no loading screen."""
    strings_entry = _chunk_entry(data, STRINGS, LOADING_SCREEN)
    screen_entry = _chunk_entry(data, SCREENS, LOADING_SCREEN)
    if strings_entry is None or screen_entry is None:
        return data
    chunk = _u32(data, strings_entry + 20)
    records = _strings(data, chunk)
    if any(text == HINT for _, _, text in records):
        return data
    count, flags = struct.unpack_from("<HH", data, chunk)
    size = _u32(data, strings_entry + 24)
    offsets = [_u32(data, chunk + 4 + 4 * k) for k in range(count)]
    body = data[chunk + 4 + 4 * count : chunk + size]
    hint_string = max(id_ for _, id_, _ in records) + 1
    table = (struct.pack("<HH", count + 1, flags) + b"".join(struct.pack("<I", o + 4) for o in offsets)
             + struct.pack("<I", 4 + 4 * (count + 1) + len(body)) + body
             + struct.pack("<I", hint_string) + HINT + b"\0")
    data = _replace_chunk(data, strings_entry, table)

    screen_entry = _chunk_entry(data, SCREENS, LOADING_SCREEN)
    start, size = _u32(data, screen_entry + 20), _u32(data, screen_entry + 24)
    header, elements = parse_layout(data[start : start + size])
    name = next((e for e in elements if dict(layout_props(e)).get(6) == QUEST_NAME_ID), None)
    if name is None:
        raise FormatError("the loading screen has no quest name")
    hint = [5, 2, *HINT_RECT]
    for key, value in layout_props(name):
        if key in (12, 13):  # its background picture
            continue
        value = {7: hint_string, 6: HINT_ID, 18: HINT_FONT}.get(key, value)
        hint += [key, len(value), *value] if key in COUNTED_KEYS else [key, value]
    return _replace_chunk(data, screen_entry, build_layout(header, [*elements, [*hint, -1]]))

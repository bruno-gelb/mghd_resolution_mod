"""Steam's launch options for the game, in each Steam account's `userdata/<account>/config/localconfig.vdf`.

The file is Valve's text KeyValues format: quoted keys and values (`\\"` and `\\\\` escaped), `{ }` blocks, tabs.
The game's options are at UserLocalConfigStore / Software / Valve / Steam / apps / 73230 / LaunchOptions. Steam keeps
the file in memory while it runs and writes it back when it quits, so it's changed only while Steam is closed.

Only that one value is touched: the rest of the file stays byte for byte as it was.
"""

import re
from dataclasses import dataclass
from pathlib import Path

PATH = ["UserLocalConfigStore", "Software", "Valve", "Steam", "apps"]
KEY = "LaunchOptions"
PROCESS_NAMES = {"steam", "steamwebhelper"}


class VdfError(ValueError):
    pass


@dataclass
class Token:
    kind: str  # "str", "{" or "}"
    value: str
    start: int
    end: int


TOKEN = re.compile(r'\s+|//[^\n]*|"((?:\\.|[^"\\])*)"|([{}])|([^\s{}"]+)')


def unescape(raw: str) -> str:
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m[1], m[1]), raw)


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def tokens(text: str) -> list[Token]:
    found, at = [], 0
    while at < len(text):
        m = TOKEN.match(text, at)
        if not m:
            raise VdfError(f"unexpected {text[at:at + 20]!r} at {at}")
        if m[1] is not None:
            found.append(Token("str", unescape(m[1]), m.start(), m.end()))
        elif m[2]:
            found.append(Token(m[2], m[2], m.start(), m.end()))
        elif m[3]:
            found.append(Token("str", m[3], m.start(), m.end()))
        at = m.end()
    return found


def _block_end(toks: list[Token], open_at: int) -> int:
    """The index of the `}` closing the `{` at open_at."""
    depth = 0
    for i in range(open_at, len(toks)):
        if toks[i].kind == "{":
            depth += 1
        elif toks[i].kind == "}":
            depth -= 1
            if depth == 0:
                return i
    raise VdfError("a block isn't closed")


def _children(toks: list[Token], open_at: int):
    """(key index, value index) of each entry in the block opened at open_at; a block's value index is its `{`."""
    i, end = open_at + 1, _block_end(toks, open_at)
    while i < end:
        if toks[i].kind != "str" or i + 1 >= end:
            raise VdfError(f"expected a key at {toks[i].start}")
        yield i, i + 1
        i = _block_end(toks, i + 1) + 1 if toks[i + 1].kind == "{" else i + 2


def _find(toks: list[Token], open_at: int, key: str, block: bool) -> int | None:
    for k, v in _children(toks, open_at):
        if toks[k].value.lower() == key.lower() and (toks[v].kind == "{") == block:
            return v
    return None


def _root(toks: list[Token]) -> int:
    if len(toks) < 2 or toks[0].kind != "str" or toks[1].kind != "{":
        raise VdfError("not a KeyValues file")
    if toks[0].value != PATH[0]:
        raise VdfError(f"starts with {toks[0].value!r}, not {PATH[0]!r}")
    return 1


def _line_indent(text: str, at: int) -> str:
    line_start = text.rfind("\n", 0, at) + 1
    return re.match(r"[ \t]*", text[line_start:at])[0]


def get_options(text: str, app_id: str) -> str | None:
    """The game's launch options, or None when it has none set (no entry)."""
    toks = tokens(text)
    block = _root(toks)
    for key in [*PATH[1:], app_id]:
        block = _find(toks, block, key, block=True)
        if block is None:
            return None
    value = _find(toks, block, KEY, block=False)
    return None if value is None else toks[value].value


def set_options(text: str, app_id: str, value: str) -> str:
    """The file's text with the game's launch options set to value, adding the game's entry if needed."""
    toks = tokens(text)
    block = _root(toks)
    for key in PATH[1:]:
        block = _find(toks, block, key, block=True)
        if block is None:
            raise VdfError(f"no {key!r} section: start Steam once, then run this again")
    app = _find(toks, block, app_id, block=True)
    quoted = f'"{escape(value)}"'
    if app is None:  # a new entry at the end of apps, indented like Steam does
        close = toks[_block_end(toks, block)]
        indent = _line_indent(text, close.start) + "\t"
        line_start = text.rfind("\n", 0, close.start) + 1
        entry = f'{indent}"{app_id}"\n{indent}{{\n{indent}\t"{KEY}"\t\t{quoted}\n{indent}}}\n'
        result = text[:line_start] + entry + text[line_start:]
    else:
        current = _find(toks, app, KEY, block=False)
        if current is not None:
            t = toks[current]
            result = text[:t.start] + quoted + text[t.end:]
        else:
            close = toks[_block_end(toks, app)]
            indent = _line_indent(text, close.start) + "\t"
            line_start = text.rfind("\n", 0, close.start) + 1
            result = text[:line_start] + f'{indent}"{KEY}"\t\t{quoted}\n' + text[line_start:]
    if get_options(result, app_id) != value:
        raise VdfError("the launch options didn't read back as written")
    return result


def config_files(roots: list[Path]) -> list[Path]:
    """Each Steam account's localconfig.vdf under these Steam folders, once each."""
    seen, found = set(), []
    for root in roots:
        for path in sorted(root.glob("userdata/*/config/localconfig.vdf")):
            try:
                key = path.resolve()
            except OSError:
                continue
            if key not in seen and path.is_file():
                seen.add(key)
                found.append(key)
    return found


def read(path: Path, app_id: str) -> str | None:
    return get_options(path.read_text(encoding="utf-8", errors="surrogateescape"), app_id)


def write(path: Path, app_id: str, value: str) -> None:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    new = set_options(text, app_id, value)
    tmp = path.with_name(path.name + ".mghd-tmp")
    tmp.write_text(new, encoding="utf-8", errors="surrogateescape")
    tmp.replace(path)

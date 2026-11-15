"""The loading screen waits for a key or a click before a single-player game starts (issue #1).

On today's hardware a quest loads in a moment, and its loading screen, with the quest's art, flashes by. The patch
makes the game wait, after loading, until the player presses a key or clicks, with "Press any key to continue" on
the screen (textdata.add_loading_hint). Never in a multiplayer game: the other players would wait for one.

How the game loads a quest (see docs/findings.md, "Loading screens"): one loader function draws the loading screen's
progress bar in 8 steps, and four functions call it, one for each way into a game. Three are single-player starts
(a quest, a freestyle game, the expansion's); the fourth starts a network game. The patch points the three
single-player calls at a small routine in the free space at the end of the exe's code section: it calls the loader,
then waits. Two of those three also start network games when the player came from the multiplayer staging room
(screen `AP73`): the game tells by a global that holds the screen it came from, and so does the routine, which
doesn't wait then.

Everything is found by the code's structure, not by address, so Steam's 1.5.2.24 and GOG's 1.5.2.28 (whose code
is at other addresses) are patched the same way:

- the progress function, by its first instructions, and the loader, the only function that calls it many times;
- the loader's callers; the network game's start is the one called as a method (`mov ecx, <reg>` before the call);
- the "came from" global, stored right after the screen loop compares the screen with `AP73`;
- PeekMessageA, DispatchMessageA and Sleep in the exe's imports, and the code section's free space.

If anything isn't found exactly as expected, nothing is patched (PatchError).

The routine is WAIT_CODE, assembled from src/tools/loading_wait.s with placeholder addresses (see there); the
installer fills in each exe's own.
"""

import re
import struct
from dataclasses import dataclass

# src/tools/loading_wait.s, assembled with LOADER at the routine's own address and these placeholders.
WAIT_CODE = bytes.fromhex(
    "e8fbffffff813d44444444415037330f"
    "84c800000050535783ec1c89e36a0168"
    "0901000068000100006a0053ff151111"
    "111185c075e76a01680d020000680102"
    "00006a0053ff151111111185c075e731"
    "ff6a006a006a006a0053ff1511111111"
    "85c07466837b0412746d6a016a006a00"
    "6a0053ff151111111185c074d48b4304"
    "85ff75233d0001000074173d01020000"
    "74103d0402000074093d070200007402"
    "eb098d7801ebaa39f8742c8d8800ffff"
    "ff83f909769b8d8800feffff83f90d76"
    "9053ff1522222222eb876a0aff153333"
    "3333e97affffff83c41c5f5b58c3"
)
LOADER_REL = 1  # the routine's first instruction: call rel32 to the loader
FIXUPS = {"came_from": [7], "PeekMessageA": [46, 71, 92, 117], "DispatchMessageA": [196], "Sleep": [206]}
PLACEHOLDERS = {"came_from": 0x44444444, "PeekMessageA": 0x11111111, "DispatchMessageA": 0x22222222,
                "Sleep": 0x33333333}

PROGRESS = re.compile(rb"\xA1....\x83\xEC\x14\x85\xC0", re.S)  # mov eax, [screen]; sub esp, 0x14; test eax, eax
CAME_FROM = re.compile(rb"\x3D\x41\x50\x37\x33\x0F\x85....\xA3(....)", re.S)  # cmp eax, 'AP73'; jne; mov [g], eax
MIN_PROGRESS_CALLS = 6


class PatchError(Exception):
    """This exe isn't one the patch knows how to change."""


@dataclass
class Section:
    name: bytes
    header: int  # file offset of its section header
    rva: int
    vsize: int
    raw: int
    raw_size: int


@dataclass
class Pe:
    data: bytes
    base: int
    sections: list[Section]

    def section_of(self, rva: int) -> Section:
        for s in self.sections:
            if s.rva <= rva < s.rva + max(s.vsize, s.raw_size):
                return s
        raise PatchError(f"address {rva:#x} is in no section")

    def off(self, rva: int) -> int:
        s = self.section_of(rva)
        return s.raw + rva - s.rva

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.data, off)[0]


def read_pe(data: bytes) -> Pe:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise PatchError("not a Windows program")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", data, pe + 24)[0] != 0x10B:
        raise PatchError("not a 32-bit Windows program")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    first = pe + 24 + struct.unpack_from("<H", data, pe + 20)[0]
    sections = []
    for k in range(count):
        h = first + 40 * k
        vsize, rva, raw_size, raw = struct.unpack_from("<IIII", data, h + 8)
        sections.append(Section(data[h:h + 8].rstrip(b"\0"), h, rva, vsize, raw, raw_size))
    return Pe(data, struct.unpack_from("<I", data, pe + 24 + 28)[0], sections)


def imports(pe: Pe) -> dict[str, int]:
    """Imported function name -> the address of its slot in the import address table."""
    opt = struct.unpack_from("<I", pe.data, 0x3C)[0] + 24
    table_rva = pe.u32(opt + 96 + 8)  # data directory 1: the import table
    found, d = {}, pe.off(table_rva)
    while pe.u32(d + 12):  # Name
        names_rva, slots_rva = pe.u32(d) or pe.u32(d + 16), pe.u32(d + 16)
        k = 0
        while thunk := pe.u32(pe.off(names_rva) + 4 * k):
            if not thunk & 0x80000000:  # by name, not by ordinal
                o = pe.off(thunk) + 2
                name = pe.data[o:pe.data.index(b"\0", o)].decode("latin1")
                found[name] = pe.base + slots_rva + 4 * k
            k += 1
        d += 20
    return found


@dataclass
class Code:
    """The code section and its direct calls."""
    pe: Pe
    text: Section
    calls: dict[int, list[int]]  # target address -> addresses of `call rel32` to it

    @property
    def start(self) -> int:
        return self.pe.base + self.text.rva

    def bytes_at(self, va: int, n: int) -> bytes:
        o = self.text.raw + va - self.start
        return self.pe.data[o:o + n]

    def function_start(self, va: int) -> int:
        """The start of the function around va: just after the int3 padding the compiler puts between functions."""
        o = self.text.raw + va - self.start
        for back in range(0, 0x8000):
            if self.pe.data[o - back - 1] == 0xCC and self.pe.data[o - back - 2] == 0xCC:
                return va - back
        raise PatchError(f"no function start before {va:#x}")


def read_code(pe: Pe) -> Code:
    text = next((s for s in pe.sections if s.name == b".text"), None)
    if text is None:
        raise PatchError("no code section")
    seg = pe.data[text.raw:text.raw + min(text.vsize, text.raw_size)]
    start = pe.base + text.rva
    calls: dict[int, list[int]] = {}
    for m in re.finditer(b"\xE8", seg):
        i = m.start()
        if i + 5 <= len(seg):
            target = start + i + 5 + struct.unpack_from("<i", seg, i + 1)[0]
            calls.setdefault(target, []).append(start + i)
    return Code(pe, text, calls)


@dataclass
class Plan:
    loader: int
    sites: list[int]  # the single-player starts' calls to the loader
    network_start: int
    came_from: int
    imports: dict[str, int]
    cave: int  # where the routine goes


def find(data: bytes) -> Plan:
    """Where everything is in this exe, or PatchError."""
    try:
        return _find(data)
    except (struct.error, IndexError, ValueError, KeyError) as error:  # a damaged or foreign file
        raise PatchError(f"the exe can't be read ({error})") from error


def _find(data: bytes) -> Plan:
    if is_patched(data):
        raise PatchError("it has the wait already")
    pe = read_pe(data)
    code = read_code(pe)
    seg = pe.data[code.text.raw:code.text.raw + code.text.vsize]
    progress = [code.start + m.start() for m in PROGRESS.finditer(seg)]
    progress = [p for p in progress if len(code.calls.get(p, [])) >= MIN_PROGRESS_CALLS]
    if len(progress) != 1:
        raise PatchError(f"{len(progress)} candidates for the loading screen's progress function")
    loaders = {code.function_start(c) for c in code.calls[progress[0]]}
    if len(loaders) != 1:
        raise PatchError("the progress bar is drawn from more than one function")
    loader = loaders.pop()
    starts = {}
    for site in code.calls.get(loader, []):
        starts.setdefault(code.function_start(site), []).append(site)
    if len(starts) < 2:
        raise PatchError("fewer ways into a game than expected")

    def is_method(f: int) -> bool:  # called with `mov ecx, <register>` right before
        return any(code.bytes_at(c - 2, 1) == b"\x8B" and code.bytes_at(c - 1, 1)[0] & 0xF8 == 0xC8
                   for c in code.calls.get(f, []))

    network = [f for f in starts if is_method(f)]
    if len(network) != 1:
        raise PatchError(f"{len(network)} candidates for the network game's start")
    sites = sorted(s for f, ss in starts.items() if f != network[0] for s in ss)
    found = CAME_FROM.findall(seg)
    if len(found) != 1:
        raise PatchError(f"{len(found)} candidates for the screen the player came from")
    names = imports(pe)
    missing = [n for n in FIXUPS if n != "came_from" and n not in names]
    if missing:
        raise PatchError(f"the exe doesn't import {', '.join(missing)}")
    cave_rva = (code.text.rva + code.text.vsize + 15) & ~15
    free = code.text.rva + code.text.raw_size - cave_rva
    if free < len(WAIT_CODE):
        raise PatchError(f"{free} bytes free in the code section, {len(WAIT_CODE)} needed")
    if any(pe.data[pe.off(cave_rva):pe.off(cave_rva) + len(WAIT_CODE)]):
        raise PatchError("the code section's free space isn't empty")
    return Plan(loader, sites, network[0], struct.unpack("<I", found[0])[0], names, pe.base + cave_rva)


def patch(data: bytes) -> bytes:
    """The game's own exe with the wait added. Raises PatchError for an exe it doesn't know."""
    plan = find(data)
    pe = read_pe(data)
    text = next(s for s in pe.sections if s.name == b".text")
    routine = bytearray(WAIT_CODE)
    struct.pack_into("<i", routine, LOADER_REL, plan.loader - (plan.cave + 5))
    values = {"came_from": plan.came_from, **{n: plan.imports[n] for n in FIXUPS if n != "came_from"}}
    for name, offsets in FIXUPS.items():
        for o in offsets:
            assert struct.unpack_from("<I", routine, o)[0] == PLACEHOLDERS[name]
            struct.pack_into("<I", routine, o, values[name])
    out = bytearray(data)
    cave_off = pe.off(plan.cave - pe.base)
    out[cave_off:cave_off + len(routine)] = routine
    for site in plan.sites:
        struct.pack_into("<i", out, pe.off(site - pe.base) + 1, plan.cave - (site + 5))
    # The code section's size in memory covers the routine (its size in the file already does).
    struct.pack_into("<I", out, text.header + 8, plan.cave - pe.base + len(routine) - text.rva)
    return bytes(out)


def is_patched(data: bytes) -> bool:
    """Whether this exe has the wait: its code section reaches past where the game's own code ends, into the
    routine. A game update or a file check puts the original back."""
    try:
        pe = read_pe(data)
    except PatchError:
        return False
    text = next((s for s in pe.sections if s.name == b".text"), None)
    if text is None or text.vsize < len(WAIT_CODE):
        return False
    end = text.raw + text.vsize
    tail = data[end - len(WAIT_CODE):end]
    filled = {o + k for o in [LOADER_REL, *(o for offsets in FIXUPS.values() for o in offsets)] for k in range(4)}
    return len(tail) == len(WAIT_CODE) and all(tail[i] == WAIT_CODE[i] for i in range(len(WAIT_CODE))
                                               if i not in filled)

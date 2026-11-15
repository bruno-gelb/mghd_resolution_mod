"""The loading screen's wait, on a synthetic exe with the structure the patch looks for: a progress function, a loader
that calls it 8 times, three single-player starts and a network start (called as a method) that call the loader, the
screen loop's `cmp eax, 'AP73'` and store, and an import table with PeekMessageA, DispatchMessageA and Sleep."""

import struct

import pytest

from mghd_resolution_mod import loading_wait as lw

BASE, TEXT_RVA, TEXT_RAW, IDATA_RVA = 0x400000, 0x1000, 0x400, 0x3000
FILE_ALIGNMENT = 0x200
CAME_FROM = 0x7B55E4


class Asm:
    """Functions laid out like a compiler does: int3 padding between them."""

    def __init__(self):
        self.code = bytearray(b"\xCC" * 16)
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def va(self, at: int) -> int:
        return BASE + TEXT_RVA + at

    def function(self, name: str, *parts):
        self.labels[name] = len(self.code)
        for part in parts:
            if isinstance(part, tuple):  # ("call", target)
                self.code += b"\xE8\0\0\0\0"
                self.fixups.append((len(self.code) - 4, part[1]))
            else:
                self.code += part
        self.code += b"\xC3" + b"\xCC" * 16

    def build(self) -> bytes:
        for at, name in self.fixups:
            struct.pack_into("<i", self.code, at, self.labels[name] - (at + 4))
        return bytes(self.code)


def program(network_as_method=True, extra_progress=False) -> tuple[bytes, Asm]:
    a = Asm()
    a.function("progress", b"\xA1\x08\x17\x7C\x00\x83\xEC\x14\x85\xC0")
    a.function("loader", *[("call", "progress")] * 8)
    for name in ("quest", "freestyle", "expansion", "network"):
        a.function(name, b"\x8B\xCE", ("call", "loader"))  # mov ecx, esi; call loader
    a.function("screens",
               ("call", "quest"),
               b"\x6A\x00", ("call", "freestyle"),           # push 0
               b"\x52", ("call", "expansion"),               # push edx
               b"\x8B\xC8" if network_as_method else b"\x50", ("call", "network"),  # mov ecx, eax
               b"\x3D\x41\x50\x37\x33\x0F\x85\0\0\0\0\xA3" + struct.pack("<I", CAME_FROM))
    if extra_progress:
        a.function("progress2", b"\xA1\x08\x17\x7C\x00\x83\xEC\x14\x85\xC0")
        a.function("loader2", *[("call", "progress2")] * 8)
    code = a.build()
    # Like a linker: the section's size in the file is its code's, rounded up to the file alignment. Pad the code so
    # the free space left is a little more than the routine needs, as in the game's exes.
    free = len(lw.WAIT_CODE) + 40
    code += b"\xCC" * ((-(len(code) + free)) % FILE_ALIGNMENT)
    return pe(code, len(code) + free), a


def pe(code: bytes, text_size: int) -> bytes:
    """A 32-bit PE with .text (the code, then free space) and .idata (the imports)."""
    idata = bytearray(0x200)
    names = {"USER32.dll": ["PeekMessageA", "DispatchMessageA"], "KERNEL32.dll": ["Sleep"]}
    descriptors, pos = [], 0x60
    for dll, funcs in names.items():
        lookup = pos
        pos += 4 * (len(funcs) + 1)
        slots = pos
        pos += 4 * (len(funcs) + 1)
        for k, f in enumerate(funcs):
            struct.pack_into("<I", idata, lookup + 4 * k, IDATA_RVA + pos)
            struct.pack_into("<I", idata, slots + 4 * k, IDATA_RVA + pos)
            idata[pos + 2:pos + 2 + len(f)] = f.encode()
            pos += 2 + len(f) + 1
        dll_at = pos
        idata[pos:pos + len(dll)] = dll.encode()
        pos += len(dll) + 1
        descriptors.append((IDATA_RVA + lookup, IDATA_RVA + dll_at, IDATA_RVA + slots))
    for k, (lookup, dll, slots) in enumerate(descriptors):
        struct.pack_into("<IIIII", idata, 20 * k, lookup, 0, 0, dll, slots)

    head = bytearray(TEXT_RAW)
    head[:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", head, 0x84, 0x14C, 2)          # i386, 2 sections
    struct.pack_into("<H", head, 0x94, 0xE0)               # optional header size
    opt = 0x98
    struct.pack_into("<H", head, opt, 0x10B)
    struct.pack_into("<I", head, opt + 28, BASE)
    struct.pack_into("<II", head, opt + 32, 0x1000, FILE_ALIGNMENT)
    struct.pack_into("<I", head, opt + 92, 16)
    struct.pack_into("<II", head, opt + 96 + 8, IDATA_RVA, 20 * (len(descriptors) + 1))
    sections = opt + 0xE0
    idata_raw = TEXT_RAW + text_size
    struct.pack_into("<8sIIII", head, sections, b".text", len(code), TEXT_RVA, text_size, TEXT_RAW)
    struct.pack_into("<8sIIII", head, sections + 40, b".idata", len(idata), IDATA_RVA, len(idata), idata_raw)
    text = code + bytes(text_size - len(code))
    return bytes(head) + text + bytes(idata)


def calls_to(data: bytes, a: Asm, name: str) -> int:
    """Where the call in function `name` goes."""
    at = a.labels[name] + 2 + 1
    return a.va(at + 4) + struct.unpack_from("<i", data, TEXT_RAW + at)[0]


def test_finds_everything():
    data, a = program()
    plan = lw.find(data)
    assert plan.loader == a.va(a.labels["loader"])
    assert plan.network_start == a.va(a.labels["network"])
    assert plan.sites == sorted(a.va(a.labels[n] + 2) for n in ("quest", "freestyle", "expansion"))
    assert plan.came_from == CAME_FROM
    assert set(lw.FIXUPS) - {"came_from"} <= set(plan.imports)
    assert plan.cave % 16 == 0 and plan.cave >= BASE + TEXT_RVA + len(a.build())


def test_the_single_player_starts_go_through_the_wait_and_the_network_start_doesnt():
    data, a = program()
    plan = lw.find(data)
    patched = lw.patch(data)
    for name in ("quest", "freestyle", "expansion"):
        assert calls_to(patched, a, name) == plan.cave
    assert calls_to(patched, a, "network") == plan.loader
    cave = TEXT_RAW + plan.cave - BASE - TEXT_RVA
    routine = patched[cave:cave + len(lw.WAIT_CODE)]
    assert plan.cave + 5 + struct.unpack_from("<i", routine, 1)[0] == plan.loader
    assert struct.unpack_from("<I", routine, 7)[0] == CAME_FROM
    assert struct.unpack_from("<I", routine, 46)[0] == plan.imports["PeekMessageA"]
    assert struct.unpack_from("<I", routine, 196)[0] == plan.imports["DispatchMessageA"]
    assert struct.unpack_from("<I", routine, 206)[0] == plan.imports["Sleep"]
    assert lw.is_patched(patched) and not lw.is_patched(data)
    assert lw.read_pe(patched).sections[0].vsize == plan.cave - BASE - TEXT_RVA + len(lw.WAIT_CODE)


def test_unknown_programs_are_left_alone():
    with pytest.raises(lw.PatchError):
        lw.patch(b"MZ fake exe")
    with pytest.raises(lw.PatchError, match="network"):
        lw.patch(program(network_as_method=False)[0])
    with pytest.raises(lw.PatchError, match="progress"):
        lw.patch(program(extra_progress=True)[0])
    data, a = program()
    with pytest.raises(lw.PatchError):
        lw.patch(lw.patch(data))  # the free space is taken already


def test_the_routine_matches_its_source():
    capstone = pytest.importorskip("capstone")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    code = list(md.disasm(lw.WAIT_CODE, 0x10000000))
    assert sum(i.size for i in code) == len(lw.WAIT_CODE)
    text = [f"{i.mnemonic} {i.op_str}" for i in code]
    assert text[0] == "call 0x10000000" and text[-1].strip() == "ret"
    assert "cmp dword ptr [0x44444444], 0x33375041" in text
    assert text.count("call dword ptr [0x11111111]") == 4


def rounded_up(patched: bytes) -> bytes:
    """The patch with the code section's size in memory rounded up past the routine, as the first test patch had."""
    out = bytearray(patched)
    text = lw.read_pe(patched).sections[0]
    struct.pack_into("<I", out, text.header + 8, text.raw_size)
    return bytes(out)


def test_a_patch_is_recognized_wherever_the_section_size_ends():
    data, _ = program()
    rounded = rounded_up(lw.patch(data))
    assert lw.is_patched(rounded)
    with pytest.raises(lw.PatchError, match="already"):
        lw.patch(rounded)

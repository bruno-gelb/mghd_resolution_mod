import struct

import pytest

from mghd_resolution_mod import textdata
from conftest import make_layout, make_textdata, menu_layout


def chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    return [(data[e:e + 4], data[textdata._u32(data, e + 20):][:textdata._u32(data, e + 24)])
            for e in textdata._entries(data)]


def test_label_puts_the_mod_in_front_of_the_menu_line():
    data = make_textdata()
    labelled = textdata.label(data, "1.2.3")
    assert textdata.find_menu_version(labelled)[2] == b"mghd-resolution-mod 1.2.3, game Version %s"
    assert len(labelled) == len(data) + len(b"mghd-resolution-mod 1.2.3, game ")


def test_label_keeps_every_other_string_and_chunk():
    data = make_textdata()
    before, after = chunks(data), chunks(textdata.label(data, "0.1.0"))
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert [before[i][0] for i in changed] == [b"GMTX"]
    strings = textdata._strings(textdata.label(data, "0.1.0"), textdata._u32(
        textdata.label(data, "0.1.0"), textdata.find_menu_version(textdata.label(data, "0.1.0"))[0] + 20))
    assert [s[1] for s in strings] == list(range(0x50, 0x58))
    assert strings[-1][2] == b"string 87"


def test_unlabel_gives_back_the_original_byte_for_byte():
    data = make_textdata()
    assert textdata.unlabel(textdata.label(data, "0.1.0")) == data


def test_label_replaces_an_older_label():
    data = make_textdata()
    assert textdata.label(textdata.label(data, "0.1.0"), "0.2.0") == textdata.label(data, "0.2.0")


def test_the_main_menus_own_placeholder_stays():
    assert b"Version #" in textdata.label(make_textdata(), "0.1.0")


def test_not_an_archive():
    with pytest.raises(textdata.FormatError):
        textdata.label(b"not a cam file" * 4, "0.1.0")


def test_no_menu_line():
    data = make_textdata().replace(textdata.MENU_VERSION, b"Versiom %s")
    with pytest.raises(textdata.FormatError):
        textdata.find_menu_version(data)


@pytest.mark.parametrize("data", [make_textdata(), make_layout((1920, 1200))])
def test_widen_and_narrow_the_box(data):
    wide = textdata.widen_version_box(data)
    assert struct.pack("<4i", *textdata.WIDE_VERSION_BOX) in wide
    assert textdata.widen_version_box(wide) == wide
    assert textdata.narrow_version_box(wide) == data
    assert len(wide) == len(data)


def test_the_box_keeps_its_center():
    x, _, w, _ = textdata.VERSION_BOX
    wx, _, ww, _ = textdata.WIDE_VERSION_BOX
    assert abs((x + w / 2) - (wx + ww / 2)) <= 1


def test_no_box_at_800x600():
    data = make_layout((800, 600))
    assert textdata.widen_version_box(data) == data


def test_find_chunk():
    data = make_textdata()
    offset, size = textdata.find_chunk(data, b"SMNU", b"AP29")
    assert data[offset:offset + size] == menu_layout()
    assert textdata.find_chunk(data, b"SMNU", b"APMK") is None
    assert textdata.find_chunk(data, b"XXXX", b"AP29") is None
    assert textdata.find_chunk(b"not an archive", b"SMNU", b"AP29") is None

import json

import pytest

from mghd_resolution_mod import game, install, layouts, textdata
from conftest import make_textdata, snapshot

SIZES = [(2560, 1080), (3440, 1440)]


def test_install_adds_layouts_and_the_label(game_dir):
    install.install(game_dir, SIZES, log=lambda _: None)
    for size in SIZES:
        assert (game_dir / game.DATA / layouts.file_name(size)).is_file()
    text = (game_dir / game.DATA / "textdata.cam").read_bytes()
    assert textdata.find_menu_version(text)[2].startswith(b"mghd-resolution-mod ")
    assert textdata.widen_version_box(text) == text != textdata.narrow_version_box(text)
    layout = (game_dir / game.DATA / "UIData_1920_1080.dat").read_bytes()
    assert textdata.narrow_version_box(layout) != layout
    state = install.status(game_dir)
    assert state.installed and not state.reverted and len(state.added) == 2


def test_uninstall_puts_everything_back(game_dir):
    before = snapshot(game_dir)
    install.install(game_dir, SIZES, log=lambda _: None)
    install.uninstall(game_dir, log=lambda _: None)
    assert snapshot(game_dir) == before


def test_install_twice_is_the_same(game_dir):
    install.install(game_dir, SIZES, log=lambda _: None)
    once = snapshot(game_dir)
    install.install(game_dir, SIZES, log=lambda _: None)
    assert snapshot(game_dir) == once


def test_install_again_keeps_added_sizes(game_dir):
    install.install(game_dir, SIZES, log=lambda _: None)
    install.install(game_dir, [(1720, 720)], log=lambda _: None)
    assert len(install.status(game_dir).added) == 3


def test_a_steam_update_is_noticed_and_backed_up(game_dir):
    before = snapshot(game_dir)
    install.install(game_dir, SIZES, log=lambda _: None)
    updated = make_textdata(b" patched")  # Steam puts back a newer original
    (game_dir / game.DATA / "textdata.cam").write_bytes(updated)
    assert install.status(game_dir).reverted
    install.install(game_dir, SIZES, log=lambda _: None)
    assert not install.status(game_dir).reverted
    install.uninstall(game_dir, log=lambda _: None)
    assert (game_dir / game.DATA / "textdata.cam").read_bytes() == updated
    before["Data/textdata.cam"] = updated
    assert snapshot(game_dir) == before


def test_a_layout_the_mod_didnt_make_is_left_alone(game_dir):
    mine = game_dir / game.DATA / "UIData_2560_1080.dat"
    mine.write_bytes(b"someone else's")
    install.install(game_dir, SIZES, log=lambda _: None)
    assert mine.read_bytes() == b"someone else's"
    install.uninstall(game_dir, log=lambda _: None)
    assert mine.read_bytes() == b"someone else's"


def test_files_changed_by_something_else(game_dir):
    path = game_dir / game.DATA / "textdata.cam"
    path.write_bytes(textdata.label(path.read_bytes(), "9.9.9"))
    with pytest.raises(install.InstallError, match="already changed"):
        install.install(game_dir, SIZES, log=lambda _: None)


def test_incomplete_game_folder(game_dir):
    (game_dir / game.DATA / "UIData_1920_1200.dat").unlink()
    with pytest.raises(install.InstallError, match="UIData_1920_1200.dat"):
        install.install(game_dir, SIZES, log=lambda _: None)


def test_game_running(game_dir, monkeypatch):
    monkeypatch.setattr(game, "running", lambda: True)
    with pytest.raises(install.InstallError, match="running"):
        install.install(game_dir, SIZES, log=lambda _: None)


def test_uninstall_when_not_installed(game_dir):
    with pytest.raises(install.InstallError, match="isn't installed"):
        install.uninstall(game_dir, log=lambda _: None)


def test_damaged_manifest(game_dir):
    install.install(game_dir, SIZES, log=lambda _: None)
    (game_dir / install.BACKUP_DIR / "manifest.json").write_text(json.dumps({"changed": []}))
    with pytest.raises(install.InstallError, match="damaged"):
        install.status(game_dir)

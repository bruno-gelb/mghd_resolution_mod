import pytest

from mghd_resolution_mod import display, launch, layouts

AVAILABLE = sorted(layouts.ORIGINAL_SIZES | set(layouts.COMMON_SIZES))
PREFS = """<?xml version="1.0"?>
<MajXPrefs><PixWidth>3440</PixWidth><PixHeight>1440</PixHeight><Windowed>1</Windowed><UseD3D>0</UseD3D>
<Other>7</Other></MajXPrefs>
"""
STATE = [7, [[["HDMI-1", "XMI", "Mi Monitor", "0"], [
    ["3440x1440@100.000", 3440, 1440, 100.0, 1.0, [1.0, 1.25, 1.3333333730697632, 2.0],
     {"is-current": {"type": "b", "data": True}}],
    ["2560x1080@60.000", 2560, 1080, 60.0, 1.0, [1.0], {}],
], {}]], [[0, 0, 1.3333333730697632, 0, True, [["HDMI-1", "XMI", "Mi Monitor", "0"]], {}]], {}]


@pytest.mark.parametrize("screen, render", [
    ((3440, 1440), (2560, 1080)), ((2560, 1440), (1920, 1080)), ((3840, 2160), (1920, 1080)),
    ((5120, 1440), (3840, 1080)), ((2560, 1600), (1920, 1200)), ((3840, 1600), (2560, 1080)),
    ((1920, 1080), None), ((1920, 1200), None), ((2560, 1080), None),
])
def test_render_size(screen, render):
    assert launch.pick_render(screen, AVAILABLE) == render


def test_render_size_needs_a_layout_of_the_same_shape():
    assert launch.pick_render((3440, 1440), sorted(layouts.ORIGINAL_SIZES)) is None


def test_settings_file(tmp_path):
    prefix = tmp_path / "73230"
    prefs = prefix / "pfx/drive_c/users/steamuser/Documents/My Games/MajestyHD/MajXPrefs"
    prefs.parent.mkdir(parents=True)
    prefs.write_text(PREFS)
    found = launch.find_prefs({"STEAM_COMPAT_DATA_PATH": str(prefix)})
    assert found == prefs
    launch.set_prefs(found, (2560, 1080))
    assert prefs.read_text() == (PREFS.replace("3440", "2560").replace("1440", "1080")
                                 .replace("<Windowed>1", "<Windowed>0").replace("<UseD3D>0", "<UseD3D>1"))
    assert launch.find_prefs({}) is None


def test_the_display_from_gnome():
    d = display.parse_state(STATE)
    assert d.size == (3440, 1440) and d.connector == "HDMI-1" and d.mode == "3440x1440@100.000"
    assert display.apply_args(d, 1, display.TEMPORARY) == [
        display.APPLY_SIGNATURE, "7", "1", "1", "0", "0", "1.0", "0", "true", "1", "HDMI-1", "3440x1440@100.000",
        "0", "0"]
    two = [STATE[0], STATE[1], STATE[2] * 2, {}]
    assert display.parse_state(two) is None


@pytest.fixture
def fake_run(game_dir, tmp_path, monkeypatch):
    """launch.run with GNOME, gamescope and the game faked; returns what happened."""
    happened = {"scales": [], "started": None}
    d = display.parse_state(STATE)
    monkeypatch.setattr(display, "current", lambda: d)
    monkeypatch.setattr(display, "set_scale", lambda _d, scale, method: happened["scales"].append((scale, method)))
    monkeypatch.setattr(launch.shutil, "which", lambda name: f"/usr/bin/{name}")
    for size in layouts.COMMON_SIZES:
        (game_dir / "Data" / layouts.file_name(size)).write_bytes(b"")
    prefix = tmp_path / "prefix"
    prefs = prefix / "pfx/drive_c/users/steamuser/Documents/My Games/MajestyHD/MajXPrefs"
    prefs.parent.mkdir(parents=True)
    prefs.write_text(PREFS)
    monkeypatch.setenv("STEAM_COMPAT_DATA_PATH", str(prefix))
    happened["prefs"] = prefs

    class Child:
        def __init__(self, command, env):
            happened["started"] = command
            self.code = happened.get("exit", 0)

        def wait(self):
            if happened.get("crash"):
                raise OSError("boom")
            return self.code

        def poll(self):
            return self.code

    monkeypatch.setattr(launch.subprocess, "Popen", Child)
    return happened


def test_run_scales_up_with_gamescope_at_100_percent(fake_run, game_dir):
    exe = str(game_dir / "MajestyHD.exe")
    code = launch.run(["proton", "waitforexitandrun", exe], log_dir=game_dir)
    assert code == 0
    assert fake_run["scales"] == [(1.0, display.TEMPORARY), (1.3333333730697632, display.PERSISTENT)]
    started = fake_run["started"]
    assert started[0] == "gamescope" and started[-4:] == ["--", "proton", "waitforexitandrun", exe]
    assert started[started.index("-w"):started.index("-w") + 4] == ["-w", "2560", "-h", "1080"]
    assert started[started.index("-W"):started.index("-W") + 4] == ["-W", "3440", "-H", "1440"]
    assert "<PixWidth>2560</PixWidth>" in fake_run["prefs"].read_text()
    assert "scaled up to 3440x1440" in (game_dir / launch.LOG).read_text()


def test_run_puts_the_scale_back_when_the_game_fails(fake_run, game_dir):
    fake_run["crash"] = True
    assert launch.run(["proton", str(game_dir / "MajestyHD.exe")], log_dir=game_dir) == 127
    assert fake_run["scales"][-1] == (1.3333333730697632, display.PERSISTENT)


def test_run_without_gamescope_leaves_the_game_as_it_is(fake_run, game_dir, monkeypatch):
    monkeypatch.setattr(launch.shutil, "which", lambda name: None)
    fake_run["exit"] = 3
    exe = str(game_dir / "MajestyHD.exe")
    assert launch.run(["proton", exe], log_dir=game_dir) == 3
    assert fake_run["started"] == ["proton", exe]
    assert "<PixWidth>3440</PixWidth>" in fake_run["prefs"].read_text()
    assert len(fake_run["scales"]) == 2


def test_run_needs_the_games_command(game_dir):
    assert launch.run([], log_dir=game_dir) == 2

import json
import shutil
import sys

import pytest

from mghd_resolution_mod import heroic, install, launch_setup, steam
from test_steam import CONFIG

SIZES = [(2560, 1080)]
quiet = dict(log=lambda _: None)
linux_only = pytest.mark.skipif(sys.platform == "win32", reason="the launch is set up on Linux only")


@pytest.fixture
def steam_game(game_dir, tmp_path):
    """The game in a Steam library that is also the Steam folder, with one account's settings."""
    root = tmp_path / "Steam"
    common = root / "steamapps" / "common"
    common.mkdir(parents=True)
    moved = common / game_dir.name
    shutil.move(game_dir, moved)
    config = root / "userdata" / "1" / "config" / "localconfig.vdf"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG.replace('"LastPlayed"', '"LaunchOptions"\t\t"OLD=1 %command%"\n\t\t\t\t\t\t"LastPlayed"'))
    return moved, config


@pytest.fixture
def heroic_game(game_dir, tmp_path, monkeypatch):
    config = tmp_path / "heroic"
    (config / "gog_store").mkdir(parents=True)
    (config / "gog_store" / "installed.json").write_text(json.dumps(
        {"installed": [{"appName": heroic.GOG_ID, "install_path": str(game_dir)}]}))
    (config / "GamesConfig").mkdir()
    settings = config / "GamesConfig" / f"{heroic.GOG_ID}.json"
    settings.write_text(json.dumps({heroic.GOG_ID: {"winePrefix": "/x", "wrapperOptions": [{"exe": "mine", "args": ""}]},
                                    "version": "v0"}, indent=2))
    monkeypatch.setattr(heroic, "CONFIG_DIRS", [config])
    return game_dir, settings


def launcher_value():
    return launch_setup.steam_options([sys.executable, "-m", "mghd_resolution_mod", "run"])


@linux_only
def test_steam_gets_the_launch_and_uninstall_puts_the_old_one_back(steam_game):
    game_dir, config = steam_game
    before = config.read_text()
    install.install(game_dir, SIZES, **quiet)
    record = install.set_up_launch(game_dir, **quiet)
    assert record["store"] == "Steam"
    assert steam.read(config, "73230") == launcher_value() and launcher_value().endswith(" run %command%")
    assert steam.read(config, "825730") == "other %command%"
    install.install(game_dir, SIZES, **quiet)  # again: the player's own options are still remembered
    install.set_up_launch(game_dir, **quiet)
    assert install.status(game_dir).launch["entries"][0]["previous"] == "OLD=1 %command%"
    install.uninstall(game_dir, **quiet)
    assert config.read_text() == before


@linux_only
def test_a_launch_changed_since_is_left_alone(steam_game):
    game_dir, config = steam_game
    install.install(game_dir, SIZES, **quiet)
    install.set_up_launch(game_dir, **quiet)
    steam.write(config, "73230", "player's new %command%")
    install.uninstall(game_dir, **quiet)
    assert steam.read(config, "73230") == "player's new %command%"


@linux_only
def test_a_running_launcher_blocks_with_nothing_changed(steam_game, monkeypatch):
    game_dir, config = steam_game
    install.install(game_dir, SIZES, **quiet)
    monkeypatch.setattr(launch_setup, "running", lambda store: True)
    before = config.read_text()
    with pytest.raises(launch_setup.LaunchBlocked, match="Steam"):
        install.set_up_launch(game_dir, **quiet)
    assert config.read_text() == before
    monkeypatch.setattr(launch_setup, "running", lambda store: False)
    install.set_up_launch(game_dir, **quiet)
    monkeypatch.setattr(launch_setup, "running", lambda store: True)
    install.install(game_dir, SIZES, **quiet)
    install.set_up_launch(game_dir, **quiet)  # already the mod's: nothing to change, so Steam may run
    with pytest.raises(launch_setup.LaunchBlocked):
        install.uninstall(game_dir, **quiet)
    assert install.status(game_dir).installed  # nothing removed


@linux_only
def test_heroic_gets_the_wrapper_and_uninstall_puts_the_old_one_back(heroic_game):
    game_dir, settings = heroic_game
    before = json.loads(settings.read_text())
    install.install(game_dir, SIZES, **quiet)
    install.set_up_launch(game_dir, **quiet)
    after = json.loads(settings.read_text())
    assert after[heroic.GOG_ID]["wrapperOptions"] == [{"exe": sys.executable, "args": "-m mghd_resolution_mod run"}]
    assert after[heroic.GOG_ID]["winePrefix"] == "/x" and after["version"] == "v0"
    install.uninstall(game_dir, **quiet)
    assert json.loads(settings.read_text()) == before


def test_no_launch_on_windows(steam_game, monkeypatch):
    game_dir, config = steam_game
    monkeypatch.setattr(launch_setup.sys, "platform", "win32")
    before = config.read_text()
    install.install(game_dir, SIZES, **quiet)
    assert install.set_up_launch(game_dir, **quiet) is None
    assert config.read_text() == before


def test_no_launch_outside_steam_and_heroic(game_dir):
    install.install(game_dir, SIZES, **quiet)
    assert install.set_up_launch(game_dir, **quiet) is None
    assert install.status(game_dir).launch is None


def test_steam_options_quote_paths_with_spaces():
    assert launch_setup.steam_options(["/a b/x", "run"]) == '"/a b/x" run %command%'


@linux_only
def test_steam_needs_closing_only_when_its_settings_change(steam_game):
    game_dir, config = steam_game
    backup = game_dir / install.BACKUP_DIR
    install.install(game_dir, SIZES, **quiet)
    assert launch_setup.needs_change(game_dir, backup)
    install.set_up_launch(game_dir, **quiet)
    assert not launch_setup.needs_change(game_dir, backup)
    steam.write(config, "73230", "player's own %command%")
    assert launch_setup.needs_change(game_dir, backup)


def test_nothing_to_change_outside_steam_and_heroic(game_dir):
    assert not launch_setup.needs_change(game_dir, game_dir / install.BACKUP_DIR)

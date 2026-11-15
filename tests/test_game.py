import json

from mghd_resolution_mod import game, heroic


def heroic_config(config, entries):
    (config / "gog_store").mkdir(parents=True)
    (config / "gog_store" / "installed.json").write_text(json.dumps({"installed": entries}))


def test_heroic_installs_are_found(game_dir, tmp_path, monkeypatch):
    config = tmp_path / "heroic"
    heroic_config(config, [{"appName": "1207659252", "install_path": "/elsewhere/Tzar"},
                           {"appName": heroic.GOG_ID, "install_path": str(game_dir)}])
    monkeypatch.setattr(heroic, "CONFIG_DIRS", [config])
    monkeypatch.setattr(game, "_steam_game_dirs", lambda: [])
    monkeypatch.chdir(tmp_path)
    assert heroic.game_dirs() == [game_dir]
    assert game_dir.resolve() in game.find()


def test_other_heroic_games_and_broken_settings_are_ignored(tmp_path, monkeypatch):
    good, broken, odd = tmp_path / "good", tmp_path / "broken", tmp_path / "odd"
    heroic_config(good, [{"appName": "1", "install_path": "/x"}, {"appName": heroic.GOG_ID}])
    (broken / "gog_store").mkdir(parents=True)
    (broken / "gog_store" / "installed.json").write_text("{not json")
    (odd / "gog_store").mkdir(parents=True)
    (odd / "gog_store" / "installed.json").write_text('{"installed": "nope"}')
    monkeypatch.setattr(heroic, "CONFIG_DIRS", [good, broken, odd, tmp_path / "missing"])
    assert heroic.game_dirs() == []

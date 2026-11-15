from click.testing import CliRunner

from mghd_resolution_mod import __version__, cli, screen


def test_version():
    result = CliRunner().invoke(cli.cli, ["--version"])
    assert result.exit_code == 0 and __version__ in result.output


def test_install_status_uninstall(game_dir, monkeypatch):
    monkeypatch.setattr(screen, "detect_screens", lambda: [(3440, 1440)])
    monkeypatch.setattr(cli.layouts, "COMMON_SIZES", [(2560, 1080)])
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["install", "--game-dir", str(game_dir), "--yes", "--size", "1720x720"])
    assert result.exit_code == 0, result.output
    assert "1720x720, 2560x1080, 3440x1440" in result.output
    result = runner.invoke(cli.cli, ["status", "--game-dir", str(game_dir)])
    assert "installed" in result.output and "1720x720" in result.output
    result = runner.invoke(cli.cli, ["uninstall", "--game-dir", str(game_dir), "--yes"])
    assert result.exit_code == 0 and "back to how it was" in result.output


def test_bad_size(game_dir):
    result = CliRunner().invoke(cli.cli, ["install", "--game-dir", str(game_dir), "--size", "big"])
    assert result.exit_code != 0 and "isn't a size" in result.output


def test_run_passes_the_games_command_through(monkeypatch):
    from click.testing import CliRunner

    from mghd_resolution_mod import cli, launch

    seen = []
    monkeypatch.setattr(launch, "run", lambda command: seen.append(command) or 5)
    monkeypatch.setattr(cli.sys, "platform", "linux")
    command = ["/steam/reaper", "SteamLaunch", "AppId=73230", "--", "/proton", "waitforexitandrun", "-x", "/g/M.exe"]
    result = CliRunner().invoke(cli.cli, ["run", *command], standalone_mode=False)
    assert seen == [command] and result.return_value == 5

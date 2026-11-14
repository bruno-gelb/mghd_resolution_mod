"""mghd-resolution-mod: install the resolution mod for Majesty Gold HD, or remove it.

Run it with no arguments (double-click on Windows) and it finds the game, says what it will do and asks before changing
anything.
"""

import re
import sys
from pathlib import Path

import click

from mghd_resolution_mod import __version__, game, install, layouts, screen

PROG = "mghd-resolution-mod"
ISSUES = "https://github.com/bruno-gelb/mghd_resolution_mod/issues"
# Written by src/tools/build_release.py and bundled with the release programs: the licenses of what's inside them.
NOTICES = Path(__file__).parent / "THIRD-PARTY-NOTICES.txt"


class SizeParam(click.ParamType):
    name = "WxH"

    def convert(self, value, param, ctx):
        m = re.fullmatch(r"(\d+)[xX](\d+)", str(value).strip())
        if not m:
            self.fail(f"{value!r} isn't a size like 2560x1080", param, ctx)
        size = (int(m[1]), int(m[2]))
        if size[0] < layouts.MIN_SIZE[0] or size[1] < layouts.MIN_SIZE[1]:
            self.fail(f"{value} is smaller than the game's smallest, 800x600", param, ctx)
        return size


size_option = click.option(
    "--size", "sizes", type=SizeParam(), multiple=True,
    help="Also make a layout for this size, like 1720x720 (for a scaler such as gamescope). Can be given more than "
         "once.")
game_dir_option = click.option(
    "--game-dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="The game folder (the one with MajestyHD.exe), if it isn't found on its own.")
yes_option = click.option("--yes", "-y", is_flag=True, help="Don't ask anything.")


def _show_licenses(ctx: click.Context, _param, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    if NOTICES.is_file():
        click.echo(NOTICES.read_text(encoding="utf-8"))
    else:
        click.echo("This copy isn't a release build, so it has no third-party notices: see the README's License "
                   "section.")
    ctx.exit()


def _menu(title: str, options: list[str], default: int = 1) -> int:
    """A numbered choice; Enter picks the default. Returns it 1-based."""
    click.echo(title)
    for i, option in enumerate(options, 1):
        click.echo(f"  {i}. {option}")
    return click.prompt("Choose", type=click.IntRange(1, len(options)), default=default)


def _pick_game_dir(given: Path | None) -> Path:
    if given:
        if not game.is_game_dir(given):
            raise install.InstallError(f"{given} doesn't look like the Majesty Gold HD folder (no {game.EXE} and "
                                       f"{game.DATA} folder in it)")
        return given.resolve()
    found = game.find()
    if not found:
        raise install.InstallError(
            "couldn't find the game. Put this program in the Majesty HD folder and run it from there, or pass the "
            "folder: --game-dir \"<path to Majesty HD>\"")
    if len(found) == 1:
        return found[0]
    return found[_menu("Found more than one Majesty folder:", [str(p) for p in found]) - 1]


def _open_game(game_dir: Path | None) -> tuple[Path, install.Status]:
    click.echo(f"Majesty Gold HD resolution mod {__version__}\n")
    path = _pick_game_dir(game_dir)
    state = install.status(path)
    click.echo(f"Game folder: {path}")
    if state.installed:
        click.echo(f"Mod: installed (version {state.version}, {len(state.added)} layouts)\n")
    else:
        click.echo("Mod: not installed\n")
    return path, state


def _fmt(sizes: list[layouts.Size]) -> str:
    return ", ".join(f"{w}x{h}" for w, h in sizes)


def _plan(extra: list[layouts.Size]) -> list[layouts.Size]:
    detected = screen.detect_screens()
    sizes = layouts.sizes_to_make(detected, extra)
    for w, h in detected:
        own = "the game has a layout for it already" if (w, h) in layouts.ORIGINAL_SIZES else "included"
        click.echo(f"Your screen: {w}x{h} ({own}).")
    if not detected:
        click.echo("Couldn't tell your screen's size: making the common sizes only. Add yours with --size WxH.")
    click.echo(f"Layouts to make: {_fmt(sizes)}.\n")
    return sizes


def _do_install(path: Path, sizes: list[layouts.Size]) -> None:
    install.install(path, sizes, log=lambda line: click.echo(f"  {line}"))
    click.echo("\nDone. Start the game, open ADJUST SETTINGS on the main menu and pick your screen's resolution: the")
    click.echo("ones with a layout are green. The main menu now shows the mod's version under the picture.")
    click.echo("The interface doesn't scale: at a high resolution the text gets small. For bigger text, pick a lower")
    click.echo("resolution of the same shape (on a 3440x1440 screen, 2560x1080). To remove the mod, run this again.")


def _do_uninstall(path: Path) -> None:
    install.uninstall(path, log=lambda line: click.echo(f"  {line}"))
    click.echo("\nDone: the game is back to how it was. If its resolution was one of the mod's, the game falls back")
    click.echo("to the closest layout it has, centered in a frame; pick another in ADJUST SETTINGS.")


def _interactive(path: Path, state: install.Status, extra: list[layouts.Size]) -> None:
    if state.installed:
        if state.reverted:
            click.echo("The mod is installed, but the game's files were put back, probably by a Steam update.\n")
        picked = _menu("What now?", ["install again (and add any new sizes)",
                                     "remove the mod and put the original files back", "nothing"],
                       default=1 if state.reverted else 3)
        if picked == 1:
            click.echo()
            _do_install(path, _plan(extra))
        elif picked == 2:
            _do_uninstall(path)
        return
    click.echo("This adds interface layouts for screens the game doesn't support, like ultrawide, 1440p and 4K, and")
    click.echo("the mod's version on the main menu. It keeps the originals of the files it changes in")
    click.echo(f"{install.BACKUP_DIR}/, so running it again can remove the mod.\n")
    sizes = _plan(extra)
    if click.confirm("Install the mod?", default=True):
        _do_install(path, sizes)


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@size_option
@game_dir_option
@click.version_option(__version__, prog_name=PROG)
@click.option("--licenses", is_flag=True, expose_value=False, is_eager=True, callback=_show_licenses,
              help="Show the licenses of the mod and of the software bundled with it, and exit.")
@click.pass_context
def cli(ctx: click.Context, sizes: tuple, game_dir: Path | None) -> None:
    """Resolution mod for Majesty Gold HD: interface layouts for ultrawide, 1440p, 4K and more.

    With no command, it finds the game and asks what to do.
    """
    ctx.obj = {"game_dir": game_dir, "sizes": list(sizes)}
    if ctx.invoked_subcommand is None:
        _interactive(*_open_game(game_dir), list(sizes))


@cli.command("install")
@size_option
@game_dir_option
@yes_option
@click.pass_context
def install_command(ctx: click.Context, sizes: tuple, game_dir: Path | None, yes: bool) -> None:
    """Install the mod, or install it again (after a Steam update, or to add sizes)."""
    path, _ = _open_game(game_dir or ctx.obj["game_dir"])
    planned = _plan([*ctx.obj["sizes"], *sizes])
    if yes or click.confirm("Install the mod?", default=True):
        _do_install(path, planned)


@cli.command("uninstall")
@game_dir_option
@yes_option
@click.pass_context
def uninstall_command(ctx: click.Context, game_dir: Path | None, yes: bool) -> None:
    """Remove the mod and put the game's original files back."""
    path, _ = _open_game(game_dir or ctx.obj["game_dir"])
    if yes or click.confirm("Remove the mod?", default=True):
        _do_uninstall(path)


@cli.command("status")
@game_dir_option
@click.pass_context
def status_command(ctx: click.Context, game_dir: Path | None) -> None:
    """Show what's installed, without changing anything."""
    _, state = _open_game(game_dir or ctx.obj["game_dir"])
    if state.installed:
        sizes = [layouts.parse_name(Path(rel).name) for rel in state.added]
        click.echo(f"Layouts added: {_fmt([s for s in sizes if s])}")
        if state.reverted:
            click.echo("The game's files were put back since (a Steam update?): install again.")


def main() -> None:
    # Started by double-click on Windows: keep the window open at the end so the result can be read.
    pause = sys.platform == "win32" and len(sys.argv) == 1
    try:
        code = cli.main(prog_name=PROG, standalone_mode=False)
        code = code if isinstance(code, int) else 0
    except click.exceptions.Abort:
        click.echo("\nStopped.")
        code = 1
    except click.ClickException as error:
        error.show()
        code = error.exit_code
    except install.InstallError as error:
        click.echo(f"\nCan't continue: {error}")
        code = 1
    if pause:
        click.pause("\nPress any key to close this window.")
    sys.exit(code)

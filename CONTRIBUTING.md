# Contributing

Notes for working on the mod. For what it is and how to play it, see the [README](README.md).

## How it works

The game picks its interface layout from `Data/UIData_<w>_<h>.dat`: the exact size if there's a file for it,
otherwise the biggest one that fits, centered. It ships 13 of them, up to 1920x1200. The mod generates new ones from
the player's own files, so the interface fills screens the game never planned for. The target is the screen's shape,
not always its full size: on a 3440x1440 screen, a 1720x720 game picture scaled up 2x keeps the interface and fonts
big and sharp, where native 3440x1440 would make them tiny.

What it takes so far:

- **Re-anchoring.** Files of the same size have the same structure. Comparing them shows which coordinates follow the
  right or bottom edge, or the center, and those get recomputed for the new size. The rest were tuned by hand per
  screen height, and come from the original file with the closest height.
- **Fixes for heights the game never had.** Below 768 px, the left panel's second building preview doesn't fit, so
  it's moved off the screen.

All the details, with offsets and addresses: [docs/findings.md](docs/findings.md).

## Running from source

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

```bash
uv run python src/tools/uidata_gen.py "<game folder>/Data" 1720 720 build/UIData_1720_720.dat
```

There's no installer yet: copy the generated file into the game's `Data/` folder, and set `PixWidth` and
`PixHeight` in `MajXPrefs` (in `Documents/My Games/MajestyHD/`, on Linux inside the game's Proton prefix). Back up
`MajXPrefs` first. To undo, delete the generated file and put the backup back.

Every third-party dependency is pinned to an exact version: Python in `.python-version`, packages in
`pyproject.toml` and, with their whole tree, in `uv.lock`. Update a pin on purpose, in its own commit, and run
`uv lock` after changing `pyproject.toml`.

Real-game checks (the game starts, the interface fills the screen, nothing is cut off) are manual: describe them in
the pull request, with screenshots.

## Tools

`src/tools/` has scripts for development, run with `uv run python src/tools/<script>`:

- `uidata_diff.py`: lists every 32-bit word that differs between same-sized `UIData` files, and classifies it as
  right, bottom or center anchored, or `???` when no rule fits.

  ```bash
  uv run python src/tools/uidata_diff.py "<game folder>/Data" 40016
  ```

- `uidata_gen.py`: builds a new `UIData` file from a base one (1360x768 by default).
- `xref.py`: static analysis of the exe, with [pefile](https://github.com/erocarrera/pefile) and
  [Capstone](https://www.capstone-engine.org/). `str` finds a string and disassembles around the code that
  references it, `dis` disassembles from an address. It only disassembles small windows, so it fits in memory on
  this 3.9 MB exe.

  ```bash
  uv run python src/tools/xref.py "<game folder>/MajestyHD.exe" str UIData_%d_%d.dat
  ```

  ```bash
  uv run python src/tools/xref.py "<game folder>/MajestyHD.exe" dis 4f0870 40
  ```

## Plans and bugs

They're [GitHub issues](https://github.com/bruno-gelb/mghd_resolution_mod/issues): what's next, known problems and
ideas. Open one before starting on something bigger. Bug reports, feature requests and testing help are most welcome,
especially on Windows.

Each issue starts with an **Impact** section: a level, **High**, **Medium** or **Low**, then who it affects and how
(Windows or Linux, which resolution, which players), and what it does for the mod. The rest goes under **Details**.
The [issue template](.github/ISSUE_TEMPLATE/issue.md) starts new issues with both.

Two labels sort the issues: `impact: high`, `medium` or `low`, matching the Impact section, and `effort: high`,
`medium` or `low`, a rough guess at the work: a sitting or two for low, a few days for medium, a week or more, or
big unknowns, for high. High impact with low effort goes first.

## Workflow

- **Commit messages** follow [How to Write a Git Commit Message](https://cbea.ms/git-commit/): a subject line of up
  to 50 characters, capitalized, in the imperative mood ("Hide the second preview", not "Hid..."), with no period at
  the end; a blank line; then a body wrapped at 72 characters that says what changed and why.
- **Branches** follow [trunk-based development](https://trunkbaseddevelopment.com/): `main` is the trunk and the only
  long-lived branch. Make each change on a short-lived branch and merge it into `main` with a pull request within a
  day or two. Pull request titles follow the same rules as commit subjects. Keep `main` working: every merge should
  leave the mod in a state that runs.
- **Branch names**: a prefix (`feature`, `bug` or `chore`), a slash, the number of the GitHub issue the branch works
  on, a hyphen, and a short description in kebab-case (lowercase words joined by hyphens):
  - `feature/1-loading-screen-keypress`
  - `bug/2-panel-cut-off`

## Versions and releases

Versions follow [semantic versioning](https://semver.org), and the version lives in `pyproject.toml`: the major
number for changes that make players do something differently, the minor one for new features (resolutions,
layouts), the patch one for fixes. While it's 0.x, minor versions can also carry bigger changes. There are no
releases yet.

## License

Contributions are under the [MIT License](LICENSE), like the rest of the mod. Never commit the game's files: its
exe, DLLs or data. `.gitignore` keeps `.exe`, `.dll` and `.dat` files out, generated layouts included: they're made
from the game's own files.

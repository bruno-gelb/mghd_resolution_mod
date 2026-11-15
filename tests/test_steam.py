import pytest

from mghd_resolution_mod import steam

CONFIG = '''"UserLocalConfigStore"
{
\t"Software"
\t{
\t\t"Valve"
\t\t{
\t\t\t"Steam"
\t\t\t{
\t\t\t\t"apps"
\t\t\t\t{
\t\t\t\t\t"825730"
\t\t\t\t\t{
\t\t\t\t\t\t"LaunchOptions"\t\t"other %command%"
\t\t\t\t\t}
\t\t\t\t\t"73230"
\t\t\t\t\t{
\t\t\t\t\t\t"LastPlayed"\t\t"1794445414"
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
\t"WebStorage"
\t{
\t\t"Cached"\t\t"{\\"a\\":\\"b\\\\c\\"}"
\t}
}
'''


def test_adds_the_options_to_the_games_entry_and_nothing_else():
    new = steam.set_options(CONFIG, "73230", '"/a b/launcher" run %command%')
    assert steam.get_options(new, "73230") == '"/a b/launcher" run %command%'
    assert '\t\t\t\t\t\t"LaunchOptions"\t\t"\\"/a b/launcher\\" run %command%"\n\t\t\t\t\t}' in new
    assert steam.get_options(new, "825730") == "other %command%"
    assert new.replace('\t\t\t\t\t\t"LaunchOptions"\t\t"\\"/a b/launcher\\" run %command%"\n', "") == CONFIG


def test_replaces_existing_options_in_place():
    new = steam.set_options(CONFIG, "825730", "mine %command%")
    assert new == CONFIG.replace('"other %command%"', '"mine %command%"')
    assert steam.set_options(new, "825730", "other %command%") == CONFIG


def test_adds_the_game_when_steam_has_no_entry_for_it():
    new = steam.set_options(CONFIG, "999", "x %command%")
    assert steam.get_options(new, "999") == "x %command%"
    assert steam.get_options(new, "825730") == "other %command%"
    assert steam.get_options(CONFIG, "999") is None


def test_escapes_round_trip():
    assert steam.tokens(CONFIG)[-3].value == '{"a":"b\\c"}'
    value = 'say "hi" \\ there'
    assert steam.get_options(steam.set_options(CONFIG, "73230", value), "73230") == value


def test_broken_or_foreign_files():
    with pytest.raises(steam.VdfError):
        steam.set_options('"Other"\n{\n}\n', "73230", "x")
    with pytest.raises(steam.VdfError):
        steam.set_options('"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n}\n', "73230", "x")
    with pytest.raises(steam.VdfError, match="Software"):
        steam.set_options('"UserLocalConfigStore"\n{\n}\n', "73230", "x")

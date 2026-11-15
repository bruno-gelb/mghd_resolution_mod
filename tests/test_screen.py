from mghd_resolution_mod import screen


def connector(root, name, status, modes, enabled=None):
    d = root / name
    d.mkdir()
    (d / "status").write_text(status + "\n")
    (d / "modes").write_text(modes)
    if enabled is not None:
        (d / "enabled").write_text(enabled + "\n")


def test_native_modes_of_connected_displays(tmp_path, monkeypatch):
    connector(tmp_path, "card1-HDMI-A-1", "connected", "3440x1440\n2560x1440\n")
    connector(tmp_path, "card1-eDP-1", "connected", "1920x1200\n")
    connector(tmp_path, "card1-DP-1", "disconnected", "")
    monkeypatch.setattr(screen, "DRM", tmp_path)
    assert sorted(screen._drm_screens()) == [(1920, 1200), (3440, 1440)]


def test_a_laptop_panel_turned_off_for_an_external_screen_is_left_out(tmp_path, monkeypatch):
    connector(tmp_path, "card1-HDMI-A-1", "connected", "3440x1440\n", "enabled")
    connector(tmp_path, "card1-eDP-1", "connected", "1920x1200\n", "disabled")
    monkeypatch.setattr(screen, "DRM", tmp_path)
    assert screen._drm_screens() == [(3440, 1440)]


def test_with_no_display_on_all_connected_ones_count(tmp_path, monkeypatch):
    connector(tmp_path, "card1-HDMI-A-1", "connected", "3440x1440\n", "disabled")
    connector(tmp_path, "card1-eDP-1", "connected", "1920x1200\n", "disabled")
    monkeypatch.setattr(screen, "DRM", tmp_path)
    assert sorted(screen._drm_screens()) == [(1920, 1200), (3440, 1440)]

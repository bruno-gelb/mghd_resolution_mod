from mghd_resolution_mod import screen


def connector(root, name, status, modes):
    d = root / name
    d.mkdir()
    (d / "status").write_text(status + "\n")
    (d / "modes").write_text(modes)


def test_native_modes_of_connected_displays(tmp_path, monkeypatch):
    connector(tmp_path, "card1-HDMI-A-1", "connected", "3440x1440\n2560x1440\n")
    connector(tmp_path, "card1-eDP-1", "connected", "1920x1200\n")
    connector(tmp_path, "card1-DP-1", "disconnected", "")
    monkeypatch.setattr(screen, "DRM", tmp_path)
    assert sorted(screen._drm_screens()) == [(1920, 1200), (3440, 1440)]

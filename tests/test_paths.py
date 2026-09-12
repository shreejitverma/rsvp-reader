from pathlib import Path

from rsvpreader.paths import default_book_root, legacy_config_dir, user_config_dir


def test_config_dir_override():
    assert user_config_dir({"RSVPREADER_CONFIG_DIR": "/tmp/x"}, "darwin") == Path("/tmp/x")


def test_config_dir_per_platform():
    env = {"HOME": "/home/u"}
    assert user_config_dir(env, "darwin") == Path("/home/u/Library/Application Support/rsvpreader")
    assert user_config_dir(env, "linux") == Path("/home/u/.config/rsvpreader")
    assert user_config_dir({**env, "XDG_CONFIG_HOME": "/xdg"}, "linux") == Path("/xdg/rsvpreader")
    assert user_config_dir({**env, "APPDATA": "C:/AppData"}, "win32") == Path(
        "C:/AppData/rsvpreader"
    )


def test_default_book_root():
    assert default_book_root({}, Path("/w")) == Path("/w/book")
    assert default_book_root({"RSVPREADER_BOOK_ROOT": "/b"}, Path("/w")) == Path("/b")


def test_legacy_config_dir_uses_pre_rename_name_and_ignores_override():
    env = {"HOME": "/home/u", "RSVPREADER_CONFIG_DIR": "/tmp/x"}
    assert legacy_config_dir(env, "darwin") == Path(
        "/home/u/Library/Application Support/rsvp-reader"
    )
    assert legacy_config_dir(env, "linux") == Path("/home/u/.config/rsvp-reader")
    assert legacy_config_dir({**env, "APPDATA": "C:/AppData"}, "win32") == Path(
        "C:/AppData/rsvp-reader"
    )
    assert legacy_config_dir(env, "linux") != user_config_dir({"HOME": "/home/u"}, "linux")


def test_legacy_config_dir_honors_pre_rename_override_only():
    env = {"HOME": "/home/u", "RSVP_READER_CONFIG_DIR": "/dotfiles/rsvp"}
    assert legacy_config_dir(env, "linux") == Path("/dotfiles/rsvp")
    assert user_config_dir(env, "linux") == Path("/home/u/.config/rsvpreader")

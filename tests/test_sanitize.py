"""Tests for cronwrap.sanitize."""
import pytest
from unittest.mock import patch
from cronwrap.sanitize import SanitizeConfig, Sanitizer


@pytest.fixture
def sanitizer():
    return Sanitizer(SanitizeConfig())


def test_config_enabled_by_default():
    cfg = SanitizeConfig.from_env()
    assert cfg.enabled is True


def test_config_disabled_via_env():
    with patch.dict("os.environ", {"CRONWRAP_SANITIZE_ENABLED": "false"}):
        cfg = SanitizeConfig.from_env()
    assert cfg.enabled is False


def test_config_extra_patterns_from_env():
    with patch.dict("os.environ", {"CRONWRAP_SANITIZE_PATTERNS": "foo,bar"}):
        cfg = SanitizeConfig.from_env()
    assert cfg.extra_patterns == ["foo", "bar"]


def test_strip_ansi_codes(sanitizer):
    dirty = "\x1b[31mRed text\x1b[0m"
    assert sanitizer.sanitize(dirty) == "Red text"


def test_strip_control_characters(sanitizer):
    dirty = "hello\x07world\x0c!"
    assert sanitizer.sanitize(dirty) == "helloworld!"


def test_strip_both(sanitizer):
    dirty = "\x1b[1mBold\x1b[0m\x07"
    assert sanitizer.sanitize(dirty) == "Bold"


def test_passthrough_when_disabled():
    cfg = SanitizeConfig(enabled=False)
    s = Sanitizer(cfg)
    dirty = "\x1b[31mstill here\x1b[0m"
    assert s.sanitize(dirty) == dirty


def test_extra_pattern_removed():
    cfg = SanitizeConfig(extra_patterns=[r"SECRET\w+"])
    s = Sanitizer(cfg)
    assert s.sanitize("prefix SECRETtoken suffix") == "prefix  suffix"


def test_clean_text_unchanged(sanitizer):
    clean = "normal log output 123"
    assert sanitizer.sanitize(clean) == clean

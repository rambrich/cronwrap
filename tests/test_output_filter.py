import pytest
from cronwrap.output_filter import OutputFilterConfig, OutputFilter


@pytest.fixture
def default_filter():
    return OutputFilter(OutputFilterConfig())


def test_config_enabled_by_default():
    cfg = OutputFilterConfig()
    assert cfg.enabled is True


def test_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_OUTPUT_FILTER_ENABLED", "false")
    cfg = OutputFilterConfig.from_env()
    assert cfg.enabled is False


def test_config_from_env_max_bytes(monkeypatch):
    monkeypatch.setenv("CRONWRAP_OUTPUT_MAX_BYTES", "1024")
    cfg = OutputFilterConfig.from_env()
    assert cfg.max_bytes == 1024


def test_config_from_env_exclude_patterns(monkeypatch):
    monkeypatch.setenv("CRONWRAP_OUTPUT_EXCLUDE_PATTERNS", "DEBUG,TRACE")
    cfg = OutputFilterConfig.from_env()
    assert cfg.exclude_patterns == ["DEBUG", "TRACE"]


def test_strip_ansi(default_filter):
    text = "\x1b[32mhello\x1b[0m world"
    result = default_filter.filter(text)
    assert result == "hello world"


def test_no_strip_ansi_when_disabled():
    cfg = OutputFilterConfig(strip_ansi=False)
    f = OutputFilter(cfg)
    text = "\x1b[32mhello\x1b[0m"
    assert f.filter(text) == text


def test_truncates_large_output():
    cfg = OutputFilterConfig(max_bytes=10)
    f = OutputFilter(cfg)
    text = "a" * 50
    result = f.filter(text)
    assert "[output truncated]" in result
    assert result.startswith("aaaaaaaaaa")


def test_exclude_patterns_remove_lines():
    cfg = OutputFilterConfig(exclude_patterns=[r"DEBUG"])
    f = OutputFilter(cfg)
    text = "INFO: ok\nDEBUG: noisy\nINFO: done\n"
    result = f.filter(text)
    assert "DEBUG" not in result
    assert "INFO: ok" in result


def test_passthrough_when_disabled():
    cfg = OutputFilterConfig(enabled=False)
    f = OutputFilter(cfg)
    text = "\x1b[32mcolored\x1b[0m"
    assert f.filter(text) == text

import pytest
from cronwrap.redact import RedactConfig, Redactor


@pytest.fixture
def redactor():
    return Redactor(RedactConfig(enabled=True))


def test_redact_config_enabled_by_default():
    cfg = RedactConfig()
    assert cfg.enabled is True


def test_redact_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REDACT_ENABLED", "false")
    cfg = RedactConfig.from_env()
    assert cfg.enabled is False


def test_redact_config_extra_patterns(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REDACT_PATTERNS", r"myfield=\S+,other=\S+")
    cfg = RedactConfig.from_env()
    assert len(cfg.extra_patterns) == 2


def test_redact_password_in_command(redactor):
    cmd = "run.sh --password=supersecret --verbose"
    result = redactor.redact(cmd)
    assert "supersecret" not in result
    assert "password=***" in result


def test_redact_token_in_url(redactor):
    cmd = "curl https://api.example.com?token=abc123"
    result = redactor.redact(cmd)
    assert "abc123" not in result
    assert "token=***" in result


def test_redact_disabled_leaves_text_unchanged():
    r = Redactor(RedactConfig(enabled=False))
    cmd = "run.sh --password=supersecret"
    assert r.redact(cmd) == cmd


def test_redact_env_masks_sensitive_keys(redactor):
    env = {"DB_PASSWORD": "s3cr3t", "HOME": "/root", "API_TOKEN": "tok"}
    result = redactor.redact_env(env)
    assert result["DB_PASSWORD"] == "***"
    assert result["API_TOKEN"] == "***"
    assert result["HOME"] == "/root"


def test_redact_env_disabled_unchanged():
    r = Redactor(RedactConfig(enabled=False))
    env = {"DB_PASSWORD": "s3cr3t"}
    assert r.redact_env(env) == env

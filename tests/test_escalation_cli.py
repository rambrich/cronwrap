import pytest
from cronwrap.escalation import EscalationConfig, EscalationManager
from cronwrap.escalation_cli import build_parser, cmd_status, cmd_reset
from cronwrap.runner import RunResult


def _result(success: bool) -> RunResult:
    return RunResult(command="echo hi", returncode=0 if success else 1,
                     stdout="", stderr="", duration=1.0, success=success, attempts=1)


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = EscalationConfig(
        enabled=True, threshold=3,
        recipients=["ops@example.com"],
        state_file=str(tmp_path / "esc.json")
    )
    return EscalationManager(cfg)


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_output(tmp_mgr, capsys, monkeypatch):
    tmp_mgr.record(_result(False), "echo hi")
    tmp_mgr.record(_result(False), "echo hi")
    monkeypatch.setattr("cronwrap.escalation_cli._manager", lambda: tmp_mgr)
    args = build_parser().parse_args(["status", "echo hi"])
    cmd_status(args)
    out = capsys.readouterr().out
    assert "Failures  : 2" in out
    assert "Escalated : no" in out


def test_cmd_status_shows_escalated(tmp_mgr, capsys, monkeypatch):
    for _ in range(3):
        tmp_mgr.record(_result(False), "echo hi")
    monkeypatch.setattr("cronwrap.escalation_cli._manager", lambda: tmp_mgr)
    args = build_parser().parse_args(["status", "echo hi"])
    cmd_status(args)
    out = capsys.readouterr().out
    assert "Escalated : yes" in out


def test_cmd_reset_clears_count(tmp_mgr, capsys, monkeypatch):
    tmp_mgr.record(_result(False), "echo hi")
    monkeypatch.setattr("cronwrap.escalation_cli._manager", lambda: tmp_mgr)
    args = build_parser().parse_args(["reset", "echo hi"])
    cmd_reset(args)
    assert tmp_mgr.consecutive_failures("echo hi") == 0
    out = capsys.readouterr().out
    assert "Reset" in out

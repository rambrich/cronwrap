"""Tests for cronwrap.snapshot_cli."""
import json
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.snapshot import SnapshotConfig, SnapshotManager, SnapshotEntry
from cronwrap.snapshot_cli import build_parser, cmd_show, cmd_reset, cmd_list


def _entry():
    return SnapshotEntry(job_name="myjob", output_hash="abc123", timestamp="2024-01-01T00:00:00")


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_show_prints_entry(capsys):
    args = MagicMock(job_name="myjob")
    with patch("cronwrap.snapshot_cli._manager") as mock_mgr:
        mock_mgr.return_value.load.return_value = _entry()
        cmd_show(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["job_name"] == "myjob"
    assert data["output_hash"] == "abc123"


def test_cmd_show_exits_when_not_found():
    args = MagicMock(job_name="missing")
    with patch("cronwrap.snapshot_cli._manager") as mock_mgr:
        mock_mgr.return_value.load.return_value = None
        with pytest.raises(SystemExit):
            cmd_show(args)


def test_cmd_reset_removes_file(tmp_path):
    state_file = tmp_path / "myjob.json"
    state_file.write_text("{}")
    args = MagicMock(job_name="myjob")
    with patch("cronwrap.snapshot_cli._manager") as mock_mgr:
        mock_mgr.return_value._state_path.return_value = str(state_file)
        cmd_reset(args)
    assert not state_file.exists()


def test_cmd_list_no_dir(capsys):
    args = MagicMock()
    with patch("cronwrap.snapshot_cli.SnapshotConfig.from_env") as mock_cfg:
        mock_cfg.return_value.state_dir = "/nonexistent/path"
        cmd_list(args)
    out = capsys.readouterr().out
    assert "No snapshots directory" in out


def test_cmd_list_shows_jobs(tmp_path, capsys):
    (tmp_path / "jobA.json").write_text("{}")
    (tmp_path / "jobB.json").write_text("{}")
    args = MagicMock()
    with patch("cronwrap.snapshot_cli.SnapshotConfig.from_env") as mock_cfg:
        mock_cfg.return_value.state_dir = str(tmp_path)
        cmd_list(args)
    out = capsys.readouterr().out
    assert "jobA" in out
    assert "jobB" in out

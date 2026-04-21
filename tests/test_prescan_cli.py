"""Tests for cronwrap.prescan_cli module."""
import pytest
from io import StringIO
from unittest.mock import patch

from cronwrap.prescan import PrescanConfig
from cronwrap.prescan_cli import build_parser, cmd_status, cmd_test


def test_build_parser_has_subcommands():
    parser = build_parser()
    # Should not raise
    args = parser.parse_args(["status"])
    assert args.command == "status"


def test_build_parser_test_subcommand():
    parser = build_parser()
    args = parser.parse_args(["test", "some output text"])
    assert args.command == "test"
    assert args.text == "some output text"


def test_cmd_status_output(capsys):
    config = PrescanConfig(
        enabled=True,
        warn_patterns=["WARNING"],
        fail_patterns=["ERROR"],
    )
    cmd_status(config)
    captured = capsys.readouterr()
    assert "True" in captured.out
    assert "WARNING" in captured.out
    assert "ERROR" in captured.out


def test_cmd_status_disabled(capsys):
    config = PrescanConfig(enabled=False)
    cmd_status(config)
    captured = capsys.readouterr()
    assert "False" in captured.out


def test_cmd_test_disabled_prints_message(capsys):
    config = PrescanConfig(enabled=False)
    cmd_test(config, "ERROR: something")
    captured = capsys.readouterr()
    assert "disabled" in captured.out.lower()


def test_cmd_test_detects_fail_pattern(capsys):
    config = PrescanConfig(enabled=True, warn_patterns=[], fail_patterns=["ERROR"])
    cmd_test(config, "ERROR: crash occurred")
    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert "FAIL matches" in captured.out


def test_cmd_test_no_match(capsys):
    config = PrescanConfig(enabled=True, warn_patterns=["WARNING"], fail_patterns=["ERROR"])
    cmd_test(config, "everything is fine")
    captured = capsys.readouterr()
    assert "(none)" in captured.out

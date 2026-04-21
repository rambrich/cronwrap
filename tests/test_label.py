"""Tests for cronwrap.label."""
import pytest
from unittest.mock import patch

from cronwrap.label import (
    LabelConfig,
    LabelManager,
    parse_labels,
    matches_labels,
)


def test_label_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=False):
        import os; os.environ.pop("CRONWRAP_LABELS", None)
        cfg = LabelConfig.from_env()
    assert cfg.enabled is False
    assert cfg.labels == {}


def test_label_config_from_env():
    with patch.dict("os.environ", {"CRONWRAP_LABELS": "env=prod,team=ops"}):
        cfg = LabelConfig.from_env()
    assert cfg.enabled is True
    assert cfg.labels == {"env": "prod", "team": "ops"}


def test_parse_labels_simple():
    result = parse_labels("k=v")
    assert result == {"k": "v"}


def test_parse_labels_multiple():
    result = parse_labels("a=1,b=2,c=3")
    assert result == {"a": "1", "b": "2", "c": "3"}


def test_parse_labels_empty_string():
    assert parse_labels("") == {}


def test_parse_labels_no_value():
    result = parse_labels("flag")
    assert result == {"flag": ""}


def test_parse_labels_whitespace_is_stripped():
    """Keys and values with surrounding whitespace should be stripped."""
    result = parse_labels(" env = prod , team = ops ")
    assert result == {"env": "prod", "team": "ops"}


def test_matches_labels_all_match():
    assert matches_labels({"env": "prod", "team": "ops"}, {"env": "prod"}) is True


def test_matches_labels_mismatch():
    assert matches_labels({"env": "prod"}, {"env": "staging"}) is False


def test_matches_labels_empty_selector():
    assert matches_labels({"env": "prod"}, {}) is True


def test_matches_labels_missing_key():
    """Selector key not present in entry labels should not match."""
    assert matches_labels({"env": "prod"}, {"team": "ops"}) is False


def test_get_labels_disabled():
    mgr = LabelManager(LabelConfig(enabled=False, labels={"env": "prod"}))
    assert mgr.get_labels() == {}


def test_get_labels_enabled():
    mgr = LabelManager(LabelConfig(enabled=True, labels={"env": "prod"}))
    assert mgr.get_labels() == {"env": "prod"}


def test_annotate_adds_labels():
    mgr = LabelManager(LabelConfig(enabled=True, labels={"env": "prod"}))
    result = mgr.annotate({"command": "echo hi"})
    assert result["labels"] == {"env": "prod"}
    assert result["command"] == "echo hi"


def test_filter_entries_by_label():
    mgr = LabelManager(LabelConfig(enabled=True, labels={}))
    entries = [
        {"id": 1, "labels": {"env": "prod"}},
        {"id": 2, "labels": {"env": "staging"}},
    ]
    result = mgr.filter_entries(entries, {"env": "prod"})
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_filter_entries_empty_selector_returns_all():
    mgr = LabelManager(LabelConfig(enabled=True, labels={}))
    entries = [{"id": 1}, {"id": 2}]
    assert mgr.filter_entries(entries, {}) == entries

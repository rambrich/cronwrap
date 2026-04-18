"""Tests for cronwrap.tags module."""
import pytest
from unittest.mock import patch
from cronwrap.tags import TagConfig, TagManager, parse_tags, matches_filter


def test_tag_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = TagConfig.from_env()
    assert cfg.enabled is False
    assert cfg.tags == []
    assert cfg.filter_tags == []


def test_tag_config_from_env():
    env = {"CRONWRAP_TAGS": "prod,nightly", "CRONWRAP_FILTER_TAGS": "prod"}
    with patch.dict("os.environ", env, clear=True):
        cfg = TagConfig.from_env()
    assert cfg.enabled is True
    assert "prod" in cfg.tags
    assert "nightly" in cfg.tags
    assert cfg.filter_tags == ["prod"]


def test_parse_tags_splits_correctly():
    assert parse_tags("a, b, c") == ["a", "b", "c"]


def test_parse_tags_empty_string():
    assert parse_tags("") == []


def test_matches_filter_empty_filter_always_true():
    assert matches_filter(["prod"], []) is True


def test_matches_filter_intersection():
    assert matches_filter(["prod", "nightly"], ["nightly"]) is True


def test_matches_filter_no_intersection():
    assert matches_filter(["staging"], ["prod"]) is False


def test_should_run_when_disabled():
    cfg = TagConfig(tags=[], filter_tags=[], enabled=False)
    mgr = TagManager(config=cfg)
    assert mgr.should_run(["anything"]) is True


def test_should_run_with_matching_tag():
    cfg = TagConfig(tags=["prod"], filter_tags=["prod"], enabled=True)
    mgr = TagManager(config=cfg)
    assert mgr.should_run(["prod"]) is True


def test_should_run_with_non_matching_tag():
    cfg = TagConfig(tags=["prod"], filter_tags=["prod"], enabled=True)
    mgr = TagManager(config=cfg)
    assert mgr.should_run(["staging"]) is False


def test_annotate_adds_tags():
    cfg = TagConfig(tags=["prod"], filter_tags=[], enabled=True)
    mgr = TagManager(config=cfg)
    result = mgr.annotate({"job": "backup"})
    assert result["tags"] == ["prod"]


def test_annotate_skips_when_no_tags():
    cfg = TagConfig(tags=[], filter_tags=[], enabled=False)
    mgr = TagManager(config=cfg)
    result = mgr.annotate({"job": "backup"})
    assert "tags" not in result

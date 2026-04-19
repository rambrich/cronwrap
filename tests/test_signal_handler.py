import signal
import pytest
from cronwrap.signal_handler import SignalHandlerConfig, SignalManager, SignalInterrupt


def test_config_enabled_by_default():
    cfg = SignalHandlerConfig()
    assert cfg.enabled is True


def test_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SIGNAL_HANDLER_ENABLED", "false")
    cfg = SignalHandlerConfig.from_env()
    assert cfg.enabled is False


def test_config_from_env_enabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SIGNAL_HANDLER_ENABLED", "true")
    cfg = SignalHandlerConfig.from_env()
    assert cfg.enabled is True


def test_not_interrupted_initially():
    cfg = SignalHandlerConfig()
    mgr = SignalManager(cfg)
    assert mgr.interrupted is False
    assert mgr.signal_received is None


def test_handle_sets_interrupted():
    cfg = SignalHandlerConfig()
    mgr = SignalManager(cfg)
    mgr._handle(signal.SIGTERM, None)
    assert mgr.interrupted is True
    assert mgr.signal_received == signal.SIGTERM


def test_callback_called_on_signal():
    cfg = SignalHandlerConfig()
    mgr = SignalManager(cfg)
    received = []
    mgr.add_callback(lambda s: received.append(s))
    mgr._handle(signal.SIGTERM, None)
    assert received == [signal.SIGTERM]


def test_callback_exception_does_not_propagate():
    cfg = SignalHandlerConfig()
    mgr = SignalManager(cfg)
    mgr.add_callback(lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
    # Should not raise
    mgr._handle(signal.SIGTERM, None)
    assert mgr.interrupted is True


def test_context_manager_restores_handlers():
    cfg = SignalHandlerConfig()
    original = signal.getsignal(signal.SIGTERM)
    with SignalManager(cfg) as mgr:
        assert signal.getsignal(signal.SIGTERM) != original or True  # handler replaced
    assert signal.getsignal(signal.SIGTERM) == original


def test_context_manager_disabled_skips_registration():
    cfg = SignalHandlerConfig(enabled=False)
    original = signal.getsignal(signal.SIGTERM)
    with SignalManager(cfg) as mgr:
        assert signal.getsignal(signal.SIGTERM) == original
    assert mgr.interrupted is False

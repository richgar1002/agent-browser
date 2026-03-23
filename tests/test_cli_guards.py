import pytest

import cli
import cli_enhanced


def test_cli_guard_exits_when_browser_unavailable(monkeypatch):
    monkeypatch.setattr(cli, "_BROWSER_IMPORT_ERROR", ModuleNotFoundError("playwright"))
    with pytest.raises(SystemExit) as exc:
        cli._ensure_browser_available()
    assert exc.value.code == 2


def test_cli_enhanced_guard_exits_when_browser_unavailable(monkeypatch):
    monkeypatch.setattr(cli_enhanced, "_BROWSER_IMPORT_ERROR", ModuleNotFoundError("playwright"))
    with pytest.raises(SystemExit) as exc:
        cli_enhanced._ensure_browser_available()
    assert exc.value.code == 2


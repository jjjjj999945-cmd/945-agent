from datetime import date


def test_app_date_uses_the_system_date_without_a_reference_override(monkeypatch):
    monkeypatch.delenv("945_REFERENCE_DATE", raising=False)

    from backend.app.core.dates import app_date

    assert app_date() == date.today().isoformat()


def test_app_date_uses_the_reference_override_for_deterministic_tests(monkeypatch):
    monkeypatch.setenv("945_REFERENCE_DATE", "2026-07-11")

    from backend.app.core.dates import app_date

    assert app_date() == "2026-07-11"

import pytest

from backend.scripts import run_http_qa_server, run_mongo_qa_server


def test_http_qa_server_starts_uvicorn_with_subprocess(monkeypatch):
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> None:
        calls.append((command, kwargs))

    monkeypatch.setattr(run_http_qa_server.subprocess, "run", run)
    monkeypatch.setattr(
        run_http_qa_server.os,
        "execvpe",
        lambda *_: pytest.fail("HTTP QA server must not use os.execvpe on Windows."),
    )

    run_http_qa_server.main()

    assert calls[0][0][1:4] == ["-m", "uvicorn", "backend.app.main:app"]
    assert calls[0][1]["check"] is True
    assert calls[0][1]["env"]["945_STORAGE_BACKEND"] == "demo"


def test_mongo_qa_server_starts_uvicorn_with_subprocess(monkeypatch):
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> None:
        calls.append((command, kwargs))

    monkeypatch.setattr(run_mongo_qa_server.subprocess, "run", run)
    monkeypatch.setattr(
        run_mongo_qa_server.os,
        "execvpe",
        lambda *_: pytest.fail("Mongo QA server must not use os.execvpe on Windows."),
    )

    run_mongo_qa_server.main()

    assert calls[1][0][1:4] == ["-m", "uvicorn", "backend.app.main:app"]
    assert calls[1][1]["check"] is True
    assert calls[1][1]["env"]["945_STORAGE_BACKEND"] == "mongo"

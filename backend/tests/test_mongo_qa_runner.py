from types import SimpleNamespace

from backend.scripts import run_mongo_qa


def test_mongo_qa_runner_uses_an_isolated_dynamic_port_and_removes_the_container(monkeypatch):
    commands: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object):
        commands.append((command, kwargs))
        if command[:2] == ["docker", "port"]:
            return SimpleNamespace(returncode=0, stdout="127.0.0.1:49153\n", stderr="")
        if command[:2] == ["docker", "exec"]:
            return SimpleNamespace(returncode=0, stdout="1\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="container-id\n", stderr="")

    monkeypatch.setattr(run_mongo_qa, "_run", run)
    monkeypatch.setattr(run_mongo_qa, "uuid4", lambda: SimpleNamespace(hex="test-mongo"))

    assert run_mongo_qa.main() == 0

    assert commands[0][0] == [
        "docker",
        "run",
        "--detach",
        "--name",
        "945-mongo-qa-test-mongo",
        "-p",
        "127.0.0.1::27017",
        "mongo:8.0",
    ]
    playwright_command, playwright_kwargs = next(
        (command, kwargs) for command, kwargs in commands if command[:2] == [run_mongo_qa._npx_command(), "playwright"]
    )
    assert playwright_command[-1] == "--config=playwright.mongo.config.ts"
    assert playwright_kwargs["env"]["945_MONGODB_URI"] == "mongodb://127.0.0.1:49153"
    assert commands[-1][0] == ["docker", "rm", "--force", "945-mongo-qa-test-mongo"]

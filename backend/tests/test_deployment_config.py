from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_env_template() -> dict[str, str]:
    return {
        key: value
        for line in (ROOT / ".env.production.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", 1)]
    }


def test_production_template_declares_real_agent_runtime_configuration():
    env = read_env_template()

    assert env["945_LLM_PROVIDER"] == "deepseek"
    assert env["DEEPSEEK_API_KEY"] == "replace-with-your-deepseek-key"
    assert env["945_LANGSMITH_TRACING"] == "false"
    assert env["LANGSMITH_API_KEY"] == ""
    assert env["945_AUTH_SECRET"] == "replace-with-a-long-random-secret"


def test_compose_keeps_the_local_production_service_contract():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "mongo_data:/data/db" in compose
    assert "945_STORAGE_BACKEND: mongo" in compose
    assert "945_APP_ENV: production" in compose
    assert '945_AUTH_REQUIRED: "true"' in compose
    assert '"8080:80"' in compose


def test_docker_build_context_excludes_local_and_generated_files():
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {".git", ".worktrees", ".venv", "node_modules", "dist", "output", "test-results"} <= ignored
    assert ".env.production" in ignored

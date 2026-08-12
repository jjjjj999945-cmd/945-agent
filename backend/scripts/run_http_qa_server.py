import os
import subprocess
import sys


HTTP_QA_ENVIRONMENT = {
    "945_STORAGE_BACKEND": "demo",
    "945_LLM_PROVIDER": "deterministic",
    "945_APP_ENV": "development",
    "945_REFERENCE_DATE": "2026-07-11",
}


def main() -> None:
    environment = os.environ | HTTP_QA_ENVIRONMENT
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        check=True,
        env=environment,
    )


if __name__ == "__main__":
    main()

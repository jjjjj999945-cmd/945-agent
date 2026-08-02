import os
import subprocess
import sys
from pathlib import Path


MONGO_QA_ENVIRONMENT = {
    "945_STORAGE_BACKEND": "mongo",
    "945_MONGODB_URI": "mongodb://127.0.0.1:27017",
    "945_MONGODB_DATABASE": "945_mongo_qa",
    "945_LLM_PROVIDER": "deterministic",
    "945_APP_ENV": "development",
    "945_REFERENCE_DATE": "2026-07-11",
}


def main() -> None:
    environment = os.environ | MONGO_QA_ENVIRONMENT
    script_path = Path(__file__).with_name("reset_mongo_database.py")
    subprocess.run([sys.executable, str(script_path)], check=True, env=environment)
    os.execvpe(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        environment,
    )


if __name__ == "__main__":
    main()

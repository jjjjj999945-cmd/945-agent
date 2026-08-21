import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from pymongo import MongoClient

from backend.app.models.domain import AgentRun
from backend.app.repositories.mongo import MongoRepository
from backend.app.services.agent_run_lease import lease_token_from_run
from backend.app.services.repository_store import RepositoryBackedStore


pytestmark = pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run Mongo lease tests.",
)


def test_two_mongo_stores_allow_only_one_resume_owner():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2000)
    database_name = "945_agent_lease_test"
    client.drop_database(database_name)
    first = RepositoryBackedStore(MongoRepository(client[database_name]))
    second = RepositoryBackedStore(MongoRepository(client[database_name]))
    first.seed_demo_data()
    try:
        created = first.create_agent_run_with_lease(
            AgentRun(
                agent_run_id="run-mongo-race",
                user_id="demo-user-945",
                status="running",
                started_at="2026-08-21T12:00:00Z",
            ),
            "worker-a",
        )
        assert created is not None
        assert (
            second.create_agent_run_with_lease(
                created.model_copy(),
                "worker-duplicate",
            )
            is None
        )
        client[database_name]["agent_runs"].update_one(
            {"_id": created.agent_run_id},
            {
                "$set": {
                    "lease_expires_at": datetime.now(UTC) - timedelta(seconds=1)
                }
            },
        )
        assert first.interrupt_expired_agent_runs(created.user_id) == 1

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda owner: second.acquire_agent_run_lease(
                        created.user_id,
                        created.agent_run_id,
                        owner,
                    ),
                    ["worker-b", "worker-c"],
                )
            )

        winners = [run for run in results if run is not None]
        assert len(winners) == 1
        assert winners[0].lease_version == 2
        assert (
            first.transition_agent_run_with_lease(
                lease_token_from_run(created),
                created.model_copy(update={"status": "completed"}),
            )
            is None
        )
    finally:
        client.drop_database(database_name)
        client.close()

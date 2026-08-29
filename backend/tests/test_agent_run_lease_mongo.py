import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from pymongo import MongoClient

from backend.app.models.domain import AgentMessage, AgentRun
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
        created_token = lease_token_from_run(created)
        observed = second.list_agent_runs(created.user_id)
        assert observed is not None
        assert observed[0].status == "running"
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
        interrupted = second.list_agent_runs(created.user_id)
        assert interrupted is not None
        assert interrupted[0].status == "interrupted"

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
        winner = winners[0]
        assert winner.lease_version == 2
        winner_token = lease_token_from_run(winner)
        assert first.renew_agent_run_lease(created_token) is None
        assert (
            first.set_agent_run_resume_checkpoint(
                created_token,
                "checkpoint-stale",
            )
            is None
        )
        assert (
            first.transition_agent_run_with_lease(
                created_token,
                created.model_copy(update={"status": "completed"}),
            )
            is None
        )
        assert first.list_agent_messages(created.user_id) == []
        completed = second.transition_agent_run_with_lease(
            winner_token,
            winner.model_copy(
                update={
                    "status": "completed",
                    "completed_at": "2026-08-21T12:01:00Z",
                    "messages_persisted": False,
                }
            ),
        )
        assert completed is not None

        messages = [
            AgentMessage(
                message_id=f"msg-user-{created.agent_run_id}",
                user_id=created.user_id,
                role="user",
                content="继续任务",
                locale="zh-CN",
                created_at="2026-08-21T12:01:00Z",
            ),
            AgentMessage(
                message_id=f"msg-agent-{created.agent_run_id}",
                user_id=created.user_id,
                role="agent",
                content="恢复完成",
                locale="zh-CN",
                created_at="2026-08-21T12:01:00Z",
            ),
        ]
        for message in messages:
            second.save_agent_message(message)
            second.save_agent_message(message)
        assert second.mark_agent_run_messages_persisted(
            completed.user_id,
            completed.agent_run_id,
            completed.lease_version,
        )

        final_runs = first.list_agent_runs(created.user_id)
        final_messages = first.list_agent_messages(created.user_id)
        assert final_runs is not None
        assert final_runs[0].status == "completed"
        assert final_runs[0].lease_version == 2
        assert final_runs[0].messages_persisted is True
        assert final_messages is not None
        assert [message.message_id for message in final_messages] == [
            f"msg-user-{created.agent_run_id}",
            f"msg-agent-{created.agent_run_id}",
        ]
    finally:
        client.drop_database(database_name)
        client.close()

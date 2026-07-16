from backend.app.core.config import get_settings
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import AgentChatInput, WorkoutLogInput
from backend.app.repositories.mongo import MongoRepository
from backend.app.services import demo_store
from backend.app.services.repository_store import RepositoryBackedStore
from backend.tests.test_mongo_repository import FakeDatabase


def test_demo_store_delegates_to_repository_store_in_mongo_mode(monkeypatch):
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    get_settings.cache_clear()
    store = RepositoryBackedStore(MongoRepository(FakeDatabase()))
    store.seed_demo_data()
    demo_store.set_repository_store_for_tests(store)

    try:
        saved = demo_store.create_workout_log(
            WorkoutLogInput(
                user_id=DEMO_USER_ID,
                date=TODAY_DATE,
                status="completed",
                exercises=[{"name": "深蹲", "sets": [{"reps": 8}]}]
            )
        )
        reply = demo_store.create_agent_reply(
            AgentChatInput(
                user_id=DEMO_USER_ID,
                locale="zh-CN",
                message="今天深蹲做了 4 组，每组 8 次，80kg。"
            )
        )

        assert saved.workout_log_id.startswith("workout-2026-07-11-")
        assert demo_store.list_workout_logs(DEMO_USER_ID)[0].workout_log_id == saved.workout_log_id
        assert reply.record_draft.type == "workout_log"
        assert [message.role for message in demo_store.list_agent_messages(DEMO_USER_ID)] == ["user", "agent"]
    finally:
        demo_store.set_repository_store_for_tests(None)
        monkeypatch.delenv("945_STORAGE_BACKEND", raising=False)
        get_settings.cache_clear()

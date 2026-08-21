from backend.app.core.config import get_settings
from backend.app.models.domain import AgentRun, WorkoutLog
from backend.app.repositories.mongo import MongoRepository, mongo_document_to_model, model_to_mongo_document


class FakeCollection:
    def __init__(self):
        self.documents = []

    def update_one(self, filter_doc, update_doc, upsert=False):
        replacement = update_doc["$set"]
        existing = next(
            (
                document
                for document in self.documents
                if all(document.get(key) == value for key, value in filter_doc.items())
            ),
            None
        )
        if existing:
            existing.update(replacement)
        elif upsert:
            self.documents.append({**filter_doc, **replacement})

    def find(self, filter_doc):
        return [
            document
            for document in self.documents
            if all(document.get(key) == value for key, value in filter_doc.items())
        ]

    def find_one(self, filter_doc):
        return next(iter(self.find(filter_doc)), None)

    def find_one_and_update(
        self,
        filter_doc,
        update_doc,
        *,
        upsert=False,
        return_document=None,
    ):
        existing = self.find_one(filter_doc)
        if existing is None:
            if not upsert:
                return None
            existing = dict(filter_doc)
            self.documents.append(existing)
        existing.update(update_doc["$set"])
        return existing


class FakeDatabase(dict):
    def __getitem__(self, collection_name):
        if collection_name not in self:
            self[collection_name] = FakeCollection()
        return dict.__getitem__(self, collection_name)


def test_settings_default_to_demo_store():
    settings = get_settings()

    assert settings.storage_backend == "demo"
    assert settings.mongodb_uri == "mongodb://127.0.0.1:27017"
    assert settings.mongodb_database == "945"


def test_model_to_mongo_document_uses_domain_id_as_mongo_id():
    log = WorkoutLog(
        workout_log_id="workout-2026-07-11-1",
        user_id="demo-user-945",
        plan_id="plan-2026-07-11-demo",
        date="2026-07-11",
        status="completed",
        duration_minutes=58,
        exercises=[{"name": "深蹲", "sets": [{"reps": 8, "weight_kg": 80}]}],
        rpe=8,
        notes="测试记录",
        created_at="2026-07-11T00:00:00.000Z",
        updated_at="2026-07-11T00:00:00.000Z"
    )

    document = model_to_mongo_document(log, id_field="workout_log_id")

    assert document["_id"] == "workout-2026-07-11-1"
    assert document["workout_log_id"] == "workout-2026-07-11-1"
    assert document["exercises"][0]["sets"][0]["weight_kg"] == 80.0


def test_mongo_document_to_model_ignores_mongo_internal_id():
    document = {
        "_id": "workout-2026-07-11-1",
        "workout_log_id": "workout-2026-07-11-1",
        "user_id": "demo-user-945",
        "plan_id": None,
        "date": "2026-07-11",
        "status": "completed",
        "duration_minutes": None,
        "exercises": [{"name": "深蹲", "sets": [{"reps": 8}]}],
        "rpe": None,
        "notes": None,
        "created_at": "2026-07-11T00:00:00.000Z",
        "updated_at": "2026-07-11T00:00:00.000Z"
    }

    log = mongo_document_to_model(document, WorkoutLog)

    assert log.workout_log_id == "workout-2026-07-11-1"
    assert log.exercises[0].name == "深蹲"


def test_repository_upserts_and_lists_models_by_user():
    database = FakeDatabase()
    repository = MongoRepository(database)
    log = WorkoutLog(
        workout_log_id="workout-2026-07-11-1",
        user_id="demo-user-945",
        plan_id=None,
        date="2026-07-11",
        status="completed",
        duration_minutes=None,
        exercises=[{"name": "深蹲", "sets": [{"reps": 8}]}],
        rpe=None,
        notes=None,
        created_at="2026-07-11T00:00:00.000Z",
        updated_at="2026-07-11T00:00:00.000Z"
    )

    repository.upsert_model("workout_logs", log, id_field="workout_log_id")
    repository.upsert_model("workout_logs", log.model_copy(update={"notes": "已更新"}), id_field="workout_log_id")
    logs = repository.list_models("workout_logs", WorkoutLog, {"user_id": "demo-user-945"})

    assert len(logs) == 1
    assert logs[0].notes == "已更新"


def test_repository_find_one_and_update_returns_the_updated_model():
    database = FakeDatabase()
    repository = MongoRepository(database)
    run = AgentRun(
        agent_run_id="run-atomic",
        user_id="demo-user-945",
        status="interrupted",
        started_at="2026-08-21T12:00:00Z",
    )
    repository.upsert_model("agent_runs", run, id_field="agent_run_id")

    updated = repository.find_one_and_update_model(
        "agent_runs",
        AgentRun,
        {"_id": "run-atomic", "status": "interrupted"},
        {"$set": {"status": "running", "lease_version": 1}},
    )

    assert updated is not None
    assert updated.status == "running"
    assert updated.lease_version == 1

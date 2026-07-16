from typing import Any, TypeVar

from pydantic import BaseModel

from backend.app.core.config import get_settings


ModelT = TypeVar("ModelT", bound=BaseModel)


def model_to_mongo_document(model: BaseModel, id_field: str) -> dict[str, Any]:
    document = model.model_dump()
    document["_id"] = document[id_field]
    return document


def mongo_document_to_model(document: dict[str, Any], model_type: type[ModelT]) -> ModelT:
    payload = {key: value for key, value in document.items() if key != "_id"}
    return model_type(**payload)


class MongoRepository:
    def __init__(self, database: Any):
        self.database = database

    def upsert_model(self, collection_name: str, model: BaseModel, id_field: str) -> None:
        document = model_to_mongo_document(model, id_field=id_field)
        self.database[collection_name].update_one(
            {"_id": document["_id"]},
            {"$set": document},
            upsert=True
        )

    def list_models(
        self,
        collection_name: str,
        model_type: type[ModelT],
        filter_doc: dict[str, Any] | None = None
    ) -> list[ModelT]:
        documents = self.database[collection_name].find(filter_doc or {})
        return [mongo_document_to_model(document, model_type) for document in documents]

    def get_model(
        self,
        collection_name: str,
        model_type: type[ModelT],
        filter_doc: dict[str, Any]
    ) -> ModelT | None:
        document = self.database[collection_name].find_one(filter_doc)
        if document is None:
            return None
        return mongo_document_to_model(document, model_type)


def create_mongo_repository() -> MongoRepository:
    from pymongo import MongoClient

    settings = get_settings()
    client = MongoClient(settings.mongodb_uri)
    return MongoRepository(client[settings.mongodb_database])

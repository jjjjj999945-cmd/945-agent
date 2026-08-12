import os

from pymongo import MongoClient


database_name = os.getenv("945_MONGODB_DATABASE", "")
if not database_name.endswith("_qa"):
    raise SystemExit("Refusing to delete a MongoDB database without the '_qa' suffix.")

MongoClient(os.getenv("945_MONGODB_URI", "mongodb://127.0.0.1:27017")).drop_database(database_name)

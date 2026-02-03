# backend/db/mongo.py
from pymongo import MongoClient
import os
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
_client = MongoClient(MONGO_URI)

def get_db():
    return _client[MONGO_DB_NAME]

def close_db():
    _client.close()
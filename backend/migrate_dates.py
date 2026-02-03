from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

print("Starting migration...")
cursor = db.bills.find({"bill_date": {"$type": "string"}})
count = 0
for doc in cursor:
    date_str = doc["bill_date"]
    try:
        # standardizing to datetime object
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        db.bills.update_one(
            {"_id": doc["_id"]},
            {"$set": {"bill_date": dt}}
        )
        count += 1
    except Exception as e:
        print(f"Failed to migrate doc {doc['_id']}: {e}")

print(f"Migrated {count} documents.")

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

bills = list(db.bills.find({}, {"bill_date": 1, "vendor": 1, "total_amount": 1}))
print(f"Total bills: {len(bills)}")
for b in bills:
    date_val = b.get("bill_date")
    print(f"Vendor: {b.get('vendor')}, Date: {date_val}, Type: {type(date_val)}")

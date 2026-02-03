def create_indexes(db):
    db.bills.create_index([("user_id", 1), ("bill_date", 1)])
    db.bills.create_index([("user_id", 1), ("category", 1), ("bill_date", 1)])
    db.bills.create_index([("user_id", 1), ("vendor", 1)])
    db.bills.create_index([("user_id", 1), ("total_amount", 1)])

from datetime import datetime
def mongo_op(op: str):
    return {
        ">": "$gt",
        ">=": "$gte",
        "<": "$lt",
        "<=": "$lte",
        "=": "$eq",
        "!=": "$ne"
    }.get(op)

def semantic_search(user_id: str, plan: dict, user_query: str):
    mongo_match = {"user_id": user_id}

    if plan.entities.get("category"):
        mongo_match["category"] = plan.entities["category"]

    if plan.time_range:
        mongo_match["bill_date"] = {
            "$gte": datetime.fromisoformat(plan.time_range["from"]),
            "$lte": datetime.fromisoformat(plan.time_range["to"])
        }

    pipeline = [
        {"$match": mongo_match},
        {"$project": {"_id": 1}}
    ]

    return {
        "mongo_pipeline": pipeline,
        "vector_query": {
            "query": user_query,
            "filter": {
                "user_id": user_id,
                "category": plan.entities.get("category")
            },
            "top_k": 5
        }
    }
def semantic_compare(user_id: str, plan: dict, user_query: str):
    return {
        "vector_query": {
            "query": user_query,
            "filter": {
                "user_id": user_id,
                "category": plan.entities.get("category")
            },
            "top_k": 10
        }
    }

#mixed
def aggregation_with_explanation(user_id: str, plan: dict, user_query: str):
    aggregation_pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "category": plan.entities["category"],
                "bill_date": {
                    "$gte": datetime.fromisoformat(plan.time_range["from"]),
                    "$lte": datetime.fromisoformat(plan.time_range["to"])
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "total_amount": {"$sum": "$amount"},
                "bill_ids": {"$push": "$_id"}
            }
        }
    ]

    vector_query = {
        "query": user_query,
        "filter": {
            "user_id": user_id,
            "category": plan.entities["category"]
        },
        "top_k": 5
    }

    return {
        "mongo_pipeline": aggregation_pipeline,
        "vector_query": vector_query
    }
def filter_with_explanation(user_id: str, plan: dict, user_query: str):
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "category": plan.entities["category"]
            }
        }
    ]

    return {
        "mongo_pipeline": pipeline,
        "vector_query": {
            "query": "unusual charges",
            "filter": {
                "user_id": user_id,
                "category": plan.entities["category"]
            },
            "top_k": 3
        }
    }
# FILTER / AGGREGATION TEMPLATES
def  list_bills(user_id: str, params: dict):
    match = {"user_id": user_id}

    if params.entities.get("category"):
        match["category"] = params.entities["category"]

    if params.entities.get("subcategory"):
        match["subcategory"] = params.entities["subcategory"]

    if params.filters and params.filters.get("amount"):
        match["amount"] = {
            mongo_op(params.filters["amount"]["operator"]):
            params.filters["amount"]["value"]
        }

    if params.time_range:
        match["bill_date"] = {
            "$gte": datetime.fromisoformat(params.time_range["from"]),
            "$lte": datetime.fromisoformat(params.time_range["to"])
        }

    return [
        {"$match": match},
        {"$sort": {"bill_date": -1}}
    ]

def total_spend(user_id: str, params: dict):
    return [
        {
            "$match": {
                "user_id": user_id,
                "category": params.entities["category"],
                "bill_date": {
                    "$gte": datetime.fromisoformat(params.time_range["from"]),
                    "$lte": datetime.fromisoformat(params.time_range["to"])
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "total_amount": {"$sum": "$amount"}
            }
        }
    ]
def monthly_summary(user_id: str, params: dict):
    return [
        {
            "$match": {
                "user_id": user_id,
                "category": params.entities.get("category"),
                "bill_date": {
                    "$gte": datetime.fromisoformat(params.time_range["from"]),
                    "$lte": datetime.fromisoformat(params.time_range["to"])
                }
            }
        },
        {
            "$group": {
                "_id": {"$month": "$bill_date"},
                "total": {"$sum": "$amount"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
def bills_by_payment_mode(user_id: str, params: dict):
    return [
        {"$match": {"user_id": user_id}},
        {
            "$lookup": {
                "from": "payments",
                "localField": "_id",
                "foreignField": "bill_id",
                "as": "payment"
            }
        },
        {"$unwind": "$payment"},
        {"$match": {"payment.mode": params.entities["payment_mode"]}}
    ]
def bills_by_vendor(user_id: str, params: dict):
    return [
        {
            "$match": {
                "user_id": user_id,
                "vendor": params.entities["vendor"]
            }
        },
        {"$sort": {"bill_date": -1}}
    ]
def category_breakdown(user_id: str, params: dict):
    return [
        {
            "$match": {
                "user_id": user_id,
                "bill_date": {
                    "$gte": datetime.fromisoformat(params.time_range["from"]),
                    "$lte": datetime.fromisoformat(params.time_range["to"])
                }
            }
        },
        {
            "$group": {
                "_id": "$category",
                "total": {"$sum": "$amount"}
            }
        },
        {"$sort": {"total": -1}}
    ]

def sum_amount(user_id: str, plan):
    match = {
        "user_id": user_id
    }

    # optional category filter
    if plan.entities.get("category"):
        match["category"] = plan.entities["category"]

    # optional time range
    if plan.time_range:
        match["bill_date"] = {
            "$gte": datetime.fromisoformat(plan.time_range["from"]),
            "$lte": datetime.fromisoformat(plan.time_range["to"]),
        }

    return [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"}
            }
        }
    ]


def count_bills(user_id: str):
    return [
        {"$match": {"user_id": user_id}},
        {"$count": "count"}
    ]


def find_bills(user_id: str):
    return [
        {"$match": {"user_id": user_id}},
        {"$limit": 20}
    ]


QUERY_TEMPLATES = {
    "LIST_BILLS":  list_bills,
    "TOTAL_SPEND": total_spend,
    "MONTHLY_SUMMARY": monthly_summary,
    "BILLS_BY_PAYMENT_MODE": bills_by_payment_mode,
    "BILLS_BY_VENDOR": bills_by_vendor,
    "CATEGORY_BREAKDOWN": category_breakdown,

    # Semantic
    "SEMANTIC_SEARCH": semantic_search,
    "SEMANTIC_COMPARE": semantic_compare,

    # Mixed
    "AGGREGATION_WITH_EXPLANATION": aggregation_with_explanation,
    "FILTER_WITH_EXPLANATION": filter_with_explanation,

    "sum": sum_amount,
    "count": count_bills,
    "find": find_bills,
}
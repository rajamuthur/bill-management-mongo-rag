import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.embeddings import HuggingFaceEmbeddings

from pinecone import Pinecone, ServerlessSpec

from templates.resolve_time_range_to_mongo import resolve_time_range_to_mongo
from templates.safe_time import extract_time_range_semantic, safe_time_range
from templates.query_templates import QUERY_TEMPLATES
from templates.time_resolver import resolve_time_range
from templates.time_range import TimeRange, DatePart

# -------------------------------------------------------------------
# ENV
# -------------------------------------------------------------------

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_REGION = os.getenv("PINECONE_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


from typing import Optional, Dict, Any
from pydantic import BaseModel



# -------------------------------------------------------------------
# Mongo
# -------------------------------------------------------------------

mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_DB_NAME]
bills_col = db.bills

# -------------------------------------------------------------------
# Pinecone
# -------------------------------------------------------------------

INDEX_NAME = "bills-rag"

pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in pinecone_client.list_indexes().names():
    pinecone_client.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="dotproduct",
        spec=ServerlessSpec(
            cloud="aws",
            region=PINECONE_REGION,
        ),
    )

pc_index = pinecone_client.Index(INDEX_NAME)

# -------------------------------------------------------------------
# LLM
# -------------------------------------------------------------------
from helper import groqllm
groq_llm = groqllm

# -------------------------------------------------------------------
# Embeddings
# -------------------------------------------------------------------

embeddings_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# -------------------------------------------------------------------
# Query Plan Schema
# -------------------------------------------------------------------
from typing import Optional, Dict, Any

class QueryPlan1(BaseModel):
    type: str
    operation: str
    entities: dict
    filters: Optional[dict] = None
    time_range: Optional[Dict[str, Any]] = None   # 👈 semantic only
    needs_rag: bool = False

class QueryPlan(BaseModel):
    type: str = Field(..., description="FILTER, AGGREGATION, SEMANTIC, or MIXED")
    operation: str = Field(..., description="sum, count, or list")
    
    # Filters are for top-level fields (vendor, category, payment_method, etc.)
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Top-level bill filters like 'payment_method', 'vendor', 'category', 'bill_no'"
    )
    
    # Entities are for nested fields (items inside the bill)
    entities: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Search for specific items. Use key 'item' for product descriptions."
    )
    
    time_range: Optional[Dict[str, Any]] = None
    needs_rag: bool = False


# -------------------------------------------------------------------
# Classifier Chain
# -------------------------------------------------------------------
classifier_prompt2 = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a STRICT query planner for a bill management application.

You MUST output ONLY valid JSON.

You MUST choose type from EXACTLY one of:
- FILTER
- AGGREGATION
- SEMANTIC
- MIXED

DO NOT invent new types like SELECT, QUERY, SQL, etc.

Rules:
- FILTER → simple listing / filtering bills
- AGGREGATION → totals, sums, counts, grouping
- SEMANTIC → explanation, reasoning
- MIXED → aggregation + explanation

CRITICAL RULES (MANDATORY):
- The "filters" field MUST ONLY include non-time fields:
  - category
  - subcategory
  - status
  - currency

- NEVER include time or date logic in "filters".
- NEVER use fields like: date, from, to, now, range.
- ALL time meaning MUST go ONLY into "time_range".

- If a query mentions time, set "filters" to null.

The JSON MUST match this schema:
{{
  "type": "...",
  "operation": "...",
  "entities": {{}},
  "filters": null,
  "time_range": null,
  "needs_rag": false
}}
            """,
        ),
        ("human", "{query}"),
    ]
)

classifier_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a STRICT query planner for a bill management application.
You MUST output ONLY valid JSON.

### SCHEMA DEFINITIONS
1. **type**: One of [FILTER, AGGREGATION, SEMANTIC, MIXED]
2. **operation**: One of [list, sum, count]
3. **entities**: Use ONLY for items/products found INSIDE the bill (e.g., "Rice", "Milk", "Soap"). 
   - Format: {{"item": "product name"}}
4. **filters**: Use ONLY for top-level bill fields:
   - "vendor": Store names (e.g., "Fresh Mart")
   - "category": Broad types (e.g., "Grocery", "Medical", "Travel")
   - "payment_method": Method used (e.g., "CASH", "UPI", "CARD")
   - "bill_no": Specific bill IDs
5. **time_range**: Extract the time intent.

### CRITICAL MAPPING RULES
- "Rice", "Milk", "Chicken" are **ENTITIES** (item), NOT filters.
- "CASH", "UPI", "Online" are **FILTERS** (payment_method).
- If the user asks for a specific product, set `entities = {{"item": "product_name"}}`.
- If the user asks for a total amount, `operation` is "sum".
- If the user asks for a count of bills, `operation` is "count".
- NEVER include time/date logic in "filters". All time goes in "time_range".

### EXAMPLES
Query: "show all the bills of Rice purchase in jan 2026"
Output: {{
  "type": "FILTER",
  "operation": "list",
  "entities": {{"item": "Rice"}},
  "filters": null,
  "time_range": {{ "type": "ABSOLUTE", "granularity": "month", "from": {{ "month": 1, "year": 2026 }} }},
  "needs_rag": false
}}

Query: "How much did I spend on groceries via UPI?"
Output: {{
  "type": "AGGREGATION",
  "operation": "sum",
  "entities": null,
  "filters": {{"category": "Grocery", "payment_method": "UPI"}},
  "time_range": null,
  "needs_rag": false
}}
"""
        ),
        ("human", "{query}"),
    ]
)

classifier_prompt1 = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a STRICT query planner for a bill management application.

You MUST output ONLY valid JSON.
You MUST choose type from EXACTLY one of:
- FILTER
- AGGREGATION
- SEMANTIC
- MIXED

DO NOT invent new types like SELECT, QUERY, SQL, etc.

Rules:
- FILTER → simple listing / filtering bills
- AGGREGATION → totals, sums, counts, grouping
- SEMANTIC → explanation, reasoning, comparison without totals
- MIXED → aggregation + explanation

The JSON MUST match this schema:
{{
  "type": "...",
  "operation": "...",
  "entities": {{}},
  "filters": null,
  "time_range": null,
  "needs_rag": false
}}
            """,
        ),
        ("human", "{query}"),
    ]
)

classifier_chain = (
    classifier_prompt
    | groq_llm
    | JsonOutputParser(pydantic_object=QueryPlan)
)

# -------------------------------------------------------------------
# Mongo Helpers
# -------------------------------------------------------------------


def run_mongo_pipeline(pipeline: List[dict]):
    return list(bills_col.aggregate(pipeline))

def execute_mongo(plan: QueryPlan, user_id: str):
    match = {"user_id": user_id}
    print(f"[entities] {plan.entities} ({type(plan.entities)})")
    print(f"[FILTERS] {plan.filters} ({type(plan.filters)})")
    # 1️⃣ Bill-level filters (date, category, bill_no, vendor)
    if plan.filters:
        for key, value in plan.filters.items():
            if isinstance(value, str):
                # Use case-insensitive regex for vendor, payment_method, etc.
                match[key] = {"$regex": re.escape(value), "$options": "i"}
            else:
                match[key] = value

    entities = plan.entities or {}
    operation = plan.operation.lower()

    pipeline = [{"$match": match}]

    has_item = "item" in entities and entities["item"]

    # 2️⃣ ITEM-level queries
    if has_item:
        pipeline += [
            {"$unwind": "$items"},
            {
                "$match": {
                    "items.description": {
                        "$regex": entities["item"],
                        "$options": "i"
                    }
                }
            }
        ]

        if operation == "sum":
            pipeline.append({
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$items.amount"}
                }
            })

        elif operation == "count":
            pipeline.append({"$count": "total"})

        elif operation == "list":
            pipeline.append({
                "$project": {
                    "_id": 0,
                    "vendor": 1,
                    "bill_no": 1,
                    "bill_date": 1,
                    "category": 1,
                    "payment_method": 1,
                    "items": 1,
                    "item": "$items"
                }
            })

    # 3️⃣ BILL-level queries
    else:
        if operation == "sum":
            pipeline.append({
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$total_amount"}
                }
            })

        elif operation == "count":
            pipeline.append({"$count": "total"})

        elif operation == "list":
            pipeline.append({
                "$project": {
                    "_id": 0,
                    "vendor": 1,
                    "bill_no": 1,
                    "bill_date": 1,
                    "category": 1,
                    "payment_method": 1,
                    "items": 1,
                    "total_amount": 1
                }
            })

    # 🔍 Debug
    print("\n[MONGO PIPELINE]")
    for p in pipeline:
        print(p)

    return list(bills_col.aggregate(pipeline))

def execute_mongo_(plan: QueryPlan, user_id: str):
    match = {"user_id": user_id}

    # normal filters
    if plan.filters:
        match.update(plan.filters)

    # ⏱️ time filter applied HERE
    # if plan.time_range:
    #     match["bill_date"] = resolve_time_range_to_mongo(plan.time_range)

    pipeline = [
        {"$match": match},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]

    print("[MONGO PIPELINE]")
    for p in pipeline:
        print(p)

    return list(bills_col.aggregate(pipeline))
    

# -------------------------------------------------------------------
# Vector Search
# -------------------------------------------------------------------

def vector_search(
    query: str,
    user_id: str,
    category: Optional[str] = None,
    top_k: int = 5,
):
    vector = embeddings_model.embed_query(query)

    index_filter = {"user_id": user_id}
    if category:
        index_filter["category"] = category

    results = pc_index.query(
        vector=vector,
        top_k=top_k,
        filter=index_filter,
        include_metadata=True,
    )

    return [
        match["metadata"].get("text", "")
        for match in results.get("matches", [])
    ]

# -------------------------------------------------------------------
# Semantic Chain
# -------------------------------------------------------------------

def semantic_chain(plan: QueryPlan, user_query: str, user_id: str):
    context = vector_search(
        query=user_query,
        user_id=user_id,
        category=plan.entities.get("category"),
    )

    prompt = f"""
Answer the question using the following bill context:

{context}

Question: {user_query}
"""

    return groq_llm.invoke(prompt).content

# -------------------------------------------------------------------
# Mixed Chain
# -------------------------------------------------------------------

def mixed_chain(plan: QueryPlan, user_query: str, user_id: str):
    mongo_result = execute_mongo(plan, user_id)

    facts = mongo_result[0] if mongo_result else {}

    context = vector_search(
        query=user_query,
        user_id=user_id,
        category=plan.entities.get("category"),
    )

    prompt = f"""
Facts:
{facts}

Bill Details:
{context}

Answer the user question clearly.
"""

    return groq_llm.invoke(prompt).content

def normalize_time_range1(plan_dict: dict, user_query: str) -> dict:
    tr = plan_dict.get("time_range")

    # Case 1: TimeRange object → dict
    if isinstance(tr, TimeRange):
        plan_dict["time_range"] = tr.model_dump()

    # Case 2: string like "last 2 months"
    elif isinstance(tr, str):
        plan_dict["time_range"] = extract_time_range_semantic(user_query)

    # Case 3: missing / invalid
    elif tr is None or not isinstance(tr, dict):
        plan_dict["time_range"] = extract_time_range_semantic(user_query)

    return plan_dict

import re

RANGE_WORDS = r"\b(to|till|until|upto|between|from)\b"

def normalize_time_range(plan_dict: dict, user_query: str) -> dict:
    tr = plan_dict.get("time_range")

    if tr is None:
        return plan_dict

    # already valid semantic shape
    if not isinstance(tr, dict) or "type" not in tr:
        plan_dict["time_range"] = extract_time_range_semantic(user_query)
        return plan_dict

    # 🔥 SINGLE DAY COLLAPSE RULE
    if (
        tr.get("type") == "ABSOLUTE"
        and tr.get("from")
        and tr.get("to")
        and tr["from"].get("day")
        and tr["to"].get("day")
        and tr["from"]["month"] == tr["to"]["month"]
        and tr["from"]["year"] == tr["to"]["year"]
        and not re.search(RANGE_WORDS, user_query.lower())
    ):
        # collapse to single day
        plan_dict["time_range"] = {
            "type": "ABSOLUTE",
            "from": tr["to"],   # 👈 keep only the mentioned day
            "to": None,
            "granularity": "day"
        }

    return plan_dict


def normalize_time_range11(plan_dict: dict, user_query: str) -> dict:
    tr = plan_dict.get("time_range")

    # Case 1: missing or null
    if tr is None:
        return plan_dict

    # Case 2: already valid semantic shape
    if isinstance(tr, dict) and "type" in tr:
        return plan_dict

    # Case 3: garbage like {start, end} or strings
    # 👉 discard and re-extract semantically
    plan_dict["time_range"] = extract_time_range_semantic(user_query)

    return plan_dict


# -------------------------------------------------------------------
# Router
# -------------------------------------------------------------------
def query_router(user_query: str, user_id: str):
    plan_dict = classifier_chain.invoke({"query": user_query})

    # 🔒 Enforce semantic contract
    plan_dict = normalize_time_range(plan_dict, user_query)

    # Convert TimeRange object → dict if needed
    tr = plan_dict.get("time_range")
    if isinstance(tr, TimeRange):
        plan_dict["time_range"] = tr.model_dump()
        tr = plan_dict["time_range"]

    # HARD ASSERT
    if tr is not None:
        assert isinstance(tr, dict), f"time_range leaked as {type(tr)}"
        assert "type" in tr, "time_range missing type"
        assert "granularity" in tr, "time_range missing granularity"

    # ✅ Now safe to construct QueryPlan
    plan = QueryPlan(**plan_dict)

    # Resolve dates only at runtime
    if plan.time_range:
        tr_obj = TimeRange(**plan.time_range)
        mongo_range = resolve_time_range(tr_obj)

        if mongo_range:
            plan.filters = plan.filters or {}
            plan.filters["bill_date"] = mongo_range

    if plan.type in ("FILTER", "AGGREGATION"):
        return execute_mongo(plan, user_id)

    if plan.type == "SEMANTIC":
        return semantic_chain(plan, user_query, user_id)

    if plan.type == "MIXED":
        return mixed_chain(plan, user_query, user_id)

    raise ValueError(f"Unsupported query type: {plan.type}")

def query_router1(user_query: str, user_id: str):
    plan_dict = classifier_chain.invoke({"query": user_query})

    # 🔐 HARD GUARANTEE
    plan_dict = normalize_time_range(plan_dict, user_query)

    # 🔥 FORCE time_range to dict — NO EXCEPTIONS
    tr = plan_dict.get("time_range")
    print(f"[TIME RANGE RAW] {tr} ({type(tr)})")

    if isinstance(tr, TimeRange):
        print("[TIME RANGE NORMALIZED]")
        plan_dict["time_range"] = tr.model_dump()

    elif isinstance(tr, str):
        print("[TIME RANGE EXTRACTED FROM STRING]")
        plan_dict["time_range"] = extract_time_range_semantic(user_query)

    elif not isinstance(tr, dict):
        print("[TIME RANGE EXTRACTED FROM MISSING]")
        plan_dict["time_range"] = extract_time_range_semantic(user_query)

    # 🧪 HARD ASSERT (fail early, not inside Pydantic)
    assert isinstance(plan_dict["time_range"], dict), (
        f"time_range leaked as {type(plan_dict['time_range'])}"
    )

    # ✅ Now this will NEVER fail
    plan = QueryPlan(**plan_dict)

    plan.type = plan.type.upper()
    plan.operation = plan.operation.lower()

    print(
        f"[QUERY ROUTER] type={plan.type}, "
        f"operation={plan.operation}, "
        f"time_range={plan.time_range}"
    )

    print(f"[PLAN DICT] {plan_dict}")
    print(f"[PLAN] {plan}")

    # Resolve to Mongo only after validation
    if plan.time_range:
        tr_obj = TimeRange(**plan.time_range)
        mongo_range = resolve_time_range(tr_obj)

        if mongo_range:
            plan.filters = plan.filters or {}
            plan.filters["bill_date"] = mongo_range

    if plan.type in ("FILTER", "AGGREGATION"):
        return execute_mongo(plan, user_id)

    if plan.type == "SEMANTIC":
        return semantic_chain(plan, user_query, user_id)

    if plan.type == "MIXED":
        return mixed_chain(plan, user_query, user_id)

    raise ValueError(f"Unsupported query type: {plan.type}")

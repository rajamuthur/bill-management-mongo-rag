import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.embeddings import HuggingFaceEmbeddings

from pinecone import Pinecone, ServerlessSpec

from templates.query_templates import QUERY_TEMPLATES

# -------------------------------------------------------------------
# ENV
# -------------------------------------------------------------------

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_REGION = os.getenv("PINECONE_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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

groq_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",
    temperature=0,
)

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

class QueryPlan(BaseModel):
    type: str
    operation: Optional[str] = None
    entities: Dict[str, Any] = {}
    filters: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, str]] = None
    needs_rag: bool = False

# -------------------------------------------------------------------
# Classifier Chain
# -------------------------------------------------------------------

classifier_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a query planner for a bill management app. "
            "Output ONLY valid JSON matching the QueryPlan schema.",
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
    if not plan.operation:
        raise ValueError("Missing operation for Mongo execution")

    template_fn = QUERY_TEMPLATES.get(plan.operation)
    if not template_fn:
        raise ValueError(f"Unsupported operation: {plan.operation}")

    pipeline = template_fn(user_id, plan)
    return run_mongo_pipeline(pipeline)

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

# -------------------------------------------------------------------
# Router
# -------------------------------------------------------------------

def query_router(user_query: str, user_id: str):
    plan: QueryPlan = classifier_chain.invoke({"query": user_query})

    if plan.type in ("FILTER", "AGGREGATION"):
        return execute_mongo(plan, user_id)

    if plan.type == "SEMANTIC":
        return semantic_chain(plan, user_query, user_id)

    if plan.type == "MIXED":
        return mixed_chain(plan, user_query, user_id)

    raise ValueError(f"Unsupported query type: {plan.type}")

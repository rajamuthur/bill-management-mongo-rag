from pymongo import MongoClient
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_DB_NAME]
bills_col = db.bills


# embeddings_model = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2",
#     model_kwargs={"device": "cpu"},
#     encode_kwargs={"normalize_embeddings": True}
# )

from pinecone import Pinecone, ServerlessSpec
index_name = "bills-rag"
pinecone_client = Pinecone(
        api_key=os.getenv("PINECONE_API_KEY"),
    )

if index_name not in pinecone_client.list_indexes().names():
    pinecone_client.create_index(
        name=index_name,
        dimension=384,
        metric="dotproduct",
        spec=ServerlessSpec(
            cloud="aws",
            region=os.getenv("PINECONE_REGION"),
        ),
    )

pcIndex = pinecone_client.Index(index_name)
print('Pinecone index initialized:', index_name, pcIndex)

# groq_api_key = os.getenv("GROQ_API_KEY")
# groq_llm = ChatGroq(
#     api_key=groq_api_key,
#     model_name="llama-3.1-8b-instant",
#     temperature=0,
# )



# llm = ChatGroq(
#     model="llama3-70b-8192",
#     temperature=0
# )


# pc = Pinecone(api_key=PINECONE_API_KEY)
# index = pc.Index("bills-rag")

# embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )
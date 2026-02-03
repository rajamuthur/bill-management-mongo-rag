from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vector_db = Chroma(
    collection_name="bills",
    embedding_function=embeddings,
    persist_directory="./vector_store"
)


def insert_bill_vector(bill_id: str, user_id: str, text: str):
    vector_db.add_texts(
        texts=[text],
        metadatas=[{
            "bill_id": bill_id,
            "user_id": user_id
        }],
        ids=[bill_id]
    )

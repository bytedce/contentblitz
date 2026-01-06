# rag.py
import os
import pandas as pd
from typing import List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
import streamlit as st
from config import ALLOWED_DOMAINS, LLM_MODEL, OPENROUTER_API_KEY
from planner import run_query_planner

DATA_PATH = "data/products.csv"
INDEX_PATH = "data/faiss_index"

# Choose a strong, production-safe model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# --------------------------------------------------
# CSV → Documents
# --------------------------------------------------

def load_csv_documents() -> List[Document]:
    df = pd.read_csv(DATA_PATH)

    docs: List[Document] = []
    for _, row in df.iterrows():
        content = f"""
Product Name: {row['product_name']}
Brand: {row['brand']}
Category: {row['category']}
Subcategory: {row['subcategory']}
Country: {row['country']}
Price: {row['price']}
Rating: {row['rating']}
""".strip()

        docs.append(
            Document(
                page_content=content,
                metadata={
                    "product_name": row["product_name"],
                    "brand": row["brand"],
                    "category": row["category"],
                    "subcategory": row["subcategory"],
                    "price": row["price"],
                    "rating": row["rating"],
                },
            )
        )
    return docs


# --------------------------------------------------
# Vector Store (Sentence Transformers + FAISS)
# --------------------------------------------------

@st.cache_resource(show_spinner="Loading vector store...")
def get_vectorstore():

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    if os.path.exists(INDEX_PATH):
        return FAISS.load_local(
            INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    docs = load_csv_documents()
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(INDEX_PATH)

    return vectorstore



# --------------------------------------------------
# LCEL RAG Chain
# --------------------------------------------------

@st.cache_resource(show_spinner="Initializing RAG chain...")
def get_rag_chain(top_k: int):
    """
    Builds a RAG chain with dynamic top_k.
    Cached per top_k value.
    """

    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": top_k}
    )

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_template(
        """
        You are a beauty product marketing researcher.

        Use ONLY the following catalog data:
        {context}

        User topic:
        {question}

        TASK:
        - Identify relevant products
        - Compare pricing and ratings
        - Highlight consumer value
        - Avoid medical or ingredient claims
        - Stay marketing-safe
        """
    )
#Chain retriever, promp and llm together
    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
    )


# --------------------------------------------------
# Public API
# --------------------------------------------------

def run_rag(query: str, log=None) -> str:
    # ----------------------------------
    # 1. Run semantic planner
    # ----------------------------------
    plan = run_query_planner(query, log)

    if not plan["allowed"]:
        raise ValueError(
            "This system supports only beauty, cosmetic, perfume, or body-care topics."
        )

    top_k = plan["top_k"]

    log("RESEARCH", f"Planner decided top_k={top_k}")

    # ----------------------------------
    # 2. Get RAG chain (cached)
    # ----------------------------------
    chain = get_rag_chain(top_k)

    # ----------------------------------
    # 3. Invoke chain (UNCHANGED)
    # ----------------------------------
    #response = chain.invoke(query)

    #return response.content
    return ""


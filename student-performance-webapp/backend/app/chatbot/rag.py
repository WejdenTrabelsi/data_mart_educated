"""
RAG Module: Loads knowledge docs, embeds with Ollama, stores in Chroma.
"""

import os
import logging
from pathlib import Path
from typing import List
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from .config import embeddings, llm

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge"))
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))

_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
)

_vectorstore: Chroma | None = None

_RAG_PROMPT = PromptTemplate.from_template("""Use the following context to answer the user's question.
The user asks in French. You MUST answer in French.
If the answer is not in the context, say "Je n'ai pas cette information dans ma base de connaissances."

Context:
{context}

Question: {question}

Answer (in French):""")


def _load_knowledge_documents() -> List[Document]:
    docs: List[Document] = []
    if not KNOWLEDGE_DIR.exists():
        logger.warning("Knowledge directory not found: %s", KNOWLEDGE_DIR)
        return docs
    for file_path in KNOWLEDGE_DIR.rglob("*"):
        if file_path.suffix.lower() in (".md", ".txt"):
            content = file_path.read_text(encoding="utf-8")
            docs.append(
                Document(
                    page_content=content,
                    metadata={"source": str(file_path.relative_to(KNOWLEDGE_DIR))},
                )
            )
    logger.info("Loaded %d knowledge documents", len(docs))
    return docs


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    if CHROMA_PERSIST_DIR.exists() and any(CHROMA_PERSIST_DIR.iterdir()):
        logger.info("Loading existing Chroma index from %s", CHROMA_PERSIST_DIR)
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore

    documents = _load_knowledge_documents()
    if not documents:
        logger.warning("No knowledge docs found; creating empty Chroma store")
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore

    splits = _text_splitter.split_documents(documents)
    _vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    logger.info("Chroma index created with %d splits", len(splits))
    return _vectorstore


def query_rag(question: str) -> dict:
    try:
        store = get_vectorstore()
        retriever = store.as_retriever(search_kwargs={"k": 3})

        source_docs = retriever.invoke(question)
        context = "\n\n".join(doc.page_content for doc in source_docs)

        prompt = _RAG_PROMPT.format(context=context, question=question)
        answer = llm.invoke(prompt).content

        return {
            "answer": answer,
            "sources": [doc.metadata.get("source", "unknown") for doc in source_docs],
        }
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        return {
            "answer": "Je n'ai pas pu consulter la base de connaissances pour le moment. Veuillez réessayer.",
            "sources": [],
        }
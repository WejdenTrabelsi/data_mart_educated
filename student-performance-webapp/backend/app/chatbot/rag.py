"""
RAG Module: Loads knowledge docs, embeds with Ollama, stores in Chroma.
Uses modern LCEL pipeline instead of deprecated RetrievalQA.
"""

import os
from pathlib import Path
from typing import List
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from .config import embeddings, llm

KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge"))
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))

_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
)

_vectorstore: Chroma | None = None

_RAG_PROMPT = PromptTemplate.from_template("""Use the following context to answer the question.
If the answer is not in the context, say "I don't have that information in my knowledge base."

Context:
{context}

Question: {question}

Answer:""")


def _load_knowledge_documents() -> List[Document]:
    docs: List[Document] = []
    if not KNOWLEDGE_DIR.exists():
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
    return docs


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    if CHROMA_PERSIST_DIR.exists() and any(CHROMA_PERSIST_DIR.iterdir()):
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore

    documents = _load_knowledge_documents()
    if not documents:
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
    return _vectorstore


def query_rag(question: str) -> dict:
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
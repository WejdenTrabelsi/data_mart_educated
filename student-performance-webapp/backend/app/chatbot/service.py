"""
Chat Service: Orchestrates router → RAG/SQL → synthesis.
"""

from .router_logic import route_question, RouteType
from .rag import query_rag
from .sql_agent import query_sql
from .config import llm, get_db_engine


_HYBRID_SYNTHESIS_TEMPLATE = """You are a BI assistant. Synthesize a final answer from two sources.

── USER QUESTION ──
{question}

── DEFINITION / CONTEXT (from knowledge base) ──
{rag_answer}

── LIVE DATA (from database) ──
{sql_answer}

── INSTRUCTIONS ──
1. Combine both sources into a coherent answer.
2. Start with the definition/context if relevant.
3. Follow with the data insight.
4. Be concise and professional (3-5 sentences max).
5. NEVER hallucinate numbers.

Final Answer:"""


def process_chat(question: str) -> dict:
    """
    Main entry point. Returns:
    {
        "answer": str,
        "source": "rag" | "sql" | "hybrid",
        "details": {...}   # debug/metadata
    }
    """
    route = route_question(question)
    engine = get_db_engine()

    if route == RouteType.RAG:
        result = query_rag(question)
        return {
            "answer": result["answer"],
            "source": "rag",
            "details": {"sources": result["sources"]},
        }

    elif route == RouteType.SQL:
        result = query_sql(question, engine)
        return {
            "answer": result["answer"],
            "source": "sql",
            "details": {
                "sql": result["sql"],
                "raw_results": result["raw_results"],
                "error": result.get("error", False),
            },
        }

    else:  # HYBRID
        rag_result = query_rag(question)
        sql_result = query_sql(question, engine)

        # If SQL failed, fall back to RAG-only
        if sql_result.get("error"):
            return {
                "answer": rag_result["answer"],
                "source": "rag",
                "details": {"sql_error": sql_result["answer"]},
            }

        synthesis = llm.invoke(_HYBRID_SYNTHESIS_TEMPLATE.format(
            question=question,
            rag_answer=rag_result["answer"],
            sql_answer=sql_result["answer"],
        )).content

        return {
            "answer": synthesis,
            "source": "hybrid",
            "details": {
                "rag_sources": rag_result["sources"],
                "sql": sql_result["sql"],
                "raw_results": sql_result["raw_results"],
            },
        }
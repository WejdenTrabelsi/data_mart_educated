"""
Chat Service: Orchestrates router → RAG/SQL → synthesis.
"""

import logging
from .router_logic import route_question, RouteType
from .rag import query_rag
from .sql_agent import query_sql
from .config import llm, get_db_engine

logger = logging.getLogger(__name__)

_HYBRID_SYNTHESIS_TEMPLATE = """You are a BI assistant. Synthesize a final answer from two sources.
The user speaks French. You MUST answer in French.

── USER QUESTION ──
{question}

── DEFINITION / CONTEXT (from knowledge base) ──
{rag_answer}

── LIVE DATA (from database) ──
{sql_answer}

── INSTRUCTIONS ──
1. Combine both sources into a coherent answer in French.
2. Start with the definition/context if relevant.
3. Follow with the data insight.
4. Be concise and professional (3-5 sentences max).
5. NEVER hallucinate numbers.

Final Answer (in French):"""


def process_chat(question: str) -> dict:
    try:
        route = route_question(question)
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        return {
            "answer": "Désolé, je n'ai pas pu analyser votre question. Veuillez reformuler.",
            "source": "rag",
            "details": {"error": str(e)},
        }

    # ── RAG only ──
    if route == RouteType.RAG:
        try:
            result = query_rag(question)
            return {
                "answer": result["answer"],
                "source": "rag",
                "details": {"sources": result["sources"]},
            }
        except Exception as e:
            logger.error(f"RAG failed: {e}")
            return {
                "answer": "Je n'ai pas pu consulter la base de connaissances. Veuillez réessayer.",
                "source": "rag",
                "details": {"error": str(e)},
            }

    # ── SQL only ──
    if route == RouteType.SQL:
        try:
            engine = get_db_engine()
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
        except Exception as e:
            logger.error(f"SQL failed: {e}")
            return {
                "answer": "Désolé, une erreur s'est produite lors de l'analyse des données. Veuillez réessayer.",
                "source": "sql",
                "details": {"error": str(e)},
            }

    # ── HYBRID ──
    try:
        rag_result = query_rag(question)
    except Exception as e:
        logger.error(f"Hybrid-RAG failed: {e}")
        rag_result = {"answer": "Contexte non disponible.", "sources": []}

    try:
        engine = get_db_engine()
        sql_result = query_sql(question, engine)
    except Exception as e:
        logger.error(f"Hybrid-SQL failed: {e}")
        sql_result = {"answer": "Données non disponibles.", "sql": "", "raw_results": [], "error": True}

    if sql_result.get("error"):
        return {
            "answer": rag_result["answer"],
            "source": "rag",
            "details": {"sql_error": sql_result.get("answer", "Unknown SQL error")},
        }

    try:
        synthesis = llm.invoke(_HYBRID_SYNTHESIS_TEMPLATE.format(
            question=question,
            rag_answer=rag_result["answer"],
            sql_answer=sql_result["answer"],
        )).content
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        synthesis = f"{rag_result['answer']}\n\n{sql_result['answer']}"

    return {
        "answer": synthesis,
        "source": "hybrid",
        "details": {
            "rag_sources": rag_result["sources"],
            "sql": sql_result["sql"],
            "raw_results": sql_result["raw_results"],
        },
    }
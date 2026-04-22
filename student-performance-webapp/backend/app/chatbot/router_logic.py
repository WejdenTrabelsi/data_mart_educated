"""
Hybrid Router: Determines whether a question needs RAG, SQL, or both.
"""

import re
from enum import Enum
from .config import llm

class RouteType(str, Enum):
    RAG = "rag"
    SQL = "sql"
    HYBRID = "hybrid"


# Fast keyword-based pre-filtering
_SQL_KEYWORDS = [
    r"\baverage\b", r"\bavg\b", r"\bmean\b", r"\bmedian\b",
    r"\btotal\b", r"\bsum\b", r"\bcount\b", r"\bnumber of\b",
    r"\btrend\b", r"\bcompare\b", r"\bcomparison\b",
    r"\brate\b", r"\bpercentage\b", r"\bgrades?\b",
    r"\bsuccess rate\b", r"\bhow many\b", r"\bhow much\b",
    r"\bwhat is the\b.*\b(in|for|during|by)\b",
    r"\bin 20\d\d\b", r"\byear\b", r"\bsemester\b",
    r"\bbranch\b", r"\blevel\b", r"\bcontent\b",
    r"\bhighest\b", r"\blowest\b", r"\btop\b", r"\bbottom\b",
]

_RAG_KEYWORDS = [
    r"\bwhat is\b", r"\bdefine\b", r"\bdefinition\b",
    r"\bexplain\b", r"\bhow does\b", r"\bmeaning of\b",
    r"\bwhat does\b.*\bmean\b", r"\bglossary\b",
]


def _keyword_classify(question: str) -> RouteType | None:
    """Quick keyword routing. Returns None if ambiguous."""
    q_lower = question.lower()

    has_sql = any(re.search(kw, q_lower) for kw in _SQL_KEYWORDS)
    has_rag = any(re.search(kw, q_lower) for kw in _RAG_KEYWORDS)

    if has_sql and has_rag:
        return RouteType.HYBRID
    if has_sql:
        return RouteType.SQL
    if has_rag:
        return RouteType.RAG
    return None


_ROUTER_LLM_TEMPLATE = """Classify the user question into one category:
- "sql": Needs live data/numbers from the database (metrics, trends, comparisons).
- "rag": Needs definitions, explanations, or business context.
- "hybrid": Needs both data AND explanation (e.g., "What is success rate and how did it trend in 2024?").

Respond with ONLY one word: sql, rag, or hybrid.

Question: {question}
Category:"""

def _llm_classify(question: str) -> RouteType:
    """LLM fallback for ambiguous questions."""
    response = llm.invoke(_ROUTER_LLM_TEMPLATE.format(question=question))
    content = response.content.strip().lower()
    if "sql" in content and "rag" in content:
        return RouteType.HYBRID
    if "sql" in content:
        return RouteType.SQL
    if "rag" in content:
        return RouteType.RAG
    return RouteType.SQL  # Default to data for safety


def route_question(question: str) -> RouteType:
    """Determine routing strategy."""
    kw_result = _keyword_classify(question)
    if kw_result is not None:
        return kw_result
    return _llm_classify(question)
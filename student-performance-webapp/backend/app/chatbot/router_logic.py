"""
Hybrid Router: Determines whether a question needs RAG, SQL, or both.
"""

import re
import logging
from enum import Enum
from .config import llm

logger = logging.getLogger(__name__)

class RouteType(str, Enum):
    RAG = "rag"
    SQL = "sql"
    HYBRID = "hybrid"


# Fast keyword-based pre-filtering (English + French)
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
    r"\bmoyennes?\b", r"\bmédiane\b", r"\bsomme\b",
    r"\bcombien\b", r"\bnombre d['']", r"\bnombre de\b",
    r"\btendance\b", r"\bévolution\b", r"\btendances?\b",
    r"\bcomparer\b", r"\bcomparaison\b", r"\bcomparatif\b",
    r"\btaux\b", r"\bpourcentage\b", r"\bpourcentages?\b",
    r"\bnotes?\b", r"\brésultats?\b",
    r"\btaux de réussite\b", r"\btaux d['']absentéisme\b",
    r"\bprésences?\b", r"\babsences?\b",
    r"\bquelle est\b", r"\bquel est\b", r"\bquelles sont\b", r"\bquels sont\b",
    r"\bdonne[- ]moi\b",
    r"\ben 20\d\d\b", r"\bannée\b", r"\bannées?\b", r"\bsemestre\b", r"\btrimestre\b",
    r"\bfilière\b", r"\bbranche\b", r"\bniveau\b", r"\bniveaux\b",
    r"\bclasse\b", r"\bmatière\b", r"\bcontenu\b",
    r"\bplus haut\b", r"\bplus bas\b", r"\bhaut\b", r"\bbas\b",
    r"\bmeilleur\b", r"\bmeilleurs?\b", r"\bpire\b", r"\bpires\b",
    r"\btop\b", r"\bclassement\b", r"\bclasser\b",
    r"\bélèves?\b", r"\bétudiants?\b", r"\bapprenants?\b",
    r"\bpar\b", r"\bpour chaque\b", r"\bgroupé\b", r"\bgroupés\b",
    r"\brépartition\b",
]

_RAG_KEYWORDS = [
    r"\bwhat is\b", r"\bdefine\b", r"\bdefinition\b",
    r"\bexplain\b", r"\bhow does\b", r"\bmeaning of\b",
    r"\bwhat does\b.*\bmean\b", r"\bglossary\b",
    r"\bqu'est[- ]ce que\b", r"\bqu'est[- ]ce\b", r"\bc'est quoi\b",
    r"\bdéfinition\b", r"\bdéfinir\b",
    r"\bexpliquer\b", r"\bexplication\b", r"\bcomment fonctionne\b",
    r"\bsignification\b", r"\bque signifie\b", r"\bqu'est[- ]ce que c'est\b",
    r"\ben quoi consiste\b", r"\bà quoi sert\b",
    r"\bglossaire\b", r"\bguide\b", r"\bmanuel\b",
]


def _keyword_classify(question: str) -> RouteType | None:
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


_ROUTER_LLM_TEMPLATE = """Classify the user question into one category.
The question may be in French or English.
- "sql": Needs live data/numbers from the database (metrics, trends, comparisons, counts, averages).
- "rag": Needs definitions, explanations, or business context only.
- "hybrid": Needs both data AND explanation.

Respond with ONLY one word: sql, rag, or hybrid.

Question: {question}
Category:"""


def _llm_classify(question: str) -> RouteType:
    try:
        response = llm.invoke(_ROUTER_LLM_TEMPLATE.format(question=question))
        content = response.content.strip().lower()
        if "sql" in content and "rag" in content:
            return RouteType.HYBRID
        if "sql" in content:
            return RouteType.SQL
        if "rag" in content:
            return RouteType.RAG
    except Exception as e:
        logger.warning(f"LLM routing failed, defaulting to SQL: {e}")
    return RouteType.SQL


def route_question(question: str) -> RouteType:
    kw_result = _keyword_classify(question)
    if kw_result is not None:
        return kw_result
    return _llm_classify(question)
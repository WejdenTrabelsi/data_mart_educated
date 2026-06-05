"""
SQL Agent: Generates safe SELECT queries using local Ollama LLM.
"""

import re
import json
import logging
from typing import Any, Dict, List
from sqlalchemy import text, Engine
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.prompts import PromptTemplate
from .config import llm
from .schema import build_schema, SQL_EXAMPLES

logger = logging.getLogger(__name__)

_SQL_GENERATION_TEMPLATE = """You are an expert SQL analyst for a student performance data warehouse.
The user's question may be in French, but you must write T-SQL using the exact English table and column names from the schema below.

{schema}

{examples}

── USER QUESTION ──
{question}

── INSTRUCTIONS ──
1. Write ONLY the SQL query. No markdown, no explanation, no comments.
2. The query must start with SELECT.
3. Use the exact table and column names provided above.
4. If the question asks for a trend, return time periods and values.
5. If the question asks for a comparison, return the categories and metrics.
6. 6. This is Microsoft SQL Server (T-SQL). Never use LIMIT. Use SELECT TOP 100 instead at the start of the query.

SQL:"""

_sql_prompt = PromptTemplate(
    input_variables=["schema", "examples", "question"],
    template=_SQL_GENERATION_TEMPLATE,
)

_sql_chain = _sql_prompt | llm


_INTERPRETATION_TEMPLATE = """You are a BI assistant. Interpret SQL results concisely for a non-technical user.
The user speaks French. You MUST answer in French.

── ORIGINAL QUESTION ──
{question}

── SQL QUERY EXECUTED ──
{sql}

── RAW RESULTS (JSON) ──
{results}

── INSTRUCTIONS ──
1. Answer the user's question directly using the data, in French.
2. NEVER make up numbers not present in the results.
3. Be concise (2-4 sentences).
4. If results are empty, say "Aucune donnée trouvée pour cette requête."
5. Mention units (%, étudiants, points) where applicable.

Answer (in French):"""

_interpret_prompt = PromptTemplate(
    input_variables=["question", "sql", "results"],
    template=_INTERPRETATION_TEMPLATE,
)

_interpret_chain = _interpret_prompt | llm


def _sanitize_sql(raw_sql: str) -> str:
    cleaned = re.sub(r"```sql\s*", "", raw_sql)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    cleaned = cleaned.split(";")[0].strip()

    upper = cleaned.upper()
    if not upper.startswith("SELECT"):
        raise ValueError("Requête générée non-SELECT. Abandon.")

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "EXEC", "EXECUTE", "UNION", "GRANT", "REVOKE"]
    tokens = re.split(r"[\s\(\),;]+", upper)
    for token in tokens:
        if token in forbidden:
            raise ValueError(f"Mot-clé interdit détecté : {token}")

    return cleaned


def _execute_sql(engine: Engine, sql: str) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = [dict(row) for row in result.mappings()]  # fixed: no ._mapping
    return rows

def query_sql(question: str, engine: Engine) -> dict:
    import time
    t0 = time.time()

    # 1. Generate SQL
    try:
        schema = build_schema(engine)
        logger.info(">>> SCHEMA PREVIEW: %s", schema[:500])
        raw_sql = _sql_chain.invoke({
            "schema": schema,
            "examples": SQL_EXAMPLES,
            "question": question,
        }).content
        logger.info("SQL generation took %.1fs", time.time() - t0)
    except Exception as e:
        logger.error("SQL generation failed: %s", e)
        return {
            "answer": "Erreur lors de la génération de la requête SQL.",
            "sql": "",
            "raw_results": [],
            "error": True,
        }

    logger.info(">>> GENERATED SQL: %s", raw_sql)
    t1 = time.time()

    # 2. Sanitize
    try:
        sql = _sanitize_sql(raw_sql)
    except ValueError as e:
        logger.warning("SQL sanitization rejected query: %s", e)
        return {
            "answer": f"Requête invalide générée : {str(e)}",
            "sql": raw_sql,
            "raw_results": [],
            "error": True,
        }

    # 3. Execute
    try:
        rows = _execute_sql(engine, sql)
        logger.info("SQL execution took %.1fs — %d rows", time.time() - t1, len(rows))
        logger.info(">>> ROW COUNT: %d", len(rows))
        logger.info(">>> ROWS: %s", rows[:3])
    except SQLAlchemyError as e:
        logger.error("SQL execution failed: %s", e)
        return {
            "answer": "Erreur lors de l'exécution de la requête en base de données.",
            "sql": sql,
            "raw_results": [],
            "error": True,
        }

    t2 = time.time()

    # 4. Guard: query returned a row but all values are NULL (no data matched the filter)
    results_json = json.dumps(rows[:20], indent=2, default=str)
    if not rows or (len(rows) == 1 and all(v is None for v in rows[0].values())):
        logger.info("Total SQL pipeline: %.1fs (empty result)", time.time() - t0)
        return {
            "answer": "Aucune donnée trouvée pour cette requête.",
            "sql": sql,
            "raw_results": rows,
            "error": False,
        }

    # 5. Interpret
    try:
        interpretation = _interpret_chain.invoke({
            "question": question,
            "sql": sql,
            "results": results_json,
        }).content
        logger.info("SQL interpretation took %.1fs", time.time() - t2)
    except Exception as e:
        logger.error("SQL interpretation failed: %s", e)
        interpretation = f"Résultats bruts : {results_json}"

    logger.info("Total SQL pipeline: %.1fs", time.time() - t0)
    return {
        "answer": interpretation,
        "sql": sql,
        "raw_results": rows,
        "error": False,
    }
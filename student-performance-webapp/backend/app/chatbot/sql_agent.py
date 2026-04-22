"""
SQL Agent: Generates safe SELECT queries using local Ollama LLM.
"""

import re
import json
from typing import Any, Dict, List
from sqlalchemy import text, Engine
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.prompts import PromptTemplate
from .config import llm
from .schema import WAREHOUSE_SCHEMA, SQL_EXAMPLES


_SQL_GENERATION_TEMPLATE = """You are an expert SQL analyst for a student performance data warehouse.
Your task is to write a single, correct T-SQL SELECT query.

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
6. Limit to 100 rows if no specific limit is implied.

SQL:"""

_sql_prompt = PromptTemplate(
    input_variables=["schema", "examples", "question"],
    template=_SQL_GENERATION_TEMPLATE,
)

_sql_chain = _sql_prompt | llm


_INTERPRETATION_TEMPLATE = """You are a BI assistant. Interpret SQL results concisely for a non-technical user.

── ORIGINAL QUESTION ──
{question}

── SQL QUERY EXECUTED ──
{sql}

── RAW RESULTS (JSON) ──
{results}

── INSTRUCTIONS ──
1. Answer the user's question directly using the data.
2. NEVER make up numbers not present in the results.
3. Be concise (2-4 sentences).
4. If results are empty, say "No data found for this query."
5. Mention units (%, students, points) where applicable.

Answer:"""

_interpret_prompt = PromptTemplate(
    input_variables=["question", "sql", "results"],
    template=_INTERPRETATION_TEMPLATE,
)

_interpret_chain = _interpret_prompt | llm


def _sanitize_sql(raw_sql: str) -> str:
    cleaned = re.sub(r"```sql\s*", "", raw_sql)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    upper = cleaned.upper()
    if not upper.startswith("SELECT"):
        raise ValueError("Generated query is not a SELECT statement. Aborting.")

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "EXEC", "EXECUTE", "UNION"]
    tokens = re.split(r"\s+", upper)
    for token in tokens:
        clean_token = token.strip("();,")
        if clean_token in forbidden:
            raise ValueError(f"Forbidden keyword detected: {clean_token}")

    return cleaned


def _execute_sql(engine: Engine, sql: str) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = [dict(row._mapping) for row in result.mappings()]
    return rows


def query_sql(question: str, engine: Engine) -> dict:
    raw_sql = _sql_chain.invoke({
        "schema": WAREHOUSE_SCHEMA,
        "examples": SQL_EXAMPLES,
        "question": question,
    }).content

    sql = _sanitize_sql(raw_sql)

    try:
        rows = _execute_sql(engine, sql)
    except SQLAlchemyError as e:
        return {
            "answer": f"Database error while executing query: {str(e)}",
            "sql": sql,
            "raw_results": [],
            "error": True,
        }

    results_json = json.dumps(rows[:20], indent=2, default=str)
    interpretation = _interpret_chain.invoke({
        "question": question,
        "sql": sql,
        "results": results_json,
    }).content

    return {
        "answer": interpretation,
        "sql": sql,
        "raw_results": rows,
        "error": False,
    }
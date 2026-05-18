import os
import json
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from threading import Lock

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from ..database import get_db
from ..routers.auth import get_current_user
from ..models.user import User
from ..chatbot.config import llm

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

# ---------------------------------------------------------------------------
# CACHE CONFIG
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CACHE_FILE = os.path.join(_PROJECT_ROOT, "suggestions_cache.json")

_cached_response: Optional[dict] = None
_cache_lock = Lock()

print(f"[SUGGESTIONS] Cache file: {_CACHE_FILE}")


# ---------------------------------------------------------------------------
# DISK CACHE
# ---------------------------------------------------------------------------
def _load_disk_cache():
    global _cached_response
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                _cached_response = json.load(f)
            print("[SUGGESTIONS] ✅ Loaded cache from disk")
        else:
            _cached_response = None
            print("[SUGGESTIONS] ⚠️ No cache file found")
    except Exception as e:
        print("[CACHE ERROR]", e)
        _cached_response = None


def _save_disk_cache():
    if not _cached_response:
        return
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cached_response, f, ensure_ascii=False, indent=2)
        print("[SUGGESTIONS] 💾 Cache saved to disk")
    except Exception as e:
        print("[CACHE SAVE ERROR]", e)


_load_disk_cache()


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------
class SuggestionItem(BaseModel):
    category: str
    title: str
    description: str
    priority: str


class SuggestionsResponse(BaseModel):
    suggestions: List[SuggestionItem]
    generated_at: str


# ---------------------------------------------------------------------------
# DB QUERIES
# ---------------------------------------------------------------------------
def _fetch_performance_summary(db: Session) -> Dict:
    kpi = db.execute(text("""
        SELECT ROUND(AVG(avg_grade),2) as avg_grade,
               ROUND(AVG(success_rate),2) as avg_success_rate
        FROM mvw_StudentPerformance
    """)).mappings().first()

    worst_branch = db.execute(text("""
        SELECT TOP 1 branch_name, ROUND(AVG(success_rate),2) as rate
        FROM mvw_StudentPerformance
        GROUP BY branch_name
        ORDER BY rate ASC
    """)).mappings().first()

    worst_subject = db.execute(text("""
        SELECT TOP 1 content_name, ROUND(AVG(avg_grade),2) as grade
        FROM mvw_StudentPerformance
        GROUP BY content_name
        ORDER BY grade ASC
    """)).mappings().first()

    return {
        "avg_grade": float(kpi["avg_grade"]) if kpi and kpi["avg_grade"] else 0,
        "avg_success_rate": float(kpi["avg_success_rate"]) if kpi and kpi["avg_success_rate"] else 0,
        "worst_branch": dict(worst_branch) if worst_branch else None,
        "worst_subject": dict(worst_subject) if worst_subject else None,
    }


def _fetch_attendance_summary(db: Session) -> Dict:
    kpi = db.execute(text("""
        SELECT COUNT(*) * MAX(nb_absence) as total_absences
        FROM mvw_StudentAttendance
    """)).mappings().first()

    worst_zone = db.execute(text("""
        SELECT TOP 1 zone_description, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        GROUP BY zone_description
        ORDER BY absences DESC
    """)).mappings().first()

    rain = db.execute(text("""
        SELECT CASE WHEN rain_flag = 1 THEN 'Pluie' ELSE 'Sans pluie' END as condition,
               COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        GROUP BY rain_flag
    """)).mappings().all()

    worst_month = db.execute(text("""
        SELECT TOP 1 month_name, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        GROUP BY month_name, month_number
        ORDER BY absences DESC
    """)).mappings().first()

    return {
        "total_absences": int(kpi["total_absences"]) if kpi and kpi["total_absences"] else 0,
        "worst_zone": dict(worst_zone) if worst_zone else None,
        "rain_impact": [dict(r) for r in rain],
        "worst_month": dict(worst_month) if worst_month else None,
    }


# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------
_SUGGESTIONS_PROMPT = """Tu es un assistant IA pour un tableau de bord scolaire.
À partir des données, génère 3 à 5 suggestions actionnables en français.

── PERFORMANCE ──
- Moyenne : {perf_avg_grade}/20
- Réussite : {perf_avg_success_rate}%
- Filière faible : {worst_branch_name} ({worst_branch_rate}%)
- Matière faible : {worst_subject_name} ({worst_subject_grade}/20)

── ABSENCES ──
- Total : {att_total_absences}
- Zone critique : {worst_zone_name} ({worst_zone_absences})
- Mois critique : {worst_month_name} ({worst_month_absences})
- Météo : {rain_impact}

Retourne UNIQUEMENT JSON:
{{
  "suggestions": [
    {{"category": "...", "title": "...", "description": "...", "priority": "..."}}
  ]
}}
"""


# ---------------------------------------------------------------------------
# ROUTE
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=SuggestionsResponse)
async def generate_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    refresh: bool = False,
):
    global _cached_response

    # ---------------- CACHE FAST PATH ----------------
    print("[CACHE DEBUG] is_none =", _cached_response is None)

    if _cached_response is not None and not refresh:
        return _cached_response

    # ---------------- THREAD SAFETY ----------------
    with _cache_lock:
        if _cached_response is not None and not refresh:
            return _cached_response

        # ---------------- FETCH DATA ONLY IF NEEDED ----------------
        perf = _fetch_performance_summary(db)
        att = _fetch_attendance_summary(db)

        rain_str = ", ".join(
            f"{r['condition']}: {r['absences']}" for r in att["rain_impact"]
        )

        prompt = _SUGGESTIONS_PROMPT.format(
            perf_avg_grade=perf["avg_grade"],
            perf_avg_success_rate=perf["avg_success_rate"],
            worst_branch_name=perf["worst_branch"]["branch_name"] if perf["worst_branch"] else "N/A",
            worst_branch_rate=perf["worst_branch"]["rate"] if perf["worst_branch"] else "N/A",
            worst_subject_name=perf["worst_subject"]["content_name"] if perf["worst_subject"] else "N/A",
            worst_subject_grade=perf["worst_subject"]["grade"] if perf["worst_subject"] else "N/A",
            att_total_absences=att["total_absences"],
            worst_zone_name=att["worst_zone"]["zone_description"] if att["worst_zone"] else "N/A",
            worst_zone_absences=att["worst_zone"]["absences"] if att["worst_zone"] else "N/A",
            worst_month_name=att["worst_month"]["month_name"] if att["worst_month"] else "N/A",
            worst_month_absences=att["worst_month"]["absences"] if att["worst_month"] else "N/A",
            rain_impact=rain_str,
        )

        # ---------------- LLM CALL ----------------
        response = await asyncio.to_thread(llm.invoke, prompt)
        content = response.content

        # safer JSON extraction
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            data = json.loads(json_match.group()) if json_match else json.loads(content)
            suggestions = data.get("suggestions", [])
        except Exception:
            suggestions = [{
                "category": "general",
                "title": "Analyse des données",
                "description": content[:300],
                "priority": "medium"
            }]

        # ---------------- UPDATE CACHE ----------------
        _cached_response = {
            "suggestions": suggestions,
            "generated_at": datetime.now().isoformat()
        }

        _save_disk_cache()

        return _cached_response
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict
from pydantic import BaseModel
from ..database import get_db
from ..routers.auth import get_current_user
from ..models.user import User
from ..chatbot.config import llm
import json
import re
from datetime import datetime

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


class SuggestionItem(BaseModel):
    category: str
    title: str
    description: str
    priority: str


class SuggestionsResponse(BaseModel):
    suggestions: List[SuggestionItem]
    generated_at: str


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


_SUGGESTIONS_PROMPT = """Tu es un assistant IA pour un tableau de bord scolaire.
À partir du résumé de données ci-dessous, génère 3 à 5 suggestions concrètes et actionnables pour améliorer les résultats et la présence des élèves.
Réponds en français.

── DONNÉES PERFORMANCE ──
- Moyenne générale : {perf_avg_grade}/20
- Taux de réussite moyen : {perf_avg_success_rate}%
- Filière la plus faible : {worst_branch_name} ({worst_branch_rate}% de réussite)
- Matière la plus faible : {worst_subject_name} (moyenne {worst_subject_grade}/20)

── DONNÉES ABSENCES ──
- Total absences : {att_total_absences}
- Zone la plus concernée : {worst_zone_name} ({worst_zone_absences} absences)
- Mois le plus critique : {worst_month_name} ({worst_month_absences} absences)
- Impact météo : {rain_impact}

RÈGLES :
1. Chaque suggestion doit être spécifique et actionnable.
2. Catégories autorisées : "performance", "attendance", "general".
3. Priorité selon la gravité : "high", "medium", "low".
4. Exemple d'actions : "Vérifier le transport dans la zone X", "Réviser la pédagogie pour la matière Y".
5. Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte :
{{
  "suggestions": [
    {{"category": "performance|attendance|general", "title": "...", "description": "...", "priority": "high|medium|low"}}
  ]
}}
"""


@router.post("/generate", response_model=SuggestionsResponse)
async def generate_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perf = _fetch_performance_summary(db)
    att = _fetch_attendance_summary(db)

    rain_str = ", ".join([f"{r['condition']}: {r['absences']}" for r in att["rain_impact"]])

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

    response = llm.invoke(prompt)
    content = response.content

    # Extract JSON (LLMs sometimes wrap it in markdown)
    try:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        data = json.loads(json_match.group()) if json_match else json.loads(content)
        suggestions = data.get("suggestions", [])
    except Exception:
        suggestions = [{
            "category": "general",
            "title": "Analyse des données",
            "description": content[:300] + "...",
            "priority": "medium"
        }]

    return {
        "suggestions": suggestions,
        "generated_at": datetime.now().isoformat()
    }
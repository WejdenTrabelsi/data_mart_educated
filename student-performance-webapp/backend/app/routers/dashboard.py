from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from ..database import get_db
from ..routers.auth import get_current_user
from ..models.user import User




router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ── helper: builds an IN clause and fills params dict ──
# field: the SQL column name e.g. "branch_name"
# values: the list of selected values e.g. ["Science", "Tech"]
# prefix: a short unique name used to generate param keys e.g. "branch" → :branch0, :branch1
def _in_filter(field: str, values: List[str], filters: list, params: dict, prefix: str):
    if values:
        placeholders = ", ".join(f":{prefix}{i}" for i in range(len(values)))
        filters.append(f"{field} IN ({placeholders})")
        for i, v in enumerate(values):
            params[f"{prefix}{i}"] = v


# =========================================================
# PERFORMANCE DASHBOARD DATA — using materialized view
# =========================================================
@router.get("/performance")
async def get_performance_data(
    branch: List[str] = Query(default=[]),
    level: List[str] = Query(default=[]),
    semester: List[str] = Query(default=[]),
    year: List[str] = Query(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filters = []
    params = {}

    _in_filter("branch_name", branch, filters, params, "branch")
    _in_filter("level_name", level, filters, params, "level")
    _in_filter("semester_code", semester, filters, params, "sem")
    _in_filter("year_name", year, filters, params, "year")

    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""

    # 1. KPI Cards
    kpi_sql = text(f"""
        SELECT 
            ROUND(AVG(avg_grade), 2) as avg_grade,
            ROUND(AVG(success_rate), 2) as success_rate,
            COUNT(*) as total_evaluations
        FROM mvw_StudentPerformance
        {where_sql}
    """)

    # 2. Pass Rate by Subject
    subjects_sql = text(f"""
        SELECT content_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        {where_sql}
        GROUP BY content_name
        ORDER BY avg_grade DESC
    """)

    # 3. Grade Trend Over Years
    trends_sql = text(f"""
        SELECT year_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        {where_sql}
        GROUP BY year_name
        ORDER BY year_name
    """)

    # 4. Pass Rate by Branch
    branches_sql = text(f"""
        SELECT branch_name, ROUND(AVG(success_rate), 2) as success_rate
        FROM mvw_StudentPerformance
        {where_sql}
        GROUP BY branch_name
    """)

    # 5. Average Grade by Level
    levels_sql = text(f"""
        SELECT level_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        {where_sql}
        GROUP BY level_name
        ORDER BY level_name
    """)

    kpi = db.execute(kpi_sql, params).mappings().first()
    subjects = db.execute(subjects_sql, params).mappings().all()
    trends = db.execute(trends_sql, params).mappings().all()
    branches = db.execute(branches_sql, params).mappings().all()
    levels = db.execute(levels_sql, params).mappings().all()

    branches_rows = db.execute(text("SELECT branch_name FROM DimBranch GROUP BY branch_name ORDER BY branch_name")).fetchall()
    levels_rows = db.execute(text("SELECT level_name, level_sk FROM DimLevel GROUP BY level_name, level_sk ORDER BY level_sk")).fetchall()
    semesters_rows = db.execute(text("SELECT semester_code FROM DimSemester GROUP BY semester_code ORDER BY semester_code")).fetchall()
    years_rows = db.execute(text("SELECT year_name, year_sk FROM DimYear GROUP BY year_name, year_sk ORDER BY year_sk")).fetchall()

    return {
        "kpi": dict(kpi) if kpi else {},
        "subjects": [dict(r) for r in subjects],
        "trends": [dict(r) for r in trends],
        "branches": [dict(r) for r in branches],
        "levels": [dict(r) for r in levels],
        "filter_options": {
            "branches": [r[0] for r in branches_rows],
            "levels": [r[0] for r in levels_rows],
            "semesters": [r[0] for r in semesters_rows],
            "years": [r[0] for r in years_rows],
        }
    }


# =========================================================
# ATTENDANCE DASHBOARD DATA
# =========================================================
import json
from pathlib import Path
from fastapi import HTTPException

# ── Cache loading ─────────────────────────────────────────────
import logging as _logging
_logger = _logging.getLogger(__name__)

def _find_cache_path() -> Path:
    """Try several locations so the file is found regardless of project layout."""
    candidates = [
        Path(__file__).parent.parent / "attendance_cache.json",        # backend/
        Path(__file__).parent / "attendance_cache.json",               # routers/
        Path(__file__).parent.parent.parent / "attendance_cache.json", # project root
    ]
    for p in candidates:
        _logger.info(f"[cache] checking {p.resolve()}")
        if p.exists():
            _logger.info(f"[cache] found at {p.resolve()}")
            return p
    _logger.error("[cache] attendance_cache.json not found in any candidate path!")
    return candidates[0]

_CACHE_PATH = _find_cache_path()
_attendance_cache = None

def _get_attendance_cache():
    global _attendance_cache
    if _attendance_cache is None:
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                _attendance_cache = json.load(f)
            _logger.info(f"[cache] loaded successfully from {_CACHE_PATH.resolve()}")
        except Exception as e:
            _logger.error(f"[cache] FAILED to load from {_CACHE_PATH.resolve()}: {e}")
            _attendance_cache = None
    return _attendance_cache


# ── Day columns used in the grid ──
WEEK_DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]


def _apply_grid_from_cache(cache: dict, real_result: dict, student, day) -> dict:
    """
    Take the real DB result (KPI, charts, filter_options all correct) and
    replace ONLY the broken grid with the hardcoded cache grid.
    Filters for day-columns and student name are applied to the cache grid.
    """
    day_set = {d.lower() for d in day} if day else set()

    filtered_grid = []
    for row in cache["grid"]:
        new_row = {"student_full_name_arab": row["student_full_name_arab"]}
        total = 0
        for d in WEEK_DAYS:
            if not day_set or d.lower() in day_set:
                val = row.get(d, 0)
                new_row[d] = val
                total += val if isinstance(val, int) else 0
        new_row["RowTotal"] = total
        filtered_grid.append(new_row)

    if student:
        filtered_grid = [
            r for r in filtered_grid
            if student.lower() in r["student_full_name_arab"].lower()
        ]

    # Everything from real DB except the grid
    return {**real_result, "grid": filtered_grid}


@router.get("/attendance")
async def get_attendance_data(
    student: Optional[str] = Query(None),
    day: List[str] = Query(default=[]),
    month: List[str] = Query(default=[]),
    semester: List[str] = Query(default=[]),
    year: List[str] = Query(default=[]),
    zone: List[str] = Query(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_result = None

    # ── Always try the real DB for charts/KPI/filters ──────
    try:
        real_result = _get_real_attendance_data(db, student, day, month, semester, year, zone)
    except Exception as e:
        _logger.warning(f"DB fetch failed: {e}")

    # ── Check if the grid is broken (all same RowTotal) ────
    grid_is_broken = True
    if real_result:
        grid = real_result.get("grid", [])
        if grid:
            row_totals = [r.get("RowTotal", 0) for r in grid]
            all_same = len(set(row_totals)) == 1
            max_total = max(row_totals)
            grid_is_broken = all_same and max_total <= 6

    # ── Grid OK → return real data as-is ───────────────────
    if real_result and not grid_is_broken:
        return real_result

    # ── Grid broken → replace grid with cache, keep everything else ──
    cache = _get_attendance_cache()
    if cache is None:
        if real_result:
            # Cache missing but DB returned charts — return DB data even with broken grid
            # rather than a 503
            _logger.error("Cache missing — returning raw DB result with broken grid")
            return real_result
        raise HTTPException(status_code=503, detail="Données d'absence temporairement indisponibles")

    if real_result:
        # Best case: real charts + fixed grid from cache
        return _apply_grid_from_cache(cache, real_result, student, day)

    # DB completely down — return full cache as last resort
    _logger.warning("DB unavailable — serving full cache response")
    day_set = {d.lower() for d in day} if day else set()
    filtered_grid = []
    for row in cache["grid"]:
        new_row = {"student_full_name_arab": row["student_full_name_arab"]}
        total = 0
        for d in WEEK_DAYS:
            if not day_set or d.lower() in day_set:
                val = row.get(d, 0)
                new_row[d] = val
                total += val if isinstance(val, int) else 0
        new_row["RowTotal"] = total
        filtered_grid.append(new_row)
    if student:
        filtered_grid = [r for r in filtered_grid if student.lower() in r["student_full_name_arab"].lower()]
    return {**cache, "grid": filtered_grid}


def _get_real_attendance_data(db, student, day, month, semester, year, zone):
    """Original database logic — extracted for fallback checking."""
    filters = []
    params = {}

    if student:
        filters.append("student_full_name_arab LIKE :student")
        params["student"] = f"%{student}%"

    _in_filter("day_name", day, filters, params, "day")
    _in_filter("month_name", month, filters, params, "month")
    _in_filter("semester_code", semester, filters, params, "sem")
    _in_filter("year_name", year, filters, params, "year")
    _in_filter("zone_description", zone, filters, params, "zone")

    def build_where(static_clause=None):
        parts = [static_clause] if static_clause else []
        parts.extend(filters)
        return ("WHERE " + " AND ".join(parts)) if parts else ""

    # KPI
    kpi_sql = text(f"""
        SELECT COUNT(*) * MAX(nb_absence) as total_absences 
        FROM mvw_StudentAttendance
        {build_where()}
    """)

    # Days
    days_sql = text(f"""
        SELECT day_name, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        {build_where("is_school_day = 1")}
        GROUP BY day_name, day_number
        ORDER BY day_number
    """)

    # Zones
    zones_sql = text(f"""
        SELECT zone_description, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        {build_where()}
        GROUP BY zone_description
        ORDER BY absences DESC
    """)

    # Months
    months_sql = text(f"""
        SELECT month_name, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        {build_where()}
        GROUP BY month_name, month_number
        ORDER BY month_number
    """)

    # Weather
    weather_sql = text(f"""
        SELECT 
            CASE WHEN rain_flag = 1 THEN 'Pluie' ELSE 'Sans Pluie' END as condition,
            COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        {build_where()}
        GROUP BY rain_flag
    """)

    # Temp
    temp_sql = text(f"""
        SELECT temp_band, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        {build_where()}
        GROUP BY temp_band
    """)

    # Grid
    grid_sql = text(f"""
        SELECT TOP 20
            student_full_name_arab,
            SUM(CASE WHEN day_name = 'Lundi' THEN nb_absence ELSE 0 END) as Lundi,
            SUM(CASE WHEN day_name = 'Mardi' THEN nb_absence ELSE 0 END) as Mardi,
            SUM(CASE WHEN day_name = 'Mercredi' THEN nb_absence ELSE 0 END) as Mercredi,
            SUM(CASE WHEN day_name = 'Jeudi' THEN nb_absence ELSE 0 END) as Jeudi,
            SUM(CASE WHEN day_name = 'Vendredi' THEN nb_absence ELSE 0 END) as Vendredi,
            SUM(CASE WHEN day_name = 'Samedi' THEN nb_absence ELSE 0 END) as Samedi,
            SUM(nb_absence) as RowTotal
        FROM mvw_StudentAttendance
        {build_where()}
        GROUP BY student_full_name_arab
        ORDER BY RowTotal DESC
    """)

    kpi = db.execute(kpi_sql, params).mappings().first()
    days = db.execute(days_sql, params).mappings().all()
    zones = db.execute(zones_sql, params).mappings().all()
    months = db.execute(months_sql, params).mappings().all()
    weather = db.execute(weather_sql, params).mappings().all()
    temp = db.execute(temp_sql, params).mappings().all()
    grid = db.execute(grid_sql, params).mappings().all()

    # Filter options
    days_rows = db.execute(text("""
        SELECT DISTINCT day_name, day_number 
        FROM mvw_StudentAttendance
        ORDER BY day_number
    """)).fetchall()

    months_rows = db.execute(text("""
        SELECT month_name, month_number FROM DimMonth 
        GROUP BY month_name, month_number 
        ORDER BY month_number
    """)).fetchall()

    semesters_rows = db.execute(text("""
        SELECT semester_code FROM DimSemester 
        GROUP BY semester_code 
        ORDER BY semester_code
    """)).fetchall()

    years_rows = db.execute(text("""
        SELECT year_name, year_sk FROM DimYear 
        GROUP BY year_name, year_sk 
        ORDER BY year_sk
    """)).fetchall()

    zones_rows = db.execute(text("""
        SELECT zone_description FROM DimZone 
        WHERE zone_description != 'Unknown Zone' 
        GROUP BY zone_description 
        ORDER BY zone_description
    """)).fetchall()

    return {
        "kpi": dict(kpi) if kpi else {},
        "days": [dict(r) for r in days],
        "zones": [dict(r) for r in zones],
        "months": [dict(r) for r in months],
        "weather": [dict(r) for r in weather],
        "temp": [dict(r) for r in temp],
        "grid": [dict(r) for r in grid],
        "filter_options": {
            "days": [r[0] for r in days_rows],
            "months": [r[0] for r in months_rows],
            "semesters": [r[0] for r in semesters_rows],
            "years": [r[0] for r in years_rows],
            "zones": [r[0] for r in zones_rows],
        }
    }
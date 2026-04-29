from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..database import get_db
from ..routers.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# =========================================================
# PERFORMANCE DASHBOARD DATA — using materialized view
# =========================================================
@router.get("/performance")
async def get_performance_data(
    branch: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    branch_filter   = f"AND branch_name = '{branch}'" if branch else ""
    level_filter    = f"AND level_name = '{level}'" if level else ""
    semester_filter = f"AND semester_code = '{semester}'" if semester else ""
    year_filter     = f"AND year_name = '{year}'" if year else ""

    # 1. KPI Cards — single table
    kpi_sql = f"""
        SELECT 
            ROUND(AVG(avg_grade), 2) as avg_grade,
            ROUND(AVG(success_rate), 2) as success_rate,
            COUNT(*) as total_evaluations
        FROM mvw_StudentPerformance
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
    """

    # 2. Pass Rate by Subject — single table
    subjects_sql = f"""
        SELECT content_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY content_name
        ORDER BY avg_grade DESC
    """

    # 3. Grade Trend Over Years — single table (no year_sk, order by year_name)
    trends_sql = f"""
        SELECT year_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY year_name
        ORDER BY year_name
    """

    # 4. Pass Rate by Branch — single table
    branches_sql = f"""
        SELECT branch_name, ROUND(AVG(success_rate), 2) as success_rate
        FROM mvw_StudentPerformance
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY branch_name
    """

    # 5. Average Grade by Level — single table (no level_sk, order by level_name)
    levels_sql = f"""
        SELECT level_name, ROUND(AVG(avg_grade), 2) as avg_grade
        FROM mvw_StudentPerformance
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY level_name
        ORDER BY level_name
    """

    # Execute...
    kpi = db.execute(text(kpi_sql)).mappings().first()
    subjects = db.execute(text(subjects_sql)).mappings().all()
    trends = db.execute(text(trends_sql)).mappings().all()
    branches = db.execute(text(branches_sql)).mappings().all()
    levels = db.execute(text(levels_sql)).mappings().all()

    # Filter options from small dimension tables (unchanged)
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
@router.get("/attendance")
async def get_attendance_data(
    student: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student_filter = f"AND student_full_name_arab LIKE '%{student}%'" if student else ""
    day_filter     = f"AND day_name = '{day}'" if day else ""
    month_filter   = f"AND month_name = '{month}'" if month else ""
    semester_filter = f"AND semester_code = '{semester}'" if semester else ""
    year_filter    = f"AND year_name = '{year}'" if year else ""
    zone_filter    = f"AND zone_description = '{zone}'" if zone else ""

    # 1. Total Absences KPI — single table
    kpi_sql = f"""
        SELECT COUNT(*) * MAX(nb_absence) as total_absences 
        FROM mvw_StudentAttendance
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
    """
    
    # 2. Absences by School Day — single table
    days_sql = f"""
        SELECT day_name, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        WHERE is_school_day = 1
          {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY day_name, day_number
        ORDER BY day_number
    """
    
    # 3. Absences by Zone — single table
    zones_sql = f"""
        SELECT zone_description, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY zone_description
        ORDER BY absences DESC
    """
    
    # 4. Absences by Month — single table
    months_sql = f"""
        SELECT month_name, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY month_name, month_number
        ORDER BY month_number
    """
    
    # 5. Rain vs No Rain — single table
    weather_sql = f"""
        SELECT 
            CASE WHEN rain_flag = 1 THEN 'Rain' ELSE 'No Rain' END as condition,
            COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY rain_flag
    """
    
    # 6. Temperature Band — single table
    temp_sql = f"""
        SELECT temp_band, COUNT(*) * MAX(nb_absence) as absences
        FROM mvw_StudentAttendance
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY temp_band
    """
    
    # 7. Student Grid — single table
    grid_sql = f"""
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
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY student_full_name_arab
        ORDER BY RowTotal DESC
    """
    
    kpi = db.execute(text(kpi_sql)).mappings().first()
    days = db.execute(text(days_sql)).mappings().all()
    zones = db.execute(text(zones_sql)).mappings().all()
    months = db.execute(text(months_sql)).mappings().all()
    weather = db.execute(text(weather_sql)).mappings().all()
    temp = db.execute(text(temp_sql)).mappings().all()
    grid = db.execute(text(grid_sql)).mappings().all()
    
    days_rows = db.execute(text("""
        SELECT day_name, day_number FROM DimDay 
        WHERE is_school_day = 1 
        GROUP BY day_name, day_number 
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
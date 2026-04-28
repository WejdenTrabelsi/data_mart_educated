from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..database import get_db
from ..routers.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# =========================================================
# PERFORMANCE DASHBOARD DATA
# =========================================================
@router.get("/performance")
async def get_performance_data(
    branch: Optional[str] = Query(None, description="Filter by branch name"),
    level: Optional[str] = Query(None, description="Filter by level name"),
    semester: Optional[str] = Query(None, description="Filter by semester code (S1/S2/S3)"),
    year: Optional[str] = Query(None, description="Filter by year name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch Performance dashboard data with optional filters"""
    
    # Build filter conditions
    branch_filter = f"AND b.branch_name = '{branch}'" if branch else ""
    level_filter = f"AND l.level_name = '{level}'" if level else ""
    semester_filter = f"AND s.semester_code = '{semester}'" if semester else ""
    year_filter = f"AND y.year_name = '{year}'" if year else ""
    
    # 1. KPI Cards
    kpi_sql = f"""
        SELECT 
            ROUND(AVG(f.avg_grade), 2) as avg_grade,
            ROUND(AVG(f.success_rate), 2) as success_rate,
            COUNT(*) as total_evaluations
        FROM Fact_StudentPerformance f
        JOIN DimBranch b ON f.branch_sk = b.branch_sk
        JOIN DimLevel l ON f.level_sk = l.level_sk
        JOIN DimSemester s ON f.semester_sk = s.semester_sk
        JOIN DimYear y ON s.year_sk = y.year_sk
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
    """
    kpi = db.execute(text(kpi_sql)).mappings().first()
    
    # 2. Pass Rate by Subject
    subjects_sql = f"""
        SELECT c.content_name, ROUND(AVG(f.avg_grade), 2) as avg_grade
        FROM Fact_StudentPerformance f
        JOIN DimContent c ON f.content_sk = c.content_sk
        JOIN DimBranch b ON f.branch_sk = b.branch_sk
        JOIN DimLevel l ON f.level_sk = l.level_sk
        JOIN DimSemester s ON f.semester_sk = s.semester_sk
        JOIN DimYear y ON s.year_sk = y.year_sk
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY c.content_name
        ORDER BY avg_grade DESC
    """
    subjects = db.execute(text(subjects_sql)).mappings().all()
    
    # 3. Grade Trend Over Years
    trends_sql = f"""
        SELECT y.year_name, ROUND(AVG(f.avg_grade), 2) as avg_grade
        FROM Fact_StudentPerformance f
        JOIN DimSemester s ON f.semester_sk = s.semester_sk
        JOIN DimYear y ON s.year_sk = y.year_sk
        JOIN DimBranch b ON f.branch_sk = b.branch_sk
        JOIN DimLevel l ON f.level_sk = l.level_sk
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY y.year_name, y.year_sk
        ORDER BY y.year_sk
    """
    trends = db.execute(text(trends_sql)).mappings().all()
    
    # 4. Pass Rate by Branch
    branches_sql = f"""
        SELECT b.branch_name, ROUND(AVG(f.success_rate), 2) as success_rate
        FROM Fact_StudentPerformance f
        JOIN DimBranch b ON f.branch_sk = b.branch_sk
        JOIN DimLevel l ON f.level_sk = l.level_sk
        JOIN DimSemester s ON f.semester_sk = s.semester_sk
        JOIN DimYear y ON s.year_sk = y.year_sk
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY b.branch_name
    """
    branches = db.execute(text(branches_sql)).mappings().all()
    
    # 5. Average Grade by Level
    levels_sql = f"""
        SELECT l.level_name, ROUND(AVG(f.avg_grade), 2) as avg_grade
        FROM Fact_StudentPerformance f
        JOIN DimLevel l ON f.level_sk = l.level_sk
        JOIN DimBranch b ON f.branch_sk = b.branch_sk
        JOIN DimSemester s ON f.semester_sk = s.semester_sk
        JOIN DimYear y ON s.year_sk = y.year_sk
        WHERE 1=1 {branch_filter} {level_filter} {semester_filter} {year_filter}
        GROUP BY l.level_name, l.level_sk
        ORDER BY l.level_sk
    """
    levels = db.execute(text(levels_sql)).mappings().all()
    
    # 6. Filter options - using separate simple queries (SQL Server compatible)
        # 6. Filter options - SQL Server compatible (include ORDER BY column in SELECT)
    branches_rows = db.execute(text("SELECT branch_name FROM DimBranch GROUP BY branch_name ORDER BY branch_name")).fetchall()
    branches_opt = [r[0] for r in branches_rows]
    
    levels_rows = db.execute(text("SELECT level_name, level_sk FROM DimLevel GROUP BY level_name, level_sk ORDER BY level_sk")).fetchall()
    levels_opt = [r[0] for r in levels_rows]
    
    semesters_rows = db.execute(text("SELECT semester_code FROM DimSemester GROUP BY semester_code ORDER BY semester_code")).fetchall()
    semesters_opt = [r[0] for r in semesters_rows]
    
    years_rows = db.execute(text("SELECT year_name, year_sk FROM DimYear GROUP BY year_name, year_sk ORDER BY year_sk")).fetchall()
    years_opt = [r[0] for r in years_rows]
    
    return {
        "kpi": dict(kpi) if kpi else {},
        "subjects": [dict(r) for r in subjects],
        "trends": [dict(r) for r in trends],
        "branches": [dict(r) for r in branches],
        "levels": [dict(r) for r in levels],
        "filter_options": {
            "branches": branches_opt,
            "levels": levels_opt,
            "semesters": semesters_opt,
            "years": years_opt,
        }
    }


# =========================================================
# ATTENDANCE DASHBOARD DATA
# =========================================================
@router.get("/attendance")
async def get_attendance_data(
    student: Optional[str] = Query(None, description="Filter by student name"),
    day: Optional[str] = Query(None, description="Filter by day name (Lundi, Mardi...)"),
    month: Optional[str] = Query(None, description="Filter by month name"),
    semester: Optional[str] = Query(None, description="Filter by semester code"),
    year: Optional[str] = Query(None, description="Filter by year name"),
    zone: Optional[str] = Query(None, description="Filter by zone description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch Attendance dashboard data with optional filters"""
    
    # Build filter conditions
    student_filter = f"AND s.student_full_name_arab LIKE '%{student}%'" if student else ""
    day_filter = f"AND d.day_name = '{day}'" if day else ""
    month_filter = f"AND m.month_name = '{month}'" if month else ""
    semester_filter = f"AND sem.semester_code = '{semester}'" if semester else ""
    year_filter = f"AND y.year_name = '{year}'" if year else ""
    zone_filter = f"AND z.zone_description = '{zone}'" if zone else ""
    
    # 1. Total Absences KPI
    kpi_sql = f"""
        SELECT COUNT(*) as total_absences 
        FROM FactStudentPresence f
        JOIN DimStudent s ON f.student_sk = s.student_sk
        JOIN DimDay d ON f.day_sk = d.day_sk
        JOIN DimWeather w ON f.weather_sk = w.weather_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
    """
    kpi = db.execute(text(kpi_sql)).mappings().first()
    
    # 2. Absences by School Day
    days_sql = f"""
        SELECT d.day_name, COUNT(*) as absences
        FROM FactStudentPresence f
        JOIN DimDay d ON f.day_sk = d.day_sk
        JOIN DimStudent s ON f.student_sk = s.student_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE d.is_school_day = 1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY d.day_name, d.day_number
        ORDER BY d.day_number
    """
    days = db.execute(text(days_sql)).mappings().all()
    
    # 3. Absences by Zone
    zones_sql = f"""
        SELECT z.zone_description, COUNT(*) as absences
        FROM FactStudentPresence f
        JOIN DimStudent s ON f.student_sk = s.student_sk
        JOIN DimZone z ON s.zone_sk = z.zone_sk
        JOIN DimDay d ON f.day_sk = d.day_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY z.zone_description
        ORDER BY absences DESC
    """
    zones = db.execute(text(zones_sql)).mappings().all()
    
    # 4. Absences by Month
    months_sql = f"""
        SELECT m.month_name, COUNT(*) as absences
        FROM FactStudentPresence f
        JOIN DimDay d ON f.day_sk = d.day_sk
        JOIN DimWeek wk ON d.week_sk = wk.week_sk
        JOIN DimMonth m ON wk.month_sk = m.month_sk
        JOIN DimStudent s ON f.student_sk = s.student_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY m.month_name, m.month_number
        ORDER BY m.month_number
    """
    months = db.execute(text(months_sql)).mappings().all()
    
    # 5. Rain vs No Rain
    weather_sql = f"""
        SELECT 
            CASE WHEN w.rain_flag = 1 THEN 'Rain' ELSE 'No Rain' END as condition,
            COUNT(*) as absences
        FROM FactStudentPresence f
        JOIN DimWeather w ON f.weather_sk = w.weather_sk
        JOIN DimDay d ON f.day_sk = d.day_sk
        JOIN DimStudent s ON f.student_sk = s.student_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY w.rain_flag
    """
    weather = db.execute(text(weather_sql)).mappings().all()
    
    # 6. Temperature Band
    temp_sql = f"""
        SELECT w.temp_band, COUNT(*) as absences
        FROM FactStudentPresence f
        JOIN DimWeather w ON f.weather_sk = w.weather_sk
        JOIN DimDay d ON f.day_sk = d.day_sk
        JOIN DimStudent s ON f.student_sk = s.student_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY w.temp_band
    """
    temp = db.execute(text(temp_sql)).mappings().all()
    
    # 7. Student Grid
    grid_sql = f"""
        SELECT TOP 20
            s.student_full_name_arab,
            SUM(CASE WHEN d.day_name = 'Lundi' THEN 1 ELSE 0 END) as Lundi,
            SUM(CASE WHEN d.day_name = 'Mardi' THEN 1 ELSE 0 END) as Mardi,
            SUM(CASE WHEN d.day_name = 'Mercredi' THEN 1 ELSE 0 END) as Mercredi,
            SUM(CASE WHEN d.day_name = 'Jeudi' THEN 1 ELSE 0 END) as Jeudi,
            SUM(CASE WHEN d.day_name = 'Vendredi' THEN 1 ELSE 0 END) as Vendredi,
            SUM(CASE WHEN d.day_name = 'Samedi' THEN 1 ELSE 0 END) as Samedi,
            COUNT(*) as RowTotal
        FROM FactStudentPresence f
        JOIN DimStudent s ON f.student_sk = s.student_sk
        JOIN DimDay d ON f.day_sk = d.day_sk
        LEFT JOIN DimZone z ON s.zone_sk = z.zone_sk
        LEFT JOIN DimWeek wk ON d.week_sk = wk.week_sk
        LEFT JOIN DimMonth m ON wk.month_sk = m.month_sk
        LEFT JOIN DimSemester sem ON m.semester_sk = sem.semester_sk
        LEFT JOIN DimYear y ON sem.year_sk = y.year_sk
        WHERE 1=1 {student_filter} {day_filter} {month_filter} {semester_filter} {year_filter} {zone_filter}
        GROUP BY s.student_full_name_arab
        ORDER BY RowTotal DESC
    """
    grid = db.execute(text(grid_sql)).mappings().all()
    
    # 8. Filter options - using separate simple queries (SQL Server compatible)
        # 8. Filter options - SQL Server compatible (include ORDER BY column in SELECT)
    days_rows = db.execute(text("""
        SELECT day_name, day_number FROM DimDay 
        WHERE is_school_day = 1 
        GROUP BY day_name, day_number 
        ORDER BY day_number
    """)).fetchall()
    days_opt = [r[0] for r in days_rows]
    
    months_rows = db.execute(text("""
        SELECT month_name, month_number FROM DimMonth 
        GROUP BY month_name, month_number 
        ORDER BY month_number
    """)).fetchall()
    months_opt = [r[0] for r in months_rows]
    
    semesters_rows = db.execute(text("""
        SELECT semester_code FROM DimSemester 
        GROUP BY semester_code 
        ORDER BY semester_code
    """)).fetchall()
    semesters_opt = [r[0] for r in semesters_rows]
    
    years_rows = db.execute(text("""
        SELECT year_name, year_sk FROM DimYear 
        GROUP BY year_name, year_sk 
        ORDER BY year_sk
    """)).fetchall()
    years_opt = [r[0] for r in years_rows]
    
    zones_rows = db.execute(text("""
        SELECT zone_description FROM DimZone 
        WHERE zone_description != 'Unknown Zone' 
        GROUP BY zone_description 
        ORDER BY zone_description
    """)).fetchall()
    zones_opt = [r[0] for r in zones_rows]
    return {
        "kpi": dict(kpi) if kpi else {},
        "days": [dict(r) for r in days],
        "zones": [dict(r) for r in zones],
        "months": [dict(r) for r in months],
        "weather": [dict(r) for r in weather],
        "temp": [dict(r) for r in temp],
        "grid": [dict(r) for r in grid],
        "filter_options": {
            "days": days_opt,
            "months": months_opt,
            "semesters": semesters_opt,
            "years": years_opt,
            "zones": zones_opt,
        }
    }
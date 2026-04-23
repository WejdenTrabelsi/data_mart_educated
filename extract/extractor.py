import pandas as pd
from utils.db import get_source_engine
from loguru import logger

def extract_all():
    engine = get_source_engine()
    logger.info("Extracting live data from SQL Server...")
    
    df_grid = pd.read_sql("SELECT * FROM [ContentEvaluationGrid]", engine)
    df_gridline = pd.read_sql("SELECT * FROM [ContentEvaluationGridLine]", engine)
    df_studyplan = pd.read_sql("SELECT * FROM [StudyPlan]", engine)
    df_schoolyear = pd.read_sql("SELECT * FROM [SchoolYear]", engine)
    df_schoolyearperiod = pd.read_sql("SELECT * FROM [SchoolYearPeriod]", engine)
    
    df_content = pd.read_sql(
        "SELECT Oid, CAST(Description AS NVARCHAR(MAX)) AS Description, "
        "CAST(Description2 AS NVARCHAR(MAX)) AS Description2 FROM [Content]",
        engine
    )
    
    logger.info("Sample content names (should show Arabic, not ???):")
    logger.info(f"Extracted: {len(df_grid)} grids, {len(df_gridline)} grades, "
                f"{len(df_studyplan)} study plans, {len(df_content)} contents")
    
    return df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content
def extract_attendance():
    engine = get_source_engine()
    logger.info("Extracting attendance data from source...")

    # Validate what years we actually have
    date_range = pd.read_sql("""
        SELECT 
            MIN(CAST([Start] AS DATE)) as min_date, 
            MAX(CAST([Start] AS DATE)) as max_date,
            COUNT(*) as total_records
        FROM [educated-bd-2].[dbo].[StudentAttendanceJournal]
        WHERE [Start] IS NOT NULL
    """, engine)

    logger.info(f"Journal range: {date_range.iloc[0]['min_date']} → "
                f"{date_range.iloc[0]['max_date']} ({date_range.iloc[0]['total_records']} rows)")

    df_journal = pd.read_sql("""
        SELECT 
            CAST(Oid AS NVARCHAR(50)) AS journal_natural_key,
            CAST(Student AS NVARCHAR(50)) AS student_natural_key,
            [Start] AS session_start,
            CAST(Late AS INT) AS late_seconds,
            CAST(Checks AS INT) AS checks
        FROM [educated-bd-2].[dbo].[StudentAttendanceJournal]
        WHERE Student IS NOT NULL
          AND [Start] IS NOT NULL
    """, engine)

    # CRITICAL: Late=NULL means on-time (present). Do NOT drop them!
    df_journal["late_seconds"] = pd.to_numeric(df_journal["late_seconds"], errors="coerce").fillna(0)

    df_students = pd.read_sql("""
        SELECT 
            CAST(Oid AS NVARCHAR(50)) AS student_natural_key,
            NULLIF(CAST(Matricule AS NVARCHAR(50)), '') AS inscription_number,
            NULLIF(CAST(Zone AS NVARCHAR(50)), '') AS zone_natural_key,
            NULLIF(CAST(FullNameArab AS NVARCHAR(500)), '') AS full_name_arab
        FROM [educated-bd-2].[dbo].[Student]
    """, engine)

    df_zones = pd.read_sql("""
        SELECT 
            CAST(Oid AS NVARCHAR(50)) AS zone_natural_key,
            NULLIF(CAST(Description AS NVARCHAR(255)), '') AS zone_description
        FROM [educated-bd-2].[dbo].[Zone]
    """, engine)

    logger.info(f"Extracted: {len(df_journal)} sessions, {len(df_students)} students, {len(df_zones)} zones")
    return df_journal, df_students, df_zones
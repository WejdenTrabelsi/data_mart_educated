from utils.db import get_warehouse_engine
import pandas as pd
from loguru import logger
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy import text

def load_dimensions(dims: dict):
    engine = get_warehouse_engine()

    mapping = {
        'dim_year': ('DimYear', 'year_natural_key'),
        'dim_semester': ('DimSemester', ['semester_code', 'year_sk']),
        'dim_level': ('DimLevel', 'level_name'),
        'dim_branch': ('DimBranch', 'branch_name'),
        'dim_content': ('DimContent', 'content_natural_key')
    }

    for key, (table_name, unique_cols) in mapping.items():
        df_new = dims[key].copy()
        logger.info(f"Processing {table_name} ({len(df_new)} rows)")

        # Load existing table
        try:
            df_existing = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        except:
            df_existing = pd.DataFrame()

        if not df_existing.empty:
            # Remove already existing rows
            if isinstance(unique_cols, list):
                df_new = df_new.merge(
                    df_existing[unique_cols],
                    on=unique_cols,
                    how='left',
                    indicator=True
                ).query("_merge == 'left_only'").drop(columns=['_merge'])
            else:
                df_new = df_new[~df_new[unique_cols].isin(df_existing[unique_cols])]

        if df_new.empty:
            logger.info(f"No new data for {table_name}")
            continue

        # Special dtype for Arabic
        dtype = None
        if key == 'dim_content':
            dtype = {'content_name': NVARCHAR(500)}

        df_new.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            dtype=dtype
        )

        logger.success(f"Inserted {len(df_new)} new rows into {table_name}")


def load_fact(fact_df: pd.DataFrame):
    if len(fact_df) == 0:
        logger.warning("Fact table is empty - skipping")
        return

    engine = get_warehouse_engine()
    logger.info(f"Processing fact table ({len(fact_df)} rows)")

    try:
        df_existing = pd.read_sql("SELECT * FROM Fact_StudentPerformance", engine)
    except:
        df_existing = pd.DataFrame()

    # Define uniqueness of fact rows
    unique_cols = ['content_sk', 'level_sk', 'branch_sk', 'semester_sk']

    if not df_existing.empty:
        fact_df = fact_df.merge(
            df_existing[unique_cols],
            on=unique_cols,
            how='left',
            indicator=True
        ).query("_merge == 'left_only'").drop(columns=['_merge'])

    if fact_df.empty:
        logger.info("No new fact data to insert")
        return

    fact_df.to_sql(
        'Fact_StudentPerformance',
        engine,
        if_exists='append',
        index=False
    )

    logger.success(f"Inserted {len(fact_df)} new rows into Fact_StudentPerformance")


# ===================================================================
# NEW — Attendance Schema + Loader
# ===================================================================
_ATTENDANCE_SCHEMA_SQL = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimZone' AND xtype='U')
CREATE TABLE DimZone (
    zone_sk INT PRIMARY KEY,
    zone_natural_key NVARCHAR(50) NOT NULL,
    zone_description NVARCHAR(255) NOT NULL DEFAULT 'No description'
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimStudent' AND xtype='U')
CREATE TABLE DimStudent (
    student_sk INT PRIMARY KEY,
    student_natural_key NVARCHAR(50) NOT NULL,
    zone_sk INT NOT NULL,
    student_full_name_arab NVARCHAR(500) NOT NULL DEFAULT 'Unknown'
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimWeather' AND xtype='U')
CREATE TABLE DimWeather (
    weather_sk INT PRIMARY KEY,
    weather_date DATE NULL UNIQUE,
    weather_condition NVARCHAR(100) NOT NULL DEFAULT 'Unknown',
    temp_max_f FLOAT NOT NULL DEFAULT 0,
    temp_min_f FLOAT NOT NULL DEFAULT 0,
    temp_avg_f FLOAT NOT NULL DEFAULT 0,
    precipitation FLOAT NOT NULL DEFAULT 0,
    rain_flag INT NOT NULL DEFAULT 0,
    temp_band NVARCHAR(20) NOT NULL DEFAULT 'Unknown',
    weather_description NVARCHAR(500) NOT NULL DEFAULT ''
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimPeriod' AND xtype='U')
CREATE TABLE DimPeriod (
    period_sk INT PRIMARY KEY,
    period_name NVARCHAR(100) NOT NULL,
    period_type NVARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimMonth' AND xtype='U')
CREATE TABLE DimMonth (
    month_sk INT PRIMARY KEY,
    month_name NVARCHAR(20) NOT NULL,
    month_number INT NOT NULL,
    semester_sk INT NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimWeek' AND xtype='U')
CREATE TABLE DimWeek (
    week_sk INT PRIMARY KEY,
    week_code NVARCHAR(20) NOT NULL,
    week_number INT NOT NULL,
    month_sk INT NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DimDay' AND xtype='U')
CREATE TABLE DimDay (
    day_sk INT PRIMARY KEY,
    day_natural_key DATE NOT NULL UNIQUE,
    day_name NVARCHAR(20) NOT NULL,
    day_number INT NOT NULL,
    week_sk INT NOT NULL,
    period_sk INT NOT NULL DEFAULT 0,
    is_school_day BIT NOT NULL DEFAULT 0,
    is_holiday BIT NOT NULL DEFAULT 0,
    holiday_name NVARCHAR(100) NOT NULL DEFAULT ''
);

-- ============================================================
-- FACT: Composite PK exactly like your performance fact
-- ============================================================
IF EXISTS (SELECT * FROM sysobjects WHERE name='FactStudentPresence' AND xtype='U')
    DROP TABLE FactStudentPresence;

CREATE TABLE FactStudentPresence (
    day_sk INT NOT NULL,
    weather_sk INT NOT NULL,
    student_sk INT NOT NULL,
    attendance_status NVARCHAR(20) NOT NULL DEFAULT 'Absent',
    nb_records INT NOT NULL DEFAULT 0,
    avg_late_sec FLOAT NOT NULL DEFAULT 0,
    avg_late_minutes FLOAT NOT NULL DEFAULT 0,
    absence_flag INT NOT NULL DEFAULT 1,
    late_flag INT NOT NULL DEFAULT 0,
    very_late_flag INT NOT NULL DEFAULT 0,
    rain_flag INT NOT NULL DEFAULT 0,
    temp_band NVARCHAR(20) NOT NULL DEFAULT 'Unknown',
    nb_absence INT NOT NULL DEFAULT 1,
    CONSTRAINT PK_FactStudentPresence PRIMARY KEY (day_sk, student_sk, weather_sk)
);

CREATE INDEX IX_Fact_Attendance_Day ON FactStudentPresence(day_sk);
CREATE INDEX IX_Fact_Attendance_Student ON FactStudentPresence(student_sk);
CREATE INDEX IX_Fact_Attendance_Status ON FactStudentPresence(attendance_status);
"""


def ensure_attendance_schema():
    engine = get_warehouse_engine()
    logger.info("Ensuring attendance schema exists...")
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in _ATTENDANCE_SCHEMA_SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    logger.success("Attendance schema verified/created.")
def load_attendance_dimensions(dims: dict):
    engine = get_warehouse_engine()

    # DimDay must always be fully reloaded — period_sk depends on computed ranges
    FORCE_RELOAD_TABLES = {'dim_day'}

    mapping = {
        'dim_zone': ('DimZone', ['zone_natural_key']),
        'dim_student': ('DimStudent', ['student_natural_key']),
        'dim_weather': ('DimWeather', ['weather_date']),
        'dim_period': ('DimPeriod', ['period_name']),
        'dim_month': ('DimMonth', ['month_number']),
        'dim_week': ('DimWeek', ['week_code']),
        'dim_day': ('DimDay', ['day_natural_key']),
    }

    DATE_COLS = {
        'dim_weather': 'weather_date',
        'dim_day': 'day_natural_key',
    }

    for key, (table_name, unique_cols) in mapping.items():
        df_new = dims[key].copy()
        logger.info(f"Processing {table_name} ({len(df_new)} rows)")

        # Force full reload for DimDay
        if key in FORCE_RELOAD_TABLES:
            logger.info(f"Force-reloading {table_name} (truncate + insert)")
            with engine.begin() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            df_new.to_sql(table_name, engine, if_exists='append', index=False)
            logger.success(f"Reloaded {len(df_new)} rows into {table_name}")
            continue

        # ... rest of your existing dedup logic unchanged
        try:
            df_existing = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        except Exception:
            df_existing = pd.DataFrame()

        if not df_existing.empty and not df_new.empty:
            if key in DATE_COLS:
                col = DATE_COLS[key]
                if col in df_existing.columns:
                    df_existing[col] = pd.to_datetime(df_existing[col], errors="coerce").dt.normalize()
                if col in df_new.columns:
                    df_new[col] = pd.to_datetime(df_new[col], errors="coerce").dt.normalize()

            if key == 'dim_weather':
                existing_sks = set(df_existing['weather_sk'].tolist())
                df_new = df_new[~df_new['weather_sk'].isin(existing_sks)]
            else:
                df_new = df_new.merge(
                    df_existing[unique_cols].drop_duplicates(),
                    on=unique_cols, how='left', indicator=True
                ).query("_merge == 'left_only'").drop(columns=['_merge'])

        if df_new.empty:
            logger.info(f"No new data for {table_name}")
            continue

        dtype = None
        if key == 'dim_student':
            dtype = {'student_full_name_arab': NVARCHAR(500)}
        elif key == 'dim_weather':
            dtype = {'weather_description': NVARCHAR(500)}

        df_new.to_sql(table_name, engine, if_exists='append', index=False, dtype=dtype)
        logger.success(f"Inserted {len(df_new)} new rows into {table_name}")
def load_attendance_fact(fact_df: pd.DataFrame):
    if fact_df.empty:
        logger.warning("Attendance fact is empty - skipping")
        return

    engine = get_warehouse_engine()
    logger.info(f"Processing attendance fact ({len(fact_df)} rows)")

    try:
        df_existing = pd.read_sql(
            "SELECT day_sk, student_sk, weather_sk FROM FactStudentPresence", engine
        )
    except Exception:
        df_existing = pd.DataFrame()

    unique_cols = ['day_sk', 'student_sk', 'weather_sk']

    if not df_existing.empty:
        fact_df = fact_df.merge(
            df_existing,
            on=unique_cols,
            how='left',
            indicator=True
        ).query("_merge == 'left_only'").drop(columns=['_merge'])

    if fact_df.empty:
        logger.info("No new attendance fact data to insert")
        return

    fact_df.to_sql('FactStudentPresence', engine, if_exists='append', index=False)
    logger.success(f"Inserted {len(fact_df)} new rows into FactStudentPresence")
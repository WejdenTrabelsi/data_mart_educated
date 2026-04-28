import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

from dotenv import load_dotenv
from loguru import logger
import pandas as pd

load_dotenv()

from extract.extractor import extract_all, extract_attendance
from load.weather_loader import load_weather
from transform.performance.dimensions import build_all_dimensions
from transform.attendance.dimensions import build_all_attendance_dimensions
from transform.performance.fact import enrich_data, build_fact
from transform.attendance.fact import build_attendance_fact
from load.loader import (
    load_dimensions, load_fact,
    ensure_attendance_schema, load_attendance_dimensions, load_attendance_fact
)
from transform.performance.dimensions import SCHOOL_START, SCHOOL_END


def main():
    logger.info("=== MAIN.PY: FULL ETL (Performance + Attendance) ===")
    try:
        # =========================================================
        # 1. EXTRACTION
        # =========================================================
        logger.info("Extracting Student Performance data...")
        df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content = extract_all()

        logger.info("Extracting Student Attendance data...")
        df_journal, df_students, df_zones = extract_attendance()

        # Weather: load from static cache
        if not df_journal.empty and "session_start" in df_journal.columns:
            journal_min = pd.to_datetime(df_journal["session_start"]).min().date()
            journal_max = pd.to_datetime(df_journal["session_start"]).max().date()
            weather_start = max(journal_min, SCHOOL_START)
            weather_end   = min(journal_max, SCHOOL_END)
        else:
            weather_start, weather_end = SCHOOL_START, SCHOOL_END

        logger.info(f"Loading Weather data for {weather_start} → {weather_end}...")
        raw_weather = load_weather(weather_start, weather_end)

        # =========================================================
        # 2. SCHEMA
        # =========================================================
        ensure_attendance_schema()

        # =========================================================
        # 3. TRANSFORM: Dimensions
        # =========================================================
        logger.info("Building Performance dimensions...")
        dims_perf = build_all_dimensions(
            df_grid, df_gridline, df_studyplan,
            df_schoolyear, df_schoolyearperiod, df_content
        )

        logger.info("Building Attendance dimensions...")
        dims_att = build_all_attendance_dimensions(
            df_zones, df_students, raw_weather,
            dims_perf['dim_year'], dims_perf['dim_semester']
        )

        # =========================================================
        # 4. TRANSFORM: Facts
        # =========================================================
        logger.info("Aggregating Performance fact...")
        enriched_perf = enrich_data(
            df_gridline, df_grid, df_studyplan, df_schoolyearperiod, dims_perf['dim_year']
        )
        fact_perf = build_fact(enriched_perf, dims_perf)

        logger.info("Aggregating Attendance fact...")
        fact_att = build_attendance_fact(
            df_journal, dims_att['dim_student'], dims_att['dim_day'], dims_att['dim_weather']
        )

        # =========================================================
        # 5. LOAD
        # =========================================================
        logger.info("Loading dimensions...")
        load_dimensions(dims_perf)
        load_attendance_dimensions(dims_att)

        logger.info("Loading facts...")
        load_fact(fact_perf)
        load_attendance_fact(fact_att)

        logger.success("=== FULL ETL COMPLETED SUCCESSFULLY ===")
        logger.info(f"Performance fact rows: {len(fact_perf)}")
        logger.info(f"Attendance fact rows: {len(fact_att)}")

    except Exception as e:
        logger.error(f"ETL failed with error: {e}")
        import traceback
        traceback.print_exc()
        logger.remove()
        os._exit(1)


if __name__ == "__main__":
    try:
        main()
        logger.remove()
        os._exit(0)
    except Exception as e:
        logger.remove()
        os._exit(1)
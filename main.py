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

load_dotenv()

from extract.extractor import extract_all
from transform.dimensions import build_all_dimensions
from transform.fact import enrich_data, build_fact
from load.loader import load_dimensions, load_fact


def main():
    logger.info("=== MAIN.PY VERSION: OS_EXIT ===")   # <-- proof line
    try:
        logger.info("Starting Student Performance ETL Pipeline")
        logger.info("Extracting data from source database...")
        df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content = extract_all()

        logger.info("Building dimensions...")
        dims = build_all_dimensions(df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content)

        logger.info("Aggregating fact table...")
        enriched = enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod, dims['dim_year'])
        fact = build_fact(enriched, dims)

        logger.info("Loading into warehouse...")
        load_dimensions(dims)
        load_fact(fact)

        logger.success("ETL Pipeline completed successfully!")
        logger.info(f"Fact rows loaded: {len(fact)}")

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
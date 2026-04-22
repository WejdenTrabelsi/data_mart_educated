from utils.db import get_warehouse_engine
import pandas as pd
from loguru import logger
from sqlalchemy.dialects.mssql import NVARCHAR


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
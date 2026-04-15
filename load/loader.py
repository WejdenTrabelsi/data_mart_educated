from utils.db import get_warehouse_engine
import pandas as pd
from loguru import logger
from sqlalchemy import text

def load_dimensions(dims: dict):
    engine = get_warehouse_engine()
    
    mapping = {
        'dim_year': 'DimYear',
        'dim_semester': 'DimSemester',
        'dim_level': 'DimLevel',
        'dim_branch': 'DimBranch',
        'dim_content': 'DimContent'
    }
    
    for key, table_name in mapping.items():
        df = dims[key]
        logger.info(f"Loading {len(df)} rows into {table_name}")
        
        # Load directly with correct table name using schema parameter (most reliable way)
        df.to_sql(table_name, engine, if_exists='replace', index=False, schema=None)
    
    logger.success("✅ All dimensions loaded successfully")


def load_fact(fact_df: pd.DataFrame):
    if len(fact_df) == 0:
        logger.warning("Fact table is empty - skipping")
        return
    
    engine = get_warehouse_engine()
    logger.info(f"Loading fact table with {len(fact_df)} rows")
    
    # Direct load with correct table name
    fact_df.to_sql('Fact_StudentPerformance', engine, if_exists='replace', index=False)
    
    logger.success(f"✅ Fact_StudentPerformance loaded successfully with {len(fact_df)} rows")
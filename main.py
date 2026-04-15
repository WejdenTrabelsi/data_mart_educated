import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Import our modules
from extract.extractor import extract_all
from transform.dimensions import build_all_dimensions
from transform.fact import enrich_data, build_fact
from load.loader import load_dimensions, load_fact

def main():
    try:
        logger.info("🚀 Starting Student Performance ETL Pipeline")
        
        # 1. Extract
        logger.info("📥 Extracting data from source database...")
        df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content = extract_all()
        
        # 2. Build dimensions
        logger.info("🔧 Building dimensions...")
        dims = build_all_dimensions(df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content)
        
        # 3. Build fact
        logger.info("📊 Aggregating fact table...")
        enriched = enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod)
        fact = build_fact(enriched, dims)
        
        # 4. Load
        logger.info("💾 Loading into warehouse...")
        load_dimensions(dims)
        load_fact(fact)
        
        logger.success("✅ ETL Pipeline completed successfully!")
        logger.info(f"   Fact rows loaded: {len(fact)}")
        
    except Exception as e:
        logger.error(f"❌ ETL failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
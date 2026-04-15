import pandas as pd
from utils.db import get_source_engine

def extract_all():
    engine = get_source_engine()
    print("Extracting live data from SQL Server...")
    
    df_grid = pd.read_sql("SELECT * FROM [ContentEvaluationGrid]", engine)
    df_gridline = pd.read_sql("SELECT * FROM [ContentEvaluationGridLine]", engine)
    df_studyplan = pd.read_sql("SELECT * FROM [StudyPlan]", engine)
    df_schoolyear = pd.read_sql("SELECT * FROM [SchoolYear]", engine)
    df_schoolyearperiod = pd.read_sql("SELECT * FROM [SchoolYearPeriod]", engine)
    
    # Cast Arabic text columns explicitly to NVARCHAR to force Unicode retrieval
    df_content = pd.read_sql(
        "SELECT Oid, CAST(Description AS NVARCHAR(MAX)) AS Description, "
        "CAST(Description2 AS NVARCHAR(MAX)) AS Description2 FROM [Content]",
        engine
    )
    
    # Quick sanity check — print a sample to verify Arabic shows correctly
    print("Sample content names (should show Arabic, not ???):")
    print(df_content[['Oid', 'Description']].head(3).to_string())
    
    print(f"Extracted: {len(df_grid)} grids, {len(df_gridline)} grades, "
          f"{len(df_studyplan)} study plans, {len(df_content)} contents")
    
    return df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content
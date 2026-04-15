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
    df_content = pd.read_sql("SELECT * FROM [Content]", engine)        # ← NEW
    
    print(f"Extracted: {len(df_grid)} grids, {len(df_gridline)} grades, "
          f"{len(df_studyplan)} study plans, {len(df_content)} contents")
    
    return df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content
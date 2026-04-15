import pandas as pd
from transform.derive import derive_level, derive_branch
from transform.normalize import normalize_semester
from transform.clean import clean_grades

def enrich_data(df_gridline: pd.DataFrame, df_grid: pd.DataFrame, 
                df_studyplan: pd.DataFrame, df_schoolyearperiod: pd.DataFrame) -> pd.DataFrame:
    df = clean_grades(df_gridline)
    print(f"After cleaning grades: {len(df)} rows")
    
    # Merge with Grid
    df = df.merge(df_grid, left_on='ContentEvaluationGrid', right_on='Oid', how='left', suffixes=('', '_grid'))
    print(f"After merging with Grid: {len(df)} rows")
    
    # Derive level and branch
    study_mapping = df_studyplan[['SchoolLevel', 'Description']].drop_duplicates()
    study_mapping['level_name'] = study_mapping['Description'].apply(derive_level)
    study_mapping['branch_name'] = study_mapping['Description'].apply(derive_branch)
    
    df = df.merge(study_mapping, left_on='SchoolLevel', right_on='SchoolLevel', how='left')
    print(f"After merging level/branch: {len(df)} rows")
    
    # Semester
    period_mapping = df_schoolyearperiod[['Oid', 'Name']].rename(columns={'Oid': 'SchoolYearPeriod'})
    period_mapping['semester_code'] = period_mapping['Name'].apply(normalize_semester)
    df = df.merge(period_mapping, on='SchoolYearPeriod', how='left')
    print(f"After merging semester: {len(df)} rows")
    
    # Drop rows missing key fields
    df = df.dropna(subset=['Content', 'level_name', 'branch_name', 'semester_code'])
    print(f"Final enriched rows before aggregation: {len(df)} rows")
    
    return df

def build_fact(enriched_df: pd.DataFrame, dims: dict) -> pd.DataFrame:
    if len(enriched_df) == 0:
        print("WARNING: Enriched dataframe is empty - no data to aggregate!")
        return pd.DataFrame()
    
    df = enriched_df.copy()
    
    # Map to surrogate keys
    df = df.merge(dims['dim_content'][['content_natural_key', 'content_sk']], 
                  left_on='Content', right_on='content_natural_key', how='left')
    
    df = df.merge(dims['dim_level'][['level_natural_key', 'level_sk']], 
                  left_on='SchoolLevel', right_on='level_natural_key', how='left')
    
    df = df.merge(dims['dim_branch'][['branch_name', 'branch_sk']], 
                  on='branch_name', how='left')
    
    df = df.merge(dims['dim_semester'][['semester_code', 'year_sk', 'semester_sk']], 
                  on='semester_code', how='left')
    
    print(f"Rows after all key mapping: {len(df)}")
    
    # Aggregation
    fact = df.groupby(['content_sk', 'level_sk', 'branch_sk', 'semester_sk']).agg(
        avg_grade=('Note', 'mean'),
        success_rate=('Note', lambda x: (x >= 10).mean() * 100),
        nb_students=('Note', 'count')
    ).reset_index()
    
    fact['avg_grade'] = fact['avg_grade'].round(2)
    fact['success_rate'] = fact['success_rate'].round(2)
    
    print(f"Final fact rows: {len(fact)}")
    return fact
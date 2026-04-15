import pandas as pd
from transform.derive import derive_level, derive_branch
from transform.normalize import normalize_semester
from transform.clean import clean_grades
def enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod):
    df = clean_grades(df_gridline)
    print(f"After cleaning grades: {len(df)} rows")
    
    # Merge with Grid
    df = df.merge(
        df_grid[['Oid', 'SchoolLevel', 'SchoolYearPeriod', 'Content']], 
        left_on='ContentEvaluationGrid', right_on='Oid', 
        how='left', suffixes=('', '_grid')
    )
    print(f"After merging with Grid: {len(df)} rows")
    
    # Drop rows with no SchoolLevel at all (truly orphaned grades)
    before = len(df)
    df = df.dropna(subset=['SchoolLevel'])
    print(f"Dropped {before - len(df)} rows with no SchoolLevel (orphaned grids)")
    
    # Build study mapping — ONE row per SchoolLevel UUID
    study_mapping = (
    df_studyplan[['SchoolLevel', 'Description']]
    .dropna(subset=['Description'])          # drop nulls first
    .drop_duplicates(subset=['SchoolLevel'])  # then deduplicate
    .copy()
)
    study_mapping['level_name'] = study_mapping['Description'].apply(derive_level)
    study_mapping['branch_name'] = study_mapping['Description'].apply(derive_branch)
    
    df = df.merge(study_mapping, on='SchoolLevel', how='left')
    print(f"After merging level/branch: {len(df)} rows")
    
    # ---- Handle NaN level/branch from unmatched SchoolLevel UUIDs ----
    # These are valid grades but their StudyPlan entry is missing
    # Try to recover by looking at the grid's Description directly if available
    nan_mask = df['level_name'].isna() | df['branch_name'].isna()
    print(f"Rows with missing level/branch after merge: {nan_mask.sum()}")
    
    # Semester
    period_mapping = (
        df_schoolyearperiod[['Oid', 'Name']]
        .rename(columns={'Oid': 'SchoolYearPeriod'})
        .copy()
    )
    period_mapping['semester_code'] = period_mapping['Name'].apply(normalize_semester)
    df = df.merge(period_mapping, on='SchoolYearPeriod', how='left')
    print(f"After merging semester: {len(df)} rows")
    
    print("\n=== BRANCH DISTRIBUTION ===")
    print(df['branch_name'].value_counts(dropna=False))
    print("\n=== LEVEL DISTRIBUTION ===")
    print(df['level_name'].value_counts(dropna=False))
    unknown_branch = df[df['branch_name'] == 'Unknown']
    print("=== UNKNOWN BRANCH DESCRIPTIONS ===")
    print(unknown_branch['Description'].value_counts().head(20))
    unknown_level = df[df['level_name'] == 'Unknown']  
    print("=== UNKNOWN LEVEL DESCRIPTIONS ===")
    print(unknown_level['Description'].value_counts().head(20))
    # Drop invalid rows
    df = df.dropna(subset=['Content', 'level_name', 'branch_name', 'semester_code'])
    df = df[df['level_name'] != 'Unknown']
    df = df[df['branch_name'] != 'Unknown']
    print(f"\nFinal enriched rows before aggregation: {len(df)} rows")
    
    return df

def build_fact(enriched_df, dims):
    if len(enriched_df) == 0:
        print("WARNING: Enriched dataframe is empty!")
        return pd.DataFrame()
    
    df = enriched_df.copy()
    print(f"Starting fact build with {len(df)} rows")
    
    # Content
    df = df.merge(dims['dim_content'][['content_natural_key', 'content_sk']], 
                  left_on='Content', right_on='content_natural_key', how='left')
    print(f"After content_sk merge: {len(df)} | NaN: {df['content_sk'].isna().sum()}")
    
    # Level — join on level_name (NOT level_natural_key)
    df = df.merge(dims['dim_level'][['level_name', 'level_sk']], 
                  on='level_name', how='left')
    print(f"After level_sk merge: {len(df)} | NaN: {df['level_sk'].isna().sum()}")
    
    # Branch
    df = df.merge(dims['dim_branch'][['branch_name', 'branch_sk']], 
                  on='branch_name', how='left')
    print(f"After branch_sk merge: {len(df)} | NaN: {df['branch_sk'].isna().sum()}")
    
    # Semester
    df = df.merge(dims['dim_semester'][['semester_code', 'semester_sk']], 
                  on='semester_code', how='left')
    print(f"After semester_sk merge: {len(df)} | NaN: {df['semester_sk'].isna().sum()}")
    
    # Drop any remaining missing keys
    before = len(df)
    df = df.dropna(subset=['content_sk', 'level_sk', 'branch_sk', 'semester_sk'])
    print(f"Dropped {before - len(df)} rows | Ready: {len(df)}")
    
    # Aggregate
    fact = df.groupby(['content_sk', 'level_sk', 'branch_sk', 'semester_sk']).agg(
        avg_grade=('Note', 'mean'),
        success_rate=('Note', lambda x: (x >= 10).mean() * 100),
        nb_students=('Note', 'count')
    ).reset_index()
    
    fact['avg_grade'] = fact['avg_grade'].round(2)
    fact['success_rate'] = fact['success_rate'].round(2)
    
    print(f"Final fact rows: {len(fact)}")
    return fact
import pandas as pd
from .normalize import normalize_semester
from .derive import derive_level, derive_branch

def build_dim_year(df_schoolyear: pd.DataFrame) -> pd.DataFrame:
    df = df_schoolyear[['Oid', 'Description']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'year_natural_key', 'Description': 'year_name'})
    df['year_sk'] = range(1, len(df) + 1)
    return df[['year_sk', 'year_natural_key', 'year_name']]

def build_dim_semester(df_schoolyearperiod: pd.DataFrame, dim_year: pd.DataFrame) -> pd.DataFrame:
    df = df_schoolyearperiod[['Oid', 'Name', 'CurrentSchoolYear']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'semester_natural_key', 'Name': 'semester_raw'})
    
    df['semester_code'] = df['semester_raw'].apply(normalize_semester)
    
    # Clean merge with year
    df = df.merge(dim_year[['year_natural_key', 'year_sk']], 
                  left_on='CurrentSchoolYear', right_on='year_natural_key', how='left')
    
    df = df.dropna(subset=['year_sk', 'semester_code'])
    
    # Important: Keep only one row per (year_sk + semester_code)
    df = df.drop_duplicates(subset=['year_sk', 'semester_code'])
    
    df = df.sort_values(['year_sk', 'semester_code'])
    df['semester_sk'] = range(1, len(df) + 1)
    
    return df[['semester_sk', 'semester_code', 'year_sk']]

def build_dim_level(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['SchoolLevel', 'Description']].drop_duplicates().copy()
    df['level_name'] = df['Description'].apply(derive_level)
    
    # Clean: Keep only meaningful levels and deduplicate by name
    valid_levels = ["1ère année", "2ème année", "3ème année", "4ème année (bac)"]
    df = df[df['level_name'].isin(valid_levels)]
    
    # One row per unique level_name
    df = df.drop_duplicates(subset=['level_name'])
    
    df = df.sort_values('level_name')
    df['level_sk'] = range(1, len(df) + 1)
    df['level_natural_key'] = df['SchoolLevel']  # keep one representative UUID
    
    return df[['level_sk', 'level_natural_key', 'level_name']]

def build_dim_branch(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['Description']].drop_duplicates().copy()
    df['branch_name'] = df['Description'].apply(derive_branch)
    
    # Clean branches
    df = df[df['branch_name'] != "Unknown"]
    df = df.drop_duplicates(subset=['branch_name'])
    df = df.sort_values('branch_name')
    df['branch_sk'] = range(1, len(df) + 1)
    return df[['branch_sk', 'branch_name']]
def build_dim_content(df_grid: pd.DataFrame, df_content: pd.DataFrame) -> pd.DataFrame:
    # Get unique Content OIDs from the grids
    df = df_grid[['Content']].drop_duplicates().copy()
    df = df.rename(columns={'Content': 'content_natural_key'})
    
    # Join with real Content table
    df = df.merge(
        df_content[['Oid', 'Description', 'Description2']], 
        left_on='content_natural_key', 
        right_on='Oid', 
        how='left'
    )
    
    # Priority: Use Description2 if available, then Description, then fallback
    df['content_name'] = df['Description2'].fillna(df['Description'])
    
    # Clean the name
    df['content_name'] = df['content_name'].astype(str).str.strip()
    
    # Remove very short or useless names and replace with better fallback
    mask_bad = (df['content_name'].str.len() < 3) | (df['content_name'] == 'nan')
    df.loc[mask_bad, 'content_name'] = df.loc[mask_bad, 'content_natural_key'].astype(str)
    
    # Final fallback
    df['content_name'] = df['content_name'].replace('nan', 'Unknown Subject')
    
    df = df.drop(columns=['Oid', 'Description', 'Description2'])
    df['content_sk'] = range(1, len(df) + 1)
    
    return df[['content_sk', 'content_natural_key', 'content_name']]
def build_all_dimensions(df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content):
    dim_year = build_dim_year(df_schoolyear)
    dim_semester = build_dim_semester(df_schoolyearperiod, dim_year)
    dim_level = build_dim_level(df_studyplan)
    dim_branch = build_dim_branch(df_studyplan)
    dim_content = build_dim_content(df_grid, df_content)   # ← updated
    
    print(f"✅ Dimensions built:")
    print(f"   - Year: {len(dim_year)}")
    print(f"   - Semester: {len(dim_semester)}")
    print(f"   - Level: {len(dim_level)}")
    print(f"   - Branch: {len(dim_branch)}")
    print(f"   - Content: {len(dim_content)} (with real names)")
    
    return {
        'dim_year': dim_year,
        'dim_semester': dim_semester,
        'dim_level': dim_level,
        'dim_branch': dim_branch,
        'dim_content': dim_content
    }
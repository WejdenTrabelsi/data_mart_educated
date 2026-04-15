import pandas as pd
from .normalize import normalize_semester
from .derive import derive_level, derive_branch

def build_dim_year(df_schoolyear: pd.DataFrame) -> pd.DataFrame:
    df = df_schoolyear[['Oid', 'Description']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'year_natural_key', 'Description': 'year_name'})
    df['year_sk'] = range(1, len(df) + 1)
    return df[['year_sk', 'year_natural_key', 'year_name']]

# Quick fix: just keep one row per semester_code (ignore year)
def build_dim_semester(df_schoolyearperiod, dim_year):
    df = df_schoolyearperiod[['Oid', 'Name', 'CurrentSchoolYear']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'semester_natural_key', 'Name': 'semester_raw'})
    df['semester_code'] = df['semester_raw'].apply(normalize_semester)
    df = df[df['semester_code'] != 'Unknown']
    df = df.drop_duplicates(subset=['semester_code'])  # Only 3 rows: S1, S2, S3
    df = df.sort_values('semester_code').reset_index(drop=True)
    df['semester_sk'] = range(1, len(df) + 1)
    return df[['semester_sk', 'semester_code']]
def build_dim_level(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['SchoolLevel', 'Description']].drop_duplicates().copy()
    df = df.dropna(subset=['Description'])
    df['level_name'] = df['Description'].apply(derive_level)
    
    # Group to keep only 4 levels
    level_map = df.groupby('level_name').agg({
        'SchoolLevel': 'first',
        'Description': 'first'
    }).reset_index()
    
    level_map = level_map[level_map['level_name'] != "Unknown"]
    level_map = level_map.sort_values('level_name').reset_index(drop=True)
    level_map['level_sk'] = range(1, len(level_map) + 1)
    level_map['level_natural_key'] = level_map['SchoolLevel']
    
    print("\n=== FINAL CLEAN LEVEL DIMENSION ===")
    print(level_map[['level_sk', 'level_name', 'Description']])
    print(f"Total clean levels: {len(level_map)}")
    
    return level_map[['level_sk', 'level_natural_key', 'level_name']]
def build_dim_branch(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['Description']].drop_duplicates().copy()
    df = df.dropna(subset=['Description'])
    df['branch_name'] = df['Description'].apply(derive_branch)   # ← use new function
    
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
import pandas as pd
from transform.derive import derive_level, derive_branch
from transform.normalize import normalize_semester
from transform.clean import clean_grades


def enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod, dim_year):
    df = clean_grades(df_gridline)
    print(f"After cleaning grades: {len(df)} rows")

    # Merge with Grid
    df = df.merge(
        df_grid[['Oid', 'SchoolLevel', 'SchoolYearPeriod', 'Content']],
        left_on='ContentEvaluationGrid',
        right_on='Oid',
        how='left',
        suffixes=('', '_grid')
    )
    print(f"After merging with Grid: {len(df)} rows")

    # Drop orphan rows
    before = len(df)
    df = df.dropna(subset=['SchoolLevel'])
    print(f"Dropped {before - len(df)} rows with no SchoolLevel")

    # Study mapping (level + branch)
    study_mapping = (
        df_studyplan[['SchoolLevel', 'Description']]
        .dropna(subset=['Description'])
        .drop_duplicates(subset=['SchoolLevel'])
        .copy()
    )

    study_mapping['level_name'] = study_mapping['Description'].apply(derive_level)
    study_mapping['branch_name'] = study_mapping['Description'].apply(derive_branch)

    df = df.merge(study_mapping, on='SchoolLevel', how='left')
    print(f"After merging level/branch: {len(df)} rows")

    # Debug missing values
    nan_mask = df['level_name'].isna() | df['branch_name'].isna()
    print(f"Rows with missing level/branch: {nan_mask.sum()}")

    # ---- Semester + Year mapping ----
    period_mapping = (
        df_schoolyearperiod[['Oid', 'Name', 'CurrentSchoolYear']]
        .rename(columns={'Oid': 'SchoolYearPeriod'})
        .copy()
    )

    period_mapping['semester_code'] = period_mapping['Name'].apply(normalize_semester)

    # FIX: use dim_year correctly
    period_mapping = period_mapping.merge(
        dim_year[['year_natural_key', 'year_sk']],
        left_on='CurrentSchoolYear',
        right_on='year_natural_key',
        how='left'
    )

    df = df.merge(
        period_mapping[['SchoolYearPeriod', 'semester_code', 'year_sk']],
        on='SchoolYearPeriod',
        how='left'
    )
    print(f"After merging semester + year: {len(df)} rows")

    # Debug distributions
    print("\n=== BRANCH DISTRIBUTION ===")
    print(df['branch_name'].value_counts(dropna=False))

    print("\n=== LEVEL DISTRIBUTION ===")
    print(df['level_name'].value_counts(dropna=False))

    # Clean invalid rows
    df = df.dropna(subset=['Content', 'level_name', 'branch_name', 'semester_code', 'year_sk'])
    df = df[df['level_name'] != 'Unknown']
    df = df[df['branch_name'] != 'Unknown']

    print(f"\nFinal enriched rows: {len(df)} rows")

    return df


def build_fact(enriched_df, dims):
    if len(enriched_df) == 0:
        print("WARNING: Enriched dataframe is empty!")
        return pd.DataFrame()

    df = enriched_df.copy()
    print(f"Starting fact build with {len(df)} rows")

    # Content
    df = df.merge(
        dims['dim_content'][['content_natural_key', 'content_sk']],
        left_on='Content',
        right_on='content_natural_key',
        how='left'
    )
    print(f"After content_sk merge: NaN = {df['content_sk'].isna().sum()}")

    # Level
    df = df.merge(
        dims['dim_level'][['level_name', 'level_sk']],
        on='level_name',
        how='left'
    )
    print(f"After level_sk merge: NaN = {df['level_sk'].isna().sum()}")

    # Branch
    df = df.merge(
        dims['dim_branch'][['branch_name', 'branch_sk']],
        on='branch_name',
        how='left'
    )
    print(f"After branch_sk merge: NaN = {df['branch_sk'].isna().sum()}")

    # ✅ FIXED: Semester merge on BOTH keys
    df = df.merge(
        dims['dim_semester'][['semester_code', 'year_sk', 'semester_sk']],
        on=['semester_code', 'year_sk'],
        how='left'
    )
    print(f"After semester_sk merge: NaN = {df['semester_sk'].isna().sum()}")

    # Drop invalid rows
    before = len(df)
    df = df.dropna(subset=['content_sk', 'level_sk', 'branch_sk', 'semester_sk'])
    print(f"Dropped {before - len(df)} rows | Remaining: {len(df)}")

    # Aggregate
    fact = df.groupby(
        ['content_sk', 'level_sk', 'branch_sk', 'semester_sk']
    ).agg(
        avg_grade=('Note', 'mean'),
        success_rate=('Note', lambda x: (x >= 10).mean() * 100),
        nb_students=('Note', 'count')
    ).reset_index()

    fact['avg_grade'] = fact['avg_grade'].round(2)
    fact['success_rate'] = fact['success_rate'].round(2)

    print(f"Final fact rows: {len(fact)}")

    return fact
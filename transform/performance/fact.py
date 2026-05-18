import pandas as pd
from loguru import logger
from ..clean import clean_grades
from ..derive import derive_level, derive_branch
from ..normalize import normalize_semester


def enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod, dim_year):
    # Step 1: Clean grades (explicit preprocessing)
    df = clean_grades(df_gridline)
    logger.info(f"After cleaning grades: {len(df)} rows")

    # Step 2: Merge with grid
    df = df.merge(
        df_grid[['Oid', 'SchoolLevel', 'SchoolYearPeriod', 'Content']],
        left_on='ContentEvaluationGrid',
        right_on='Oid',
        how='left',
        suffixes=('', '_grid')
    )
    logger.info(f"After merging with Grid: {len(df)} rows")

    before = len(df)
    df = df.dropna(subset=['SchoolLevel'])
    logger.info(f"Dropped {before - len(df)} rows with no SchoolLevel")

    # Step 3: Derive level and branch (explicit transformation)
    study_mapping = (
        df_studyplan[['SchoolLevel', 'Description']]
        .dropna(subset=['Description'])
        .drop_duplicates(subset=['SchoolLevel'])
        .copy()
    )
    study_mapping['level_name'] = study_mapping['Description'].apply(derive_level)
    study_mapping['branch_name'] = study_mapping['Description'].apply(derive_branch)

    df = df.merge(study_mapping, on='SchoolLevel', how='left')
    logger.info(f"After merging level/branch: {len(df)} rows")

    nan_mask = df['level_name'].isna() | df['branch_name'].isna()
    logger.info(f"Rows with missing level/branch: {nan_mask.sum()}")

    # Step 4: Normalize semester (explicit normalization)
    period_mapping = (
        df_schoolyearperiod[['Oid', 'Name', 'CurrentSchoolYear']]
        .rename(columns={'Oid': 'SchoolYearPeriod'})
        .copy()
    )
    period_mapping['semester_code'] = period_mapping['Name'].apply(normalize_semester)
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
    logger.info(f"After merging semester + year: {len(df)} rows")

    logger.info(f"BRANCH DISTRIBUTION:\n{df['branch_name'].value_counts(dropna=False).to_string()}")
    logger.info(f"LEVEL DISTRIBUTION:\n{df['level_name'].value_counts(dropna=False).to_string()}")

    # Final clean
    df = df.dropna(subset=['Content', 'level_name', 'branch_name', 'semester_code', 'year_sk'])
    df = df[df['level_name'] != 'Unknown']
    df = df[df['branch_name'] != 'Unknown']

    logger.info(f"Final enriched rows: {len(df)} rows")
    return df


def build_fact(enriched_df, dims):
    if len(enriched_df) == 0:
        logger.warning("Enriched dataframe is empty!")
        return pd.DataFrame()

    df = enriched_df.copy()
    logger.info(f"Starting fact build with {len(df)} rows")

    # Dimension lookups
    df = df.merge(
        dims['dim_content'][['content_natural_key', 'content_sk']],
        left_on='Content', right_on='content_natural_key', how='left'
    )
    logger.info(f"After content_sk merge: NaN = {df['content_sk'].isna().sum()}")

    df = df.merge(
        dims['dim_level'][['level_name', 'level_sk']],
        on='level_name', how='left'
    )
    logger.info(f"After level_sk merge: NaN = {df['level_sk'].isna().sum()}")

    df = df.merge(
        dims['dim_branch'][['branch_name', 'branch_sk']],
        on='branch_name', how='left'
    )
    logger.info(f"After branch_sk merge: NaN = {df['branch_sk'].isna().sum()}")

    df = df.merge(
        dims['dim_semester'][['semester_code', 'year_sk', 'semester_sk']],
        on=['semester_code', 'year_sk'], how='left'
    )
    logger.info(f"After semester_sk merge: NaN = {df['semester_sk'].isna().sum()}")

    before = len(df)
    df = df.dropna(subset=['content_sk', 'level_sk', 'branch_sk', 'semester_sk'])
    logger.info(f"Dropped {before - len(df)} rows | Remaining: {len(df)}")

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

    logger.info(f"Final fact rows: {len(fact)}")
    VALID_CURRICULUM = {
    # 1ère année (General)
    ("General", "1ère année", "رياضيات"),
    ("General", "1ère année", "انقليزية"),
    ("General", "1ère année", "إعلامية"),
    ("General", "1ère année", "فرنسية"),
    ("General", "1ère année", "تربية بدنية"),
    ("General", "1ère année", "اللغة العربية"),
    ("General", "1ère année", "تكنولوجيا"),
    ("General", "1ère année", "علوم فيزيائية"),
    ("General", "1ère année", "تاريخ"),
    ("General", "1ère année", "تفكير إسلامي"),
    ("General", "1ère année", "جغرافيا"),
    ("General", "1ère année", "تربية مدنية"),

    # 2ème année — Science
    ("Science", "2ème année", "رياضيات"),
    ("Science", "2ème année", "انقليزية"),
    ("Science", "2ème année", "إعلامية"),
    ("Science", "2ème année", "فرنسية"),
    ("Science", "2ème année", "تربية بدنية"),
    ("Science", "2ème année", "اللغة العربية"),
    ("Science", "2ème année", "تكنولوجيا"),
    ("Science", "2ème année", "علوم فيزيائية"),
    ("Science", "2ème année", "علوم الحياة والأرض"),
    ("Science", "2ème année", "تاريخ"),
    ("Science", "2ème année", "تفكير إسلامي"),
    ("Science", "2ème année", "جغرافيا"),
    ("Science", "2ème année", "تربية مدنية"),

    # 2ème année — Eco
    ("Eco", "2ème année", "رياضيات"),
    ("Eco", "2ème année", "انقليزية"),
    ("Eco", "2ème année", "إعلامية"),
    ("Eco", "2ème année", "فرنسية"),
    ("Eco", "2ème année", "تربية بدنية"),
    ("Eco", "2ème année", "اللغة العربية"),
    ("Eco", "2ème année", "تاريخ"),
    ("Eco", "2ème année", "تفكير إسلامي"),
    ("Eco", "2ème année", "جغرافيا"),
    ("Eco", "2ème année", "تربية مدنية"),
    ("Eco", "2ème année", "إقتصاد"),
    ("Eco", "2ème année", "تصرف"),

    # 3ème année — Science
    ("Science", "3ème année", "رياضيات"),
    ("Science", "3ème année", "انقليزية"),
    ("Science", "3ème année", "إعلامية"),
    ("Science", "3ème année", "فرنسية"),
    ("Science", "3ème année", "تربية بدنية"),
    ("Science", "3ème année", "اللغة العربية"),
    ("Science", "3ème année", "علوم فيزيائية"),
    ("Science", "3ème année", "علوم الحياة والأرض"),
    ("Science", "3ème année", "تاريخ"),
    ("Science", "3ème année", "تفكير إسلامي"),
    ("Science", "3ème année", "جغرافيا"),
    ("Science", "3ème année", "الإيطالية"),
    ("Science", "3ème année", "الفلسفة"),
    ("Science", "3ème année", "الإسبانية"),
    ("Science", "3ème année", "تربية تشكيلية"),
    ("Science", "3ème année", "الألمانية"),

    # 3ème année — Eco
    ("Eco", "3ème année", "رياضيات"),
    ("Eco", "3ème année", "انقليزية"),
    ("Eco", "3ème année", "إعلامية"),
    ("Eco", "3ème année", "فرنسية"),
    ("Eco", "3ème année", "تربية بدنية"),
    ("Eco", "3ème année", "اللغة العربية"),
    ("Eco", "3ème année", "تاريخ"),
    ("Eco", "3ème année", "تفكير إسلامي"),
    ("Eco", "3ème année", "جغرافيا"),
    ("Eco", "3ème année", "الإيطالية"),
    ("Eco", "3ème année", "الفلسفة"),
    ("Eco", "3ème année", "الإسبانية"),
    ("Eco", "3ème année", "تربية تشكيلية"),
    ("Eco", "3ème année", "الألمانية"),
    ("Eco", "3ème année", "إقتصاد"),
    ("Eco", "3ème année", "تصرف"),

    # 3ème année — Technique
    ("Technique", "3ème année", "رياضيات"),
    ("Technique", "3ème année", "انقليزية"),
    ("Technique", "3ème année", "إعلامية"),
    ("Technique", "3ème année", "فرنسية"),
    ("Technique", "3ème année", "تربية بدنية"),
    ("Technique", "3ème année", "اللغة العربية"),
    ("Technique", "3ème année", "علوم فيزيائية"),
    ("Technique", "3ème année", "تاريخ"),
    ("Technique", "3ème année", "تفكير إسلامي"),
    ("Technique", "3ème année", "جغرافيا"),
    ("Technique", "3ème année", "الإيطالية"),
    ("Technique", "3ème année", "الفلسفة"),
    ("Technique", "3ème année", "الإسبانية"),
    ("Technique", "3ème année", "تربية تشكيلية"),
    ("Technique", "3ème année", "الألمانية"),
    ("Technique", "3ème année", "هندسة الية"),
    ("Technique", "3ème année", "هندسة كهربائية"),

    # 3ème année — Math
    ("Math", "3ème année", "رياضيات"),
    ("Math", "3ème année", "انقليزية"),
    ("Math", "3ème année", "إعلامية"),
    ("Math", "3ème année", "فرنسية"),
    ("Math", "3ème année", "تربية بدنية"),
    ("Math", "3ème année", "اللغة العربية"),
    ("Math", "3ème année", "علوم فيزيائية"),
    ("Math", "3ème année", "علوم الحياة والأرض"),
    ("Math", "3ème année", "تاريخ"),
    ("Math", "3ème année", "تفكير إسلامي"),
    ("Math", "3ème année", "جغرافيا"),
    ("Math", "3ème année", "الإيطالية"),
    ("Math", "3ème année", "الفلسفة"),
    ("Math", "3ème année", "الإسبانية"),
    ("Math", "3ème année", "تربية تشكيلية"),
    ("Math", "3ème année", "الألمانية"),

    # 4ème année (bac) — Science
    ("Science", "4ème année (bac)", "رياضيات"),
    ("Science", "4ème année (bac)", "انقليزية"),
    ("Science", "4ème année (bac)", "إعلامية"),
    ("Science", "4ème année (bac)", "فرنسية"),
    ("Science", "4ème année (bac)", "تربية بدنية"),
    ("Science", "4ème année (bac)", "اللغة العربية"),
    ("Science", "4ème année (bac)", "علوم فيزيائية"),
    ("Science", "4ème année (bac)", "تاريخ"),
    ("Science", "4ème année (bac)", "جغرافيا"),
    ("Science", "4ème année (bac)", "الإيطالية"),
    ("Science", "4ème année (bac)", "الفلسفة"),
    ("Science", "4ème année (bac)", "الإسبانية"),
    ("Science", "4ème année (bac)", "تربية تشكيلية"),
    ("Science", "4ème année (bac)", "الألمانية"),

    # 4ème année (bac) — Eco
    ("Eco", "4ème année (bac)", "رياضيات"),
    ("Eco", "4ème année (bac)", "انقليزية"),
    ("Eco", "4ème année (bac)", "إعلامية"),
    ("Eco", "4ème année (bac)", "فرنسية"),
    ("Eco", "4ème année (bac)", "تربية بدنية"),
    ("Eco", "4ème année (bac)", "اللغة العربية"),
    ("Eco", "4ème année (bac)", "تاريخ"),
    ("Eco", "4ème année (bac)", "جغرافيا"),
    ("Eco", "4ème année (bac)", "الإيطالية"),
    ("Eco", "4ème année (bac)", "الفلسفة"),
    ("Eco", "4ème année (bac)", "الإسبانية"),
    ("Eco", "4ème année (bac)", "تربية تشكيلية"),
    ("Eco", "4ème année (bac)", "الألمانية"),
    ("Eco", "4ème année (bac)", "إقتصاد"),
    ("Eco", "4ème année (bac)", "تصرف"),

    # 4ème année (bac) — Technique
    ("Technique", "4ème année (bac)", "رياضيات"),
    ("Technique", "4ème année (bac)", "انقليزية"),
    ("Technique", "4ème année (bac)", "إعلامية"),
    ("Technique", "4ème année (bac)", "فرنسية"),
    ("Technique", "4ème année (bac)", "تربية بدنية"),
    ("Technique", "4ème année (bac)", "اللغة العربية"),
    ("Technique", "4ème année (bac)", "علوم فيزيائية"),
    ("Technique", "4ème année (bac)", "تاريخ"),
    ("Technique", "4ème année (bac)", "جغرافيا"),
    ("Technique", "4ème année (bac)", "الإيطالية"),
    ("Technique", "4ème année (bac)", "الفلسفة"),
    ("Technique", "4ème année (bac)", "الإسبانية"),
    ("Technique", "4ème année (bac)", "تربية تشكيلية"),
    ("Technique", "4ème année (bac)", "الألمانية"),
    ("Technique", "4ème année (bac)", "هندسة الية"),
    ("Technique", "4ème année (bac)", "هندسة كهربائية"),

    # 4ème année (bac) — Math
    ("Math", "4ème année (bac)", "رياضيات"),
    ("Math", "4ème année (bac)", "انقليزية"),
    ("Math", "4ème année (bac)", "إعلامية"),
    ("Math", "4ème année (bac)", "فرنسية"),
    ("Math", "4ème année (bac)", "تربية بدنية"),
    ("Math", "4ème année (bac)", "اللغة العربية"),
    ("Math", "4ème année (bac)", "علوم فيزيائية"),
    ("Math", "4ème année (bac)", "تاريخ"),
    ("Math", "4ème année (bac)", "جغرافيا"),
    ("Math", "4ème année (bac)", "الإيطالية"),
    ("Math", "4ème année (bac)", "الفلسفة"),
    ("Math", "4ème année (bac)", "الإسبانية"),
    ("Math", "4ème année (bac)", "تربية تشكيلية"),
    ("Math", "4ème année (bac)", "الألمانية"),
}

    # Merge dimension names back for validation
    fact_check = fact.merge(
        dims["dim_branch"][["branch_sk", "branch_name"]], on="branch_sk"
    ).merge(
        dims["dim_level"][["level_sk", "level_name"]], on="level_sk"
    ).merge(
        dims["dim_content"][["content_sk", "content_name"]], on="content_sk"
    )

    mask = fact_check.apply(
        lambda r: (r["branch_name"], r["level_name"], r["content_name"]) in VALID_CURRICULUM,
        axis=1,
    )
    fact = fact_check[mask][
        ["content_sk", "level_sk", "branch_sk", "semester_sk", "avg_grade", "success_rate", "nb_students"]
    ].copy()

    logger.info(f"Curriculum guard: dropped {len(fact_check) - len(fact)} invalid rows, kept {len(fact)}")
    return fact
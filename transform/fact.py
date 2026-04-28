import pandas as pd
from transform.derive import derive_level, derive_branch
from transform.normalize import normalize_semester
from transform.clean import clean_grades
from loguru import logger


def enrich_data(df_gridline, df_grid, df_studyplan, df_schoolyearperiod, dim_year):
    df = clean_grades(df_gridline)
    logger.info(f"After cleaning grades: {len(df)} rows")

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
    return fact


# ===================================================================
# Student Attendance Fact (absence-only model)
# ===================================================================
def build_attendance_fact(df_journal: pd.DataFrame,
                          dim_student: pd.DataFrame,
                          dim_day: pd.DataFrame,
                          dim_weather: pd.DataFrame) -> pd.DataFrame:

    logger.info("Building absence-only attendance fact...")

    # 1. Normalize dates
    df = df_journal.copy()
    df["session_date"] = pd.to_datetime(df["session_start"], errors="coerce").dt.normalize()

    dim_day = dim_day.copy()
    dim_day["day_natural_key"] = pd.to_datetime(dim_day["day_natural_key"], errors="coerce").dt.normalize()

    # 2. Journal coverage
    journal_min = df["session_date"].min()
    journal_max = df["session_date"].max()
    logger.info(f"Journal coverage: {journal_min.date()} → {journal_max.date()}")

    # 3. Student filtering
    journal_students = set(df["student_natural_key"].unique())
    dim_students_keys = set(dim_student["student_natural_key"].unique())

    matched = journal_students & dim_students_keys
    unmatched = journal_students - dim_students_keys

    logger.info(f"Journal unique students: {len(journal_students)}")
    logger.info(f"Dim_student unique keys: {len(dim_students_keys)}")
    logger.info(f"Matched: {len(matched)}")
    logger.info(f"Unmatched: {len(unmatched)}")

    if unmatched:
        logger.warning(f"Sample unmatched keys: {list(unmatched)[:5]}")

    dim_student_filtered = dim_student[
        dim_student["student_natural_key"].isin(matched)
    ].copy()

    logger.info(f"Students kept for fact: {len(dim_student_filtered)}")

    # 4. School days within journal range
    school_days = dim_day[
        (dim_day["is_school_day"] == 1) &
        (dim_day["day_natural_key"] >= journal_min) &
        (dim_day["day_natural_key"] <= journal_max)
    ][["day_sk", "day_natural_key"]].copy()

    logger.info(f"School days in journal range: {len(school_days)}")

    school_day_dates = set(school_days["day_natural_key"])
    df_school = df[df["session_date"].isin(school_day_dates)]

    if len(df_school) == 0:
        logger.error("ZERO journal records fall within school days!")
        raise ValueError("No journal records on school days.")

    # 5. Aggregate actual attendance (count records per student-day)
    actual = df_school.groupby(["student_natural_key", "session_date"]).size().reset_index(name="nb_records")
    actual["session_date"] = pd.to_datetime(actual["session_date"]).dt.normalize()

    logger.info(f"Actual aggregated records: {len(actual)}")

    # 6. Expected grid (students × days)
    expected = school_days.merge(
        dim_student_filtered[["student_sk", "student_natural_key"]],
        how="cross"
    )
    expected["day_natural_key"] = pd.to_datetime(expected["day_natural_key"]).dt.normalize()

    logger.info(f"Expected grid size: {len(school_days)} days × {len(dim_student_filtered)} students = {len(expected)}")

    # 7. Merge (expected LEFT JOIN actual)
    fact = expected.merge(
        actual,
        left_on=["student_natural_key", "day_natural_key"],
        right_on=["student_natural_key", "session_date"],
        how="left"
    )

    logger.info(f"After left join rows: {len(fact)}")

    # 8. Identify absences (nb_records == 0)
    fact["nb_records"] = fact["nb_records"].fillna(0).astype(int)
    
    present_count = (fact["nb_records"] > 0).sum()
    absence_count = (fact["nb_records"] == 0).sum()
    logger.info(f"Rows with records (present): {present_count}")
    logger.info(f"Rows with no records (absent): {absence_count}")

    # Keep only absences
    fact = fact[fact["nb_records"] == 0].copy()
    fact["nb_absence"] = 1

    if fact.empty:
        logger.warning("No absences found!")
        return pd.DataFrame(columns=["day_sk", "weather_sk", "student_sk", "nb_absence"])

    # 9. Weather join
    weather_map = dim_weather[["weather_date", "weather_sk"]].copy()

    fact["day_natural_key"] = pd.to_datetime(fact["day_natural_key"]).dt.normalize()
    weather_map["weather_date"] = pd.to_datetime(weather_map["weather_date"]).dt.normalize()

    fact = fact.merge(
        weather_map,
        left_on="day_natural_key",
        right_on="weather_date",
        how="left"
    )

    fallback = dim_weather[dim_weather["weather_condition"] == "Inconnu"]
    fallback_sk = int(fallback.iloc[0]["weather_sk"]) if not fallback.empty else 1

    fact["weather_sk"] = fact["weather_sk"].fillna(fallback_sk).astype(int)

    # 10. Final clean
    fact = fact[["day_sk", "weather_sk", "student_sk", "nb_absence"]].copy()

    logger.info(f"Final absence fact: {len(fact)} rows")

    return fact
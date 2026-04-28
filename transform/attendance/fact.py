import pandas as pd
from loguru import logger
from ..clean import clean_dates


def build_attendance_fact(df_journal: pd.DataFrame,
                          dim_student: pd.DataFrame,
                          dim_day: pd.DataFrame,
                          dim_weather: pd.DataFrame) -> pd.DataFrame:

    logger.info("Building absence-only attendance fact...")

    # Step 1: Clean dates (explicit preprocessing)
    df = clean_dates(df_journal.copy(), ["session_start"])
    df = df.rename(columns={"session_start": "session_date"})

    dim_day_clean = clean_dates(dim_day.copy(), ["day_natural_key"])

    # Step 2: Journal coverage analysis
    journal_min = df["session_date"].min()
    journal_max = df["session_date"].max()
    logger.info(f"Journal coverage: {journal_min.date()} → {journal_max.date()}")

    # Step 3: Student filtering
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

    # Step 4: School days within journal range
    school_days = dim_day_clean[
        (dim_day_clean["is_school_day"] == 1) &
        (dim_day_clean["day_natural_key"] >= journal_min) &
        (dim_day_clean["day_natural_key"] <= journal_max)
    ][["day_sk", "day_natural_key"]].copy()

    logger.info(f"School days in journal range: {len(school_days)}")

    school_day_dates = set(school_days["day_natural_key"])
    df_school = df[df["session_date"].isin(school_day_dates)]

    if len(df_school) == 0:
        logger.error("ZERO journal records fall within school days!")
        raise ValueError("No journal records on school days.")

    # Step 5: Aggregate actual attendance
    actual = df_school.groupby(["student_natural_key", "session_date"]).size().reset_index(name="nb_records")
    actual = clean_dates(actual, ["session_date"])

    logger.info(f"Actual aggregated records: {len(actual)}")

    # Step 6: Expected grid (students × days)
    expected = school_days.merge(
        dim_student_filtered[["student_sk", "student_natural_key"]],
        how="cross"
    )
    expected = clean_dates(expected, ["day_natural_key"])

    logger.info(f"Expected grid size: {len(school_days)} days × {len(dim_student_filtered)} students = {len(expected)}")

    # Step 7: Merge (expected LEFT JOIN actual)
    fact = expected.merge(
        actual,
        left_on=["student_natural_key", "day_natural_key"],
        right_on=["student_natural_key", "session_date"],
        how="left"
    )

    logger.info(f"After left join rows: {len(fact)}")

    # Step 8: Identify absences
    fact["nb_records"] = fact["nb_records"].fillna(0).astype(int)
    
    present_count = (fact["nb_records"] > 0).sum()
    absence_count = (fact["nb_records"] == 0).sum()
    logger.info(f"Rows with records (present): {present_count}")
    logger.info(f"Rows with no records (absent): {absence_count}")

    fact = fact[fact["nb_records"] == 0].copy()
    fact["nb_absence"] = 1

    if fact.empty:
        logger.warning("No absences found!")
        return pd.DataFrame(columns=["day_sk", "weather_sk", "student_sk", "nb_absence"])

    # Step 9: Weather join
    weather_map = clean_dates(dim_weather[["weather_date", "weather_sk"]].copy(), ["weather_date"])
    fact = clean_dates(fact, ["day_natural_key"])

    fact = fact.merge(
        weather_map,
        left_on="day_natural_key",
        right_on="weather_date",
        how="left"
    )

    fallback = dim_weather[dim_weather["weather_condition"] == "Inconnu"]
    fallback_sk = int(fallback.iloc[0]["weather_sk"]) if not fallback.empty else 1
    fact["weather_sk"] = fact["weather_sk"].fillna(fallback_sk).astype(int)

    # Step 10: Final clean
    fact = fact[["day_sk", "weather_sk", "student_sk", "nb_absence"]].copy()
    logger.info(f"Final absence fact: {len(fact)} rows")

    return fact
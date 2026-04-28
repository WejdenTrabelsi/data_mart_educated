import pandas as pd
from datetime import date, timedelta
from .normalize import normalize_semester
from .derive import derive_level, derive_branch
from loguru import logger


def build_dim_year(df_schoolyear: pd.DataFrame) -> pd.DataFrame:
    df = df_schoolyear[['Oid', 'Description']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'year_natural_key', 'Description': 'year_name'})
    df['year_sk'] = range(1, len(df) + 1)
    return df[['year_sk', 'year_natural_key', 'year_name']]


def build_dim_semester(df_schoolyearperiod: pd.DataFrame, dim_year: pd.DataFrame) -> pd.DataFrame:
    df = df_schoolyearperiod[['Oid', 'Name', 'CurrentSchoolYear']].drop_duplicates().copy()
    df = df.rename(columns={'Oid': 'semester_natural_key', 'Name': 'semester_raw'})
    df['semester_code'] = df['semester_raw'].apply(normalize_semester)
    df = df.merge(dim_year[['year_natural_key', 'year_sk']],
                  left_on='CurrentSchoolYear', right_on='year_natural_key', how='left')
    df = df.dropna(subset=['year_sk', 'semester_code'])
    df = df[df['semester_code'] != 'Unknown']
    df = df.drop_duplicates(subset=['year_sk', 'semester_code'])
    df = df.sort_values(['year_sk', 'semester_code']).reset_index(drop=True)
    df['semester_sk'] = range(1, len(df) + 1)
    return df[['semester_sk', 'semester_code', 'year_sk']]


def build_dim_level(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['SchoolLevel', 'Description']].drop_duplicates().copy()
    df = df.dropna(subset=['Description'])
    df['level_name'] = df['Description'].apply(derive_level)
    level_map = df.groupby('level_name').agg({
        'SchoolLevel': 'first',
        'Description': 'first'
    }).reset_index()
    level_map = level_map[level_map['level_name'] != "Unknown"]
    level_map = level_map.sort_values('level_name').reset_index(drop=True)
    level_map['level_sk'] = range(1, len(level_map) + 1)
    level_map['level_natural_key'] = level_map['SchoolLevel']
    logger.info(f"FINAL CLEAN LEVEL DIMENSION:\n{level_map[['level_sk', 'level_name', 'Description']].to_string()}")
    logger.info(f"Total clean levels: {len(level_map)}")
    return level_map[['level_sk', 'level_natural_key', 'level_name']]


def build_dim_branch(df_studyplan: pd.DataFrame) -> pd.DataFrame:
    df = df_studyplan[['Description']].drop_duplicates().copy()
    df = df.dropna(subset=['Description'])
    df['branch_name'] = df['Description'].apply(derive_branch)
    df = df[df['branch_name'] != "Unknown"]
    df = df.drop_duplicates(subset=['branch_name'])
    df = df.sort_values('branch_name')
    df['branch_sk'] = range(1, len(df) + 1)
    return df[['branch_sk', 'branch_name']]


def build_dim_content(df_grid: pd.DataFrame, df_content: pd.DataFrame) -> pd.DataFrame:
    df = df_grid[['Content']].drop_duplicates().copy()
    df = df.rename(columns={'Content': 'content_natural_key'})
    df = df.merge(
        df_content[['Oid', 'Description', 'Description2']],
        left_on='content_natural_key',
        right_on='Oid',
        how='left'
    )
    df['content_name'] = df['Description2'].fillna(df['Description'])
    df['content_name'] = df['content_name'].astype(str).str.strip()
    mask_bad = (df['content_name'].str.len() < 3) | (df['content_name'] == 'nan')
    df.loc[mask_bad, 'content_name'] = df.loc[mask_bad, 'content_natural_key'].astype(str)
    df['content_name'] = df['content_name'].replace('nan', 'Unknown Subject')
    df = df.drop(columns=['Oid', 'Description', 'Description2'])
    df['content_sk'] = range(1, len(df) + 1)
    return df[['content_sk', 'content_natural_key', 'content_name']]


def build_all_dimensions(df_grid, df_gridline, df_studyplan, df_schoolyear, df_schoolyearperiod, df_content):
    dim_year = build_dim_year(df_schoolyear)
    dim_semester = build_dim_semester(df_schoolyearperiod, dim_year)
    dim_level = build_dim_level(df_studyplan)
    dim_branch = build_dim_branch(df_studyplan)
    dim_content = build_dim_content(df_grid, df_content)
    logger.info(f"Dimensions built: Year={len(dim_year)}, Semester={len(dim_semester)}, "
                f"Level={len(dim_level)}, Branch={len(dim_branch)}, Content={len(dim_content)}")
    return {
        'dim_year': dim_year,
        'dim_semester': dim_semester,
        'dim_level': dim_level,
        'dim_branch': dim_branch,
        'dim_content': dim_content
    }


# =========================================================
# CALENDAR 2020-2021
# =========================================================
SCHOOL_START = date(2020, 9, 15)
SCHOOL_END   = date(2021, 6, 30)

HOLIDAY_PERIODS = [
    (date(2020, 10, 15), date(2020, 10, 15), "Fête de l'Évacuation"),
    (date(2020, 10, 28), date(2020, 10, 28), "Al Mawlid (Anniversaire du Prophète)"),
    (date(2020, 12, 21), date(2021, 1, 3),   "Vacances hiver / Nouvel An"),
    (date(2021, 1, 1),   date(2021, 1, 1),   "Jour de l'An"),
    (date(2021, 1, 14),  date(2021, 1, 14),  "Fête de la Révolution et de la Jeunesse"),
    (date(2021, 2, 1),   date(2021, 2, 7),   "Vacances mi-trimestre 2"),
    (date(2021, 3, 15),  date(2021, 3, 28),  "Vacances printemps"),
    (date(2021, 3, 20),  date(2021, 3, 20),  "Fête de l'Indépendance"),
    (date(2021, 4, 9),   date(2021, 4, 9),   "Journée des Martyrs"),
    (date(2021, 5, 1),   date(2021, 5, 1),   "Fête du Travail"),
    (date(2021, 5, 13),  date(2021, 5, 14),  "Aïd el-Fitr"),
    (date(2021, 6, 25),  date(2021, 6, 30),  "Fin année / Aïd el-Kébir approx"),
]

DAY_NAMES_FR = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche"
}

MONTH_NAMES_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}


def _month_to_semester_code(month: int) -> str:
    if month in [9, 10, 11, 12]:
        return "S1"
    elif month in [1, 2, 3]:
        return "S2"
    else:
        return "S3"


def _build_holiday_set() -> dict:
    holidays = {}
    for s, e, name in HOLIDAY_PERIODS:
        cd = pd.Timestamp(s)
        e_ts = pd.Timestamp(e)
        while cd <= e_ts:
            holidays[cd] = name
            cd += timedelta(days=1)
    return holidays


def build_dim_zone(df_zones: pd.DataFrame) -> pd.DataFrame:
    df = df_zones.copy()
    df = df.dropna(subset=["zone_natural_key"])
    df = df[df["zone_natural_key"].astype(str).str.strip() != ""]

    df["zone_description"] = (
        df["zone_description"]
        .fillna("No description")
        .astype(str)
        .str.strip()
        .str.title()
    )
    df.loc[df["zone_description"] == "", "zone_description"] = "No description"

    unique_zones = (
        df[["zone_description"]]
        .drop_duplicates()
        .sort_values("zone_description")
        .reset_index(drop=True)
    )
    unique_zones["zone_sk"] = range(2, len(unique_zones) + 2)

    unknown = pd.DataFrame([{
        "zone_sk": 1,
        "zone_description": "Unknown Zone"
    }])
    unique_zones = pd.concat([unknown, unique_zones], ignore_index=True)

    uuid_repr = (
        df.sort_values("zone_natural_key")
          .drop_duplicates(subset=["zone_description"])[["zone_description", "zone_natural_key"]]
    )
    unique_zones = unique_zones.merge(uuid_repr, on="zone_description", how="left")
    unique_zones.loc[unique_zones["zone_description"] == "Unknown Zone", "zone_natural_key"] = "UNKNOWN"

    return unique_zones[["zone_sk", "zone_natural_key", "zone_description"]]


def build_dim_student(df_students: pd.DataFrame, dim_zone: pd.DataFrame, df_zones_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_students.copy()

    raw = df_zones_raw.copy()
    raw = raw.dropna(subset=["zone_natural_key"])
    raw["zone_natural_key"] = raw["zone_natural_key"].astype(str).str.strip()
    raw["zone_description"] = (
        raw["zone_description"]
        .fillna("No description")
        .astype(str)
        .str.strip()
        .str.title()
    )
    uuid_to_desc = dict(zip(raw["zone_natural_key"], raw["zone_description"]))

    desc_to_sk = dict(zip(dim_zone["zone_description"], dim_zone["zone_sk"]))
    unknown_sk = int(dim_zone.loc[dim_zone["zone_description"] == "Unknown Zone", "zone_sk"].iloc[0])

    df["zone_natural_key"] = df["zone_natural_key"].fillna("").astype(str).str.strip()
    df["zone_description"] = df["zone_natural_key"].map(uuid_to_desc).fillna("Unknown Zone").str.title()
    df["zone_sk"] = df["zone_description"].map(desc_to_sk).fillna(unknown_sk).astype(int)

    df["full_name_arab"] = df["full_name_arab"].fillna("Unknown").astype(str).str.strip()
    df.loc[df["full_name_arab"] == "", "full_name_arab"] = "Unknown"

    df["student_sk"] = range(1, len(df) + 1)
    df = df.rename(columns={"full_name_arab": "student_full_name_arab"})

    assert df["zone_sk"].isna().sum() == 0, "zone_sk still has NULLs!"

    return df[["student_sk", "student_natural_key", "zone_sk", "student_full_name_arab"]]


def build_dim_weather(raw_weather: pd.DataFrame) -> pd.DataFrame:
    if raw_weather.empty:
        return pd.DataFrame({
            "weather_sk": [1],
            "weather_date": [pd.NaT],
            "weather_condition": ["Inconnu"],
            "temp_avg_c": [0.0],
            "precipitation": [0.0],
            "rain_flag": [0],
            "temp_band": ["Unknown"],
            "weather_description": ["API indisponible"]
        })

    df = raw_weather.copy()

    df["weather_date"] = pd.to_datetime(df["weather_date"], errors="coerce").dt.normalize()

    for col in ["temp_avg_f", "precipitation"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["temp_avg_c"] = ((df["temp_avg_f"] - 32) * 5 / 9).round(2)
    df["precipitation"] = df["precipitation"].fillna(0.0)
    df["rain_flag"] = (df["precipitation"] > 0).astype(int)
    df["temp_band"] = df["temp_avg_c"].apply(
        lambda t: "Cold" if t < 10 else "Hot" if t > 27 else "Mild"
    )
    df["weather_condition"] = df["weather_condition"].fillna("Unknown").astype(str)
    df["weather_description"] = df["weather_description"].fillna("").astype(str)

    df = df.drop_duplicates(subset=["weather_date"]).reset_index(drop=True)
    df["weather_sk"] = range(1, len(df) + 1)

    return df[[
        "weather_sk",
        "weather_date",
        "weather_condition",
        "temp_avg_c",
        "precipitation",
        "rain_flag",
        "temp_band",
        "weather_description"
    ]]


def build_dim_month(dim_semester: pd.DataFrame) -> pd.DataFrame:
    rows = []
    month_sk = 1
    for month_num in [9, 10, 11, 12, 1, 2, 3, 4, 5, 6]:
        sem_code = _month_to_semester_code(month_num)
        sem_row = dim_semester[dim_semester["semester_code"] == sem_code]
        if sem_row.empty:
            raise ValueError(f"Semestre {sem_code} introuvable dans DimSemester existante")
        semester_sk = int(sem_row.iloc[0]["semester_sk"])
        rows.append({
            "month_sk": month_sk,
            "month_number": month_num,
            "month_name": MONTH_NAMES_FR[month_num],
            "semester_sk": semester_sk
        })
        month_sk += 1
    return pd.DataFrame(rows)


def build_dim_week(dim_month: pd.DataFrame) -> pd.DataFrame:
    first_monday = SCHOOL_START
    while first_monday.weekday() != 0:
        first_monday -= timedelta(days=1)

    weeks = []
    week_sk = 1
    current_monday = first_monday

    while current_monday <= SCHOOL_END:
        week_days = []
        for i in range(7):
            d = current_monday + timedelta(days=i)
            if SCHOOL_START <= d <= SCHOOL_END:
                week_days.append(d)

        if not week_days:
            break

        month_counts = {}
        for d in week_days:
            month_counts[d.month] = month_counts.get(d.month, 0) + 1
        assigned_month = max(month_counts, key=month_counts.get)

        month_row = dim_month[dim_month["month_number"] == assigned_month]
        month_sk = int(month_row.iloc[0]["month_sk"])

        weeks.append({
            "week_sk": week_sk,
            "week_code": f"2020-2021-W{week_sk:02d}",
            "week_number": week_sk,
            "month_sk": month_sk
        })

        week_sk += 1
        current_monday += timedelta(days=7)

    return pd.DataFrame(weeks)


def build_dim_day(dim_week: pd.DataFrame) -> pd.DataFrame:
    holidays = _build_holiday_set()
    week_map = {int(r["week_number"]): int(r["week_sk"]) for _, r in dim_week.iterrows()}

    first_monday = SCHOOL_START
    while first_monday.weekday() != 0:
        first_monday -= timedelta(days=1)

    days = []
    day_sk = 1
    d = pd.Timestamp(SCHOOL_START)

    while d.date() <= SCHOOL_END:
        is_sunday = d.weekday() == 6
        is_holiday = d in holidays
        is_school = not is_sunday and not is_holiday

        days_since_start = (d - pd.Timestamp(first_monday)).days
        week_num = days_since_start // 7 + 1
        week_sk = week_map.get(week_num, -1)

        days.append({
            "day_sk": day_sk,
            "day_natural_key": d.normalize(),
            "day_name": DAY_NAMES_FR[d.weekday()],
            "day_number": d.weekday() + 1,
            "week_sk": week_sk,
            "is_school_day": 1 if is_school else 0,
            "is_holiday": 1 if (is_holiday or is_sunday) else 0,
            "holiday_name": holidays.get(d, "Dimanche" if is_sunday else "")
        })

        day_sk += 1
        d += timedelta(days=1)

    df = pd.DataFrame(days)
    df["week_sk"] = df["week_sk"].astype(int)
    df["is_school_day"] = df["is_school_day"].astype(int)
    df["is_holiday"] = df["is_holiday"].astype(int)

    return df


def build_all_attendance_dimensions(df_zones, df_students, raw_weather, dim_year, dim_semester):
    dim_zone = build_dim_zone(df_zones)
    dim_student = build_dim_student(df_students, dim_zone, df_zones)
    dim_weather = build_dim_weather(raw_weather)
    dim_month = build_dim_month(dim_semester)
    dim_week = build_dim_week(dim_month)
    dim_day = build_dim_day(dim_week)

    logger.info(f"Attendance dims built: Zone={len(dim_zone)}, Student={len(dim_student)}, "
                f"Weather={len(dim_weather)}, Month={len(dim_month)}, "
                f"Week={len(dim_week)}, Day={len(dim_day)}")

    return {
        'dim_zone': dim_zone,
        'dim_student': dim_student,
        'dim_weather': dim_weather,
        'dim_month': dim_month,
        'dim_week': dim_week,
        'dim_day': dim_day,
    }
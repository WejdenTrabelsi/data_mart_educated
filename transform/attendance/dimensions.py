import pandas as pd
from datetime import date, timedelta
from loguru import logger
from ..clean import clean_strings, clean_dates, fill_na_defaults
from ..normalize import normalize_zone_description
from ..derive import derive_weather_flags


from ..calendar import SCHOOL_START, SCHOOL_END

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
    
    # Clean: strip whitespace, drop empty keys (preserve original case for UUIDs)
    df["zone_natural_key"] = df["zone_natural_key"].astype(str).str.strip()
    df["zone_description"] = df["zone_description"].astype(str).str.strip()
    
    df = df[df["zone_natural_key"] != ""]
    df = df.dropna(subset=["zone_natural_key"])
    
    # Normalize description only (not the key)
    df = fill_na_defaults(df, {"zone_description": "No description"})
    df["zone_description"] = df["zone_description"].apply(normalize_zone_description)
    
    # Build dimension
    unique_zones = (
        df[["zone_description"]]
        .drop_duplicates()
        .sort_values("zone_description")
        .reset_index(drop=True)
    )
    unique_zones["zone_sk"] = range(2, len(unique_zones) + 2)

    unknown = pd.DataFrame([{"zone_sk": 1, "zone_description": "Unknown Zone"}])
    unique_zones = pd.concat([unknown, unique_zones], ignore_index=True)

    # Map back to natural keys (take first UUID per description)
    uuid_repr = (
        df.sort_values("zone_natural_key")
          .drop_duplicates(subset=["zone_description"])[["zone_description", "zone_natural_key"]]
    )
    unique_zones = unique_zones.merge(uuid_repr, on="zone_description", how="left")
    unique_zones.loc[unique_zones["zone_description"] == "Unknown Zone", "zone_natural_key"] = "UNKNOWN"

    return unique_zones[["zone_sk", "zone_natural_key", "zone_description"]]


def build_dim_student(df_students: pd.DataFrame, dim_zone: pd.DataFrame, df_zones_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_students.copy()
    
    # Clean: strip only, preserve case for UUID keys
    df["zone_natural_key"] = df["zone_natural_key"].astype(str).str.strip()
    df["full_name_arab"] = df["full_name_arab"].astype(str).str.strip()
    df = fill_na_defaults(df, {"full_name_arab": "Unknown", "zone_natural_key": ""})
    
    # Clean raw zones for mapping (strip only, preserve case)
    raw = df_zones_raw.copy()
    raw["zone_natural_key"] = raw["zone_natural_key"].astype(str).str.strip()
    raw["zone_description"] = raw["zone_description"].astype(str).str.strip().str.title()
    raw = fill_na_defaults(raw, {"zone_description": "No description"})
    uuid_to_desc = dict(zip(raw["zone_natural_key"], raw["zone_description"]))

    # Derive zone_sk
    desc_to_sk = dict(zip(dim_zone["zone_description"], dim_zone["zone_sk"]))
    unknown_sk = int(dim_zone.loc[dim_zone["zone_description"] == "Unknown Zone", "zone_sk"].iloc[0])

    df["zone_description"] = df["zone_natural_key"].map(uuid_to_desc).fillna("Unknown Zone")
    df["zone_sk"] = df["zone_description"].map(desc_to_sk).fillna(unknown_sk).astype(int)
    
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

    # Step 1: Clean dates (explicit preprocessing)
    df = clean_dates(raw_weather, ["weather_date"]).copy()

    # Step 2: Clean numeric columns
    for col in ["temp_avg_f", "precipitation"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Step 3: Derive weather flags (explicit transformation)
    df["temp_avg_c"] = ((df["temp_avg_f"] - 32) * 5 / 9).round(2)
    df["precipitation"] = df["precipitation"].fillna(0.0)
    
    flags = df.apply(lambda row: derive_weather_flags(row["temp_avg_c"], row["precipitation"]), axis=1)
    df["rain_flag"] = flags.apply(lambda x: x[0])
    df["temp_band"] = flags.apply(lambda x: x[1])
    
    df["weather_condition"] = df["weather_condition"].fillna("Unknown").astype(str)
    df["weather_description"] = df["weather_description"].fillna("").astype(str)

    df = df.drop_duplicates(subset=["weather_date"]).reset_index(drop=True)
    df["weather_sk"] = range(1, len(df) + 1)

    return df[[
        "weather_sk", "weather_date", "weather_condition",
        "temp_avg_c", "precipitation", "rain_flag",
        "temp_band", "weather_description"
    ]]


def build_dim_month(dim_semester: pd.DataFrame) -> pd.DataFrame:
    rows = []
    month_sk = 1
    for month_num in [9, 10, 11, 12, 1, 2, 3, 4, 5, 6]:
        sem_code = _month_to_semester_code(month_num)
        sem_row = dim_semester[dim_semester["semester_code"] == sem_code]
        if sem_row.empty:
            raise ValueError(f"Semestre {sem_code} introuvable dans DimSemester")
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
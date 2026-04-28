import json
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from loguru import logger

# Same location as before — data/ is at project root
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "weather_cache.json"


def load_weather(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Load weather from static JSON cache.
    Falls back to mock data for any dates not in cache.
    """
    if not CACHE_FILE.exists():
        logger.warning(f"Weather cache not found at {CACHE_FILE}, generating mock data")
        return _generate_mock_weather(start_date, end_date)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        logger.warning("Weather cache is empty, generating mock data")
        return _generate_mock_weather(start_date, end_date)

    df = pd.DataFrame(data)
    df["weather_date"] = pd.to_datetime(df["weather_date"]).dt.date

    # Filter to requested range
    df = df[(df["weather_date"] >= start_date) & (df["weather_date"] <= end_date)].copy()

    if df.empty:
        logger.warning(f"No weather data for {start_date} → {end_date}, generating mock")
        return _generate_mock_weather(start_date, end_date)

    logger.info(f"Weather loaded from cache: {len(df)} days ({start_date} → {end_date})")
    return df.reset_index(drop=True)


def _generate_mock_weather(start_date: date, end_date: date) -> pd.DataFrame:
    """Minimal mock generator for gaps."""
    import numpy as np
    records = []
    d = start_date
    np.random.seed(42)
    while d <= end_date:
        month = d.month
        base_temp = 77 if month in [9, 10] else 60
        temp_avg = base_temp + np.random.normal(0, 3)
        records.append({
            "weather_date": d,
            "weather_condition": "Clear",
            "temp_max_f": round(temp_avg + 5, 1),
            "temp_min_f": round(temp_avg - 5, 1),
            "temp_avg_f": round(temp_avg, 1),
            "precipitation": 0.0,
            "weather_description": "Clear conditions throughout the day."
        })
        d += timedelta(days=1)
    logger.warning(f"Mock weather generated: {len(records)} days")
    return pd.DataFrame(records)
import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from loguru import logger


CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "weather_cache.json"


def _load_cache() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        return pd.DataFrame()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df["weather_date"] = pd.to_datetime(df["weather_date"]).dt.date
        logger.info(f"Weather loaded from cache: {len(df)} days")
        return df
    except Exception:
        return pd.DataFrame()


def _save_cache(df: pd.DataFrame):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = df.copy()
    records["weather_date"] = records["weather_date"].astype(str)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(records.to_dict("records"), f, indent=2)
    logger.info(f"Weather cached to {CACHE_FILE}")


def _generate_mock_weather(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Génère des données météo réalistes pour Sousse, Tunisie.
    Saison chaude : mai-sept (25-35°C), fraîche : nov-fév (12-20°C)
    """
    logger.warning("Generating mock weather data for Sousse (API unavailable)")
    
    records = []
    d = start_date
    np.random.seed(42)  # reproductible
    
    while d <= end_date:
        month = d.month
        
        # Températures de base selon le mois (Fahrenheit)
        if month in [12, 1, 2]:
            base_temp = 60  # ~15-16°C
            temp_range = 10
            rain_prob = 0.25
        elif month in [3, 4, 11]:
            base_temp = 68  # ~20°C
            temp_range = 12
            rain_prob = 0.15
        elif month in [5, 6, 9, 10]:
            base_temp = 77  # ~25°C
            temp_range = 10
            rain_prob = 0.08
        else:  # juillet, août
            base_temp = 86  # ~30°C
            temp_range = 8
            rain_prob = 0.02
        
        temp_avg = base_temp + np.random.normal(0, 3)
        temp_max = temp_avg + abs(np.random.normal(5, 2))
        temp_min = temp_avg - abs(np.random.normal(5, 2))
        precip = np.random.exponential(0.1) if np.random.random() < rain_prob else 0
        
        # Conditions textuelles
        if precip > 0.2:
            condition = "Rain, Partially cloudy"
            desc = "Partly cloudy throughout the day with rain."
        elif precip > 0:
            condition = "Partially cloudy"
            desc = "Partly cloudy throughout the day."
        else:
            condition = "Clear"
            desc = "Clear conditions throughout the day."
        
        records.append({
            "weather_date": d,
            "weather_condition": condition,
            "temp_max_f": round(temp_max, 1),
            "temp_min_f": round(temp_min, 1),
            "temp_avg_f": round(temp_avg, 1),
            "precipitation": round(precip, 2),
            "weather_description": desc
        })
        d += timedelta(days=1)
    
    df = pd.DataFrame(records)
    _save_cache(df)
    logger.success(f"Mock weather generated: {len(df)} days")
    return df


def extract_weather(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Extraction météo avec cache + fallback mock data.
    """
    # 1. Vérifier cache
    cached = _load_cache()
    if not cached.empty:
        cached_min = cached["weather_date"].min()
        cached_max = cached["weather_date"].max()
        if cached_min <= start_date and cached_max >= end_date:
            logger.info("Using cached weather data")
            return cached

    # 2. Essayer API
    api_key = os.getenv("WEATHER_API_KEY", "AGG4FZH9RJWAH49J22WZBW6WQ")
    location = "tunisia Sousse"
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{location}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        f"?unitGroup=us&key={api_key}&contentType=json"
    )

    try:
        logger.info(f"Fetching weather {start_date} → {end_date} ...")
        resp = requests.get(url, timeout=90)
        resp.raise_for_status()
        data = resp.json()

        days = data.get("days", [])
        if not days:
            raise ValueError("Empty weather response")

        records = []
        for d in days:
            records.append({
                "weather_date": d.get("datetime"),
                "weather_condition": d.get("conditions", "Unknown"),
                "temp_max_f": d.get("tempmax"),
                "temp_min_f": d.get("tempmin"),
                "temp_avg_f": d.get("temp"),
                "precipitation": d.get("precip", 0) or 0,
                "weather_description": d.get("description", "")
            })

        df = pd.DataFrame(records)
        df["weather_date"] = pd.to_datetime(df["weather_date"]).dt.date
        _save_cache(df)
        logger.success(f"Weather API success: {len(df)} days")
        return df

    except Exception as e:
        logger.error(f"Weather API failed: {e}")
        if not cached.empty:
            logger.warning("Using partial cached weather data")
            return cached
        return _generate_mock_weather(start_date, end_date)
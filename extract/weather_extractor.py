import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from loguru import logger

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "weather_cache.json"

# ─── Cache helpers (unchanged) ─────────────────────────────────
def _load_cache() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        return pd.DataFrame()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()
        df["weather_date"] = pd.to_datetime(df["weather_date"]).dt.date
        logger.info(f"Weather loaded from cache: {len(df)} days")
        return df
    except Exception:
        logger.warning("Cache corrupted, starting fresh")
        return pd.DataFrame()

def _save_cache(df: pd.DataFrame):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = df.copy()
    records["weather_date"] = records["weather_date"].astype(str)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(records.to_dict("records"), f, indent=2)
    logger.info(f"Weather cached: {len(df)} days → {CACHE_FILE}")

# ─── Mock fallback (unchanged) ─────────────────────────────────
def _generate_mock_weather(start_date: date, end_date: date) -> pd.DataFrame:
    logger.warning("Generating mock weather data for Sousse (API unavailable)")
    records = []
    d = start_date
    np.random.seed(42)
    while d <= end_date:
        month = d.month
        if month in [12, 1, 2]:
            base_temp = 60; rain_prob = 0.25
        elif month in [3, 4, 11]:
            base_temp = 68; rain_prob = 0.15
        elif month in [5, 6, 9, 10]:
            base_temp = 77; rain_prob = 0.08
        else:
            base_temp = 86; rain_prob = 0.02
        
        temp_avg = base_temp + np.random.normal(0, 3)
        temp_max = temp_avg + abs(np.random.normal(5, 2))
        temp_min = temp_avg - abs(np.random.normal(5, 2))
        precip = np.random.exponential(0.1) if np.random.random() < rain_prob else 0
        
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

# ─── SINGLE CHUNK FETCH (max ~25 days to stay under cost limit) ─
def _fetch_chunk(start: date, end: date, api_key: str) -> pd.DataFrame:
    """Fetch one small chunk from the API."""
    location = "Sousse,Tunisia"  # no space
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{location}/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        f"?unitGroup=us&key={api_key}&contentType=json"
    )
    
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    
    days = data.get("days", [])
    if not days:
        raise ValueError(f"Empty response for {start} → {end}")
    
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
    logger.info(f"  Fetched chunk {start} → {end}: {len(df)} days")
    return df

# ─── MAIN ENTRY POINT (chunked) ────────────────────────────────
def extract_weather(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Fetch weather with automatic chunking to respect API limits.
    Uses cache first, fills gaps with batched API calls.
    """
    api_key = os.getenv("WEATHER_API_KEY", "AGG4FZH9RJWAH49J22WZBW6WQ")
    
    # 1. Load existing cache
    cached = _load_cache()
    if not cached.empty:
        cached_min = cached["weather_date"].min()
        cached_max = cached["weather_date"].max()
        # Fast path: fully cached
        if cached_min <= start_date and cached_max >= end_date:
            logger.info("Full cache hit — no API calls needed")
            result = cached[(cached["weather_date"] >= start_date) & 
                           (cached["weather_date"] <= end_date)].copy()
            return result.reset_index(drop=True)

    # 2. Build list of dates we need
    all_dates = pd.date_range(start_date, end_date, freq="D").date
    cached_dates = set(cached["weather_date"].tolist()) if not cached.empty else set()
    missing_dates = [d for d in all_dates if d not in cached_dates]
    
    if not missing_dates:
        logger.info("All dates already in cache")
        return cached[(cached["weather_date"] >= start_date) & 
                     (cached["weather_date"] <= end_date)].copy().reset_index(drop=True)

    logger.info(f"Missing {len(missing_dates)} days, fetching in chunks...")

    # 3. Chunk missing dates into ~20-day batches (safe under the limit)
    CHUNK_SIZE = 20
    chunks = []
    current_chunk = [missing_dates[0]]
    
    for d in missing_dates[1:]:
        if (d - current_chunk[0]).days < CHUNK_SIZE:
            current_chunk.append(d)
        else:
            chunks.append((current_chunk[0], current_chunk[-1]))
            current_chunk = [d]
    if current_chunk:
        chunks.append((current_chunk[0], current_chunk[-1]))

    # 4. Fetch each chunk with retry/backoff
    new_frames = []
    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        logger.info(f"Chunk {i}/{len(chunks)}: {chunk_start} → {chunk_end}")
        try:
            # Small delay to be polite to the API
            if i > 1:
                import time
                time.sleep(1.5)
            
            df_chunk = _fetch_chunk(chunk_start, chunk_end, api_key)
            new_frames.append(df_chunk)
            
        except Exception as e:
            logger.error(f"Chunk {chunk_start}→{chunk_end} failed: {e}")
            # Don't abort — try to continue with what we have
            continue

    # 5. Merge new data into cache
    if new_frames:
        df_new = pd.concat(new_frames, ignore_index=True)
        if not cached.empty:
            combined = pd.concat([cached, df_new], ignore_index=True)
            combined = combined.drop_duplicates(subset=["weather_date"], keep="last")
        else:
            combined = df_new
        _save_cache(combined)
        cached = combined

    # 6. Return requested range (with fallback for any still-missing dates)
    result = cached[(cached["weather_date"] >= start_date) & 
                   (cached["weather_date"] <= end_date)].copy()
    
    # If we STILL have gaps after all that, fall back to mock for the gaps
    result_dates = set(result["weather_date"].tolist())
    still_missing = [d for d in all_dates if d not in result_dates]
    
    if still_missing:
        logger.warning(f"{len(still_missing)} days still missing, using mock data")
        mock = _generate_mock_weather(min(still_missing), max(still_missing))
        # Merge mock into cache too so next run is complete
        combined = pd.concat([cached, mock], ignore_index=True)
        combined = combined.drop_duplicates(subset=["weather_date"], keep="last")
        _save_cache(combined)
        result = combined[(combined["weather_date"] >= start_date) & 
                         (combined["weather_date"] <= end_date)].copy()

    return result.reset_index(drop=True)
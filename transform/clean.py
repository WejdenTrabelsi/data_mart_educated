import pandas as pd


def clean_grades(df_grid_line: pd.DataFrame) -> pd.DataFrame:
    """Clean student grade records from ContentEvaluationGridLine."""
    df = df_grid_line.copy()
    
    # Handle French decimal comma (15,25 → 15.25)
    df['Note'] = df['Note'].astype(str).str.replace(',', '.').str.strip()
    df['Note'] = pd.to_numeric(df['Note'], errors='coerce')
    
    # Remove invalid grades
    df = df.dropna(subset=['Note'])
    df = df[(df['Note'] >= 0) & (df['Note'] <= 20)]
    
    return df


def clean_strings(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Strip, lowercase, and normalize accents in string columns."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
            df[col] = df[col].str.replace('è', 'e').str.replace('é', 'e').str.replace('ê', 'e')
            df[col] = df[col].str.replace('à', 'a').str.replace('â', 'a')
    return df


def clean_dates(df: pd.DataFrame, date_columns: list[str]) -> pd.DataFrame:
    """Parse date columns to datetime, coerce errors."""
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.normalize()
    return df


def fill_na_defaults(df: pd.DataFrame, defaults: dict) -> pd.DataFrame:
    """Fill NA values with specified defaults per column."""
    df = df.copy()
    for col, default in defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)
    return df
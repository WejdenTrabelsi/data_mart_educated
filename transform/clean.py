import pandas as pd

def clean_grades(df_grid_line: pd.DataFrame) -> pd.DataFrame:
    df = df_grid_line.copy()
    
    # Handle French decimal comma (15,25 → 15.25)
    df['Note'] = df['Note'].astype(str).str.replace(',', '.').str.strip()
    df['Note'] = pd.to_numeric(df['Note'], errors='coerce')
    
    # Remove invalid grades
    df = df.dropna(subset=['Note'])
    df = df[(df['Note'] >= 0) & (df['Note'] <= 20)]
    
    return df
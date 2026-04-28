import re
import pandas as pd


def derive_level(description: str) -> str:
    """Derive academic level from study plan description."""
    if pd.isna(description):
        return "Unknown"
    
    desc = str(description).lower().strip()
    desc_clean = (desc
        .replace('è', 'e').replace('é', 'e').replace('ê', 'e')
        .replace('à', 'a').replace('â', 'a')
        .replace(' ', '').replace('-', ''))
    
    # 4ème année (bac) — check FIRST
    if re.search(r'4e?m?e?annee|4eme|4ème|4éme|bac|4math|4sc|4tech|4eco|4ème|^4-', desc_clean):
        return "4ème année (bac)"
    if re.search(r'^4', desc_clean):
        return "4ème année (bac)"
    
    # 1ère année
    if re.search(r'1e?r?e?annee|1ere|1ère|1eme|^1-|^1$', desc_clean):
        return "1ère année"
    if re.search(r'^1', desc_clean):
        return "1ère année"
    
    # 2ème année
    if re.search(r'2e?m?e?annee|2eme|2ème|2éme|2sc|2eco|2tech|2math|2gen|^2-|^2$', desc_clean):
        return "2ème année"
    if re.search(r'^2', desc_clean):
        return "2ème année"
    
    # 3ème année
    if re.search(r'3e?m?e?annee|3eme|3ème|3éme|3sc|3eco|3tech|3math|3gen|^3-|^3$', desc_clean):
        return "3ème année"
    if re.search(r'^3', desc_clean):
        return "3ème année"
    
    return "Unknown"


def derive_branch(description: str) -> str:
    """Derive academic branch from study plan description."""
    if pd.isna(description):
        return "Unknown"
    
    desc = str(description).lower().strip()
    desc_clean = (desc
        .replace('è', 'e').replace('é', 'e').replace('ê', 'e')
        .replace('à', 'a').replace('â', 'a')
        .replace(' ', '').replace('-', ''))
    
    # 1ère année is always General
    if re.search(r'^1', desc_clean):
        return "General"
    
    # Math — check before Science
    if re.search(r'math', desc_clean):
        return "Math"
    
    # Technique
    if re.search(r'tech', desc_clean):
        return "Technique"
    
    # Economy / Gestion / Services
    if re.search(r'eco|econo|gestion|service', desc_clean):
        return "Eco"
    
    # Science
    if re.search(r'sc|science|experimentale', desc_clean):
        return "Science"
    
    # Defaults for years 2/3/4
    if re.search(r'^2', desc_clean):
        return "Science"
    if re.search(r'^3', desc_clean):
        return "Science"
    if re.search(r'^4', desc_clean):
        return "Science"
    
    return "Unknown"


def derive_weather_flags(temp_avg_c: float, precipitation: float) -> tuple[int, str]:
    """Derive rain_flag and temp_band from weather metrics."""
    rain_flag = 1 if precipitation > 0 else 0
    if temp_avg_c < 10:
        temp_band = "Cold"
    elif temp_avg_c > 27:
        temp_band = "Hot"
    else:
        temp_band = "Mild"
    return rain_flag, temp_band
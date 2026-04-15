import pandas as pd
import re

def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).lower().strip().replace('é', 'e').replace('è', 'e').replace('ê', 'e')

def derive_level(description: str) -> str:
    desc = normalize_text(description)
    if re.search(r'1[èe]re?', desc):
        return "1ère année"
    elif re.search(r'2[èe]me?', desc):
        return "2ème année"
    elif re.search(r'3[èe]me?', desc):
        return "3ème année"
    elif re.search(r'4[èe]me?', desc):
        return "4ème année (bac)"
    return "Unknown"

def derive_branch(description: str, level: str = None) -> str:
    if pd.isna(description):
        return "Unknown"
    
    desc = normalize_text(description)
    lvl = normalize_text(level) if level else ""
    
    # 1ère année is ALWAYS General
    if re.search(r'1[èe]re?', desc) or "1ere" in lvl:
        return "General"
    
    # Higher years
    if re.search(r'math', desc):
        return "Math"
    elif re.search(r'science|experimentales|expérimentales|4sciences|scinces', desc):
        return "Science"
    elif re.search(r'technique|tech|scences technique', desc):
        return "Technique"
    elif re.search(r'econo|écono|gestion|services|eco', desc):
        return "Eco"
    
    return "General"  # safe fallback
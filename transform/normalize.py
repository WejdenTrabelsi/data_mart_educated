def normalize_semester(period_name: str) -> str:
    name = str(period_name).lower().strip()
    if any(x in name for x in ['1', 'tr1', 'trimestre 1']):
        return "S1"
    elif any(x in name for x in ['2', 'tr2', 'trimestre 2']):
        return "S2"
    elif any(x in name for x in ['3', 'tr3', 'trimestre 3']):
        return "S3"
    return "Unknown"
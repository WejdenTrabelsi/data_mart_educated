def normalize_semester(period_name: str) -> str:
    """Normalize semester names to S1/S2/S3 codes."""
    name = str(period_name).lower().strip()
    if any(x in name for x in ['1', 'tr1', 'trimestre 1']):
        return "S1"
    elif any(x in name for x in ['2', 'tr2', 'trimestre 2']):
        return "S2"
    elif any(x in name for x in ['3', 'tr3', 'trimestre 3']):
        return "S3"
    return "Unknown"


def normalize_zone_description(desc: str) -> str:
    """Standardize zone description text."""
    if not desc or str(desc).lower() in ['nan', 'none', '']:
        return "No description"
    return str(desc).strip().title()
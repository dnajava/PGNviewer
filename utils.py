import io
def _parse_elo(elo_str: Optional[str]) -> Optional[int]:
    if not elo_str or elo_str == "?":
        return None
    try:
        return int(elo_str)
    except ValueError:
        return None

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str or date_str == "??" or date_str == "????.??.??":
        return None
    # Yksinkertainen parseri, voi laajentaa
    try:
        return date.fromisoformat(date_str.replace(".", "-"))
    except:
        return None
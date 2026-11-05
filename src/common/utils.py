import hashlib
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

def generate_id(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()

def parse_to_iso(date_str: str) -> str:
    """
    Responsible for parsing incoming string date
    and converting into ISO format and returns as string.
    expected formats  # Handles both RFC 2822 formats
        # "Tue, 17 Mar 2026 21:39:17 +0000"
        # "Wed, 18 Mar 2026 00:04:34 GMT"
    :param date_str:
    :return: ISO formated date string
    """
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        # Fallback to current UTC time
        return datetime.now(timezone.utc).isoformat()
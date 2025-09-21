import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone


def generate_rsa_hash(data: str) -> str:
    """Generates an RSA-like hash (SHA-256) of the given data."""

    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_job_id() -> str:
    """
    Generates a string representing the current datetime in 'YYYYMMDD-HHMM' format
    and appends a UUID to it.

    Returns:
      str: A string in the format 'YYYYMMDD-HHMM-UUID'.
    """
    now_utc = datetime.now(timezone.utc)
    formatted_datetime = now_utc.strftime("%Y%m%d-%H%M")
    unique_id = str(uuid.uuid4())[:8]

    return f"{formatted_datetime}-{unique_id}"


def get_now_as_utc() -> str:
    """Returns the current date in UTC as a formatted string.

    Returns:
        str:  A string representing the current time in UTC.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

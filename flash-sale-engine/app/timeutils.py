from datetime import datetime, timezone, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)

def now_ist():
    """Current time as a naive datetime representing IST — matches how flash-sale times are entered."""
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + IST_OFFSET
    return ist_now.replace(tzinfo=None)
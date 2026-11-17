from datetime import datetime, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from soloblog import settings

# Everything time-related is stored in UTC (naive ISO strings, the same
# shape utcnow().isoformat() produces), so the SQL that
# compares scheduled_at against "now" can keep comparing plain strings.
# The site's timezone (Settings > Language and time) only matters at the edges:
# turning what the admin typed into UTC on the way in, and back into
# their own local time on the way out.

# "YYYY-MM-DDTHH:MM" - what a datetime-local input sends and expects,
# and the shape scheduled_at is kept in once it's UTC
_MINUTE = "%Y-%m-%dT%H:%M"


def utcnow() -> datetime:
    """Now, in UTC, with no time zone attached - the shape every stored
    time is in. (utcnow() did this, and is deprecated; adding the
    zone would put "+00:00" on new times and break comparing them as text.)"""
    return datetime.now(UTC).replace(tzinfo=None)


def zone_names() -> list:
    return sorted(z for z in available_timezones() if "/" in z and not z.startswith(("Etc/", "SystemV/")))


def site_zone():
    try:
        return ZoneInfo(settings.get("timezone") or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        # a zone this system's tz database doesn't have (or a name that
        # isn't one): UTC. Not logged - this runs for every date shown
        return UTC


def local_input_to_utc(value: str) -> str:
    """A datetime-local value typed in the site's timezone -> UTC."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        local = datetime.fromisoformat(value).replace(tzinfo=site_zone())
    except ValueError:
        return ""
    return local.astimezone(UTC).strftime(_MINUTE)


def utc_to_local_input(value: str) -> str:
    """A stored UTC value -> a datetime-local value in the site's timezone."""
    if not value:
        return ""
    try:
        utc = datetime.fromisoformat(value[:16]).replace(tzinfo=UTC)
    except ValueError:
        return ""
    return utc.astimezone(site_zone()).strftime(_MINUTE)


def normalize_stored(value) -> str:
    """scheduled_at as read back from a post's front matter -> naive UTC.

    New files carry an explicit "Z" ("2030-01-01T09:00Z"). Older files
    carry a bare local-looking time, which the app always compared
    against UTC, so it's read as UTC here too - an old post keeps going
    live exactly when it did before. YAML turns a value with seconds
    and an offset into a real datetime, so that's handled as well."""
    if not value:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace(" ", "T"))
        except ValueError:
            return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.strftime(_MINUTE)


def to_local(dt: datetime) -> datetime:
    """A naive UTC datetime -> the same moment in the site's timezone."""
    return dt.replace(tzinfo=UTC).astimezone(site_zone())


def local_date(value: str) -> str:
    """A stored UTC timestamp -> its date in the site's timezone, for a
    post file's date: - so an evening post isn't dated tomorrow. A value
    that's already just a date (read back from a file) stays as it is."""
    value = str(value or "")
    if len(value) <= 10:
        return value
    try:
        return to_local(datetime.fromisoformat(value[:19])).strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def day_start_utc() -> str:
    """Today's midnight in the site's timezone, as a stored (naive UTC)
    timestamp - what "today" means for words written today."""
    start = datetime.now(site_zone()).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC).replace(tzinfo=None).isoformat()

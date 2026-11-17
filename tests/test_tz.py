import yaml

from soloblog import settings
from soloblog import tz


def test_utc_is_the_default():
    assert tz.local_input_to_utc("2030-06-01T12:00") == "2030-06-01T12:00"


def test_round_trip_through_a_zone():
    settings.set_many({"timezone": "America/New_York"})
    try:
        utc = tz.local_input_to_utc("2030-06-01T12:00")   # EDT, UTC-4
        assert utc == "2030-06-01T16:00"
        assert tz.utc_to_local_input(utc) == "2030-06-01T12:00"
    finally:
        settings.set_many({"timezone": "UTC"})


def test_old_files_are_read_as_utc():
    # before the fix, a bare time was always compared against UTC
    assert tz.normalize_stored("2030-01-01T09:00") == "2030-01-01T09:00"


def test_explicit_offsets_are_converted():
    assert tz.normalize_stored("2030-01-01T09:00Z") == "2030-01-01T09:00"
    assert tz.normalize_stored("2030-01-01T09:00+10:00") == "2029-12-31T23:00"
    as_yaml = yaml.safe_load("at: 2030-01-01T09:00:00+10:00")["at"]
    assert tz.normalize_stored(as_yaml) == "2029-12-31T23:00"


def test_blank_and_garbage():
    assert tz.local_input_to_utc("") == ""
    assert tz.local_input_to_utc("not a date") == ""
    assert tz.normalize_stored(None) == ""


def test_bad_zone_falls_back_to_utc():
    settings.set_many({"timezone": "Mars/Olympus_Mons"})
    try:
        assert tz.local_input_to_utc("2030-06-01T12:00") == "2030-06-01T12:00"
    finally:
        settings.set_many({"timezone": "UTC"})


def test_file_date_is_the_sites_own_date():
    settings.set_many({"timezone": "Australia/Sydney"})
    try:
        # 9pm UTC on the 1st is already the 2nd in Sydney
        assert tz.local_date("2030-06-01T21:00:00.123456") == "2030-06-02"
        assert tz.local_date("2030-06-01") == "2030-06-01"
    finally:
        settings.set_many({"timezone": "UTC"})

from datetime import datetime, timezone, timedelta
from app.services.normalization_service import normalize_to_utc, intervals_overlap
from app.services.uncertainty_service import evaluate_timeline_ordering
from app.models.entities import TimelineEvent

def test_normalize_to_utc_with_offset():
    # 10:30:00 with +05:30 offset
    tz_aware = datetime(2026, 10, 27, 10, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    utc_dt, earliest, latest = normalize_to_utc(tz_aware, uncertainty_margin_seconds=1.0)

    # UTC time should be 05:00:00
    assert utc_dt.hour == 5
    assert utc_dt.minute == 0
    assert utc_dt.tzinfo == timezone.utc

    # Bounds [04:59:59 to 05:00:01]
    assert earliest == utc_dt - timedelta(seconds=1.0)
    assert latest == utc_dt + timedelta(seconds=1.0)

def test_intervals_overlap():
    base = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    # Event A: [09:59:59 to 10:00:01] (margin 1.0s)
    start_a = base - timedelta(seconds=1.0)
    end_a = base + timedelta(seconds=1.0)

    # Event B at 10:00:01: [10:00:00 to 10:00:02] (margin 1.0s)
    # They overlap during [10:00:00 to 10:00:01]
    time_b = base + timedelta(seconds=1.0)
    start_b = time_b - timedelta(seconds=1.0)
    end_b = time_b + timedelta(seconds=1.0)

    assert intervals_overlap(start_a, end_a, start_b, end_b) is True

    # Event C at 10:00:05: [10:00:04 to 10:00:06] -> No overlap with A
    time_c = base + timedelta(seconds=5.0)
    start_c = time_c - timedelta(seconds=1.0)
    end_c = time_c + timedelta(seconds=1.0)

    assert intervals_overlap(start_a, end_a, start_c, end_c) is False

def test_evaluate_timeline_ordering_flags_uncertain():
    base = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)

    e1 = TimelineEvent(
        event_id="E1",
        normalized_utc=base,
        earliest_utc=base - timedelta(seconds=1.0),
        latest_utc=base + timedelta(seconds=1.0)
    )
    # e2 is 1 second after e1 -> intervals overlap
    e2_time = base + timedelta(seconds=1.0)
    e2 = TimelineEvent(
        event_id="E2",
        normalized_utc=e2_time,
        earliest_utc=e2_time - timedelta(seconds=1.0),
        latest_utc=e2_time + timedelta(seconds=1.0)
    )
    # e3 is 10 seconds later -> strictly ordered
    e3_time = base + timedelta(seconds=10.0)
    e3 = TimelineEvent(
        event_id="E3",
        normalized_utc=e3_time,
        earliest_utc=e3_time - timedelta(seconds=1.0),
        latest_utc=e3_time + timedelta(seconds=1.0)
    )

    events = [e1, e2, e3]
    evaluate_timeline_ordering(events)

    assert e1.order_uncertain is True
    assert e2.order_uncertain is True
    assert e3.order_uncertain is False

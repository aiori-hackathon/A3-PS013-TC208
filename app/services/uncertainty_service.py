from typing import List
from app.models.entities import TimelineEvent
from app.services.normalization_service import intervals_overlap

def evaluate_timeline_ordering(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """
    Evaluates chronological order certainty for a sorted list of events.
    If an event's uncertainty interval overlaps with its predecessor or successor,
    the event is flagged with order_uncertain = True.
    """
    if not events:
        return events

    n = len(events)
    # Reset or initialize flags
    for e in events:
        e.order_uncertain = False

    for i in range(n):
        curr = events[i]
        if not curr.earliest_utc or not curr.latest_utc:
            # Events lacking reliable timestamps cannot establish strict ordering
            curr.order_uncertain = True
            continue

        # Check with previous event
        if i > 0:
            prev = events[i - 1]
            if prev.earliest_utc and prev.latest_utc:
                if intervals_overlap(curr.earliest_utc, curr.latest_utc, prev.earliest_utc, prev.latest_utc):
                    curr.order_uncertain = True
                    prev.order_uncertain = True

        # Check with next event
        if i < n - 1:
            nxt = events[i + 1]
            if nxt.earliest_utc and nxt.latest_utc:
                if intervals_overlap(curr.earliest_utc, curr.latest_utc, nxt.earliest_utc, nxt.latest_utc):
                    curr.order_uncertain = True
                    nxt.order_uncertain = True

    return events

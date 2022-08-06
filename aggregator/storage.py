from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from aggregator.time_utils import past_round_hour_range, past_round_minute_range
from sortedcontainers import SortedList
from threading import Lock
import heapq


from aggregator.consts import *


class AggregatedEvents:

    @abstractmethod
    def accept(self, event: dict, now: datetime):
        ...

    @abstractmethod
    def top_hosts(self, mode: str, limit: int, now: datetime):
        ...


class InMemorySelfCleanedAggregatedEvents(AggregatedEvents):

    def __init__(self) -> None:
        super().__init__()
        self.events = SortedList(key=lambda e: e[EVENT_TIMESTAMP_KEY])
        self.modes_map = {
            STAT_MODE_MINUTE: past_round_minute_range,
            STAT_MODE_HOUR: past_round_hour_range
        }
        # since "events" object is not the CPython list and compound, it should be explicitly locked on access
        self.events_lock = Lock()

    def accept(self, event: dict, now: datetime):
        with self.events_lock:
            self.events.add(event)
        self._clean_old_events(now)

    def _clean_old_events(self, now: datetime):
        clean_end_t = past_round_hour_range(now).start
        first_known_event = self.events[0]  # this is safe, since at least one event should be already in
        should_clean = first_known_event[EVENT_TIMESTAMP_KEY] < clean_end_t
        if should_clean:
            with self.events_lock:
                should_clean = first_known_event[EVENT_TIMESTAMP_KEY] < clean_end_t
                # Double Check (Anti-pattern ;-)
                # It is possible for multiple requests to request cleanup.
                # However, only first should succeed and others just need to drop.
                if not should_clean:
                    return
                first_valid = next((i for i, e in enumerate(self.events) if e[EVENT_TIMESTAMP_KEY] >= clean_end_t),
                                   len(self.events))
                del self.events[0:first_valid]

    def top_hosts(self, mode: str, limit: int, now: datetime):
        accepted_range = self.modes_map[mode](now)
        return self._top_in_range(accepted_range, limit)

    def _top_in_range(self, accepted_range: range, limit: int):
        host_requests = defaultdict(lambda: 0)
        with self.events_lock:
            for event in self.events:
                if event[EVENT_TIMESTAMP_KEY] not in accepted_range:
                    if event[EVENT_TIMESTAMP_KEY] > accepted_range.stop:
                        # since events are stored sorted, no need to check if checked event ts > accepted_range
                        break
                    continue
                for host, requests in event[HOST_REQUESTS_KEY].items():
                    host_requests[host] += requests
        top = heapq.nlargest(limit,
                             ((h, r_num) for h, r_num in host_requests.items()),
                             key=lambda e: e[1])
        return dict(top)

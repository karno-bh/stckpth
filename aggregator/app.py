from collections import defaultdict
import heapq
from threading import Lock
from aggregator.time_utils import past_round_hour_range, past_round_minute_range
from datetime import datetime
from sortedcontainers import SortedList
from typing import Dict

import cherrypy

STAT_MODE_MINUTE = 'minute'
STAT_MODE_HOUR = 'hour'
ALLOWED_STATS_TYPES = {STAT_MODE_MINUTE, STAT_MODE_HOUR}
EVENT_TIMESTAMP_KEY = "timestamp"
HOST_REQUESTS_KEY = "host_request"

RESPONSE_ERROR_KEY = "error"
CLEAN_UP_THRESHOLD_HOURS = 2


class AggregatorApp:

    def __init__(self, top_host_number=10) -> None:
        super().__init__()
        # since "events" object is not a OOB list amd compound, it should be explicitly locked
        self.events = SortedList(key=lambda e:e[EVENT_TIMESTAMP_KEY])
        self.top_host_number = top_host_number
        self.modes_map = {
            STAT_MODE_MINUTE: past_round_minute_range,
            STAT_MODE_HOUR: past_round_hour_range
        }
        self.events_lock = Lock()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def counter(self):
        event, err = self.fetch_and_validate_event()
        if not event:
            return err
        self.accept_event(event)
        self.clean_old_events()
        return {
            "status": "ok"
        }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stats(self, stats_type="minute"):
        if stats_type not in ALLOWED_STATS_TYPES:
            return self.gen_error(f"Unknown statistics type {stats_type} requested."
                                  f" Supported statistics are {ALLOWED_STATS_TYPES}")
        return {
            "top_hosts": self.top_hosts(stats_type)
        }

    def gen_error(self, text, code='400'):
        cherrypy.response.status = code
        return {
            "error": text
        }

    def fetch_and_validate_event(self):
        method = cherrypy.request.method
        if method != 'POST':
            return None, self.gen_error(f"Http Method {method} is not Supported")
        event = cherrypy.request.json
        if not isinstance(event, dict):
            return None, self.gen_error("POST body _MUST_ be an JSON object")
        if len(event) < 2:
            return None, self.gen_error("POST body JSON object contains too few fields")
        if EVENT_TIMESTAMP_KEY not in event:
            return None, self.gen_error(f"POST body object _MUST_ include 'f{EVENT_TIMESTAMP_KEY}' key")
        timestamp = event[EVENT_TIMESTAMP_KEY]
        if not isinstance(timestamp, int) or timestamp < 0:
            return None, self.gen_error(f"Timestamp should be positive integer")
        return event, None

    def accept_event(self, event):
        with self.events_lock:
            self.events.add(self.restructure_event(event))

    @staticmethod
    def restructure_event(event: Dict[str, str]):
        return {
            EVENT_TIMESTAMP_KEY: event[EVENT_TIMESTAMP_KEY],
            HOST_REQUESTS_KEY: {host: requests for host, requests in event.items() if host != EVENT_TIMESTAMP_KEY}
        }

    def clean_old_events(self):
        clean_end_t = past_round_hour_range(self.now()).start
        first_known_event = self.events[0] # this is safe, since at least one event should be already in
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

    def top_hosts(self, mode):
        host_requests = defaultdict(lambda: 0)
        accepted_range = self.modes_map[mode](self.now())
        with self.events_lock:
            for event in self.events:
                if event[EVENT_TIMESTAMP_KEY] not in accepted_range:
                    continue
                for host, requests in event[HOST_REQUESTS_KEY].items():
                    host_requests[host] += requests
        top = heapq.nlargest(self.top_host_number,
                             ((h, r_num) for h, r_num in host_requests.items()),
                             key=lambda e: e[1])
        return dict(top)

    def now(self):
        return datetime.now()



if __name__ == '__main__':
    cherrypy.quickstart(AggregatorApp())

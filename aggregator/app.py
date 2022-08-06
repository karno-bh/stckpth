from datetime import datetime
from typing import Dict

from aggregator.consts import *
from aggregator.storage import AggregatedEvents, InMemorySelfCleanedAggregatedEvents

import cherrypy


class AggregatorApp:

    def __init__(self, storage: AggregatedEvents, top_host_number=10) -> None:
        super().__init__()
        self.top_host_number = top_host_number
        self.storage: AggregatedEvents = storage

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def counter(self):
        event, err = self.fetch_and_validate_event()
        if not event:
            return err
        self.storage.accept(event, self.now())
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
            "top_hosts": self.storage.top_hosts(stats_type, self.top_host_number, self.now())
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
            return None, self.gen_error("POST body _MUST_ be a JSON object")
        if len(event) < 2:
            return None, self.gen_error("POST body JSON object contains too few fields")
        if EVENT_TIMESTAMP_KEY not in event:
            return None, self.gen_error(f"POST body object _MUST_ include '{EVENT_TIMESTAMP_KEY}' key")
        timestamp = event[EVENT_TIMESTAMP_KEY]
        if not isinstance(timestamp, int) or timestamp < 0:
            return None, self.gen_error(f"Timestamp should be positive integer")
        return self.restructure_event(event), None

    @staticmethod
    def restructure_event(event: Dict[str, str]):
        return {
            EVENT_TIMESTAMP_KEY: event[EVENT_TIMESTAMP_KEY],
            HOST_REQUESTS_KEY: {host: requests for host, requests in event.items() if host != EVENT_TIMESTAMP_KEY}
        }

    def now(self):
        return datetime.now()


if __name__ == '__main__':
    storage = InMemorySelfCleanedAggregatedEvents()
    cherrypy.quickstart(AggregatorApp(storage))

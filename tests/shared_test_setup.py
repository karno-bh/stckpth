import json
from datetime import datetime

from cherrypy.test import helper

from aggregator.app import AggregatorApp
from aggregator.storage import InMemorySelfCleanedAggregatedEvents

FIXED_NOW = datetime.fromtimestamp(1659703029)


class AggregatorAppFixedNow(AggregatorApp):

    def __init__(self, top_host_number=10) -> None:
        storage = InMemorySelfCleanedAggregatedEvents()
        super().__init__(storage, top_host_number)
        self._fixed_now = FIXED_NOW

    def now(self):
        return self._fixed_now

    def set_now(self, now):
        self._fixed_now = now

    def most_past_timestamp(self):
        return self.storage.events[0]


class APPWebCase(helper.CPWebCase):

    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)

    def post_counter(self, time: datetime, domains, method="POST", upset_body=None):
        obj = {
            "timestamp": round(time.timestamp()),
            **domains
        }
        obj_json_str = json.dumps(obj)
        body = bytes(obj_json_str, 'utf-8')
        body = upset_body or body
        self.getPage("/counter", method=method, headers=[("Content-Type", "application/json"),
                                                         ("Content-Length", str(len(body)))],
                     body=body)
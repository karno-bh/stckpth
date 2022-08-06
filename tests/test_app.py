import cherrypy

from cherrypy.test import helper

import json
from datetime import datetime, timedelta
from aggregator.app import AggregatorApp
from aggregator.storage import InMemorySelfCleanedAggregatedEvents
import aggregator.app

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

    def post_counter(self, time: datetime, domains):
        obj = {
            "timestamp": round(time.timestamp()),
            **domains
        }
        obj_json_str = json.dumps(obj)
        body = bytes(obj_json_str, 'utf-8')
        self.getPage("/counter", method="POST", headers=[("Content-Type", "application/json"),
                                                         ("Content-Length", str(len(body)))],
                     body=body)


class AppTestEmptyServer(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_top_hosts_should_be_empty(self):
        self.getPage("/stats")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {}}')


class AppTestCanAppend(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_app_can_append_valid_event(self):
        self.post_counter(FIXED_NOW, {"A": 2, "B": 3})
        self.assertStatus('200 OK')


class AppTestCanAppendAndGet(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_valid_event_returned_after_submit(self):
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 2, "B": 3})
        self.getPage("/stats")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {"B": 3, "A": 2}}')


class AppTestCanAppendAndSum(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_valid_events_are_aggregated(self):
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 5, "D": 4})

        self.getPage("/stats")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {"A": 7, "D": 4, "B": 2}}')


class AppTestCanAppendAndSumLastMinute(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_valid_events_are_aggregated_for_last_minute(self):
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(minutes=2), {"A": 5, "D": 4})

        self.getPage("/stats")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {"A": 7, "D": 4, "B": 2}}')


class AppTestCanAppendAndSumLastMinute2(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_valid_events_are_aggregated_for_last_minute_only(self):
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=1), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(minutes=2), {"A": 5, "D": 4})
        # should not be taken into account since it is not last round minute
        self.post_counter(FIXED_NOW - timedelta(seconds=3), {"A": 5, "D": 4})

        self.getPage("/stats")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {"A": 7, "D": 4, "B": 2}}')


class AppTestCanAppendAndSumLastHour(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_valid_events_are_aggregated_for_last_hour(self):
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=2), {"A": 5, "D": 4})

        # These should not be taken into account
        self.post_counter(FIXED_NOW - timedelta(minutes=10), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=15), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(minutes=20), {"A": 5, "D": 4})

        self.getPage("/stats?stats_type=hour")
        self.assertStatus('200 OK')
        self.assertBody(b'{"top_hosts": {"A": 12, "D": 8, "B": 2}}')


class AppTestCanCleanOldEntries(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_old_events_are_cleaned_up(self):
        # These should be deleted if NOW = NOW + 1H
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=2), {"A": 5, "D": 4})

        self.post_counter(FIXED_NOW - timedelta(minutes=10), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=15), {"A": 5, "D": 4})
        # This should be the oldest event
        oldest_after_time_passed = FIXED_NOW - timedelta(minutes=20)
        self.post_counter(oldest_after_time_passed, {"A": 5, "D": 4})

        app: AggregatorAppFixedNow = cherrypy.tree.apps[''].root
        app.set_now(FIXED_NOW + timedelta(hours=1))
        self.post_counter(FIXED_NOW - timedelta(minutes=10), {"A": 2, "B": 2})

        t = app.most_past_timestamp()[aggregator.app.EVENT_TIMESTAMP_KEY]
        expected = oldest_after_time_passed.timestamp()

        self.assertEqual(int(expected), t)


class AppTestCanReturnExpectedNumberOfDomains(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(top_host_number=2), '/', {})

    def test_only_expected_number_of_domains_returned(self):
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=1), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(hours=1, minutes=2), {"A": 5, "D": 4})

        # These should not be taken into account
        self.post_counter(FIXED_NOW - timedelta(minutes=10), {"A": 2, "B": 2})
        self.post_counter(FIXED_NOW - timedelta(minutes=15), {"A": 5, "D": 4})
        self.post_counter(FIXED_NOW - timedelta(minutes=20), {"A": 5, "D": 4})

        self.getPage("/stats?stats_type=hour")
        self.assertStatus('200 OK')
        expected_body = b'{"top_hosts": {"A": 12, "D": 8}}'
        expected_body_obj = json.loads(expected_body)
        self.assertEqual(len(expected_body_obj["top_hosts"]), 2)
        self.assertBody(expected_body)

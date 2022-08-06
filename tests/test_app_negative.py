import cherrypy

from tests.shared_test_setup import *


class AppTestWrongRequests(APPWebCase):

    @staticmethod
    def setup_server():
        cherrypy.tree.mount(AggregatorAppFixedNow(), '/', {})

    def test_app_cannot_with_invalid_method(self):
        self.post_counter(FIXED_NOW, {"A": 2, "B": 3}, method="GET")
        self.assertStatus('400 Bad Request')
        self.assertInBody("Http Method")

    def test_app_cannot_accept_non_json_objects(self):
        self.post_counter(FIXED_NOW, {"A": 2, "B": 3}, upset_body=b'[]')
        self.assertStatus('400 Bad Request')
        self.assertInBody("_MUST_ be a JSON object")

    def test_app_cannot_accept_too_few_fields(self):
        self.post_counter(FIXED_NOW, {})
        self.assertStatus('400 Bad Request')
        self.assertInBody("too few")

    def test_app_cannot_accept_without_timestamp(self):
        self.post_counter(FIXED_NOW, {}, upset_body=b'{ "A": 1, "B": 42 }')
        self.assertStatus('400 Bad Request')
        self.assertInBody("'timestamp' key")

    def test_app_cannot_accept_negative_timestamp(self):
        self.post_counter(FIXED_NOW, {}, upset_body=b'{ "timestamp": -42,  "A": 1, "B": 42 }')
        self.assertStatus('400 Bad Request')
        self.assertInBody("positive integer")

    def test_app_cannot_return_wrong_requested_type(self):
        self.getPage("/stats?stats_type=day")
        self.assertStatus('400 Bad Request')
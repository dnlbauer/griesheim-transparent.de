from django.test import Client
from django.test import SimpleTestCase


class SearchViewTest(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_redirect_if_empty(self):
        r = self.client.get("/search")
        self.assertRedirects(r, '/', status_code=302, target_status_code=200)
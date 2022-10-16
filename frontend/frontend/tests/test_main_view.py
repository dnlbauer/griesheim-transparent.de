import unittest
from unittest.mock import patch

from django.test import Client

from solr import SearchResults


class MainViewTest(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    @patch('frontend.views.solr')
    def test_main_view(self, solr_mock):
        solr_mock.search.return_value = SearchResults([], [], 1, 1, 1337, 0)
        r = self.client.get("/")

        self.assertEqual(r.status_code, 200)
        content = str(r.content)
        assert("1337" in content)
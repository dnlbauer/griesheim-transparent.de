from unittest.mock import patch
from django.test import Client
from django.test import SimpleTestCase


class SearchViewTest(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    @patch('frontend.search.solr.count')
    @patch('frontend.search.solr.doc_id')
    def test_redirect_if_empty(self, mock_doc_id, mock_count):
        # Mock Solr responses for the main view
        mock_count.return_value = 1000
        mock_doc_id.return_value = []
        
        r = self.client.get("/search")
        self.assertRedirects(r, '/', status_code=302, target_status_code=200)
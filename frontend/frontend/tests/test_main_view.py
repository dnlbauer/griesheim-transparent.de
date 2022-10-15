import unittest
from django.test import Client


class MainViewTest(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def test_main_view(self):
        r = self.client.get("/")

        self.assertEqual(r.status_code, 200)
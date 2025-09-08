import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    """Provide a Django test client for all tests."""
    return Client()

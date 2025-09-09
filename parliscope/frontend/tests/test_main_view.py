from unittest.mock import Mock, patch

from django.test import Client


@patch("frontend.views.solr")
def test_main_view(solr_mock: Mock, client: Client) -> None:
    solr_mock.count.return_value = 1337
    response = client.get("/")

    assert response.status_code == 200
    content = str(response.content)
    assert "1337" in content

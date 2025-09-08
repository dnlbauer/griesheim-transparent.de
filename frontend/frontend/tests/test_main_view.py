from unittest.mock import patch


@patch('frontend.views.solr')
def test_main_view(solr_mock, client):
    solr_mock.count.return_value = 1337
    response = client.get("/")

    assert response.status_code == 200
    content = str(response.content)
    assert "1337" in content
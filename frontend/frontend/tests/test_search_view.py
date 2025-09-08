from unittest.mock import patch


@patch('frontend.search.solr.count')
@patch('frontend.search.solr.doc_id')
def test_redirect_if_empty(mock_doc_id, mock_count, client):
    # Mock Solr responses for the main view
    mock_count.return_value = 1000
    mock_doc_id.return_value = []

    response = client.get("/search")

    # Check redirect response
    assert response.status_code == 302
    assert response.url == '/'

    # Follow redirect and check final response
    response = client.get("/search", follow=True)
    assert response.status_code == 200

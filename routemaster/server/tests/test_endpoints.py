async def test_root(app_client):
    response = await app_client.get('/')
    data = await response.json()
    assert data == {}

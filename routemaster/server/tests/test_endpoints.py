async def test_root(app_client):
    client = await app_client()
    response = await client.get('/')
    data = await response.json()
    assert data == {
        'state_machines': 0,
        'labels': 0,
    }

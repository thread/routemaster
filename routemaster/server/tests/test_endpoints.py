from routemaster.config import Config


async def test_root(app_client):
    client = await app_client(config_file='trivial.yaml')
    response = await client.get('/')
    data = await response.json()
    assert data == {
        'config': {
            'state_machines': {
                'example': [{
                    'exit_condition': False,
                    'gate': 'start',
                }],
            },
        },
    }

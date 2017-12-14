import json

from routemaster.db import Label, History


async def test_root(app_client, create_label):
    await create_label('foo', 'test_machine', {})
    client = await app_client()
    response = await client.get('/')
    data = await response.json()
    assert data == {
        'state_machines': 1,
        'labels': 1,
    }


async def test_create_label(app_client, app_factory):
    app = app_factory()

    label_name = 'foo'
    state_machine_name = list(app.config.state_machines.keys())[0]
    label_context = {'bar': 'baz'}

    client = await app_client(app)
    response = await client.post(
        f'/state-machines/{state_machine_name}/labels/{label_name}',
        data=json.dumps(label_context),
    )

    assert response.status == 201
    response_json = await response.json()
    assert response_json == {'bar': 'baz'}

    async with app.db.begin() as conn:
        assert await conn.scalar(Label.count()) == 1
        result = await conn.execute(Label.select())
        label = await result.fetchone()
        assert label.name == label_name
        assert label.state_machine == state_machine_name
        assert label.context == label_context


async def test_create_label_404_for_not_found_state_machine(app_client):
    client = await app_client()
    response = await client.post(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'bar': 'baz'}),
    )
    assert response.status == 404


async def test_create_label_400_for_invalid_body(app_client):
    client = await app_client()
    response = await client.post(
        '/state-machines/test_machine/labels/foo',
        data='not valid json',
    )
    assert response.status == 400


async def test_update_label(app_client, app_factory, create_label):
    app = app_factory()
    await create_label('foo', 'test_machine', {})

    label_context = {'bar': 'baz'}
    client = await app_client()
    response = await client.post(
        '/state-machines/test_machine/labels/foo/update',
        data=json.dumps(label_context),
    )
    assert response.status == 200
    response_json = await response.json()
    assert response_json == label_context

    async with app.db.begin() as conn:
        result = await conn.execute(Label.select())
        label = await result.fetchone()
        assert label.context == label_context


async def test_update_label_404_for_not_found_label(app_client):
    client = await app_client()
    response = await client.post(
        '/state-machines/test_machine/labels/foo/update',
        data={'foo': 'bar'},
    )
    assert response.status == 404


async def test_update_label_400_for_invalid_body(app_client, create_label):
    await create_label('foo', 'test_machine', {})
    client = await app_client()
    response = await client.post(
        '/state-machines/test_machine/labels/foo/update',
        data='not valid json',
    )
    assert response.status == 400


async def test_get_label(app_client, create_label):
    await create_label('foo', 'test_machine', {'bar': 'baz'})
    client = await app_client()
    response = await client.get('/state-machines/test_machine/labels/foo')
    assert response.status == 200
    response_json = await response.json()
    assert response_json == {'bar': 'baz'}

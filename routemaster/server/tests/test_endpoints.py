import json

from routemaster.db import labels


def test_root(client, create_label):
    response = client.get('/')
    assert response.json == {'status': 'ok'}


def test_create_label(client, app_config):
    label_name = 'foo'
    state_machine_name = list(app_config.config.state_machines.keys())[0]
    label_context = {'bar': 'baz'}

    response = client.post(
        f'/state-machines/{state_machine_name}/labels/{label_name}',
        data=json.dumps(label_context),
        content_type='application/json',
    )

    assert response.status_code == 201
    assert response.json == {'bar': 'baz'}

    with app_config.db.begin() as conn:
        assert conn.scalar(labels.count()) == 1
        result = conn.execute(labels.select())
        label = result.fetchone()
        assert label.name == label_name
        assert label.state_machine == state_machine_name
        assert label.context == label_context


def test_create_label_404_for_not_found_state_machine(client):
    response = client.post(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'bar': 'baz'}),
        content_type='application/json',
    )
    assert response.status_code == 404


def test_create_label_400_for_invalid_body(client):
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data='not valid json',
        content_type='application/json',
    )
    assert response.status_code == 400


def test_update_label(client, app_config, create_label):
    create_label('foo', 'test_machine', {})

    label_context = {'bar': 'baz'}
    response = client.post(
        '/state-machines/test_machine/labels/foo/update',
        data=json.dumps(label_context),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert response.json == label_context

    with app_config.db.begin() as conn:
        result = conn.execute(labels.select())
        label = result.fetchone()
        assert label.context == label_context


def test_update_label_404_for_not_found_label(client):
    response = client.post(
        '/state-machines/test_machine/labels/foo/update',
        data=json.dumps({'foo': 'bar'}),
        content_type='application/json',
    )
    assert response.status_code == 404


def test_update_label_400_for_invalid_body(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo/update',
        data='not valid json',
        content_type='application/json',
    )
    assert response.status_code == 400


def test_get_label(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 200
    assert response.json == {'bar': 'baz'}

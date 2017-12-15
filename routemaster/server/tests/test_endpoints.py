import json

from routemaster.db import labels, history


def test_root(client, create_label):
    response = client.get('/')
    assert response.json == {'status': 'ok'}


def test_create_label(client, app_config):
    label_name = 'foo'
    state_machine = list(app_config.config.state_machines.values())[0]
    label_context = {'bar': 'baz'}

    response = client.post(
        f'/state-machines/{state_machine.name}/labels/{label_name}',
        data=json.dumps(label_context),
        content_type='application/json',
    )

    assert response.status_code == 201
    assert response.json == {'bar': 'baz'}

    with app_config.db.begin() as conn:
        assert conn.scalar(labels.count()) == 1
        label = conn.execute(labels.select()).fetchone()
        assert label.name == label_name
        assert label.state_machine == state_machine.name
        assert label.context == label_context

        history_entry = conn.execute(history.select()).fetchone()
        assert history_entry.label_name == label_name
        assert history_entry.old_state is None
        assert history_entry.new_state == state_machine.states[0].name


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


def test_create_label_400_for_already_existing_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({}),
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

import json

from sqlalchemy import and_, select

from routemaster.db import labels, history


    response = client.get('/')
    assert response.json == {'status': 'ok'}


def test_enumerate_state_machines(client, app_config):
    response = client.get('/state-machines')
    assert response.status_code == 200
    assert response.json == {'state-machines': [
        {
            'name': state_machine.name,
            'labels': f'/state-machines/{state_machine.name}/labels',
        }
        for state_machine in app_config.config.state_machines.values()
    ]}


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


def test_create_label_409_for_already_existing_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_label(client, app_config, create_label):
    create_label('foo', 'test_machine', {})

    label_context = {'bar': 'baz'}
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
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
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'foo': 'bar'}),
        content_type='application/json',
    )
    assert response.status_code == 404


def test_update_label_400_for_invalid_body(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data='not valid json',
        content_type='application/json',
    )
    assert response.status_code == 400


def test_get_label(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 200
    assert response.json == {'bar': 'baz'}


def test_get_label_404_for_not_found_label(client, create_label):
    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 404


def test_get_label_404_for_not_found_state_machine(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/nonexistent_machine/labels/foo')
    assert response.status_code == 404


def test_list_labels_404_for_not_found_state_machine(client, create_label):
    response = client.get('/state-machines/nonexistent_machine/labels')
    assert response.status_code == 404


def test_list_labels_when_none(client, create_label):
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert response.json == {'labels': []}


def test_list_labels_when_one(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert response.json == {'labels': [{'name': 'foo'}]}


def test_list_labels_when_many(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    create_label('quox', 'test_machine', {'spam': 'ham'})
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    # Always returned in alphabetical order
    assert response.json == {'labels': [{'name': 'foo'}, {'name': 'quox'}]}


def test_update_label_moves_label(client, create_label, app_config):
    create_label('foo', 'test_machine', {})
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'should_progress': True}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert response.json == {'should_progress': True}

    with app_config.db.begin() as conn:
        latest_state = conn.scalar(
            select([history.c.new_state]).where(and_(
                history.c.label_name == 'foo',
                history.c.label_state_machine == 'test_machine',
            )).order_by(
                history.c.created.desc(),
            ).limit(1)
        )
        assert latest_state == 'end'


def test_delete_existing_label(client, app_config, create_label):
    label_name = 'foo'
    state_machine = list(app_config.config.state_machines.values())[0]

    create_label(label_name, state_machine.name, {'bar': 'baz'})

    response = client.delete(
        f'/state-machines/{state_machine.name}/labels/{label_name}',
        content_type='application/json',
    )

    assert response.status_code == 204

    with app_config.db.begin() as conn:
        assert conn.scalar(labels.count()) == 1
        label = conn.execute(labels.select()).fetchone()
        assert label.name == label_name
        assert label.state_machine == state_machine.name
        assert label.context == {}

        history_entry = conn.execute(
            history.select().order_by(history.c.created.desc()),
        ).fetchone()
        assert history_entry.label_name == label_name
        assert history_entry.old_state == state_machine.states[0].name
        assert history_entry.new_state is None


def test_delete_non_existent_label(client, app_config):
    # When deleting a non-existent label, we do nothing.

    response = client.delete(
        f'/state-machines/test_machine/labels/foo',
        content_type='application/json',
    )

    assert response.status_code == 204

    with app_config.db.begin() as conn:
        assert conn.scalar(labels.count()) == 0
        assert conn.scalar(history.count()) == 0


def test_delete_label_404_for_not_found_state_machine(client):
    response = client.delete(
        '/state-machines/nonexistent_machine/labels/foo',
        content_type='application/json',
    )
    assert response.status_code == 404


def test_list_labels_excludes_deleted_labels(
    client,
    create_label,
    create_deleted_label,
    app_config,
):
    create_deleted_label('foo', 'test_machine')
    create_label('quox', 'test_machine', {'spam': 'ham'})

    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert response.json == {'labels': [{'name': 'quox'}]}


def test_get_label_410_for_deleted_label(
    client,
    create_deleted_label,
    app_config,
):
    create_deleted_label('foo', 'test_machine')

    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 410


def test_create_label_409_for_deleted_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_label_410_for_deleted_label(
    client,
    create_deleted_label,
    app_config,
):
    create_deleted_label('foo', 'test_machine')

    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'foo': 'bar'}),
        content_type='application/json',
    )
    assert response.status_code == 410

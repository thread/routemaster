import json

from sqlalchemy import and_, select

from routemaster.db import Label, History


def test_root(client):
    response = client.get('/')
    assert response.json == {
        'status': 'ok',
        'state-machines': '/state-machines',
    }


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
        data=json.dumps({'context': label_context}),
        content_type='application/json',
    )

    assert response.status_code == 201
    assert response.json['context'] == {'bar': 'baz'}

    label = app_config.session.query(Label).one()
    assert label.name == label_name
    assert label.state_machine == state_machine.name
    assert label.context == label_context

    history = app_config.session.query(History).one()
    assert history.label_name == label_name
    assert history.old_state is None
    assert history.new_state == state_machine.states[0].name


def test_create_label_404_for_not_found_state_machine(client):
    response = client.post(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'context': {'bar': 'baz'}}),
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


def test_create_label_400_for_missing_context_key(client):
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data='{}',
        content_type='application/json',
    )
    assert response.status_code == 400


def test_create_label_409_for_already_existing_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'context': {}}),
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_label(client, app_config, create_label):
    create_label('foo', 'test_machine', {})

    label_context = {'bar': 'baz'}
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'context': label_context}),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert response.json['context'] == label_context

    label = app_config.session.query(Label).one()
    assert label.context == label_context


def test_update_label_404_for_not_found_label(client):
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'context': {'foo': 'bar'}}),
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
    assert response.json['context'] == {'bar': 'baz'}


def test_get_label_has_state(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 200
    assert response.json['state'] == 'start'


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
    assert response.json['labels'] == []


def test_list_labels_includes_link_to_create_labels(client, create_label):
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert (
        response.json['create'] ==
        '/state-machines/test_machine/labels/:name'
    )


def test_list_labels_when_one(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert response.json['labels'] == [{'name': 'foo'}]


def test_list_labels_when_many(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    create_label('quox', 'test_machine', {'spam': 'ham'})
    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    # Always returned in alphabetical order
    assert response.json['labels'] == [{'name': 'foo'}, {'name': 'quox'}]


def test_update_label_moves_label(client, create_label, app_config):
    create_label('foo', 'test_machine', {})
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'context': {'should_progress': True}}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert response.json['context'] == {'should_progress': True}

    latest_state = app_config.session.query(History.new_state).filter_by(
        label_name='foo',
        label_state_machine='test_machine',
    ).order_by(
        History.created.desc(),
    ).scalar()
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

    label = app_config.session.query(Label).one()
    assert label.name == label_name
    assert label.state_machine == state_machine.name
    assert label.context == {}

    history = app_config.session.query(History).order_by(
        History.created.desc(),
    ).first()
    assert history.label_name == label_name
    assert history.old_state == state_machine.states[0].name
    assert history.new_state is None


def test_delete_non_existent_label(client, app_config):
    # When deleting a non-existent label, we do nothing.

    response = client.delete(
        f'/state-machines/test_machine/labels/foo',
        content_type='application/json',
    )

    assert response.status_code == 204

    assert not app_config.session.query(Label).exists().scalar()
    assert not app_config.session.query(History).exists().scalar()


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
    assert response.json['labels'] == [{'name': 'quox'}]


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
        data=json.dumps({'context': {}}),
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
        data=json.dumps({'context': {'foo': 'bar'}}),
        content_type='application/json',
    )
    assert response.status_code == 410

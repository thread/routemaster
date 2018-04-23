import json
from unittest import mock

from routemaster.db import Label, History


def test_root(client, version):
    response = client.get('/')
    assert response.json == {
        'status': 'ok',
        'state-machines': '/state-machines',
        'version': version,
    }


def test_root_error_state(client, version):
    with mock.patch(
        'sqlalchemy.orm.query.Query.count',
        side_effect=RuntimeError,
    ):
        response = client.get('/')
        assert response.status_code == 503
        assert response.json == {
            'status': 'error',
            'message': 'Cannot connect to database',
            'version': version,
        }


def test_enumerate_state_machines(client, app):
    response = client.get('/state-machines')
    assert response.status_code == 200
    assert response.json == {'state-machines': [
        {
            'name': state_machine.name,
            'labels': f'/state-machines/{state_machine.name}/labels',
        }
        for state_machine in app.config.state_machines.values()
    ]}


def test_create_label(client, app, mock_test_feed):
    label_name = 'foo'
    state_machine = app.config.state_machines['test_machine']
    label_metadata = {'bar': 'baz'}

    with mock_test_feed():
        response = client.post(
            f'/state-machines/{state_machine.name}/labels/{label_name}',
            data=json.dumps({'metadata': label_metadata}),
            content_type='application/json',
        )

    assert response.status_code == 201
    assert response.json['metadata'] == {'bar': 'baz'}

    with app.new_session():
        label = app.session.query(Label).one()
        assert label.name == label_name
        assert label.state_machine == state_machine.name
        assert label.metadata == label_metadata

        history = app.session.query(History).one()
        assert history.label_name == label_name
        assert history.old_state is None
        assert history.new_state == state_machine.states[0].name


def test_create_label_404_for_not_found_state_machine(client):
    response = client.post(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'metadata': {'bar': 'baz'}}),
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


def test_create_label_400_for_missing_metadata_key(client):
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == 400


def test_create_label_409_for_already_existing_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'metadata': {}}),
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_label(client, app, create_label, mock_webhook, mock_test_feed):
    create_label('foo', 'test_machine', {})

    label_metadata = {'bar': 'baz'}
    with mock_webhook(), mock_test_feed():
        response = client.patch(
            '/state-machines/test_machine/labels/foo',
            data=json.dumps({'metadata': label_metadata}),
            content_type='application/json',
        )

    assert response.status_code == 200
    assert response.json['metadata'] == label_metadata

    with app.new_session():
        label = app.session.query(Label).one()
        assert label.metadata == label_metadata


def test_update_label_404_for_not_found_label(client):
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'metadata': {'foo': 'bar'}}),
        content_type='application/json',
    )
    assert response.status_code == 404


def test_update_label_404_for_not_found_state_machine(client):
    response = client.patch(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'metadata': {'foo': 'bar'}}),
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


def test_update_label_400_for_no_metadata(client, app, create_label):
    create_label('foo', 'test_machine', {})

    label_metadata = {'bar': 'baz'}
    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'not_metadata': label_metadata}),
        content_type='application/json',
    )

    assert response.status_code == 400


def test_get_label(client, create_label):
    create_label('foo', 'test_machine', {'bar': 'baz'})
    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 200
    assert response.json['metadata'] == {'bar': 'baz'}


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


def test_update_label_moves_label(client, create_label, app, mock_webhook, mock_test_feed, current_state):
    label = create_label('foo', 'test_machine', {})

    with mock_webhook() as webhook, mock_test_feed():
        response = client.patch(
            '/state-machines/test_machine/labels/foo',
            data=json.dumps({'metadata': {'should_progress': True}}),
            content_type='application/json',
        )
        webhook.assert_called_once()

    assert response.status_code == 200
    assert response.json['metadata'] == {'should_progress': True}
    assert current_state(label) == 'end'


def test_delete_existing_label(client, app, create_label):
    label_name = 'foo'
    state_machine = app.config.state_machines['test_machine']

    create_label(label_name, state_machine.name, {'bar': 'baz'})

    response = client.delete(
        f'/state-machines/{state_machine.name}/labels/{label_name}',
        content_type='application/json',
    )

    assert response.status_code == 204

    with app.new_session():
        label = app.session.query(Label).one()
        assert label.name == label_name
        assert label.state_machine == state_machine.name
        assert label.metadata == {}

        history = app.session.query(History).order_by(
            History.id.desc(),
        ).first()
        assert history is not None
        assert history.label_name == label_name
        assert history.old_state == state_machine.states[0].name
        assert history.new_state is None


def test_delete_non_existent_label(client, app):
    # When deleting a non-existent label, we do nothing.

    response = client.delete(
        f'/state-machines/test_machine/labels/foo',
        content_type='application/json',
    )

    assert response.status_code == 204

    with app.new_session():
        assert app.session.query(Label).count() == 0
        assert app.session.query(History).count() == 0


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
    app,
):
    create_deleted_label('foo', 'test_machine')
    create_label('quox', 'test_machine', {'spam': 'ham'})

    response = client.get('/state-machines/test_machine/labels')
    assert response.status_code == 200
    assert response.json['labels'] == [{'name': 'quox'}]


def test_get_label_410_for_deleted_label(
    client,
    create_deleted_label,
    app,
):
    create_deleted_label('foo', 'test_machine')

    response = client.get('/state-machines/test_machine/labels/foo')
    assert response.status_code == 410


def test_create_label_409_for_deleted_label(client, create_label):
    create_label('foo', 'test_machine', {})
    response = client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'metadata': {}}),
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_label_410_for_deleted_label(
    client,
    create_deleted_label,
    app,
):
    create_deleted_label('foo', 'test_machine')

    response = client.patch(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'metadata': {'foo': 'bar'}}),
        content_type='application/json',
    )
    assert response.status_code == 410


def test_check_loggers(client):
    response = client.get('/check-loggers')
    assert response.status_code == 500

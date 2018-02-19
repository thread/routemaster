"""Core API endpoints for routemaster service."""

import pkg_resources
from flask import Flask, abort, jsonify, request

from routemaster import state_machine
from routemaster.state_machine import (
    LabelRef,
    UnknownLabel,
    LabelAlreadyExists,
    UnknownStateMachine,
)

server = Flask('routemaster')


@server.route('/', methods=['GET'])
def status():
    """
    Status check endpoint.

    Returns:
    - 200 Ok:                  if upstream services are up and the application
                               appears ready to serve requests.
    - 503 Service Unavailable: if there is any detected reason why the service
                               might not be able to serve requests.
    """
    try:
        version = pkg_resources.working_set.by_key['routemaster'].version
    except KeyError:
        version = 'development'

    try:
        with server.config.app.db.begin() as conn:
            conn.execute('select 1')
            return jsonify({
                'status': 'ok',
                'state-machines': '/state-machines',
                'version': version,
            })
    except Exception:
        return jsonify({
            'status': 'error',
            'message': 'Cannot connect to database',
            'version': version,
        }), 503


@server.route('/state-machines', methods=['GET'])
def get_state_machines():
    """
    List the state machines known to this server.

    Successful return codes return a list of dictionaries containing at least
    the name of each state machine.
    """
    return jsonify({
        'state-machines': [
            {
                'name': x.name,
                'labels': f'/state-machines/{x.name}/labels',
            }
            for x in server.config.app.config.state_machines.values()
        ],
    })


@server.route(
    '/state-machines/<state_machine_name>/labels',
    methods=['GET'],
)
def get_labels(state_machine_name):
    """
    List the labels in a state machine.

    Returns:
    - 200 Ok: if the state machine exists.
    - 404 Not Found: if the state machine does not exist.

    Successful return codes return a list of dictionaries containing at least
    the name of each label.
    """
    app = server.config.app

    try:
        state_machine_instance = app.config.state_machines[state_machine_name]
    except KeyError as k:
        msg = f"State machine '{state_machine_name}' does not exist"
        abort(404, msg)

    labels = state_machine.list_labels(app, state_machine_instance)
    return jsonify({
        'labels': [{'name': x.name} for x in labels],
        'create': f'/state-machines/{state_machine_name}/labels/:name',
    })


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['GET'],
)
def get_label(state_machine_name, label_name):
    """
    Get a label within a given state machine.

    Returns:
    - 200 Ok: if the label is exists.
    - 404 Not Found: if the state machine or label does not exist.
    - 410 Gone: if the label once existed but has since been deleted.

    Successful return codes return the full metadata for the label.
    """
    app = server.config.app
    label = LabelRef(label_name, state_machine_name)

    try:
        metadata = state_machine.get_label_metadata(app, label)
    except UnknownLabel as e:
        abort(
            410 if e.deleted else 404,
            f"Label {label.name} in state machine '{label.state_machine}' "
            f"does not exist.",
        )
    except UnknownStateMachine:
        abort(404, f"State machine '{label.state_machine}' does not exist.")

    state = state_machine.get_label_state(app, label)
    return jsonify(metadata=metadata, state=state.name)


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['POST'],
)
def create_label(state_machine_name, label_name):
    """
    Create a label with a given metadata, and start it in the state machine.

    Returns:
    - 201 Created: if the label is successfully created and started.
    - 409 Conflict: if the label already exists in the state machine.
    - 404 Not Found: if the state machine does not exist.
    - 400 Bad Request: if the request body is not a valid metadata.

    Successful return codes return the full created metadata for the label.
    """
    app = server.config.app
    label = LabelRef(label_name, state_machine_name)
    data = request.get_json()

    try:
        initial_metadata = data['metadata']
    except KeyError:
        abort(400, "No metadata given")

    try:
        initial_state_name = \
            app.config.state_machines[state_machine_name].states[0].name
        metadata = state_machine.create_label(app, label, initial_metadata)
        return jsonify(metadata=metadata, state=initial_state_name), 201
    except LookupError:
        msg = f"State machine '{state_machine_name}' does not exist"
        abort(404, msg)
    except LabelAlreadyExists:
        msg = f"Label {label_name} already exists in '{state_machine_name}'"
        abort(409, msg)


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>', # noqa
    methods=['PATCH'],
)
def update_label(state_machine_name, label_name):
    """
    Update a label in a state machine.

    Triggering progression if necessary according to the state machine
    configuration. Updates are _merged_ with existing metadata.

    Returns:
    - 200 Ok: if the label is successfully updated.
    - 400 Bad Request: if the request body is not a valid metadata.
    - 404 Not Found: if the state machine or label does not exist.
    - 410 Gone: if the label once existed but has since been deleted.

    Successful return codes return the full new metadata for a label.
    """
    app = server.config.app
    label = LabelRef(label_name, state_machine_name)

    try:
        patch_metadata = request.get_json()['metadata']
    except KeyError:
        abort(400, "No new metadata")

    try:
        new_metadata = state_machine.update_metadata_for_label(
            app,
            label,
            patch_metadata,
        )
        state = state_machine.get_label_state(app, label)
        return jsonify(metadata=new_metadata, state=state.name)
    except UnknownStateMachine:
        msg = f"State machine '{state_machine_name}' does not exist"
        abort(404, msg)
    except UnknownLabel as e:
        abort(
            410 if e.deleted else 404,
            f"Label {label_name} does not exist in state machine "
            f"'{state_machine_name}'.",
        )


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['DELETE'],
)
def delete_label(state_machine_name, label_name):
    """
    Delete a label in a state machine.

    Marks a label as deleted, but does not remove it from the database.
    Deleted labels cannot be updated and will not move state.

    Returns:
    - 204 No content: if the label is successfully deleted (or did not exist).
    - 404 Not Found: if the state machine does not exist.
    """
    app = server.config.app
    label = LabelRef(label_name, state_machine_name)

    try:
        state_machine.delete_label(app, label)
    except UnknownStateMachine:
        msg = f"State machine '{state_machine_name}' does not exist"
        abort(404, msg)

    return '', 204


@server.route('/check-loggers', methods=['GET'])
def check_loggers():
    """
    Logging check endpoint.

    This endpoint errors so as to verify that loggers are working.
    """
    raise Exception("Test exception")

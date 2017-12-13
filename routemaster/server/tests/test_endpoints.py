import json

import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ContextTrigger,
    ConstantNextState,
)
from routemaster.exit_conditions import ExitConditionProgram

TEST_STATE_MACHINES = {
    'test_machine': StateMachine(
        name='test_machine',
        states=[
            Gate(
                name='start',
                triggers=[
                    ContextTrigger(context_path='should_progress'),
                ],
                next_states=ConstantNextState(state='end'),
                exit_condition=ExitConditionProgram('should_progress = true'),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    ),
}


async def test_root(app_client):
    client = await app_client()
    response = await client.get('/')
    data = await response.json()
    assert data == {
        'state_machines': 0,
        'labels': 0,
    }


async def test_create_label(app_client, app_config):
    client = await app_client(app_config(state_machines=TEST_STATE_MACHINES))
    response = await client.post(
        '/state-machines/test_machine/labels/foo',
        data=json.dumps({'bar': 'baz'}),
    )
    assert response.status == 201


async def test_create_label_404_for_not_found_state_machine(app_client):
    client = await app_client()
    response = await client.post(
        '/state-machines/nonexistent_machine/labels/foo',
        data=json.dumps({'bar': 'baz'}),
    )
    assert response.status == 404

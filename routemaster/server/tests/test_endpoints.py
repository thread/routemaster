import json

import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ContextTrigger,
    ConstantNextState,
)
from routemaster.db import Label, History
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


async def test_create_label(app_client, app_factory):
    label_name = 'foo'
    state_machine_name = 'test_machine'
    label_context = {'bar': 'baz'}

    app = app_factory(state_machines=TEST_STATE_MACHINES)
    client = await app_client(app)
    response = await client.post(
        f'/state-machines/{state_machine_name}/labels/{label_name}',
        data=json.dumps(label_context),
    )

    response_json = await response.json()
    assert response.status == 201
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

import datetime

import pytest
import dateutil

from routemaster.config import (
    NoNextStates,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.context import Context

UTC_NOW = datetime.datetime.now(dateutil.tz.tzutc())


def test_constant_next_state():
    next_states = ConstantNextState(state='foo')
    assert next_states.all_destinations() == ['foo']
    assert next_states.next_state_for_label(None) == 'foo'


def test_no_next_states_must_not_be_called():
    next_states = NoNextStates()
    assert next_states.all_destinations() == []
    with pytest.raises(RuntimeError):
        next_states.next_state_for_label(None)


def test_context_next_states():
    next_states = ContextNextStates(
        path='metadata.foo',
        destinations=[
            ContextNextStatesOption(state='1', value=True),
            ContextNextStatesOption(state='2', value=False),
        ],
    )

    context = Context({'foo': True}, UTC_NOW, None, [])

    assert next_states.all_destinations() == ['1', '2']
    assert next_states.next_state_for_label(context) == '1'


def test_context_next_states_raises_for_no_valid_state():
    next_states = ContextNextStates(
        path='metadata.foo',
        destinations=[
            ContextNextStatesOption(state='1', value=True),
            ContextNextStatesOption(state='2', value=False),
        ],
    )

    context = Context({'foo': 'bar'}, UTC_NOW, None, [])

    with pytest.raises(RuntimeError):
        next_states.next_state_for_label(context)

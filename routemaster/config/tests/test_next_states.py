import pytest

from routemaster.config import (
    NoNextStates,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)


def test_constant_next_state():
    next_states = ConstantNextState(state='foo')
    assert next_states.all_destinations() == ['foo']
    assert next_states.next_state_for_label(None) == 'foo'


def test_no_next_states_must_not_be_called():
    next_states = NoNextStates()
    assert next_states.all_destinations() == []
    with pytest.raises(RuntimeError):
        next_states.next_state_for_label(None)


def test_context_next_states(make_context):
    next_states = ContextNextStates(
        path='metadata.foo',
        destinations=[
            ContextNextStatesOption(state='1', value=True),
            ContextNextStatesOption(state='2', value=False),
        ],
        default='3',
    )

    context = make_context(label='label1', metadata={'foo': True})

    assert next_states.all_destinations() == ['1', '2', '3']
    assert next_states.next_state_for_label(context) == '1'


def test_context_next_states_returns_default_if_no_match(make_context):
    next_states = ContextNextStates(
        path='metadata.foo',
        destinations=[
            ContextNextStatesOption(state='1', value=True),
            ContextNextStatesOption(state='2', value=False),
        ],
        default='3',
    )

    context = make_context(label='label1', metadata={'foo': 'bar'})

    assert next_states.next_state_for_label(context) == '3'

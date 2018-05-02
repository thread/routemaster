import datetime
from unittest import mock

import pytest
import dateutil
import freezegun
from requests.exceptions import RequestException

from routemaster import state_machine
from routemaster.feeds import Feed
from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ConstantNextState,
)
from routemaster.webhooks import WebhookResult
from routemaster.state_machine import utils
from routemaster.exit_conditions import ExitConditionProgram
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import UnknownStateMachine


def test_get_current_state(app, create_label):
    label = create_label('foo', 'test_machine', {})
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[0]
    with app.new_session():
        assert utils.get_current_state(app, label, state_machine) == state


def test_get_current_state_for_deleted_label(app, create_deleted_label):
    label = create_deleted_label('foo', 'test_machine')
    state_machine = app.config.state_machines['test_machine']
    with app.new_session():
        assert utils.get_current_state(app, label, state_machine) is None


def test_get_current_state_for_label_in_invalid_state(custom_app, create_label):
    state_to_be_removed = Gate(
        name='start',
        triggers=[],
        next_states=ConstantNextState('end'),
        exit_condition=ExitConditionProgram('false'),
    )
    end_state = Gate(
        name='end',
        triggers=[],
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
    )

    app = custom_app(state_machines={
        'test_machine': StateMachine(
            name='test_machine',
            states=[state_to_be_removed, end_state],
            feeds=[],
            webhooks=[],
        ),
    })

    label = create_label('foo', 'test_machine', {})
    state_machine = app.config.state_machines['test_machine']

    # Remove the state which we expect the label to be in from the state
    # machine; this is logically equivalent to loading a new config which does
    # not have the state
    del state_machine.states[0]

    with app.new_session():
        with pytest.raises(Exception):
            utils.get_current_state(app, label, state_machine)


def test_get_state_machine(app):
    label = LabelRef(name='foo', state_machine='test_machine')
    state_machine = app.config.state_machines['test_machine']
    assert utils.get_state_machine(app, label) == state_machine


def test_get_state_machine_not_found(app):
    label = LabelRef(name='foo', state_machine='nonexistent_machine')
    with pytest.raises(UnknownStateMachine):
        utils.get_state_machine(app, label)


def test_needs_gate_evaluation_for_metadata_change(app, create_label):
    label = create_label('foo', 'test_machine', {})
    state_machine = app.config.state_machines['test_machine']

    with app.new_session():
        current_state = utils.get_current_state(
            app,
            label,
            state_machine,
        )

        assert utils.needs_gate_evaluation_for_metadata_change(
            app,
            state_machine,
            label,
            {'foo': 'bar'},
        ) == (False, current_state)

        assert utils.needs_gate_evaluation_for_metadata_change(
            app,
            state_machine,
            label,
            {'should_progress': 'bar'},
        ) == (True, current_state)


def test_does_not_need_gate_evaluation_for_metadata_change_with_action(app, create_label, mock_webhook):
    state_machine = app.config.state_machines['test_machine']

    # Force the action to fail here so that the label is left in the action
    # state.
    with mock_webhook(WebhookResult.FAIL):
        label = create_label('foo', 'test_machine', {'should_progress': True})

    with app.new_session():
        current_state = utils.get_current_state(
            app,
            label,
            state_machine,
        )
        assert current_state.name == 'perform_action'

        assert utils.needs_gate_evaluation_for_metadata_change(
            app,
            state_machine,
            label,
            {},
        ) == (False, current_state)


@freezegun.freeze_time('2018-01-07 00:00:01')
def test_context_for_label_in_gate_created_with_correct_variables(app):
    label = LabelRef('foo', 'test_machine')
    metadata = {'should_progress': True}
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[0]
    dt = datetime.datetime.now(dateutil.tz.tzutc())
    history_entry = mock.Mock()

    with mock.patch(
        'routemaster.state_machine.utils.Context',
    ) as mock_constructor:

        utils.context_for_label(
            label,
            metadata,
            state_machine,
            state,
            history_entry,
            app.logger,
        )
        mock_constructor.assert_called_once_with(
            label=label.name,
            metadata=metadata,
            now=dt,
            feeds={'tests': Feed('http://localhost/tests', 'test_machine')},
            accessed_variables=[
                'metadata.should_progress',
                'feeds.tests.should_do_alternate_action',
            ],
            current_history_entry=history_entry,
            feed_logging_context=mock.ANY,
        )


@freezegun.freeze_time('2018-01-07 00:00:01')
def test_context_for_label_in_action_created_with_correct_variables(app):
    label = LabelRef('foo', 'test_machine')
    metadata = {'should_progress': True}
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[2]
    dt = datetime.datetime.now(dateutil.tz.tzutc())
    history_entry = mock.Mock()

    with mock.patch(
        'routemaster.state_machine.utils.Context',
    ) as mock_constructor:

        utils.context_for_label(
            label,
            metadata,
            state_machine,
            state,
            history_entry,
            app.logger,
        )
        mock_constructor.assert_called_once_with(
            label=label.name,
            metadata=metadata,
            now=dt,
            feeds={'tests': Feed('http://localhost/tests', 'test_machine')},
            accessed_variables=['feeds.tests.should_loop'],
            current_history_entry=history_entry,
            feed_logging_context=mock.ANY,
        )


def test_labels_needing_metadata_update_retry_in_gate(app, mock_test_feed, create_label, create_deleted_label, current_state):
    label_unprocessed = create_label('label_unprocessed', 'test_machine', {})
    label_processed = create_label('label_processed', 'test_machine', {})
    label_deleted = create_deleted_label('label_deleted', 'test_machine')

    test_machine = app.config.state_machines['test_machine']
    gate = test_machine.states[0]

    with mock_test_feed(), app.new_session():
        with mock.patch(
            'routemaster.context.Context._pre_warm_feeds',
            side_effect=RequestException,
        ):
            state_machine.update_metadata_for_label(
                app,
                label_unprocessed,
                {'should_progress': True},
            )

    # Both should be in the start state...
    assert current_state(label_processed) == 'start'
    assert current_state(label_unprocessed) == 'start'
    assert current_state(label_deleted) is None

    # But only label_unprocessed should be pending a metadata update
    with app.new_session():
        assert utils.labels_needing_metadata_update_retry_in_gate(
            app,
            test_machine,
            gate,
        ) == [label_unprocessed.name]


def test_labels_in_state(app, mock_test_feed, mock_webhook, create_label, create_deleted_label, current_state):
    label_in_state = create_label('label_in_state', 'test_machine', {})
    label_deleted = create_deleted_label('label_deleted', 'test_machine')

    with mock_test_feed(), mock_webhook():
        label_not_in_state = create_label(
            'label_not_in_state',
            'test_machine',
            {'should_progress': True},
        )

    test_machine = app.config.state_machines['test_machine']
    gate = test_machine.states[0]

    assert current_state(label_in_state) == 'start'
    assert current_state(label_deleted) is None
    assert current_state(label_not_in_state) == 'end'

    # But only label_unprocessed should be pending a metadata update
    with app.new_session():
        assert utils.labels_in_state(
            app,
            test_machine,
            gate,
        ) == [label_in_state.name]

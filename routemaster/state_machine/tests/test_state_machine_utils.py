import datetime

import mock
import pytest
import dateutil
import freezegun

from routemaster.feeds import Feed
from routemaster.webhooks import WebhookResult
from routemaster.state_machine import utils
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import UnknownStateMachine


def test_get_state_machine(app_config):
    label = LabelRef(name='foo', state_machine='test_machine')
    state_machine, = app_config.config.state_machines.values()
    assert utils.get_state_machine(app_config, label) == state_machine


def test_get_state_machine_not_found(app_config):
    label = LabelRef(name='foo', state_machine='nonexistent_machine')
    with pytest.raises(UnknownStateMachine):
        utils.get_state_machine(app_config, label)


def test_needs_gate_evaluation_for_metadata_change(app_config, create_label):
    label = create_label('foo', 'test_machine', {})
    state_machine, = app_config.config.state_machines.values()

    with app_config.db.begin() as conn:
        assert utils.needs_gate_evaluation_for_metadata_change(
            state_machine,
            label,
            {'foo': 'bar'},
            conn,
        ) is False
        assert utils.needs_gate_evaluation_for_metadata_change(
            state_machine,
            label,
            {'should_progress': 'bar'},
            conn,
        ) is True


def test_does_not_need_gate_evaluation_for_metadata_change_with_action(app_config, create_label, mock_webhook):
    state_machine, = app_config.config.state_machines.values()

    # Force the action to fail here so that the label is left in the action
    # state.
    with mock_webhook(WebhookResult.FAIL):
        label = create_label('foo', 'test_machine', {'should_progress': True})

    with app_config.db.begin() as conn:
        current_state = utils.get_current_state(label, state_machine, conn)
        assert current_state.name == 'perform_action'

    with app_config.db.begin() as conn:
        assert utils.needs_gate_evaluation_for_metadata_change(
            state_machine,
            label,
            {},
            conn,
        ) is False


@freezegun.freeze_time('2018-01-07 00:00:01')
def test_context_for_label_in_gate_created_with_correct_variables(app_config):
    label = LabelRef('foo', 'test_machine')
    metadata = {'should_progress': True}
    state_machine, = app_config.config.state_machines.values()
    state = state_machine.states[0]
    dt = datetime.datetime.now(dateutil.tz.tzutc())

    with mock.patch(
        'routemaster.state_machine.utils.Context',
    ) as mock_constructor:

        utils.context_for_label(label, metadata, state_machine, state)
        mock_constructor.assert_called_once_with(
            label.name,
            metadata,
            dt,
            {'tests': Feed('http://localhost/tests', 'test_machine')},
            [
                'metadata.should_progress',
                'feeds.tests.should_do_alternate_action',
            ],
        )


@freezegun.freeze_time('2018-01-07 00:00:01')
def test_context_for_label_in_action_created_with_correct_variables(app_config):
    label = LabelRef('foo', 'test_machine')
    metadata = {'should_progress': True}
    state_machine, = app_config.config.state_machines.values()
    state = state_machine.states[2]
    dt = datetime.datetime.now(dateutil.tz.tzutc())

    with mock.patch(
        'routemaster.state_machine.utils.Context',
    ) as mock_constructor:

        utils.context_for_label(label, metadata, state_machine, state)
        mock_constructor.assert_called_once_with(
            label.name,
            metadata,
            dt,
            {'tests': Feed('http://localhost/tests', 'test_machine')},
            ['feeds.tests.should_loop'],
        )

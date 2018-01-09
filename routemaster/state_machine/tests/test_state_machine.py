import mock
import pytest
from sqlalchemy import and_, select
from requests.exceptions import RequestException

from routemaster import state_machine
from routemaster.db import labels, history
from routemaster.state_machine import (
    LabelRef,
    UnknownLabel,
    UnknownStateMachine,
)


def current_state(app_config, label):
    with app_config.db.begin() as conn:
        return conn.scalar(
            select([history.c.new_state]).where(and_(
                history.c.label_name == label.name,
                history.c.label_state_machine == label.state_machine,
            )).order_by(
                history.c.created.desc(),
            ).limit(1)
        )

def metadata_triggers_processed(app_config, label):
    with app_config.db.begin() as conn:
        return conn.scalar(select([labels.c.metadata_triggers_processed]))


def test_label_get_state(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')
    with mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {'foo': 'bar'},
        )

    assert state_machine.get_label_state(app_config, label).name == 'start'


def test_label_get_state_raises_for_unknown_label(app_config):
    label = LabelRef('unknown', 'test_machine')
    with pytest.raises(UnknownLabel):
        assert state_machine.get_label_state(app_config, label)


def test_label_get_state_raises_for_unknown_state_machine(app_config):
    label = LabelRef('foo', 'unknown_machine')
    with pytest.raises(UnknownStateMachine):
        assert state_machine.get_label_state(app_config, label)


def test_state_machine_simple(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {},
        )
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'foo': 'bar'},
        )

    assert state_machine.get_label_metadata(app_config, label) == {'foo': 'bar'}


def test_update_metadata_for_label_raises_for_unknown_state_machine(app_config):
    label = LabelRef('foo', 'nonexistent_machine')
    with pytest.raises(UnknownStateMachine):
        state_machine.update_metadata_for_label(app_config, label, {})


def test_state_machine_progresses_on_update(app_config, mock_webhook, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_webhook() as webhook, mock_test_feed():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert metadata_triggers_processed(app_config, label) is True
    assert current_state(app_config, label) == 'end'


def test_state_machine_progresses_automatically(app_config, mock_webhook, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_webhook() as webhook, mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert current_state(app_config, label) == 'end'


def test_state_machine_does_not_progress_when_not_eligible(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_test_feed():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': False},
        )

    assert current_state(app_config, label) == 'start'


def test_stays_in_gate_if_gate_processing_fails(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_test_feed(), mock.patch(
        'routemaster.context.Context._pre_warm_feeds',
        side_effect=RequestException,
    ):
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )

    assert metadata_triggers_processed(app_config, label) is False
    assert current_state(app_config, label) == 'start'


def test_concurrent_metadata_update_gate_evaluations_dont_race(create_label, app_config, assert_history):
    test_machine_2 = app_config.config.state_machines['test_machine_2']
    gate_1 = test_machine_2.states[0]

    label = create_label('foo', 'test_machine_2', {})

    with mock_test_feed():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )
        assert current_state(app_config, label) == 'gate_2'

    with mock.patch(
        'routemaster.state_machine.api.needs_gate_evaluation_for_metadata_change',
        return_value=(True, gate_1),
    ):
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )

    assert_history([
        (None, 'gate_1'),
        ('gate_1', 'gate_2'),
    ])


def test_metadata_update_gate_evaluations_dont_process_subsequent_metadata_triggered_gate(create_label, app_config, assert_history):
    label = create_label('foo', 'test_machine_2', {})

    state_machine.update_metadata_for_label(
        app_config,
        label,
        {'should_progress': True},
    )

    assert current_state(app_config, label) == 'gate_2'
    assert_history([
        (None, 'gate_1'),
        ('gate_1', 'gate_2'),
        # Note: has not progressed to end because there is no on entry trigger
        # on gate 2 and we were not processing a metadata trigger on gate 2,
        # only gate 1.
    ])


def test_metadata_update_gate_evaluations_dont_race_processing_subsequent_metadata_triggered_gate(create_label, app_config, assert_history):
    test_machine_2 = app_config.config.state_machines['test_machine_2']
    gate_1 = test_machine_2.states[0]
    gate_2 = test_machine_2.states[1]

    label = create_label('foo', 'test_machine_2', {})

    with mock.patch(
        'routemaster.state_machine.api.needs_gate_evaluation_for_metadata_change',
        return_value=(True, gate_1),
    ), mock.patch(
        'routemaster.state_machine.api.get_current_state',
        return_value=gate_2,
    ):

        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )

    # We should have no history entry 1->2 (as we mocked out the current state)
    # so the state machine should have considered us up-to-date and not moved.
    assert_history([
        (None, 'gate_1'),
    ])

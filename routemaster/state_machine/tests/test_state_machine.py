from unittest import mock

import pytest
from freezegun import freeze_time
from requests.exceptions import RequestException

from routemaster import state_machine
from routemaster.db import Label, History
from routemaster.state_machine import (
    LabelRef,
    UnknownLabel,
    UnknownStateMachine,
)
from routemaster.state_machine.gates import process_gate


def current_state(app_config, label):
    with app_config.new_session():
        return app_config.session.query(
            History.new_state,
        ).filter_by(
            label_name=label.name,
            label_state_machine=label.state_machine,
        ).order_by(
            History.created.desc(),
        ).limit(1).scalar()


def metadata_triggers_processed(app_config, label):
    with app_config.new_session():
        return app_config.session.query(
            Label.metadata_triggers_processed,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()


def test_label_get_state(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')
    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {'foo': 'bar'},
        )

    with app_config.new_session():
        assert state_machine.get_label_state(app_config, label).name == 'start'


def test_label_get_state_raises_for_unknown_label(app_config):
    label = LabelRef('unknown', 'test_machine')
    with pytest.raises(UnknownLabel), app_config.new_session():
        assert state_machine.get_label_state(app_config, label)


def test_label_get_state_raises_for_unknown_state_machine(app_config):
    label = LabelRef('foo', 'unknown_machine')
    with pytest.raises(UnknownStateMachine), app_config.new_session():
        assert state_machine.get_label_state(app_config, label)


def test_state_machine_simple(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
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

    with app_config.new_session():
        assert state_machine.get_label_metadata(app_config, label) == {'foo': 'bar'}


def test_update_metadata_for_label_raises_for_unknown_state_machine(app_config):
    label = LabelRef('foo', 'nonexistent_machine')
    with pytest.raises(UnknownStateMachine), app_config.new_session():
        state_machine.update_metadata_for_label(app_config, label, {})


def test_state_machine_progresses_on_update(app_config, mock_webhook, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_webhook() as webhook, mock_test_feed(), app_config.new_session():
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

    with mock_webhook() as webhook, mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert current_state(app_config, label) == 'end'


def test_state_machine_does_not_progress_when_not_eligible(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_test_feed(), app_config.new_session():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': False},
        )

    assert current_state(app_config, label) == 'start'


def test_stays_in_gate_if_gate_processing_fails(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    assert current_state(app_config, label) == 'start'

    with mock_test_feed(), mock.patch(
        'routemaster.context.Context._pre_warm_feeds',
        side_effect=RequestException,
    ), app_config.new_session():
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

    with app_config.new_session():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )

    assert current_state(app_config, label) == 'gate_2'

    with mock.patch(
        'routemaster.state_machine.api.needs_gate_evaluation_for_metadata_change',
        return_value=(True, gate_1),
    ), app_config.new_session():
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

    with app_config.new_session():
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
    ), app_config.new_session():

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


def test_maintains_updated_field_on_label(app_config, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

        first_updated = app_config.session.query(
            Label.updated,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()

    with mock_test_feed(), app_config.new_session():
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'foo': 'bar'},
        )

        second_updated = app_config.session.query(
            Label.updated,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()

    assert second_updated > first_updated


def test_continues_after_time_since_entering_gate(app_config):
    label = LabelRef('foo', 'test_machine_timing')
    gate = app_config.config.state_machines['test_machine_timing'].states[0]

    with freeze_time('2018-01-24 12:00:00'), app_config.new_session():
        state_machine.create_label(
            app_config,
            label,
            {},
        )

    # 1 day later, not enough to progress
    with freeze_time('2018-01-25 12:00:00'), app_config.new_session():
        process_gate(
            app=app_config,
            state=gate,
            state_machine=state_machine,
            label=label,
        )

    assert current_state(app_config, label) == 'start'

    # 2 days later
    with freeze_time('2018-01-26 12:00:00'), app_config.new_session():
        process_gate(
            app=app_config,
            state=gate,
            state_machine=state_machine,
            label=label,
        )

    assert current_state(app_config, label) == 'end'


def test_delete_label(app_config, assert_history, mock_test_feed):
    label_foo = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(app_config, label_foo, {})
        state_machine.delete_label(app_config, label_foo)

    with app_config.new_session():
        _, deleted = state_machine.get_label_metadata(
            app_config,
            label_foo,
        )

        assert deleted is True

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_delete_label_only_deletes_target_label(app_config, assert_history, mock_test_feed):
    label_foo = LabelRef('foo', 'test_machine')
    label_bar = LabelRef('bar', 'test_machine')

    with mock_test_feed(), app_config.new_session():
        state_machine.create_label(app_config, label_foo, {})
        state_machine.create_label(app_config, label_bar, {})
        state_machine.delete_label(app_config, label_foo)

    with app_config.new_session():
        _, deleted_foo = state_machine.get_label_metadata(
            app_config,
            label_foo,
        )

        assert deleted_foo is True

        _, deleted_bar = state_machine.get_label_metadata(
            app_config,
            label_bar,
        )

        assert deleted_bar is False

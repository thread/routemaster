from unittest import mock

import pytest
from freezegun import freeze_time
from requests.exceptions import RequestException

from routemaster import state_machine
from routemaster.db import Label
from routemaster.state_machine import (
    LabelRef,
    DeletedLabel,
    UnknownLabel,
    UnknownStateMachine,
)
from routemaster.state_machine.gates import process_gate


def metadata_triggers_processed(app, label):
    with app.new_session():
        return app.session.query(
            Label.metadata_triggers_processed,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()


def test_label_get_state(app, mock_test_feed):
    label = LabelRef('foo', 'test_machine')
    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {'foo': 'bar'},
        )

    with app.new_session():
        assert state_machine.get_label_state(app, label).name == 'start'


def test_label_get_state_raises_for_unknown_label(app):
    label = LabelRef('unknown', 'test_machine')
    with pytest.raises(UnknownLabel), app.new_session():
        assert state_machine.get_label_state(app, label)


def test_label_get_state_raises_for_unknown_state_machine(app):
    label = LabelRef('foo', 'unknown_machine')
    with pytest.raises(UnknownStateMachine), app.new_session():
        assert state_machine.get_label_state(app, label)


def test_state_machine_simple(app, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )
        state_machine.update_metadata_for_label(
            app,
            label,
            {'foo': 'bar'},
        )

    with app.new_session():
        assert state_machine.get_label_metadata(app, label) == {'foo': 'bar'}


def test_update_metadata_for_label_raises_for_unknown_state_machine(app):
    label = LabelRef('foo', 'nonexistent_machine')
    with pytest.raises(UnknownStateMachine), app.new_session():
        state_machine.update_metadata_for_label(app, label, {})


def test_state_machine_progresses_on_update(app, mock_webhook, mock_test_feed, current_state):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )

    assert current_state(label) == 'start'

    with mock_webhook() as webhook, mock_test_feed(), app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert metadata_triggers_processed(app, label) is True
    assert current_state(label) == 'end'


def test_state_machine_progresses_automatically(app, mock_webhook, mock_test_feed, current_state):
    label = LabelRef('foo', 'test_machine')

    with mock_webhook() as webhook, mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert current_state(label) == 'end'


def test_state_machine_does_not_progress_when_not_eligible(app, mock_test_feed, current_state):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )

    assert current_state(label) == 'start'

    with mock_test_feed(), app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': False},
        )

    assert current_state(label) == 'start'


def test_stays_in_gate_if_gate_processing_fails(app, mock_test_feed, current_state):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )

    assert current_state(label) == 'start'

    with mock_test_feed(), mock.patch(
        'routemaster.context.Context._pre_warm_feeds',
        side_effect=RequestException,
    ), app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )

    assert metadata_triggers_processed(app, label) is False
    assert current_state(label) == 'start'


def test_concurrent_metadata_update_gate_evaluations_dont_race(create_label, app, assert_history, current_state):
    test_machine_2 = app.config.state_machines['test_machine_2']
    gate_1 = test_machine_2.states[0]

    label = create_label('foo', 'test_machine_2', {})

    with app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )

    assert current_state(label) == 'gate_2'

    with mock.patch(
        'routemaster.state_machine.api.needs_gate_evaluation_for_metadata_change',
        return_value=(True, gate_1),
    ), app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )

    assert_history([
        (None, 'gate_1'),
        ('gate_1', 'gate_2'),
    ])


def test_metadata_update_gate_evaluations_dont_process_subsequent_metadata_triggered_gate(create_label, app, assert_history, current_state):
    label = create_label('foo', 'test_machine_2', {})

    with app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )

    assert current_state(label) == 'gate_2'
    assert_history([
        (None, 'gate_1'),
        ('gate_1', 'gate_2'),
        # Note: has not progressed to end because there is no on entry trigger
        # on gate 2 and we were not processing a metadata trigger on gate 2,
        # only gate 1.
    ])


def test_metadata_update_gate_evaluations_dont_race_processing_subsequent_metadata_triggered_gate(create_label, app, assert_history):
    test_machine_2 = app.config.state_machines['test_machine_2']
    gate_1 = test_machine_2.states[0]
    gate_2 = test_machine_2.states[1]

    label = create_label('foo', 'test_machine_2', {})

    with mock.patch(
        'routemaster.state_machine.api.needs_gate_evaluation_for_metadata_change',
        return_value=(True, gate_1),
    ), mock.patch(
        'routemaster.state_machine.api.get_current_state',
        return_value=gate_2,
    ), app.new_session():

        state_machine.update_metadata_for_label(
            app,
            label,
            {'should_progress': True},
        )

    # We should have no history entry 1->2 (as we mocked out the current state)
    # so the state machine should have considered us up-to-date and not moved.
    assert_history([
        (None, 'gate_1'),
    ])


def test_maintains_updated_field_on_label(app, mock_test_feed):
    label = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )

        first_updated = app.session.query(
            Label.updated,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()

    with mock_test_feed(), app.new_session():
        state_machine.update_metadata_for_label(
            app,
            label,
            {'foo': 'bar'},
        )

        second_updated = app.session.query(
            Label.updated,
        ).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).scalar()

    assert second_updated > first_updated


def test_continues_after_time_since_entering_gate(app, current_state):
    label = LabelRef('foo', 'test_machine_timing')
    test_machine = app.config.state_machines['test_machine_timing']
    gate = test_machine.states[0]

    with freeze_time('2018-01-24 12:00:00'), app.new_session():
        state_machine.create_label(
            app,
            label,
            {},
        )

    # 1 day later, not enough to progress
    with freeze_time('2018-01-25 12:00:00'), app.new_session():
        process_gate(
            app=app,
            state=gate,
            state_machine=test_machine,
            label=label,
        )

    assert current_state(label) == 'start'

    # 2 days later
    with freeze_time('2018-01-26 12:00:00'), app.new_session():
        process_gate(
            app=app,
            state=gate,
            state_machine=test_machine,
            label=label,
        )

    assert current_state(label) == 'end'


def test_delete_label(app, assert_history, mock_test_feed):
    label_foo = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(app, label_foo, {})
        state_machine.delete_label(app, label_foo)

    with app.new_session():
        with pytest.raises(DeletedLabel):
            state_machine.get_label_metadata(
                app,
                label_foo,
            )

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_delete_label_idempotent(app, assert_history, mock_test_feed):
    label_foo = LabelRef('foo', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(app, label_foo, {})
        state_machine.delete_label(app, label_foo)
        state_machine.delete_label(app, label_foo)

    with app.new_session():
        with pytest.raises(DeletedLabel):
            state_machine.get_label_metadata(
                app,
                label_foo,
            )

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_delete_label_only_deletes_target_label(app, assert_history, mock_test_feed):
    label_foo = LabelRef('foo', 'test_machine')
    label_bar = LabelRef('bar', 'test_machine')

    with mock_test_feed(), app.new_session():
        state_machine.create_label(app, label_foo, {})
        state_machine.create_label(app, label_bar, {})
        state_machine.delete_label(app, label_foo)

    with app.new_session():
        with pytest.raises(DeletedLabel):
            state_machine.get_label_metadata(
                app,
                label_foo,
            )

        state_machine.get_label_metadata(
            app,
            label_bar,
        )


def test_handles_label_state_change_race_condition(app, create_deleted_label):
    test_machine = app.config.state_machines['test_machine']
    state = test_machine.states[1]

    # Create a label which is not in the expected state. Doing this and then
    # returning the affected label from the `get_labels` call is easier and
    # equivalent to having the state of the label change between the return of
    # that call and when the label is used.
    label = create_deleted_label('foo', 'test_machine')

    mock_processor = mock.Mock()
    mock_get_labels = mock.Mock(return_value=[label.name])

    with mock.patch(
        'routemaster.state_machine.api.suppress_exceptions',
    ):
        state_machine.process_cron(
            mock_processor,
            mock_get_labels,
            app,
            test_machine,
            state,
        )

    # Assert no attempt to process the label
    mock_processor.assert_not_called()

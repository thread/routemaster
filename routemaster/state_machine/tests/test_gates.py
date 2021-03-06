import pytest

from routemaster import state_machine
from routemaster.state_machine.gates import process_gate
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import DeletedLabel


def test_wont_process_deleted_label(app, create_deleted_label, assert_history):
    deleted_label = create_deleted_label('foo', 'test_machine')
    state_machine = app.config.state_machines['test_machine']
    gate = state_machine.states[0]

    with pytest.raises(DeletedLabel):
        with app.new_session():
            process_gate(
                app=app,
                state=gate,
                state_machine=state_machine,
                label=deleted_label,
            )

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_process_gate_eligible(app, mock_test_feed, assert_history):
    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            LabelRef('foo', 'test_machine'),
            {'should_progress': True},
        )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_gate_not_eligible(app, mock_test_feed, assert_history):
    with mock_test_feed(), app.new_session():
        state_machine.create_label(
            app,
            LabelRef('foo', 'test_machine'),
            {'should_progress': False},
        )

    assert_history([
        (None, 'start'),
    ])

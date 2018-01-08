import pytest

from routemaster import state_machine
from routemaster.state_machine.gates import process_gate
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import DeletedLabel


def test_wont_process_deleted_label(app_config, create_deleted_label, assert_history):
    deleted_label = create_deleted_label('foo', 'test_machine')
    state_machine, = app_config.config.state_machines.values()
    gate = state_machine.states[0]

    with pytest.raises(DeletedLabel):
        with app_config.db.begin() as conn:
            process_gate(app_config, gate, deleted_label, conn)

    assert_history(app_config, [
        (None, 'start'),
        ('start', None),
    ])


def test_process_gate_eligible(app_config, mock_test_feed, assert_history):
    with mock_test_feed():
        state_machine.create_label(
            app_config,
            LabelRef('foo', 'test_machine'),
            {'should_progress': True},
        )

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_gate_not_eligible(app_config, mock_test_feed, assert_history):
    with mock_test_feed():
        state_machine.create_label(
            app_config,
            LabelRef('foo', 'test_machine'),
            {'should_progress': False},
        )

    assert_history(app_config, [
        (None, 'start'),
    ])
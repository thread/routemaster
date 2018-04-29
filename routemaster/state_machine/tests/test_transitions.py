from unittest import mock

from routemaster.state_machine.exceptions import DeletedLabel
from routemaster.state_machine.transitions import process_transitions


def test_cannot_infinite_loop(app, create_label, set_metadata):
    label = create_label('foo', 'test_infinite_machine', {})
    set_metadata(label, {'should_progress': True})

    with app.new_session():
        process_transitions(app, label)

    app.logger.warning.assert_called_once()


def test_stops_on_delete(app, create_label, set_metadata):
    label = create_label('foo', 'test_infinite_machine', {})
    set_metadata(label, {'should_progress': True})

    with mock.patch(
        'routemaster.state_machine.transitions.process_gate',
        side_effect=[mock.DEFAULT, mock.DEFAULT, DeletedLabel],
    ) as mock_process_gate:
        with app.new_session():
            process_transitions(app, label)

    assert mock_process_gate.call_count == 3

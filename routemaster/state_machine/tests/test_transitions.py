import mock

from routemaster.state_machine.exceptions import DeletedLabel
from routemaster.state_machine.transitions import process_transitions


def test_cannot_infinite_loop(app_config, create_label, set_metadata):
    label = create_label('foo', 'test_infinite_machine', {})
    set_metadata(label, {'should_progress': True})

    with mock.patch('routemaster.state_machine.transitions.logger') as logger:
        process_transitions(app_config, label)
        logger.warn.assert_called_once()


def test_stops_on_delete(app_config, create_label, set_metadata):
    label = create_label('foo', 'test_infinite_machine', {})
    set_metadata(label, {'should_progress': True})

    with mock.patch(
        'routemaster.state_machine.transitions.process_gate',
        side_effect=[mock.DEFAULT, mock.DEFAULT, DeletedLabel],
    ) as mock_process_gate:
        process_transitions(app_config, label)

    assert mock_process_gate.call_count == 3

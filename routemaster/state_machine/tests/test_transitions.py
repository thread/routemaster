import mock

from routemaster.state_machine.transitions import process_transitions


def test_cannot_infinite_loop(app_config, create_label, set_metadata):
    label = create_label('foo', 'test_infinite_machine', {})
    set_metadata(label, {'should_progress': True})
    with mock.patch('routemaster.state_machine.transitions.logger') as logger:
        process_transitions(app_config, label)
        logger.warn.assert_called_once()

from unittest import mock

from routemaster.state_machine import process_cron


def test_handles_label_state_change_race_condition(app, create_deleted_label):
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[1]

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
        process_cron(
            mock_processor,
            mock_get_labels,
            app,
            state_machine,
            state,
        )

    # Assert no attempt to process the label
    mock_processor.assert_not_called()

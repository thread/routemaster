import pytest

from routemaster.webhooks import WebhookResult
from routemaster.state_machine import utils
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import UnknownStateMachine


def test_get_state_machine(app_config):
    label = LabelRef(name='foo', state_machine='test_machine')
    (state_machine,) = app_config.config.state_machines.values()
    assert utils.get_state_machine(app_config, label) == state_machine


def test_get_state_machine_not_found(app_config):
    label = LabelRef(name='foo', state_machine='nonexistent_machine')
    with pytest.raises(UnknownStateMachine):
        utils.get_state_machine(app_config, label)


def test_needs_gate_evaluation_for_metadata_change(app_config, create_label):
    label = LabelRef(name='foo', state_machine='test_machine')
    (state_machine,) = app_config.config.state_machines.values()
    create_label(label.name, state_machine.name, {})

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


def test_needs_gate_evaluation_for_metadata_change_with_action(app_config, create_label, mock_webhook):
    label = LabelRef('foo', 'test_machine')
    (state_machine,) = app_config.config.state_machines.values()

    with mock_webhook(WebhookResult.FAIL):
        create_label(label.name, state_machine.name, {'should_progress': True})

    with app_config.db.begin() as conn:
        assert utils.needs_gate_evaluation_for_metadata_change(
            state_machine,
            label,
            {},
            conn,
        ) is False

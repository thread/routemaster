import pytest

from sqlalchemy import and_, select

from routemaster import state_machine
from routemaster.db import history
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


def test_label_get_state(app_config):
    label = LabelRef('foo', 'test_machine')
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


def test_state_machine_simple(app_config):
    label = LabelRef('foo', 'test_machine')

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


def test_state_machine_progresses_on_update(app_config, mock_webhook):
    label = LabelRef('foo', 'test_machine')

    state_machine.create_label(
        app_config,
        label,
        {},
    )

    assert current_state(app_config, label) == 'start'

    with mock_webhook() as webhook:
        state_machine.update_metadata_for_label(
            app_config,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert current_state(app_config, label) == 'end'


def test_state_machine_progresses_automatically(app_config, mock_webhook):
    label = LabelRef('foo', 'test_machine')

    with mock_webhook() as webhook:
        state_machine.create_label(
            app_config,
            label,
            {'should_progress': True},
        )
        webhook.assert_called_once()

    assert current_state(app_config, label) == 'end'


def test_state_machine_does_not_progress_when_not_eligible(app_config):
    label = LabelRef('foo', 'test_machine')

    state_machine.create_label(
        app_config,
        label,
        {},
    )

    assert current_state(app_config, label) == 'start'

    state_machine.update_metadata_for_label(
        app_config,
        label,
        {'should_progress': False},
    )

    assert current_state(app_config, label) == 'start'

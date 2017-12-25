from sqlalchemy import and_, select

from routemaster import state_machine
from routemaster.db import History
from routemaster.state_machine import Label


def current_state(app_config, label):
    return app_config.session.query(History.new_state).filter_by(
        label_name=label.name,
        label_state_machine=label.state_machine,
    ).order_by(
        History.created.desc(),
    ).limit(1).scalar()


def test_state_machine_simple(app_config):
    label = Label('foo', 'test_machine')

    state_machine.create_label(
        app_config,
        label,
        {},
    )
    state_machine.update_context_for_label(
        app_config,
        label,
        {'foo': 'bar'},
    )

    assert state_machine.get_label_context(app_config, label) == {'foo': 'bar'}


def test_state_machine_progresses_on_update(app_config):
    label = Label('foo', 'test_machine')

    state_machine.create_label(
        app_config,
        label,
        {},
    )

    assert current_state(app_config, label) == 'start'

    state_machine.update_context_for_label(
        app_config,
        label,
        {'should_progress': True},
    )

    assert current_state(app_config, label) == 'end'

from sqlalchemy import and_, select

from routemaster import state_machine
from routemaster.db import history
from routemaster.state_machine import Label


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

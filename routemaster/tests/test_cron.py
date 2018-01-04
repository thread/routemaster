import datetime
from unittest import mock

import schedule
import freezegun

from routemaster.cron import configure_schedule
from routemaster.config import (
    Gate,
    Action,
    TimeTrigger,
    NoNextStates,
    StateMachine,
    IntervalTrigger,
)
# TODO: there must be a better way do this than importing from conftest
from routemaster.conftest import app_config
from routemaster.exit_conditions import ExitConditionProgram


def create_app(states):
    return app_config(state_machines={
        'test_machine': StateMachine('test_machine', states=states),
    })


@freezegun.freeze_time('2018-01-01 12:00')
def test_action_once_per_minute():
    action = Action('noop_action', next_states=NoNextStates(), webhook='')
    app = create_app([action])

    scheduler = schedule.Scheduler()
    with mock.patch('routemaster.cron._trigger_action') as mock_trigger_action:
        configure_schedule(scheduler, app)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 1)

    mock_trigger_action.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_trigger_action.assert_called_with(action)

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 2)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_at_fixed_time():
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(18, 30))],
    )
    app = create_app([gate])

    scheduler = schedule.Scheduler()
    with mock.patch('routemaster.cron._trigger_gate') as mock_trigger_gate:
        configure_schedule(scheduler, app)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 18, 30)

    mock_trigger_gate.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_trigger_gate.assert_called_with(gate)

    assert job.next_run == datetime.datetime(2018, 1, 2, 18, 30)

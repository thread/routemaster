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
    MetadataTrigger,
)
from routemaster.exit_conditions import ExitConditionProgram


def create_app(custom_app_config, states):
    return custom_app_config(state_machines={
        'test_machine': StateMachine(
            name='test_machine',
            states=states,
            feeds=[],
            webhooks=[],
        ),
    })


@freezegun.freeze_time('2018-01-01 12:00')
def test_action_once_per_minute(custom_app_config):
    action = Action('noop_action', next_states=NoNextStates(), webhook='')
    app = create_app(custom_app_config, [action])
    state_machine = app.config.state_machines['test_machine']

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_action_retries',
    ) as mock_retry_action:
        configure_schedule(app, scheduler, lambda: False)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 1)

    mock_retry_action.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_retry_action.assert_called_with(app, action, state_machine, mock.ANY)

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 2)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_at_fixed_time(custom_app_config):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(18, 30))],
    )
    app = create_app(custom_app_config, [gate])
    state_machine = app.config.state_machines['test_machine']

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_gate_trigger',
    ) as mock_trigger_gate:
        configure_schedule(app, scheduler, lambda: False)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 18, 30)

    mock_trigger_gate.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_trigger_gate.assert_called_with(app, gate, state_machine, mock.ANY)

    assert job.next_run == datetime.datetime(2018, 1, 2, 18, 30)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_at_interval(custom_app_config):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[IntervalTrigger(datetime.timedelta(minutes=20))],
    )
    app = create_app(custom_app_config, [gate])
    state_machine = app.config.state_machines['test_machine']

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_gate_trigger',
    ) as mock_trigger_gate:
        configure_schedule(app, scheduler, lambda: False)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 20)

    mock_trigger_gate.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_trigger_gate.assert_called_with(app, gate, state_machine, mock.ANY)

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 40)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_metadata_retry(custom_app_config):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[MetadataTrigger(metadata_path='foo.bar')],
    )
    app = create_app(custom_app_config, [gate])
    state_machine = app.config.state_machines['test_machine']

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_gate_metadata_retries',
    ) as mock_retry_metadata_updates:
        configure_schedule(app, scheduler, lambda: False)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 1)

    mock_retry_metadata_updates.assert_not_called()

    with freezegun.freeze_time(job.next_run):
        job.run()

    mock_retry_metadata_updates.assert_called_with(
        app,
        gate,
        state_machine,
        mock.ANY,
    )

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 2)


@freezegun.freeze_time('2018-01-01 12:00')
def test_cron_job_gracefully_exit_signalling(custom_app_config):
    gate = Gate(
        'gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(12, 0))],
    )
    app = create_app(custom_app_config, [gate])
    state_machine = app.config.state_machines['test_machine']

    items_to_process = ['one', 'two', 'should_not_process']

    def is_terminating():
        return len(items_to_process) == 1

    def processor(_app, _state, state_machine, should_terminate):
        for item in items_to_process:
            if should_terminate():
                break
            items_to_process.pop(0)

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_gate_trigger',
        side_effect=processor,
    ) as mock_trigger_gate:
        configure_schedule(app, scheduler, is_terminating)

    job, = scheduler.jobs
    job.run()

    mock_trigger_gate.assert_called_with(
        app,
        gate,
        state_machine,
        is_terminating,
    )

    assert items_to_process == ['should_not_process']


@freezegun.freeze_time('2018-01-01 12:00')
def test_cron_job_does_not_forward_exceptions(custom_app_config):
    gate = Gate(
        'gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(12, 0))],
    )
    app = create_app(custom_app_config, [gate])
    state_machine = app.config.state_machines['test_machine']

    scheduler = schedule.Scheduler()
    with mock.patch(
        'routemaster.cron.process_gate_trigger',
        side_effect=ValueError,
    ) as mock_trigger_gate:
        configure_schedule(app, scheduler, lambda: False)

    job, = scheduler.jobs

    # Must not error
    job.run()

    mock_trigger_gate.assert_called_with(
        app,
        gate,
        state_machine,
        mock.ANY,
    )
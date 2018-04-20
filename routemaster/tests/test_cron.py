import datetime
from unittest import mock

import schedule
import freezegun

from routemaster.cron import process_job, configure_schedule
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


def create_app(custom_app, states):
    return custom_app(state_machines={
        'test_machine': StateMachine(
            name='test_machine',
            states=states,
            feeds=[],
            webhooks=[],
        ),
    })


@freezegun.freeze_time('2018-01-01 12:00')
def test_action_once_per_minute(custom_app):
    action = Action('noop_action', next_states=NoNextStates(), webhook='')
    app = create_app(custom_app, [action])

    def processor(*, state, **kwargs):
        assert state == action
        processor.called = True

    processor.called = False

    scheduler = schedule.Scheduler()
    configure_schedule(app, scheduler, processor)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 1)
    assert processor.called is False

    with freezegun.freeze_time(job.next_run):
        job.run()

    assert processor.called is True
    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 2)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_at_fixed_time(custom_app):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(18, 30))],
    )
    app = create_app(custom_app, [gate])

    def processor(*, state, **kwargs):
        assert state == gate
        processor.called = True

    processor.called = False

    scheduler = schedule.Scheduler()
    configure_schedule(app, scheduler, processor)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 18, 30)
    assert processor.called is False

    with freezegun.freeze_time(job.next_run):
        job.run()

    assert processor.called is True
    assert job.next_run == datetime.datetime(2018, 1, 2, 18, 30)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_at_interval(custom_app):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[IntervalTrigger(datetime.timedelta(minutes=20))],
    )
    app = create_app(custom_app, [gate])

    def processor(*, state, **kwargs):
        assert state == gate
        processor.called = True

    processor.called = False

    scheduler = schedule.Scheduler()
    configure_schedule(app, scheduler, processor)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 20)
    assert processor.called is False

    with freezegun.freeze_time(job.next_run):
        job.run()

    assert processor.called is True
    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 40)


@freezegun.freeze_time('2018-01-01 12:00')
def test_gate_metadata_retry(custom_app):
    gate = Gate(
        'fixed_time_gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[MetadataTrigger(metadata_path='foo.bar')],
    )
    app = create_app(custom_app, [gate])

    def processor(*, state, **kwargs):
        assert state == gate
        processor.called = True

    processor.called = False

    scheduler = schedule.Scheduler()
    configure_schedule(app, scheduler, processor)

    assert len(scheduler.jobs) == 1, "Should have scheduled a single job"
    job, = scheduler.jobs

    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 1)
    assert processor.called is False

    with freezegun.freeze_time(job.next_run):
        job.run()

    assert processor.called is True
    assert job.next_run == datetime.datetime(2018, 1, 1, 12, 2)


@freezegun.freeze_time('2018-01-01 12:00')
def test_cron_job_gracefully_exit_signalling(custom_app):
    gate = Gate(
        'gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(12, 0))],
    )
    app = create_app(custom_app, [gate])
    state_machine = app.config.state_machines['test_machine']

    items_to_process = ['one', 'two', 'should_not_process']

    def is_terminating():
        return len(items_to_process) == 1

    def processor(app, state, state_machine, label):
        for item in items_to_process:
            items_to_process.pop(0)

    with mock.patch(
        'routemaster.state_machine.api.get_current_state',
        return_value=gate,
    ), mock.patch('routemaster.state_machine.api.lock_label'):
        process_job(
            app=app,
            is_terminating=is_terminating,
            fn=processor,
            label_provider=lambda x, y, z: items_to_process,
            state=gate,
            state_machine=state_machine,
        )

    assert items_to_process == ['should_not_process']


@freezegun.freeze_time('2018-01-01 12:00')
def test_cron_job_does_not_forward_exceptions(custom_app):
    gate = Gate(
        'gate',
        next_states=NoNextStates(),
        exit_condition=ExitConditionProgram('false'),
        triggers=[TimeTrigger(datetime.time(12, 0))],
    )
    app = create_app(custom_app, [gate])
    state_machine = app.config.state_machines['test_machine']

    def raise_value_error(*args):
        raise ValueError()

    def processor(*args, **kwargs):
        pass

    with mock.patch(
        'routemaster.state_machine.api.get_current_state',
        return_value=gate,
    ), mock.patch('routemaster.state_machine.api.lock_label'):

        process_job(
            app=app,
            is_terminating=raise_value_error,
            fn=processor,
            label_provider=lambda x, y, z: [],
            state=gate,
            state_machine=state_machine,
        )

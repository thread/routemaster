import os
import re
import datetime
import contextlib

import mock
import yaml
import pytest

from routemaster.config import (
    Gate,
    Action,
    Config,
    Webhook,
    FeedConfig,
    ConfigError,
    TimeTrigger,
    NoNextStates,
    StateMachine,
    DatabaseConfig,
    OnEntryTrigger,
    IntervalTrigger,
    MetadataTrigger,
    ConstantNextState,
    ContextNextStates,
    LoggingPluginConfig,
    ContextNextStatesOption,
    load_config,
)
from routemaster.exit_conditions import ExitConditionProgram


def reset_environment():
    return mock.patch.dict(os.environ, {}, clear=True)


def yaml_data(name: str):
    with open(f'test_data/{name}.yaml') as f:
        return yaml.load(f)


@contextlib.contextmanager
def assert_config_error(message: str):
    with pytest.raises(ConfigError) as excinfo:
        yield
    assert str(excinfo.value) == message


def test_trivial_config():
    data = yaml_data('trivial')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                feeds=[],
                webhooks=[],
                states=[
                    Gate(
                        name='start',
                        triggers=[],
                        next_states=NoNextStates(),
                        exit_condition=ExitConditionProgram('false'),
                    ),
                ]
            )
        },
        database=DatabaseConfig(
            host='localhost',
            port=5432,
            name='routemaster',
            username='routemaster',
            password='',
        ),
        logging_plugins=[],
    )
    with reset_environment():
        assert load_config(data) == expected


def test_realistic_config():
    data = yaml_data('realistic')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                feeds=[
                    FeedConfig(name='data_feed', url='http://localhost/<label>'),
                ],
                webhooks=[
                    Webhook(
                        match=re.compile('.+\\.example\\.com'),
                        headers={
                            'x-api-key': 'Rahfew7eed1ierae0moa2sho3ieB1et3ohhum0Ei',
                        },
                    ),
                ],
                states=[
                    Gate(
                        name='start',
                        triggers=[
                            TimeTrigger(time=datetime.time(18, 30)),
                            MetadataTrigger(metadata_path='foo.bar'),
                            IntervalTrigger(
                                interval=datetime.timedelta(hours=1),
                            ),
                            OnEntryTrigger(),
                        ],
                        next_states=ConstantNextState(state='stage2'),
                        exit_condition=ExitConditionProgram('true'),
                    ),
                    Gate(
                        name='stage2',
                        triggers=[],
                        next_states=ContextNextStates(
                            path='foo.bar',
                            destinations=[
                                ContextNextStatesOption(
                                    state='stage3',
                                    value='1',
                                ),
                                ContextNextStatesOption(
                                    state='stage3',
                                    value='2',
                                ),
                            ],
                            default='end',
                        ),
                        exit_condition=ExitConditionProgram(
                            'foo.bar is defined',
                        ),
                    ),
                    Action(
                        name='stage3',
                        webhook='https://localhost/hook',
                        next_states=ConstantNextState(state='end'),
                    ),
                    Gate(
                        name='end',
                        triggers=[],
                        exit_condition=ExitConditionProgram('false'),
                        next_states=NoNextStates(),
                    ),
                ],
            ),
        },
        database=DatabaseConfig(
            host='localhost',
            port=5432,
            name='routemaster',
            username='routemaster',
            password='',
        ),
        logging_plugins=[
            LoggingPluginConfig(
                dotted_path='routemaster_prometheus:PrometheusLogger',
                kwargs={'prometheus_gateway': 'localhost'},
            ),
            LoggingPluginConfig(
                dotted_path='routemaster_sentry:SentryLogger',
                kwargs={'raven_dsn': 'nai8ioca4zeeb2ahgh4V'},
            ),
        ],
    )
    with reset_environment():
        assert load_config(data) == expected


def test_raises_for_action_and_gate_state():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('action_and_gate_invalid'))


def test_raises_for_neither_action_nor_gate_state():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('not_action_or_gate_invalid'))


def test_raises_for_no_state_machines():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('no_state_machines_invalid'))


def test_raises_for_time_and_context_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('time_and_context_invalid'))


def test_raises_for_neither_time_nor_context_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('not_time_or_context_invalid'))


def test_raises_for_invalid_time_format_in_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('trigger_time_format_invalid'))


def test_raises_for_invalid_path_format_in_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('path_format_context_trigger_invalid'))


def test_raises_for_neither_constant_no_context_next_states():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('next_states_not_constant_or_context_invalid'))


def test_raises_for_invalid_interval_format_in_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('trigger_interval_format_invalid'))


def test_raises_for_nested_kwargs_in_logging_plugin_config():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('nested_kwargs_logging_plugin_invalid'))


def test_next_states_shorthand_results_in_constant_config():
    data = yaml_data('next_states_shorthand')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                feeds=[],
                webhooks=[],
                states=[
                    Gate(
                        name='start',
                        triggers=[],
                        next_states=ConstantNextState('end'),
                        exit_condition=ExitConditionProgram('false'),
                    ),
                    Gate(
                        name='end',
                        triggers=[],
                        next_states=NoNextStates(),
                        exit_condition=ExitConditionProgram('false'),
                    ),
                ]
            )
        },
        database=DatabaseConfig(
            host='localhost',
            port=5432,
            name='routemaster',
            username='routemaster',
            password='',
        ),
        logging_plugins=[],
    )
    with reset_environment():
        assert load_config(data) == expected


def test_environment_variables_override_config_file_for_database_config():
    data = yaml_data('realistic')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                feeds=[
                    FeedConfig(name='data_feed', url='http://localhost/<label>'),
                ],
                webhooks=[
                    Webhook(
                        match=re.compile('.+\\.example\\.com'),
                        headers={
                            'x-api-key': 'Rahfew7eed1ierae0moa2sho3ieB1et3ohhum0Ei',
                        },
                    ),
                ],
                states=[
                    Gate(
                        name='start',
                        triggers=[
                            TimeTrigger(time=datetime.time(18, 30)),
                            MetadataTrigger(metadata_path='foo.bar'),
                            IntervalTrigger(
                                interval=datetime.timedelta(hours=1),
                            ),
                            OnEntryTrigger(),
                        ],
                        next_states=ConstantNextState(state='stage2'),
                        exit_condition=ExitConditionProgram('true'),
                    ),
                    Gate(
                        name='stage2',
                        triggers=[],
                        next_states=ContextNextStates(
                            path='foo.bar',
                            destinations=[
                                ContextNextStatesOption(
                                    state='stage3',
                                    value='1',
                                ),
                                ContextNextStatesOption(
                                    state='stage3',
                                    value='2',
                                ),
                            ],
                            default='end',
                        ),
                        exit_condition=ExitConditionProgram(
                            'foo.bar is defined',
                        ),
                    ),
                    Action(
                        name='stage3',
                        webhook='https://localhost/hook',
                        next_states=ConstantNextState(state='end'),
                    ),
                    Gate(
                        name='end',
                        triggers=[],
                        exit_condition=ExitConditionProgram('false'),
                        next_states=NoNextStates(),
                    ),
                ],
            ),
        },
        database=DatabaseConfig(
            host='postgres.routemaster.local',
            port=9999,
            name='routemaster',
            username='username',
            password='password',
        ),
        logging_plugins=[
            LoggingPluginConfig(
                dotted_path='routemaster_prometheus:PrometheusLogger',
                kwargs={'prometheus_gateway': 'localhost'},
            ),
            LoggingPluginConfig(
                dotted_path='routemaster_sentry:SentryLogger',
                kwargs={'raven_dsn': 'nai8ioca4zeeb2ahgh4V'},
            ),
        ],
    )

    with mock.patch.dict(os.environ, {
        'DB_HOST': 'postgres.routemaster.local',
        'DB_PORT': '9999',
        'DB_NAME': 'routemaster',
        'DB_USER': 'username',
        'DB_PASS': 'password',
    }):
        assert load_config(data) == expected


def test_raises_for_unparseable_database_port_in_environment_variable():
    with mock.patch.dict(os.environ, {'DB_PORT': 'not an int'}):
        with assert_config_error("Could not parse DB_PORT as an integer: 'not an int'."):
            load_config(yaml_data('realistic'))


def test_multiple_feeds_same_name_invalid():
    with assert_config_error("FeedConfigs must have unique names at state_machines.example.feeds"):
        load_config(yaml_data('multiple_feeds_same_name_invalid'))

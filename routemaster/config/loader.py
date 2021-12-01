"""Data model for configuration format."""

import os
import re
import datetime
from typing import IO, Any, Dict, List, Union, Iterable, Optional

import yaml
import jsonschema
import pkg_resources
import jsonschema.exceptions

from routemaster.timezones import get_known_timezones
from routemaster.text_utils import join_comma_or
from routemaster.config.model import (
    Gate,
    State,
    Action,
    Config,
    Trigger,
    Webhook,
    FeedConfig,
    NextStates,
    NoNextStates,
    StateMachine,
    DatabaseConfig,
    OnEntryTrigger,
    IntervalTrigger,
    MetadataTrigger,
    ConstantNextState,
    ContextNextStates,
    SystemTimeTrigger,
    LoggingPluginConfig,
    TimezoneAwareTrigger,
    ContextNextStatesOption,
    MetadataTimezoneAwareTrigger,
)
from routemaster.exit_conditions import ExitConditionProgram
from routemaster.config.exceptions import ConfigError

Yaml = Dict[str, Any]
Path = List[str]


def yaml_load(stream: Union[IO[str], str]) -> Any:
    """Parse the first YAML document from the given stream."""
    return yaml.load(stream, getattr(yaml, 'CLoader', yaml.Loader))


def load_config(yaml: Yaml) -> Config:
    """Unpack a parsed YAML file into a `Config` object."""
    _schema_validate(yaml)

    try:
        yaml_state_machines = yaml['state_machines']
    except KeyError:  # pragma: no cover
        raise ConfigError(
            "No top-level state_machines key defined.",
        ) from None

    yaml_logging_plugins = yaml.get('plugins', {}).get('logging', [])

    return Config(
        state_machines={
            name: _load_state_machine(
                ['state_machines', name],
                name,
                yaml_state_machine,
            )
            for name, yaml_state_machine in yaml_state_machines.items()
        },
        database=load_database_config(),
        logging_plugins=_load_logging_plugins(yaml_logging_plugins),
    )


def _schema_validate(config: Yaml) -> None:
    # Load schema from package resources
    schema_raw = pkg_resources.resource_string(
        'routemaster.config',
        'schema.yaml',
    ).decode('utf-8')
    schema_yaml = yaml_load(schema_raw)

    try:
        jsonschema.validate(config, schema_yaml)
    except jsonschema.exceptions.ValidationError:
        raise ConfigError("Could not validate config file against schema.")


def load_database_config() -> DatabaseConfig:
    """Load the database config from the environment."""
    port_string = os.environ.get('DB_PORT', 5432)

    try:
        port = int(port_string)
    except ValueError:
        raise ConfigError(
            f"Could not parse DB_PORT as an integer: '{port_string}'.",
        )

    return DatabaseConfig(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=port,
        name=os.environ.get('DB_NAME', 'routemaster'),
        username=os.environ.get('DB_USER', 'routemaster'),
        password=os.environ.get('DB_PASS', ''),
    )


def _load_logging_plugins(
    yaml_logging_plugins: List[Yaml],
) -> List[LoggingPluginConfig]:
    return [
        LoggingPluginConfig(
            dotted_path=x['class'],
            kwargs=x.get('kwargs', {}),
        )
        for x in yaml_logging_plugins
    ]


def _load_state_machine(
    path: Path,
    name: str,
    yaml_state_machine: Yaml,
) -> StateMachine:
    feeds = [_load_feed_config(x) for x in yaml_state_machine.get('feeds', [])]

    if len(set(x.name for x in feeds)) < len(feeds):
        raise ConfigError(
            f"FeedConfigs must have unique names at "
            f"{'.'.join(path + ['feeds'])}",
        )

    feed_names = [x.name for x in feeds]

    return StateMachine(
        name=name,
        states=[
            _load_state(path + ['states', str(idx)], yaml_state, feed_names)
            for idx, yaml_state in enumerate(yaml_state_machine['states'])
        ],
        feeds=feeds,
        webhooks=[
            _load_webhook(x)
            for x in yaml_state_machine.get('webhooks', [])
        ],
    )


def _load_webhook(yaml: Yaml) -> Webhook:
    return Webhook(
        match=re.compile(yaml['match']),
        headers=yaml['headers'],
    )


def _load_feed_config(yaml: Yaml) -> FeedConfig:
    return FeedConfig(name=yaml['name'], url=yaml['url'])


def _load_state(path: Path, yaml_state: Yaml, feed_names: List[str]) -> State:
    if 'action' in yaml_state and 'gate' in yaml_state:  # pragma: no branch
        raise ConfigError(  # pragma: no cover
            f"State at path {'.'.join(path)} cannot be both a gate and an "
            f"action.",
        )

    if 'action' in yaml_state:
        return _load_action(path, yaml_state, feed_names)
    elif 'gate' in yaml_state:  # pragma: no branch
        return _load_gate(path, yaml_state, feed_names)
    else:
        raise ConfigError(  # pragma: no cover
            f"State at path {'.'.join(path)} must be either a gate or an "
            f"action.",
        )


def _validate_context_lookups(
    path: Path,
    lookups: Iterable[str],
    feed_names: List[str],
) -> None:
    # Changing this? Also change context lookups in
    # `routemaster.context.Context`
    VALID_TOP_LEVEL = ('feeds', 'history', 'metadata')

    for lookup in lookups:
        location, *rest = lookup.split('.')

        if location not in VALID_TOP_LEVEL:
            valid_top_level = join_comma_or(f"'{x}'" for x in VALID_TOP_LEVEL)
            raise ConfigError(
                f"Invalid context lookup at {'.'.join(path)}: key {lookup} "
                f"must start with one of {valid_top_level}.",
            )

        if location == 'feeds':
            feed_name = rest[0]
            if feed_name not in feed_names:
                valid_names = join_comma_or(f"'{x}'" for x in feed_names)
                raise ConfigError(
                    f"Invalid feed name at {'.'.join(path)}: key {lookup} "
                    f"references unknown feed '{feed_name}' (configured "
                    f"feeds are: {valid_names})",
                )


def _load_action(
    path: Path,
    yaml_state: Yaml,
    feed_names: List[str],
) -> Action:
    return Action(
        name=yaml_state['action'],
        webhook=yaml_state['webhook'],
        next_states=_load_next_states(
            path + ['next'],
            yaml_state.get('next'),
            feed_names,
        ),
    )


def _load_gate(path: Path, yaml_state: Yaml, feed_names: List[str]) -> Gate:
    yaml_exit_condition = yaml_state['exit_condition']

    if yaml_exit_condition is True:
        str_exit_condition = 'true'
    elif yaml_exit_condition is False:
        str_exit_condition = 'false'
    else:
        str_exit_condition = str(yaml_exit_condition).strip()

    exit_condition = ExitConditionProgram(str_exit_condition)
    _validate_context_lookups(
        path + ['exit_condition'],
        exit_condition.accessed_variables(),
        feed_names,
    )

    return Gate(
        name=yaml_state['gate'],
        exit_condition=exit_condition,
        triggers=[
            _load_trigger(path + ['triggers', str(idx)], yaml_trigger)
            for idx, yaml_trigger in enumerate(yaml_state.get('triggers', []))
        ],
        next_states=_load_next_states(
            path + ['next'],
            yaml_state.get('next'),
            feed_names,
        ),
    )


def _load_trigger(path: Path, yaml_trigger: Yaml) -> Trigger:
    if 'time' in yaml_trigger:
        return _load_time_trigger(path, yaml_trigger)
    elif 'metadata' in yaml_trigger:
        return _load_metadata_trigger(path, yaml_trigger)
    elif 'interval' in yaml_trigger:  # pragma: no branch
        return _load_interval_trigger(path, yaml_trigger)
    elif yaml_trigger.get('event') == 'entry':
        return OnEntryTrigger()
    else:
        raise ConfigError(  # pragma: no cover
            f"Trigger at path {'.'.join(path)} must be a time, interval, or "
            f"metadata trigger.",
        )


def _validate_known_timezone(path: Path, timezone: str) -> None:
    if timezone not in get_known_timezones():
        raise ConfigError(
            f"Timezone '{timezone}' at path {'.'.join(path)} is not a known "
            f"timezone.",
        )


def _load_time_trigger(
    path: Path,
    yaml_trigger: Yaml,
) -> Union[
    SystemTimeTrigger,
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
]:
    format_ = '%Hh%Mm'
    try:
        dt = datetime.datetime.strptime(str(yaml_trigger['time']), format_)
        trigger = dt.time()
    except ValueError:  # pragma: no cover
        raise ConfigError(
            f"Time trigger '{yaml_trigger['time']}' at path {'.'.join(path)} "
            f"does not meet expected format: {format_}.",
        ) from None

    if 'timezone' in yaml_trigger:
        timezone_path = path + ['timezone']
        timezone: str = yaml_trigger['timezone']
        if timezone.startswith('metadata.'):
            _validate_context_lookups(timezone_path, [timezone], [])
            return MetadataTimezoneAwareTrigger(
                time=trigger,
                timezone_metadata_path=timezone.split('.')[1:],
            )
        else:
            _validate_known_timezone(timezone_path, timezone)
            return TimezoneAwareTrigger(time=trigger, timezone=timezone)

    return SystemTimeTrigger(time=trigger)


RE_INTERVAL = re.compile(
    r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?'
    r'((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?',
)


def _load_interval_trigger(path: Path, yaml_trigger: Yaml) -> IntervalTrigger:
    match = RE_INTERVAL.match(yaml_trigger['interval'])
    if not match:  # pragma: no branch
        raise ConfigError(  # pragma: no cover
            f"Interval trigger '{yaml_trigger['interval']}' at path "
            f"{'.'.join(path)} does not meet expected format: 'XdYhZm'.",
        )

    parts = match.groupdict()
    interval = datetime.timedelta(**{
        x: int(y) if y is not None else 0
        for x, y in parts.items()
    })
    return IntervalTrigger(interval=interval)


RE_PATH = re.compile(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$')


def _load_metadata_trigger(path: Path, yaml_trigger: Yaml) -> MetadataTrigger:
    metadata_path = yaml_trigger['metadata']
    if not RE_PATH.match(metadata_path):  # pragma: no branch
        raise ConfigError(  # pragma: no cover
            f"Metadata trigger '{metadata_path}' at path {'.'.join(path)} is "
            f"not a valid dotted path.",
        )
    return MetadataTrigger(metadata_path=metadata_path)


def _load_next_states(
    path: Path,
    yaml_next_states: Optional[Yaml],
    feed_names: List[str],
) -> NextStates:

    if yaml_next_states is None:
        return NoNextStates()

    if isinstance(yaml_next_states, str):
        return _load_constant_next_state(path, {'state': yaml_next_states})
    if yaml_next_states['type'] == 'constant':
        return _load_constant_next_state(path, yaml_next_states)
    elif yaml_next_states['type'] == 'context':  # pragma: no branch
        return _load_context_next_states(path, yaml_next_states, feed_names)
    else:
        raise ConfigError(  # pragma: no cover
            f"Next state config at path {'.'.join(path)} must be of type "
            f"'constant' or 'context'",
        ) from None


def _load_constant_next_state(
    path: Path,
    yaml_next_states: Yaml,
) -> NextStates:
    return ConstantNextState(state=yaml_next_states['state'])


def _load_context_next_states(
    path: Path,
    yaml_next_states: Yaml,
    feed_names: List[str],
) -> NextStates:
    context_path = yaml_next_states['path']

    _validate_context_lookups(path + ['path'], (context_path,), feed_names)

    return ContextNextStates(
        path=context_path,
        destinations=[
            _load_context_next_state_option(
                path + ['destinations', str(idx)],
                yaml_option,
            )
            for idx, yaml_option in enumerate(yaml_next_states['destinations'])
        ],
        default=yaml_next_states['default'],
    )


def _load_context_next_state_option(
    path: Path,
    yaml_option: Yaml,
) -> ContextNextStatesOption:
    return ContextNextStatesOption(
        state=yaml_option['state'],
        value=yaml_option['value'],
    )

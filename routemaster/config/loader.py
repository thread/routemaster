"""Data model for configuration format."""

import re
import datetime
from typing import Any, Dict, List, Optional

import yaml
import jsonschema
import pkg_resources
import jsonschema.exceptions

from routemaster.config.model import (
    Gate,
    State,
    Action,
    Config,
    Trigger,
    NextStates,
    TimeTrigger,
    NoNextStates,
    StateMachine,
    ContextTrigger,
    DatabaseConfig,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.exit_conditions import ExitConditionProgram
from routemaster.config.exceptions import ConfigError

Yaml = Dict[str, Any]
Path = List[str]


def load_config(yaml: Yaml) -> Config:
    """Unpack a parsed YAML file into a `Config` object."""
    _schema_validate(yaml)

    try:
        yaml_state_machines = yaml['state_machines']
    except KeyError:
        raise ConfigError("No top-level state_machines key defined.") from None

    return Config(
        state_machines={
            name: _load_state_machine(
                ['state_machines', name],
                name,
                yaml_state_machine,
            )
            for name, yaml_state_machine in yaml_state_machines.items()
        },
        database=_load_database(yaml.get('database', {})),
    )


def _schema_validate(config: Yaml) -> None:
    # Load schema from package resources
    schema_raw = pkg_resources.resource_string(
        'routemaster.config',
        'schema.yaml',
    ).decode('utf-8')
    schema_yaml = yaml.load(schema_raw)

    try:
        jsonschema.validate(config, schema_yaml)
    except jsonschema.exceptions.ValidationError:
        raise ConfigError("Could not validate config file against schema.")


def _load_database(yaml: Yaml) -> DatabaseConfig:
    return DatabaseConfig(
        host=yaml.get('host', 'localhost'),
        port=yaml.get('port', 5432),
        name=yaml.get('name', 'routemaster'),
        username=yaml.get('username', ''),
        password=yaml.get('password', ''),
    )


def _load_state_machine(
    path: Path,
    name: str,
    yaml_state_machine: Yaml,
) -> StateMachine:
    return StateMachine(
        name=name,
        states=[
            _load_state(path + ['states', str(idx)], yaml_state)
            for idx, yaml_state in enumerate(yaml_state_machine['states'])
        ],
    )


def _load_state(path: Path, yaml_state: Yaml) -> State:
    if 'action' in yaml_state and 'gate' in yaml_state:
        raise ConfigError(
            f"State at path {'.'.join(path)} cannot be both a gate and an "
            f"action.",
        )

    if 'action' in yaml_state:
        return _load_action(path, yaml_state)
    elif 'gate' in yaml_state:
        return _load_gate(path, yaml_state)
    else:
        raise ConfigError(
            f"State at path {'.'.join(path)} must be either a gate or an "
            f"action.",
        )


def _load_action(path: Path, yaml_state: Yaml) -> Action:
    return Action(
        name=yaml_state['action'],
        webhook=yaml_state['webhook'],
        next_states=_load_next_states(
            path + ['next'],
            yaml_state.get('next'),
        ),
    )


def _load_gate(path: Path, yaml_state: Yaml) -> Gate:
    yaml_exit_condition = yaml_state['exit_condition']

    if yaml_exit_condition is True:
        str_exit_condition = 'true'
    elif yaml_exit_condition is False:
        str_exit_condition = 'false'
    else:
        str_exit_condition = str(yaml_exit_condition).strip()

    return Gate(
        name=yaml_state['gate'],
        exit_condition=ExitConditionProgram(str_exit_condition),
        triggers=[
            _load_trigger(path + ['triggers', str(idx)], yaml_trigger)
            for idx, yaml_trigger in enumerate(yaml_state.get('triggers', []))
        ],
        next_states=_load_next_states(path + ['next'], yaml_state.get('next')),
    )


def _load_trigger(path: Path, yaml_trigger: Yaml) -> Trigger:
    if 'time' in yaml_trigger and 'context' in yaml_trigger:
        raise ConfigError(
            f"Trigger at path {'.'.join(path)} cannot be both a time and a "
            f"context trigger."
        )

    if 'time' in yaml_trigger:
        return _load_time_trigger(path, yaml_trigger)
    elif 'context' in yaml_trigger:
        return _load_context_trigger(path, yaml_trigger)
    else:
        raise ConfigError(
            f"Trigger at path {'.'.join(path)} must be either a time or a "
            f"context trigger.",
        )


def _load_time_trigger(path: Path, yaml_trigger: Yaml) -> TimeTrigger:
    format = '%Hh%Mm'
    try:
        dt = datetime.datetime.strptime(str(yaml_trigger['time']), format)
        trigger = dt.time()
    except ValueError:
        raise ConfigError(
            f"Time trigger '{yaml_trigger['time']}' at path {'.'.join(path)} "
            f"does not meet expected format: {format}.",
        ) from None
    return TimeTrigger(time=trigger)


RE_PATH = re.compile(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$')


def _load_context_trigger(path: Path, yaml_trigger: Yaml) -> ContextTrigger:
    context_path = yaml_trigger['context']
    if not RE_PATH.match(context_path):
        raise ConfigError(
            f"Context trigger '{context_path}' at path {'.'.join(path)} is "
            f"not a valid dotted path.",
        )
    return ContextTrigger(context_path=context_path)


def _load_next_states(
    path: Path,
    yaml_next_states: Optional[Yaml],
) -> NextStates:

    if yaml_next_states is None:
        return NoNextStates()

    if yaml_next_states['type'] == 'constant':
        return _load_constant_next_state(path, yaml_next_states)
    elif yaml_next_states['type'] == 'context':
        return _load_context_next_states(path, yaml_next_states)
    else:
        raise ConfigError(
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
) -> NextStates:
    return ContextNextStates(
        path=yaml_next_states['path'],
        destinations=[
            _load_context_next_state_option(
                path + ['destinations', str(idx)],
                yaml_option,
            )
            for idx, yaml_option in enumerate(yaml_next_states['destinations'])
        ],
    )


def _load_context_next_state_option(
    path: Path,
    yaml_option: Yaml,
) -> ContextNextStatesOption:
    return ContextNextStatesOption(
        state=yaml_option['state'],
        value=yaml_option['value'],
    )

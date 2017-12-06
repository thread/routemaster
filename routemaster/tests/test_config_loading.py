import yaml

from routemaster.config import load_config, Config, StateMachine, Gate


def yaml_data(name: str):
    with open(f'test_data/{name}.yaml') as f:
        return yaml.load(f)


def test_trivial_config():
    data = yaml_data('trivial')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                states=[
                    Gate(
                        name='start',
                        triggers=[],
                        next_states=None,
                        exit_condition=None,
                    ),
                ]
            )
        }
    )
    assert load_config(data) == expected

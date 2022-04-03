import layer_loader

from routemaster.config import yaml_load, load_config
from routemaster.state_machine import nodes_for_cytoscape

TEST_MACHINE_STATE_AS_NETWORK = [
    {
        'data': {'id': 'start'},
        'classes': 'gate',
    },
    {
        'data': {
            'source': 'start',
            'target': 'perform_action',
        },
    },
    {
        'data': {
            'source': 'start',
            'target': 'perform_alternate_action',
        },
    },
    # We emit duplicate edges when the destination is duplicated; this seems to
    # be fine though.
    {
        'data': {
            'source': 'start',
            'target': 'perform_action',
        },
    },
    {
        'data': {'id': 'perform_action'},
        'classes': 'action',
    },
    {
        'data': {
            'source': 'perform_action',
            'target': 'end',
        },
    },
    {
        'data': {'id': 'perform_alternate_action'},
        'classes': 'action',
    },
    {
        'data': {
            'source': 'perform_alternate_action',
            'target': 'end',
        },
    },
    # We emit duplicate edges when the destination is duplicated; this seems to
    # be fine though.
    {
        'data': {
            'source': 'perform_alternate_action',
            'target': 'start',
        },
    },
    {
        'data': {
            'source': 'perform_alternate_action',
            'target': 'end',
        },
    },
    {
        'data': {'id': 'end'},
        'classes': 'gate',
    },
]


def test_nodes_for_cytoscape(app):
    nodes = nodes_for_cytoscape(app.config.state_machines['test_machine'])

    assert nodes == TEST_MACHINE_STATE_AS_NETWORK


def test_convert_example_to_network(app, repo_root):
    example_yaml = repo_root / 'example.yaml'

    assert example_yaml.exists(), "Example file is missing! (is this test set up correctly?)"

    example_config = load_config(
        layer_loader.load_files(
            [example_yaml],
            loader=yaml_load,
        ),
    )

    # quick check that we've loaded the config we expect
    assert list(example_config.state_machines.keys()) == ['user_lifecycle']

    nodes_for_cytoscape(example_config.state_machines['user_lifecycle'])

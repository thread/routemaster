import pytest

from routemaster.db import Label, History

INSTANCES = [
    (
        Label(state_machine='foo', name='bar'),
        "Label(state_machine='foo', name='bar')",
    ),
    (
        History(
            label_state_machine='foo',
            label_name='bar',
        ),
        "History(id=None, label_state_machine='foo', label_name='bar')",
    ),
]


@pytest.mark.parametrize('instance, representation', INSTANCES)
def test_model_is_represented_correctly(instance, representation):
    assert repr(instance) == representation

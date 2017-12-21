import pytest

from routemaster.config import MetadataTrigger

TEST_CASES = [
    ('foo', {}, False),
    ('foo', {'foo': True}, True),
    ('foo', {'foo': False}, True),
    ('foo', {'bar': True}, False),
    ('foo', {'foo': True, 'bar': True}, True),
    ('foo.bar', {'foo': {'bar': True}}, True),
    ('foo.bar', {'foo': {'bazz': True}}, False),
    ('foo.bar', {'foo': {}}, False),
    ('foo.bar', {'foo': {'bar': {'bazz': True}}}, True),
    ('foo.bar', {'foo': {'bar': {}}}, True),
]


@pytest.mark.parametrize('path, update, should_trigger', TEST_CASES)
def test_context_trigger(path, update, should_trigger):
    trigger = MetadataTrigger(metadata_path=path)
    assert trigger.should_trigger_for_update(update) == should_trigger

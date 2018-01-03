import datetime

import pytest
import dateutil

from routemaster.context import Context

UTC_NOW = datetime.datetime.now(dateutil.tz.tzutc())


def test_context_does_not_accept_naive_datetimes():
    with pytest.raises(ValueError):
        Context('label1', {}, datetime.datetime.utcnow(), None, [])


def test_finds_path_in_context():
    context = Context('label1', {'foo': {'bar': 'baz'}}, UTC_NOW, None, [])
    assert context.lookup(['metadata', 'foo', 'bar']) == 'baz'


def test_returns_none_for_unknown_prefix():
    context = Context('label1', {'foo': {'bar': 'baz'}}, UTC_NOW, None, [])
    assert context.lookup(['unknown', 'foo', 'bar']) is None


def test_returns_none_for_unknown_metadata_variable():
    context = Context('label1', {'foo': {'bar': 'baz'}}, UTC_NOW, None, [])
    assert context.lookup(['metadata', 'unknown']) is None

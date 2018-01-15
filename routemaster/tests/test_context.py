import datetime

import mock
import pytest
import httpretty

from routemaster.feeds import Feed
from routemaster.context import Context


def test_context_does_not_accept_naive_datetimes():
    with pytest.raises(ValueError):
        Context(label='label1', now=datetime.datetime.utcnow())


def test_finds_path_in_context():
    context = Context(
        label='label1',
        metadata={'foo': {'bar': 'baz'}},
        accessed_variables=['metadata.foo.bar'],
    )
    assert context.lookup(['metadata', 'foo', 'bar']) == 'baz'


def test_returns_none_for_unknown_prefix():
    context = Context(
        label='label1',
        accessed_variables=['unknown.foo.bar'],
    )
    assert context.lookup(['unknown', 'foo', 'bar']) is None


def test_returns_none_for_unknown_metadata_variable():
    context = Context(
        label='label1',
        metadata={'foo': {'bar': 'baz'}},
        accessed_variables=['metadata.unknown'],
    )
    assert context.lookup(['metadata', 'unknown']) is None


@httpretty.activate
def test_accesses_variable_in_feed():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    feed = Feed('http://example.com/<label>', 'test_machine')
    context = Context(
        label='label1',
        feeds={'example': feed},
        accessed_variables=['feeds.example.foo'],
    )
    result = context.lookup(('feeds', 'example', 'foo'))
    assert result == 'bar'


@httpretty.activate
def test_only_loads_feed_once():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    with mock.patch('requests.Response.json') as json:
        json.return_value = {'foo': 'bar'}

        feed = Feed('http://example.com/<label>', 'test_machine')
        context = Context(
            label='label1',
            metadata={},
            feeds={'example': feed},
            accessed_variables=['feeds.example.foo', 'feeds.example.baz'],
        )

        context.lookup(('feeds', 'example', 'foo'))
        context.lookup(('feeds', 'example', 'baz'))

        assert json.call_count == 1


def test_non_existent_feed_is_none():
    context = Context(
        label='label1',
        feeds={},
        accessed_variables=['feeds.foo.bar'],
    )
    assert context.lookup(['feeds', 'foo', 'bar']) is None


def test_non_existent_history_variable_is_none():
    context = Context(
        label='label1',
        accessed_variables=['history.foo'],
    )
    assert context.lookup(['history', 'foo']) is None


def test_accessing_prefix_directly_does_not_error():
    context = Context(
        label='label1',
        metadata={},
        accessed_variables=['metadata'],
    )
    assert context.lookup(['metadata']) == {}

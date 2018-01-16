import mock
import pytest
import httpretty

from routemaster.feeds import Feed, FeedNotFetched, feeds_for_state_machine
from routemaster.config import Gate, FeedConfig, NoNextStates, StateMachine
from routemaster.exit_conditions import ExitConditionProgram


def test_feeds_for_state_machine():
    state_machine = StateMachine(
        name='example',
        feeds=[
            FeedConfig(name='test_feed', url='http://localhost/<label>'),
        ],
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

    feeds = feeds_for_state_machine(state_machine)

    assert 'test_feed' in feeds
    assert feeds['test_feed'].data is None
    assert feeds['test_feed'].url == 'http://localhost/<label>'
    assert feeds['test_feed'].state_machine == 'example'


@httpretty.activate
def test_fetch_only_once():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/test_machine/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    feed = Feed('http://example.com/<state_machine>/<label>', 'test_machine')

    with mock.patch('requests.Response.json') as json:
        feed.prefetch('label1')
        feed.prefetch('label1')
        feed.prefetch('label1')

        assert json.call_count == 1


@httpretty.activate
def test_lookup():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/test_machine/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    feed = Feed('http://example.com/<state_machine>/<label>', 'test_machine')
    feed.prefetch('label1')

    assert feed.lookup(('foo',)) == 'bar'


def test_lookup_fails_on_unfetched_feed():
    feed = Feed('http://example.com/<state_machine>/<label>', 'test_machine')
    with pytest.raises(FeedNotFetched):
        feed.lookup(('foo',))


def test_equality():
    assert Feed('a', 'b') == Feed('a', 'b')
    assert Feed('a', 'b') != 'not a feed'
    assert Feed('a', 'b') != Feed('a', 'c')
    f1 = Feed('a', 'b')
    f1.data = {'foo': 'bar'}
    f2 = Feed('a', 'b')
    assert f1 == f2

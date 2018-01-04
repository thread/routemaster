import mock
import pytest
import httpretty

from routemaster.feeds import Feed, FeedNotFetched, feeds_for_state_machine
from routemaster.config import Feed as FeedConfig
from routemaster.config import Gate, NoNextStates, StateMachine
from routemaster.exit_conditions import ExitConditionProgram


def test_feeds_for_state_machine():
    state_machine = StateMachine(
        name='example',
        feeds=[
            FeedConfig(name='test_feed', url='http://localhost/<label>'),
        ],
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


@httpretty.activate
def test_fetch_only_once():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    feed = Feed('http://example.com/<label>')

    with mock.patch('requests.Response.json') as json:
        feed.fetch('label1')
        feed.fetch('label1')
        feed.fetch('label1')

        assert json.call_count == 1


@httpretty.activate
def test_lookup():
    httpretty.register_uri(
        httpretty.GET,
        'http://example.com/label1',
        body='{"foo": "bar"}',
        content_type='application/json',
    )

    feed = Feed('http://example.com/<label>')
    feed.fetch('label1')

    assert feed.lookup(('foo',)) == 'bar'


def test_lookup_fails_on_unfetched_feed():
    feed = Feed('http://example.com/<label>')
    with pytest.raises(FeedNotFetched):
        feed.lookup(('foo',))

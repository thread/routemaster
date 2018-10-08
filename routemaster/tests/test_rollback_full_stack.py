import contextlib

import pytest

from routemaster.server import server
from routemaster.state_machine import (
    LabelRef,
    UnknownLabel,
    create_label,
    get_label_metadata,
)


class BrokenRouteError(Exception):
    pass


@server.route('/tests_broken', methods=['GET'])
def broken_route():
    create_label(
        server.config.app,
        LabelRef('foo', 'test_machine'),
        metadata={},
    )
    raise BrokenRouteError("Route broken for test purposes")


def test_full_stack_rolls_back_on_uncaught_exceptions(app, client):
    with contextlib.suppress(BrokenRouteError):
        client.get('/tests_broken')

    with app.new_session():
        with pytest.raises(UnknownLabel):
            get_label_metadata(app, LabelRef('foo', 'test_machine'))

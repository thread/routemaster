import pytest

from routemaster.db import Label


def test_app_cannot_rollback_in_no_session(app):
    with pytest.raises(RuntimeError):
        app.set_rollback()


def test_explicit_rollback(app):
    with app.new_session():
        app.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))
        assert app.session.query(Label).count() == 1
        app.set_rollback()

    with app.new_session():
        assert app.session.query(Label).count() == 0


def test_unhandled_exceptions_rollback(app):
    with pytest.raises(RuntimeError):
        with app.new_session():
            app.session.add(Label(
                name='foo',
                state_machine='test_machine',
                metadata={},
            ))
            assert app.session.query(Label).count() == 1
            raise RuntimeError()

    with app.new_session():
        assert app.session.query(Label).count() == 0


def test_app_caches_webhook_runners(app):
    state_machine = app.config.state_machines['test_machine']
    test_runner_1 = app.get_webhook_runner(state_machine)
    test_runner_2 = app.get_webhook_runner(state_machine)
    assert test_runner_1 is test_runner_2


def test_no_session_when_not_in_transaction(app):
    with pytest.raises(RuntimeError):
        app.session


def test_cannot_nest_sessions(app):
    with app.new_session():
        with pytest.raises(RuntimeError):
            with app.new_session():
                pass

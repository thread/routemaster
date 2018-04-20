import pytest

from routemaster.db import Label


def test_app_cannot_rollback_in_no_session(app_config):
    with pytest.raises(RuntimeError):
        app_config.set_rollback()


def test_explicit_rollback(app_config):
    with app_config.new_session():
        app_config.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))
        assert app_config.session.query(Label).count() == 1
        app_config.set_rollback()

    with app_config.new_session():
        assert app_config.session.query(Label).count() == 0


def test_unhandled_exceptions_rollback(app_config):
    with pytest.raises(RuntimeError):
        with app_config.new_session():
            app_config.session.add(Label(
                name='foo',
                state_machine='test_machine',
                metadata={},
            ))
            assert app_config.session.query(Label).count() == 1
            raise RuntimeError()

    with app_config.new_session():
        assert app_config.session.query(Label).count() == 0


def test_app_caches_webhook_runners(app_config):
    state_machine = app_config.config.state_machines['test_machine']
    test_runner_1 = app_config.get_webhook_runner(state_machine)
    test_runner_2 = app_config.get_webhook_runner(state_machine)
    assert test_runner_1 is test_runner_2


def test_no_session_when_not_in_transaction(app_config):
    with pytest.raises(RuntimeError):
        app_config.session

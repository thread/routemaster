import pytest
from logger_plugin import TestLogger as _TestLogger  # So pytest doesn't run it

from routemaster.config import LoggingPluginConfig
from routemaster.logging import (
    BaseLogger,
    PluginConfigurationException,
    register_loggers,
)


def test_loads_plugins(custom_app):
    kwargs = {'foo': 'bar'}

    app = custom_app(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:TestLogger',
            kwargs=kwargs,
        ),
    ])

    loggers = register_loggers(app.config)

    assert len(loggers) == 1
    assert isinstance(loggers[0], _TestLogger)
    assert loggers[0].config == app.config
    assert loggers[0].kwargs == kwargs


def test_loads_plugin_from_callable(custom_app):
    app = custom_app(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:dynamic_logger',
            kwargs={},
        ),
    ])

    loggers = register_loggers(app.config)

    assert len(loggers) == 1
    assert isinstance(loggers[0], BaseLogger)
    assert loggers[0].config == app.config


def test_raises_for_invalid_plugin_base_class(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='logger_plugin:InvalidLogger',
                kwargs={},
            ),
        ])


def test_raises_for_plugin_with_invalid_constructor(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='logger_plugin:NoArgsLogger',
                kwargs={},
            ),
        ])


def test_raises_for_plugin_not_on_pythonpath(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='non_existent:DoesNotExistLogger',
                kwargs={},
            ),
        ])


def test_raises_for_plugin_in_invalid_format(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='logger_plugin.TestLogger',
                kwargs={},
            ),
        ])


def test_raises_for_plugin_non_existent_class(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='logger_plugin:DoesNotExistLogger',
                kwargs={},
            ),
        ])


def test_raises_for_not_callable_value(custom_app):
    with pytest.raises(PluginConfigurationException):
        custom_app(logging_plugins=[
            LoggingPluginConfig(
                dotted_path='logger_plugin:NOT_CALLABLE',
                kwargs={},
            ),
        ])

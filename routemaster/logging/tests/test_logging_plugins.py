import pytest
from logger_plugin import TestLogger as _TestLogger  # So pytest doesn't run it

from routemaster.config import LoggingPluginConfig
from routemaster.logging import (
    BaseLogger,
    PluginConfigurationException,
    register_loggers,
)


def test_loads_plugins(custom_app_config):
    kwargs = {'foo': 'bar'}

    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:TestLogger',
            kwargs=kwargs,
        ),
    ])

    loggers = register_loggers(app_config.config)

    assert len(loggers) == 1
    assert isinstance(loggers[0], _TestLogger)
    assert loggers[0].config == app_config.config
    assert loggers[0].kwargs == kwargs


def test_loads_plugin_from_callable(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:dynamic_logger',
            kwargs={},
        ),
    ])

    loggers = register_loggers(app_config.config)

    assert len(loggers) == 1
    assert isinstance(loggers[0], BaseLogger)
    assert loggers[0].config == app_config.config


def test_raises_for_invalid_plugin_base_class(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:InvalidLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)


def test_raises_for_plugin_with_invalid_constructor(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:NoArgsLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)


def test_raises_for_plugin_not_on_pythonpath(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='non_existent:DoesNotExistLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)


def test_raises_for_plugin_in_invalid_format(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin.TestLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)


def test_raises_for_plugin_non_existent_class(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:DoesNotExistLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)


def test_raises_for_not_callable_value(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin:NOT_CALLABLE',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)
